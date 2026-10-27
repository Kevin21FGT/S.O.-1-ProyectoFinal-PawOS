#!/usr/bin/env python3
"""
parche-aprobar-solicitudes.py

Pantalla del PERSONAL para resolver las solicitudes de adopcion que los
clientes mandan desde el Portal de Clientes. NO quita ni cambia nada
existente (Registrar adopcion sigue igual):

  - db.h / db.c   : struct SolicitudInfo, solicitud_listar_todas() y
                    solicitud_resolver() (aprobar o rechazar; aprobar
                    pone la mascota en "en_proceso", todo en UNA
                    transaccion).
  - main_gtk.c    : boton "Solicitudes del Portal" en Control de
                    Adopciones. Admin, Veterinario y Recepcionista
                    aprueban/rechazan; Voluntario solo consulta.

Flujo: Portal (Pendiente) -> personal Aprueba (mascota en_proceso, ya no
sale en el catalogo) -> al entregar la mascota se usa "Registrar
adopcion" (como siempre), que la marca adoptada.

Uso (parado en la raiz del repo):
    python3 parche-aprobar-solicitudes.py
    make gui
"""

import shutil
import sys

DB_H = "src/db/db.h"
DB_C = "src/db/db.c"
GTK_C = "src/main_gtk.c"

# ------------------------------------------------------------------ db.h
ANCLA_H1 = r"""} SolicitudAdopcion;"""
NUEVO_H1 = r"""} SolicitudAdopcion;

/* Solicitud con los nombres ya resueltos (mascota y cliente), para la
 * pantalla del personal. */
typedef struct {
    int  id;
    int  mascota_id;
    char mascota_nombre[64];
    int  cliente_id;
    char cliente_nombre[64];
    char cliente_correo[128];
    char cliente_telefono[32];
    char fecha[16];
    char estado[20];     /* Pendiente | Aprobada | Rechazada */
    char mensaje[501];
} SolicitudInfo;"""

ANCLA_H2 = r"""int  solicitud_existe_activa(int mascota_id, int cliente_id); /* 1 si, 0 no, -1 error */"""
NUEVO_H2 = r"""int  solicitud_existe_activa(int mascota_id, int cliente_id); /* 1 si, 0 no, -1 error */
int  solicitud_listar_todas(SolicitudInfo **out, int *n); /* pendientes primero; liberar con free() */
int  solicitud_resolver(int id, int mascota_id, int aprobar); /* 1 aprueba (mascota -> en_proceso), 0 rechaza; 0 = ok */"""

# ------------------------------------------------------------------ db.c
ANCLA_C = r"""int mascota_listar_disponibles(Mascota **out, int *n) {"""
NUEVO_C = r"""/* Todas las solicitudes de adopcion con nombre de mascota y de cliente
 * (las Pendientes primero, luego las demas, la mas reciente arriba). */
int solicitud_listar_todas(SolicitudInfo **out, int *n) {
    *out = NULL;
    *n = 0;
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql =
        "SELECT s.id, s.mascota_id, ISNULL(m.nombre,'(eliminada)'), s.cliente_id, "
        "ISNULL(c.nombre,'(sin nombre)'), ISNULL(c.correo,''), ISNULL(c.telefono,''), "
        "s.fecha, s.estado, ISNULL(s.mensaje,'') "
        "FROM solicitudes_adopcion s "
        "LEFT JOIN mascotas m ON m.id = s.mascota_id "
        "LEFT JOIN clientes c ON c.id = s.cliente_id "
        "ORDER BY CASE WHEN s.estado='Pendiente' THEN 0 ELSE 1 END, s.id DESC;";
    if (!SQL_SUCCEEDED(SQLExecDirect(hstmt, (SQLCHAR *)sql, SQL_NTS))) {
        SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
        api_desconectar(henv, hdbc);
        return -1;
    }
    SolicitudInfo *lista = NULL;
    int cuenta = 0, capacidad = 0;
    while (SQL_SUCCEEDED(SQLFetch(hstmt))) {
        SolicitudInfo s;
        memset(&s, 0, sizeof(s));
        SQLINTEGER v_id = 0, v_mid = 0, v_cid = 0;
        SQLLEN ind = 0;
        SQLGetData(hstmt, 1, SQL_C_SLONG, &v_id, 0, &ind);
        SQLGetData(hstmt, 2, SQL_C_SLONG, &v_mid, 0, &ind);
        SQLGetData(hstmt, 3, SQL_C_CHAR, s.mascota_nombre, sizeof(s.mascota_nombre), &ind);
        SQLGetData(hstmt, 4, SQL_C_SLONG, &v_cid, 0, &ind);
        SQLGetData(hstmt, 5, SQL_C_CHAR, s.cliente_nombre, sizeof(s.cliente_nombre), &ind);
        SQLGetData(hstmt, 6, SQL_C_CHAR, s.cliente_correo, sizeof(s.cliente_correo), &ind);
        SQLGetData(hstmt, 7, SQL_C_CHAR, s.cliente_telefono, sizeof(s.cliente_telefono), &ind);
        SQLGetData(hstmt, 8, SQL_C_CHAR, s.fecha, sizeof(s.fecha), &ind);
        SQLGetData(hstmt, 9, SQL_C_CHAR, s.estado, sizeof(s.estado), &ind);
        SQLGetData(hstmt, 10, SQL_C_CHAR, s.mensaje, sizeof(s.mensaje), &ind);
        s.id = (int)v_id;
        s.mascota_id = (int)v_mid;
        s.cliente_id = (int)v_cid;
        if (cuenta >= capacidad) {
            capacidad = capacidad ? capacidad * 2 : 8;
            SolicitudInfo *nueva = realloc(lista, (size_t)capacidad * sizeof(SolicitudInfo));
            if (!nueva) break;
            lista = nueva;
        }
        lista[cuenta++] = s;
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    *out = lista;
    *n = cuenta;
    return 0;
}

/* Resuelve una solicitud PENDIENTE. aprobar=1: la marca Aprobada y pone
 * la mascota en "en_proceso" (solo si estaba "disponible"); aprobar=0: la
 * marca Rechazada. Una sola transaccion: si algo falla no cambia nada.
 * 0 = ok, -1 = error o la solicitud/mascota ya habia cambiado. */
int solicitud_resolver(int id, int mascota_id, int aprobar) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLSetConnectAttr(hdbc, SQL_ATTR_AUTOCOMMIT, (SQLPOINTER)SQL_AUTOCOMMIT_OFF, 0);
    int ok = -1;

    SQLHSTMT h1;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &h1) == SQL_SUCCESS) {
        SQLPrepare(h1, (SQLCHAR *)
            "UPDATE solicitudes_adopcion SET estado=? WHERE id=? AND estado='Pendiente';", SQL_NTS);
        const char *nuevo = aprobar ? "Aprobada" : "Rechazada";
        SQLLEN len_estado = SQL_NTS;
        SQLINTEGER id_val = id;
        SQLBindParameter(h1, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 20, 0, (SQLPOINTER)nuevo, 0, &len_estado);
        SQLBindParameter(h1, 2, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_val, 0, NULL);
        SQLRETURN r = SQLExecute(h1);
        SQLLEN filas = 0;
        if (SQL_SUCCEEDED(r)) SQLRowCount(h1, &filas);
        SQLFreeHandle(SQL_HANDLE_STMT, h1);

        if (SQL_SUCCEEDED(r) && filas == 1) {
            if (!aprobar) {
                ok = 0;
            } else {
                SQLHSTMT h2;
                if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &h2) == SQL_SUCCESS) {
                    SQLPrepare(h2, (SQLCHAR *)
                        "UPDATE mascotas SET estado='en_proceso' WHERE id=? AND estado='disponible';", SQL_NTS);
                    SQLINTEGER mid_val = mascota_id;
                    SQLBindParameter(h2, 1, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &mid_val, 0, NULL);
                    SQLRETURN r2 = SQLExecute(h2);
                    SQLLEN filas2 = 0;
                    if (SQL_SUCCEEDED(r2)) SQLRowCount(h2, &filas2);
                    SQLFreeHandle(SQL_HANDLE_STMT, h2);
                    if (SQL_SUCCEEDED(r2) && filas2 == 1) ok = 0;
                }
            }
        }
    }

    SQLEndTran(SQL_HANDLE_DBC, hdbc, ok == 0 ? SQL_COMMIT : SQL_ROLLBACK);
    SQLSetConnectAttr(hdbc, SQL_ATTR_AUTOCOMMIT, (SQLPOINTER)SQL_AUTOCOMMIT_ON, 0);
    api_desconectar(henv, hdbc);
    return ok;
}

int mascota_listar_disponibles(Mascota **out, int *n) {"""

# --------------------------------------------------------------- main_gtk.c
ANCLA_G1 = r"""static void abrir_pantalla_adopciones(GtkWidget *area_dinamica, GtkWidget *ventana_principal, Rol rol) {"""
NUEVO_G1 = r"""/* ---------- Solicitudes de adopcion del Portal de Clientes ----------
 * El personal ve las solicitudes que mandan los clientes. Admin,
 * Veterinario y Recepcionista las aprueban o rechazan; el Voluntario
 * solo las consulta. Aprobar deja la mascota "en_proceso" (ya no sale
 * en el catalogo del Portal); la entrega final sigue siendo "Registrar
 * adopcion", que no cambio. */

enum {
    COL_S_ID = 0,
    COL_S_MASCOTA_ID,
    COL_S_MASCOTA,
    COL_S_CLIENTE,
    COL_S_CONTACTO,
    COL_S_FECHA,
    COL_S_ESTADO,
    COL_S_MENSAJE,
    N_COL_SOLICITUDES
};

typedef struct {
    GtkWidget    *dialogo;
    GtkWidget    *treeview;
    GtkListStore *store;
    GtkWidget    *chk_pendientes;
} ContextoSolicitudes;

static void cargar_solicitudes_portal(ContextoSolicitudes *sc) {
    gtk_list_store_clear(sc->store);
    SolicitudInfo *lista = NULL;
    int n = 0;
    if (solicitud_listar_todas(&lista, &n) != 0) {
        mostrar_mensaje(GTK_WINDOW(sc->dialogo), "No se pudieron leer las solicitudes.", TRUE);
        return;
    }
    gboolean solo_pendientes = gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(sc->chk_pendientes));
    for (int i = 0; i < n; i++) {
        if (solo_pendientes && strcmp(lista[i].estado, "Pendiente") != 0) continue;
        char contacto[200];
        snprintf(contacto, sizeof(contacto), "%s  %s", lista[i].cliente_correo, lista[i].cliente_telefono);
        GtkTreeIter iter;
        gtk_list_store_append(sc->store, &iter);
        gtk_list_store_set(sc->store, &iter,
            COL_S_ID, lista[i].id,
            COL_S_MASCOTA_ID, lista[i].mascota_id,
            COL_S_MASCOTA, lista[i].mascota_nombre,
            COL_S_CLIENTE, lista[i].cliente_nombre,
            COL_S_CONTACTO, contacto,
            COL_S_FECHA, lista[i].fecha,
            COL_S_ESTADO, lista[i].estado,
            COL_S_MENSAJE, lista[i].mensaje,
            -1);
    }
    free(lista);
}

static void on_filtro_solicitudes_toggled(GtkToggleButton *boton, gpointer datos) {
    (void)boton;
    cargar_solicitudes_portal((ContextoSolicitudes *)datos);
}

static void resolver_solicitud_ui(ContextoSolicitudes *sc, int aprobar) {
    GtkTreeSelection *sel = gtk_tree_view_get_selection(GTK_TREE_VIEW(sc->treeview));
    GtkTreeModel *modelo;
    GtkTreeIter iter;
    if (!gtk_tree_selection_get_selected(sel, &modelo, &iter)) {
        mostrar_mensaje(GTK_WINDOW(sc->dialogo), "Selecciona primero una solicitud de la lista.", TRUE);
        return;
    }
    gint sid = 0, mid = 0;
    gchar *estado = NULL, *nom_mascota = NULL, *nom_cliente = NULL;
    gtk_tree_model_get(modelo, &iter,
        COL_S_ID, &sid, COL_S_MASCOTA_ID, &mid,
        COL_S_ESTADO, &estado, COL_S_MASCOTA, &nom_mascota, COL_S_CLIENTE, &nom_cliente, -1);

    do {
        if (!estado || strcmp(estado, "Pendiente") != 0) {
            mostrar_mensaje(GTK_WINDOW(sc->dialogo), "Esa solicitud ya fue resuelta.", TRUE);
            break;
        }
        if (aprobar) {
            Mascota m;
            if (mascota_buscar_por_id(mid, &m) != 0) {
                mostrar_mensaje(GTK_WINDOW(sc->dialogo), "La mascota de esta solicitud ya no existe.", TRUE);
                break;
            }
            if (strcmp(m.estado, "disponible") != 0) {
                gchar *txt = g_strdup_printf(
                    "No se puede aprobar: %s esta en estado \"%s\".\nSolo se aprueba una mascota disponible.",
                    nom_mascota, m.estado);
                mostrar_mensaje(GTK_WINDOW(sc->dialogo), txt, TRUE);
                g_free(txt);
                break;
            }
        }
        gchar *pregunta = aprobar
            ? g_strdup_printf("Aprobar la solicitud de %s para adoptar a %s?", nom_cliente, nom_mascota)
            : g_strdup_printf("Rechazar la solicitud de %s para adoptar a %s?", nom_cliente, nom_mascota);
        GtkWidget *confirmar = gtk_message_dialog_new(
            GTK_WINDOW(sc->dialogo), GTK_DIALOG_MODAL, GTK_MESSAGE_QUESTION,
            GTK_BUTTONS_YES_NO, "%s", pregunta);
        g_free(pregunta);
        gint respuesta = gtk_dialog_run(GTK_DIALOG(confirmar));
        gtk_widget_destroy(confirmar);
        if (respuesta != GTK_RESPONSE_YES) break;

        if (solicitud_resolver(sid, mid, aprobar) == 0) {
            cargar_solicitudes_portal(sc);
            mostrar_mensaje(GTK_WINDOW(sc->dialogo),
                aprobar
                    ? "Solicitud aprobada. La mascota quedo \"en proceso\".\nCuando se entregue, usa Registrar adopcion."
                    : "Solicitud rechazada.",
                FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(sc->dialogo),
                "No se pudo resolver la solicitud (puede que ya haya cambiado). Actualiza la lista.", TRUE);
        }
    } while (0);

    g_free(estado);
    g_free(nom_mascota);
    g_free(nom_cliente);
}

static void on_solicitudes_portal_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoAdopciones *ctx = (ContextoAdopciones *)datos;
    gboolean puede_resolver = (ctx->rol == ROL_ADMIN || ctx->rol == ROL_VETERINARIO ||
                               ctx->rol == ROL_RECEPCIONISTA);

    ContextoSolicitudes sc;
    memset(&sc, 0, sizeof(sc));
    sc.dialogo = gtk_dialog_new_with_buttons(
        "Solicitudes de adopcion del Portal", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        NULL, NULL);
    gtk_window_set_default_size(GTK_WINDOW(sc.dialogo), 920, 420);
    if (puede_resolver) {
        gtk_dialog_add_button(GTK_DIALOG(sc.dialogo), "Aprobar", 1);
        gtk_dialog_add_button(GTK_DIALOG(sc.dialogo), "Rechazar", 2);
    }
    gtk_dialog_add_button(GTK_DIALOG(sc.dialogo), "Cerrar", GTK_RESPONSE_CLOSE);

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(sc.dialogo));
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 12);

    sc.chk_pendientes = gtk_check_button_new_with_label("Mostrar solo pendientes");
    gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(sc.chk_pendientes), TRUE);
    gtk_box_pack_start(GTK_BOX(caja), sc.chk_pendientes, FALSE, FALSE, 0);

    if (!puede_resolver) {
        GtkWidget *aviso = gtk_label_new("Solo consulta: aprobar o rechazar requiere rol Admin, Veterinario o Recepcionista.");
        gtk_widget_set_halign(aviso, GTK_ALIGN_START);
        gtk_box_pack_start(GTK_BOX(caja), aviso, FALSE, FALSE, 0);
    }

    sc.store = gtk_list_store_new(N_COL_SOLICITUDES,
        G_TYPE_INT, G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING,
        G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    sc.treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(sc.store));
    g_object_unref(sc.store);

    const char *encabezados[N_COL_SOLICITUDES] = {
        "ID", "ID Mascota", "Mascota", "Cliente", "Contacto", "Fecha", "Estado", "Mensaje"};
    for (int i = 0; i < N_COL_SOLICITUDES; i++) {
        GtkCellRenderer *render = gtk_cell_renderer_text_new();
        GtkTreeViewColumn *col = gtk_tree_view_column_new_with_attributes(
            encabezados[i], render, "text", i, NULL);
        gtk_tree_view_column_set_resizable(col, TRUE);
        gtk_tree_view_append_column(GTK_TREE_VIEW(sc.treeview), col);
    }
    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), sc.treeview);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);
    gtk_container_add(GTK_CONTAINER(area), caja);

    g_signal_connect(sc.chk_pendientes, "toggled", G_CALLBACK(on_filtro_solicitudes_toggled), &sc);
    cargar_solicitudes_portal(&sc);
    mostrar_con_fundido(sc.dialogo);

    int resp;
    while ((resp = gtk_dialog_run(GTK_DIALOG(sc.dialogo))) == 1 || resp == 2)
        resolver_solicitud_ui(&sc, resp == 1);
    gtk_widget_destroy(sc.dialogo);
}

static void abrir_pantalla_adopciones(GtkWidget *area_dinamica, GtkWidget *ventana_principal, Rol rol) {"""

ANCLA_G2 = r"""    GtkWidget *btn_registrar = gtk_button_new_with_label("Registrar adopcion");
    GtkWidget *btn_cerrar    = gtk_button_new_with_label("Cerrar");"""
NUEVO_G2 = r"""    GtkWidget *btn_solicitudes = gtk_button_new_with_label("Solicitudes del Portal");
    GtkWidget *btn_registrar = gtk_button_new_with_label("Registrar adopcion");
    GtkWidget *btn_cerrar    = gtk_button_new_with_label("Cerrar");"""

ANCLA_G3 = r"""    gtk_box_pack_start(GTK_BOX(fila_botones), btn_registrar, FALSE, FALSE, 0);
    gtk_box_pack_end(GTK_BOX(fila_botones), btn_cerrar, FALSE, FALSE, 0);

    g_signal_connect(btn_refrescar, "clicked", G_CALLBACK(on_refrescar_adopciones_clicked), ctx);"""
NUEVO_G3 = r"""    gtk_box_pack_start(GTK_BOX(fila_botones), btn_solicitudes, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_registrar, FALSE, FALSE, 0);
    gtk_box_pack_end(GTK_BOX(fila_botones), btn_cerrar, FALSE, FALSE, 0);

    g_signal_connect(btn_solicitudes, "clicked", G_CALLBACK(on_solicitudes_portal_clicked), ctx);
    g_signal_connect(btn_refrescar, "clicked", G_CALLBACK(on_refrescar_adopciones_clicked), ctx);"""

CAMBIOS = [
    (DB_H, ANCLA_H1, NUEVO_H1, "struct SolicitudAdopcion"),
    (DB_H, ANCLA_H2, NUEVO_H2, "prototipo solicitud_existe_activa"),
    (DB_C, ANCLA_C, NUEVO_C, "mascota_listar_disponibles en db.c"),
    (GTK_C, ANCLA_G1, NUEVO_G1, "abrir_pantalla_adopciones"),
    (GTK_C, ANCLA_G2, NUEVO_G2, "botones de Control de Adopciones"),
    (GTK_C, ANCLA_G3, NUEVO_G3, "pack/signal de Control de Adopciones"),
]


def main():
    contenidos = {}
    for ruta in (DB_H, DB_C, GTK_C):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenidos[ruta] = f.read()
        except FileNotFoundError:
            print(f"ERROR: no se encontro {ruta}. Corre esto desde la raiz del repo.")
            sys.exit(1)

    if "solicitud_listar_todas" in contenidos[DB_H]:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ruta, ancla, _nuevo, nombre in CAMBIOS:
        n = contenidos[ruta].count(ancla)
        if n != 1:
            print(f"ERROR: en {ruta}, '{nombre}' aparece {n} veces (debe ser 1).")
            print("       No se cambio nada.")
            sys.exit(1)

    for ruta in (DB_H, DB_C, GTK_C):
        shutil.copy(ruta, ruta + ".bak_aprobar_solicitudes")
        print(f"Backup: {ruta}.bak_aprobar_solicitudes")

    for ruta, ancla, nuevo, _nombre in CAMBIOS:
        contenidos[ruta] = contenidos[ruta].replace(ancla, nuevo, 1)

    for ruta in (DB_H, DB_C, GTK_C):
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenidos[ruta])
        print(f"{ruta} parchado OK.")

    print("")
    print("Listo. Compila:  make gui   y abre ./pawos-refugio-gui")
    print("Control de Adopciones -> boton 'Solicitudes del Portal'.")


if __name__ == "__main__":
    main()
