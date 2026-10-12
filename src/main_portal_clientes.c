/*
 * main_portal_clientes.c - PawOS Portal de Clientes
 *
 * App grafica standalone (GTK3) para que los Clientes (adoptantes y
 * donantes externos, tabla "clientes") inicien sesion y vean su
 * propia informacion, sin acceso a la administracion del refugio
 * (eso sigue siendo exclusivo de PawOS Refugio GUI / CLI).
 *
 * Reutiliza por completo la logica ya existente en db.c:
 * cliente_autenticar, cliente_registrar, cliente_existe,
 * cliente_actualizar, cliente_rol_nombre, cliente_guardar_foto,
 * cliente_obtener_foto, vacuna_listar, mascota_buscar_por_id -- no
 * reimplementa nada de negocio.
 *
 * La foto de perfil se guarda como texto base64 (mismo truco que ya
 * usa usuario_registrar para el personal del refugio), en una
 * columna de la tabla "clientes" en el SQL Server remoto. El usuario
 * elige el archivo y luego recorta libremente (tamano personalizado,
 * arrastrando el mouse) la parte que quiere usar.
 */
#include <gtk/gtk.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <glib/gstdio.h>
#include <unistd.h>
#include "db/db.h"
#include "version.h"

#define RUTA_BD_DEFECTO "/var/pawos/pawos.db"
#define RESPUESTA_REGISTRARME 1
#define RESPUESTA_OLVIDE 2
#define MAX_INTENTOS_RECUPERAR 5

static void solo_digitos(const char *src, char *dst, size_t n);
#define FOTO_AVATAR_SIZE 84
#define RECORTE_MAX_DIM 640

enum {
    COL_V_MASCOTA = 0,
    COL_V_VACUNA,
    COL_V_PROXIMA,
    COL_V_ESTADO,
    COL_V_COLOR,
    N_COLUMNAS_VACUNA
};

enum {
    COL_CAT_ID = 0,
    COL_CAT_NOMBRE,
    COL_CAT_ESPECIE,
    COL_CAT_RAZA,
    COL_CAT_EDAD,
    COL_CAT_INGRESO,
    N_COLUMNAS_CATALOGO
};

enum {
    COL_SOL_MASCOTA = 0,
    COL_SOL_FECHA,
    COL_SOL_ESTADO,
    COL_SOL_COLOR,
    COL_SOL_MENSAJE,
    N_COLUMNAS_SOLICITUD
};

enum {
    COL_DON_FECHA = 0,
    COL_DON_MONTO,
    N_COLUMNAS_DONACION
};

typedef struct {
    GtkWidget        *ventana;
    GtkWidget        *imagen_avatar;
    Cliente           cliente;
    GtkListStore     *store_vacunas;
    GtkListStore     *store_catalogo;
    GtkTreeSelection *sel_catalogo;
    GtkWidget        *lbl_catalogo;
    GtkListStore     *store_solicitudes;
    GtkWidget        *lbl_solicitudes;
    GtkListStore     *store_donaciones;
    GtkWidget        *lbl_total_donado;
    GtkWidget        *entry_monto;
    GtkWidget        *lbl_datos;     /* "Correo / Telefono" de la pestana Mi perfil */
} ContextoApp;

static void mostrar_mensaje(GtkWindow *padre, const char *texto, gboolean es_error) {
    GtkWidget *dialogo = gtk_message_dialog_new(padre, GTK_DIALOG_MODAL,
        es_error ? GTK_MESSAGE_ERROR : GTK_MESSAGE_INFO, GTK_BUTTONS_OK, "%s", texto);
    gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);
}

static void aplicar_estilos_simples(void) {
    GtkCssProvider *proveedor = gtk_css_provider_new();
    const char *css =
        "window { background-color: #F4F6F5; }"
        ".pawos-header {"
        "  background-image: linear-gradient(180deg, #23924B 0%, #12451F 100%);"
        "  padding: 16px 20px;"
        "}"
        ".pawos-header label { color: #FFFFFF; }"
        ".pawos-tarjeta {"
        "  background-color: #FFFFFF;"
        "  border-radius: 12px;"
        "  padding: 16px;"
        "  box-shadow: 0 2px 8px rgba(0,0,0,0.10);"
        "}"
        "button.pawos-accion {"
        "  background-image: none;"
        "  background-color: #23924B;"
        "  color: #FFFFFF;"
        "  border-radius: 8px;"
        "  padding: 6px 14px;"
        "}"
        "button.pawos-accion:hover { background-color: #1D7A3E; }"
        "button.pawos-peligro {"
        "  background-image: none;"
        "  background-color: #C0392B;"
        "  color: #FFFFFF;"
        "  border-radius: 8px;"
        "  padding: 6px 14px;"
        "}"
        "button.pawos-peligro:hover { background-color: #A5301F; }";
    gtk_css_provider_load_from_data(proveedor, css, -1, NULL);
    gtk_style_context_add_provider_for_screen(
        gdk_screen_get_default(), GTK_STYLE_PROVIDER(proveedor),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(proveedor);
}

/* ---------- Registro de un cliente nuevo ---------- */

/* Etiqueta de un campo del formulario, con un asterisco rojo si es
 * obligatorio (Telefono es el unico campo opcional del registro). */
static GtkWidget *crear_etiqueta_campo(const char *texto, gboolean obligatorio) {
    GtkWidget *lbl = gtk_label_new(NULL);
    gchar *markup = obligatorio
        ? g_strdup_printf("%s <span foreground='#C0392B'>*</span>", texto)
        : g_strdup(texto);
    gtk_label_set_markup(GTK_LABEL(lbl), markup);
    g_free(markup);
    gtk_widget_set_halign(lbl, GTK_ALIGN_START);
    return lbl;
}

/* Mensaje bajo un campo (vacio = no se muestra): rojo para error,
 * verde para "esta bien". Se usa gtk_widget_set_no_show_all para que
 * gtk_widget_show_all() no lo vuelva a mostrar por error cuando esta
 * vacio. */
static void marcar_mensaje_campo(GtkWidget *lbl, const char *mensaje, gboolean es_valido) {
    if (!mensaje || mensaje[0] == '\0') {
        gtk_label_set_text(GTK_LABEL(lbl), "");
        gtk_widget_hide(lbl);
        return;
    }
    const char *color = es_valido ? "#1E8449" : "#C0392B";
    gchar *markup = g_strdup_printf("<span size='small' foreground='%s'>%s</span>", color, mensaje);
    gtk_label_set_markup(GTK_LABEL(lbl), markup);
    g_free(markup);
    gtk_widget_set_no_show_all(lbl, FALSE);
    gtk_widget_show(lbl);
}

/* Atajo para el caso de error (rojo), usado por los demas campos. */
static void marcar_error_campo(GtkWidget *lbl_error, const char *mensaje) {
    marcar_mensaje_campo(lbl_error, mensaje, FALSE);
}

static GtkWidget *crear_etiqueta_error(void) {
    GtkWidget *lbl = gtk_label_new("");
    gtk_widget_set_halign(lbl, GTK_ALIGN_START);
    gtk_widget_set_no_show_all(lbl, TRUE); /* oculta hasta que haga falta, show_all no la toca */
    return lbl;
}

/* Revisa en vivo (cada vez que se escribe una letra en Contrasena o
 * Confirmar contrasena) si coinciden, sin esperar a que se de clic en
 * "Registrarme" -- evita que el mensaje aparezca de golpe al final. */
typedef struct {
    GtkWidget *entry_pass;
    GtkWidget *entry_pass2;
    GtkWidget *error_pass;
    GtkWidget *error_pass2;
} ValidacionPassword;

static void on_password_changed(GtkEditable *editable, gpointer datos) {
    (void)editable;
    ValidacionPassword *v = datos;
    const char *pass = gtk_entry_get_text(GTK_ENTRY(v->entry_pass));
    const char *pass2 = gtk_entry_get_text(GTK_ENTRY(v->entry_pass2));
    if (pass[0] == '\0' || pass2[0] == '\0') {
        marcar_mensaje_campo(v->error_pass, NULL, FALSE);
        marcar_mensaje_campo(v->error_pass2, NULL, FALSE);
    } else if (strcmp(pass, pass2) != 0) {
        marcar_mensaje_campo(v->error_pass, "Las contrasenas no coinciden", FALSE);
        marcar_mensaje_campo(v->error_pass2, "Las contrasenas no coinciden", FALSE);
    } else {
        marcar_mensaje_campo(v->error_pass, "Las contrasenas coinciden", TRUE);
        marcar_mensaje_campo(v->error_pass2, "Las contrasenas coinciden", TRUE);
    }
}

static void mostrar_registro(GtkWindow *padre) {
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Registrarme como cliente", padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL, "_Registrarme", GTK_RESPONSE_OK, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 380, -1);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area), 14);
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 4);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 10);
    gtk_container_add(GTK_CONTAINER(area), grid);

    GtkWidget *entry_correo = gtk_entry_new();
    GtkWidget *entry_nombre = gtk_entry_new();
    GtkWidget *entry_telefono = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(entry_telefono), "Numero de WhatsApp");
    GtkWidget *entry_pass = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(entry_pass), FALSE);
    GtkWidget *entry_pass2 = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(entry_pass2), FALSE);

    GtkWidget *error_correo = crear_etiqueta_error();
    GtkWidget *error_nombre = crear_etiqueta_error();
    GtkWidget *error_telefono = crear_etiqueta_error();
    GtkWidget *error_pass = crear_etiqueta_error();
    GtkWidget *error_pass2 = crear_etiqueta_error();

    ValidacionPassword vp = { entry_pass, entry_pass2, error_pass, error_pass2 };
    g_signal_connect(entry_pass, "changed", G_CALLBACK(on_password_changed), &vp);
    g_signal_connect(entry_pass2, "changed", G_CALLBACK(on_password_changed), &vp);

    int fila = 0;
    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Correo:", TRUE), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_correo, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), error_correo, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Nombre:", TRUE), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_nombre, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), error_nombre, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Telefono:", TRUE), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_telefono, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), error_telefono, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Contrasena:", TRUE), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_pass, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), error_pass, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Confirmar contrasena:", TRUE), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_pass2, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), error_pass2, 1, fila++, 1, 1);

    GtkWidget *lbl_nota = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(lbl_nota), "<span size='small' foreground='#777777'>* Campo obligatorio</span>");
    gtk_widget_set_halign(lbl_nota, GTK_ALIGN_START);
    gtk_grid_attach(GTK_GRID(grid), lbl_nota, 0, fila++, 2, 1);

    gtk_widget_show_all(dialogo);
    for (;;) {
        if (gtk_dialog_run(GTK_DIALOG(dialogo)) != GTK_RESPONSE_OK) break;

        const char *correo = gtk_entry_get_text(GTK_ENTRY(entry_correo));
        const char *nombre = gtk_entry_get_text(GTK_ENTRY(entry_nombre));
        const char *telefono = gtk_entry_get_text(GTK_ENTRY(entry_telefono));
        const char *pass = gtk_entry_get_text(GTK_ENTRY(entry_pass));
        const char *pass2 = gtk_entry_get_text(GTK_ENTRY(entry_pass2));

        marcar_error_campo(error_correo, NULL);
        marcar_error_campo(error_nombre, NULL);
        marcar_error_campo(error_telefono, NULL);
        marcar_error_campo(error_pass, NULL);
        marcar_error_campo(error_pass2, NULL);

        gboolean ok = TRUE;
        if (correo[0] == '\0') { marcar_error_campo(error_correo, "Este campo es obligatorio"); ok = FALSE; }
        if (nombre[0] == '\0') { marcar_error_campo(error_nombre, "Este campo es obligatorio"); ok = FALSE; }
        if (telefono[0] == '\0') {
            marcar_error_campo(error_telefono, "Este campo es obligatorio");
            ok = FALSE;
        } else {
            /* Se necesita para recuperar la contrasena: minimo 8 digitos */
            char digitos[64];
            solo_digitos(telefono, digitos, sizeof(digitos));
            if (strlen(digitos) < 8) {
                marcar_error_campo(error_telefono, "Escribe un telefono valido (minimo 8 digitos)");
                ok = FALSE;
            }
        }
        if (pass[0] == '\0') { marcar_error_campo(error_pass, "Este campo es obligatorio"); ok = FALSE; }
        if (pass2[0] == '\0') { marcar_error_campo(error_pass2, "Este campo es obligatorio"); ok = FALSE; }
        if (pass[0] != '\0' && pass2[0] != '\0' && strcmp(pass, pass2) != 0) {
            marcar_error_campo(error_pass, "Las contrasenas no coinciden");
            marcar_error_campo(error_pass2, "Las contrasenas no coinciden");
            ok = FALSE;
        }
        if (!ok) continue;

        if (cliente_existe(correo)) {
            marcar_error_campo(error_correo, "Ya existe un cliente registrado con ese correo");
            continue;
        }
        if (cliente_registrar(correo, pass, nombre, telefono, ROL_CLIENTE_JEFE) != 0) {
            mostrar_mensaje(GTK_WINDOW(dialogo), "No se pudo completar el registro.", TRUE);
            continue;
        }
        mostrar_mensaje(GTK_WINDOW(dialogo), "Registro completado. Ya puedes iniciar sesion.", FALSE);
        break;
    }
    gtk_widget_destroy(dialogo);
}

/* ---------- Olvide mi contrasena ----------
 * No hay envio de correos, asi que se verifica con el correo y el
 * telefono que el Cliente registro. Es una verificacion basica (pensada
 * para este proyecto): quien conozca ambos datos puede cambiar la
 * contrasena. */

static void solo_digitos(const char *src, char *dst, size_t n) {
    size_t j = 0;
    for (; *src && j + 1 < n; src++)
        if (g_ascii_isdigit(*src)) dst[j++] = *src;
    dst[j] = '\0';
}

/* Dos telefonos coinciden si tienen los mismos digitos finales (asi no
 * importa si uno lleva el codigo de pais, espacios o guiones). */
static gboolean telefonos_coinciden(const char *a, const char *b) {
    char da[64], db[64];
    solo_digitos(a, da, sizeof(da));
    solo_digitos(b, db, sizeof(db));
    size_t la = strlen(da), lb = strlen(db);
    size_t m = la < lb ? la : lb;
    if (m == 0) return FALSE;
    if (m < 8) return la == lb && strcmp(da, db) == 0;
    return strcmp(da + la - m, db + lb - m) == 0;
}

static void on_olvide_clicked(GtkButton *btn, gpointer dialogo) {
    (void)btn;
    gtk_dialog_response(GTK_DIALOG(dialogo), RESPUESTA_OLVIDE);
}

static void mostrar_recuperar_password(GtkWindow *padre) {
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Recuperar contrasena", padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL, "_Cambiar contrasena", GTK_RESPONSE_OK, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 400, -1);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area), 14);
    gtk_box_set_spacing(GTK_BOX(area), 8);

    GtkWidget *lbl_ayuda = gtk_label_new(
        "Escribe el correo y el telefono con los que te registraste, "
        "y elige una contrasena nueva.");
    gtk_label_set_line_wrap(GTK_LABEL(lbl_ayuda), TRUE);
    gtk_widget_set_halign(lbl_ayuda, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(area), lbl_ayuda, FALSE, FALSE, 0);

    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 4);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 10);
    gtk_box_pack_start(GTK_BOX(area), grid, FALSE, FALSE, 0);

    GtkWidget *entry_correo = gtk_entry_new();
    GtkWidget *entry_telefono = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(entry_telefono), "El numero que registraste");
    GtkWidget *entry_pass = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(entry_pass), FALSE);
    GtkWidget *entry_pass2 = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(entry_pass2), FALSE);

    GtkWidget *error_correo = crear_etiqueta_error();
    GtkWidget *error_telefono = crear_etiqueta_error();
    GtkWidget *error_pass = crear_etiqueta_error();
    GtkWidget *error_pass2 = crear_etiqueta_error();

    ValidacionPassword vp = { entry_pass, entry_pass2, error_pass, error_pass2 };
    g_signal_connect(entry_pass, "changed", G_CALLBACK(on_password_changed), &vp);
    g_signal_connect(entry_pass2, "changed", G_CALLBACK(on_password_changed), &vp);

    int fila = 0;
    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Correo:", TRUE), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_correo, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), error_correo, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Telefono:", TRUE), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_telefono, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), error_telefono, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Contrasena nueva:", TRUE), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_pass, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), error_pass, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Confirmar contrasena:", TRUE), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_pass2, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), error_pass2, 1, fila++, 1, 1);

    gtk_widget_show_all(dialogo);
    int intentos = 0;
    for (;;) {
        if (gtk_dialog_run(GTK_DIALOG(dialogo)) != GTK_RESPONSE_OK) break;

        const char *correo = gtk_entry_get_text(GTK_ENTRY(entry_correo));
        const char *telefono = gtk_entry_get_text(GTK_ENTRY(entry_telefono));
        const char *pass = gtk_entry_get_text(GTK_ENTRY(entry_pass));
        const char *pass2 = gtk_entry_get_text(GTK_ENTRY(entry_pass2));

        marcar_error_campo(error_correo, NULL);
        marcar_error_campo(error_telefono, NULL);
        marcar_error_campo(error_pass, NULL);
        marcar_error_campo(error_pass2, NULL);

        gboolean ok = TRUE;
        if (correo[0] == '\0') { marcar_error_campo(error_correo, "Este campo es obligatorio"); ok = FALSE; }
        if (telefono[0] == '\0') { marcar_error_campo(error_telefono, "Este campo es obligatorio"); ok = FALSE; }
        if (pass[0] == '\0') { marcar_error_campo(error_pass, "Este campo es obligatorio"); ok = FALSE; }
        if (pass2[0] == '\0') { marcar_error_campo(error_pass2, "Este campo es obligatorio"); ok = FALSE; }
        if (pass[0] != '\0' && pass2[0] != '\0' && strcmp(pass, pass2) != 0) {
            marcar_error_campo(error_pass, "Las contrasenas no coinciden");
            marcar_error_campo(error_pass2, "Las contrasenas no coinciden");
            ok = FALSE;
        }
        if (!ok) continue;

        /* Se busca al Cliente por su correo */
        Cliente *lista = NULL;
        int n = 0;
        if (cliente_listar(&lista, &n) != 0) {
            mostrar_mensaje(GTK_WINDOW(dialogo), "No se pudo consultar los clientes (revisa la conexion).", TRUE);
            continue;
        }
        Cliente encontrado;
        gboolean existe = FALSE;
        for (int i = 0; i < n; i++) {
            if (g_ascii_strcasecmp(lista[i].correo, correo) == 0) {
                encontrado = lista[i];
                existe = TRUE;
                break;
            }
        }
        free(lista);

        if (!existe) {
            marcar_error_campo(error_correo, "No hay ninguna cuenta con ese correo");
            if (++intentos >= MAX_INTENTOS_RECUPERAR) break;
            continue;
        }
        if (encontrado.telefono[0] == '\0') {
            marcar_error_campo(error_telefono, "Esta cuenta no tiene telefono registrado. Pide ayuda al refugio.");
            continue;
        }
        if (!telefonos_coinciden(telefono, encontrado.telefono)) {
            marcar_error_campo(error_telefono, "El telefono no coincide con el registrado");
            if (++intentos >= MAX_INTENTOS_RECUPERAR) {
                mostrar_mensaje(GTK_WINDOW(dialogo),
                    "Demasiados intentos fallidos. Intenta de nuevo mas tarde.", TRUE);
                break;
            }
            continue;
        }

        if (cliente_actualizar(encontrado.id, encontrado.nombre, pass) != 0) {
            mostrar_mensaje(GTK_WINDOW(dialogo), "No se pudo cambiar la contrasena.", TRUE);
            continue;
        }
        mostrar_mensaje(GTK_WINDOW(dialogo), "Contrasena cambiada. Ya puedes iniciar sesion con la nueva.", FALSE);
        break;
    }
    gtk_widget_destroy(dialogo);
}

/* ---------- Login ---------- */

static gboolean mostrar_login(Cliente *out) {
    for (;;) {
        GtkWidget *dialogo = gtk_dialog_new_with_buttons(
            "PawOS - Portal de Clientes", NULL, GTK_DIALOG_MODAL,
            "_Salir", GTK_RESPONSE_CANCEL,
            "_Registrarme", RESPUESTA_REGISTRARME,
            "_Iniciar sesion", GTK_RESPONSE_OK, NULL);
        gtk_window_set_default_size(GTK_WINDOW(dialogo), 360, -1);
        GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
        gtk_container_set_border_width(GTK_CONTAINER(area), 16);

        GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
        GtkWidget *lbl_titulo = gtk_label_new(NULL);
        gchar *markup = g_strdup_printf(
            "<span size='large' weight='bold'>\xF0\x9F\x90\xBE PawOS</span>\n<span size='small'>Portal de Clientes - v%s</span>",
            PAWOS_VERSION);
        gtk_label_set_markup(GTK_LABEL(lbl_titulo), markup);
        g_free(markup);
        gtk_box_pack_start(GTK_BOX(caja), lbl_titulo, FALSE, FALSE, 4);

        GtkWidget *entry_correo = gtk_entry_new();
        gtk_entry_set_placeholder_text(GTK_ENTRY(entry_correo), "Correo");
        GtkWidget *entry_pass = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(entry_pass), FALSE);
        gtk_entry_set_placeholder_text(GTK_ENTRY(entry_pass), "Contrasena");
        gtk_entry_set_activates_default(GTK_ENTRY(entry_pass), TRUE);

        gtk_box_pack_start(GTK_BOX(caja), entry_correo, FALSE, FALSE, 0);
        gtk_box_pack_start(GTK_BOX(caja), entry_pass, FALSE, FALSE, 0);

        GtkWidget *btn_olvide = gtk_button_new_with_label("Olvidaste tu contrasena?");
        gtk_button_set_relief(GTK_BUTTON(btn_olvide), GTK_RELIEF_NONE);
        gtk_widget_set_halign(btn_olvide, GTK_ALIGN_START);
        g_signal_connect(btn_olvide, "clicked", G_CALLBACK(on_olvide_clicked), dialogo);
        gtk_box_pack_start(GTK_BOX(caja), btn_olvide, FALSE, FALSE, 0);
        gtk_container_add(GTK_CONTAINER(area), caja);

        gtk_dialog_set_default_response(GTK_DIALOG(dialogo), GTK_RESPONSE_OK);
        gtk_widget_show_all(dialogo);

        int resp = gtk_dialog_run(GTK_DIALOG(dialogo));

        if (resp == GTK_RESPONSE_OK) {
            const char *correo = gtk_entry_get_text(GTK_ENTRY(entry_correo));
            const char *pass = gtk_entry_get_text(GTK_ENTRY(entry_pass));
            Cliente candidato;
            if (correo[0] != '\0' && cliente_autenticar(correo, pass, &candidato) == 0) {
                *out = candidato;
                gtk_widget_destroy(dialogo);
                return TRUE;
            }
            gtk_widget_destroy(dialogo);
            mostrar_mensaje(NULL, "Correo o contrasena incorrectos.", TRUE);
            continue;
        } else if (resp == RESPUESTA_REGISTRARME) {
            gtk_widget_destroy(dialogo);
            mostrar_registro(NULL);
            continue;
        } else if (resp == RESPUESTA_OLVIDE) {
            gtk_widget_destroy(dialogo);
            mostrar_recuperar_password(NULL);
            continue;
        } else {
            gtk_widget_destroy(dialogo);
            return FALSE;
        }
    }
}

/* ---------- Mis recordatorios de vacunas ---------- */

static void calcular_estado(const char *fecha_proxima, const char *hoy,
                             const char **estado_out, const char **color_out) {
    if (!fecha_proxima || fecha_proxima[0] == '\0') {
        *estado_out = "-";
        *color_out = "#555555";
        return;
    }
    int cmp = strcmp(fecha_proxima, hoy);
    if (cmp < 0) { *estado_out = "VENCIDA"; *color_out = "#C0392B"; }
    else if (cmp == 0) { *estado_out = "HOY"; *color_out = "#D68910"; }
    else { *estado_out = "Al dia"; *color_out = "#1E8449"; }
}

static void cargar_mis_vacunas(ContextoApp *ctx) {
    gtk_list_store_clear(ctx->store_vacunas);

    char hoy[16];
    time_t t = time(NULL);
    struct tm tmv;
    localtime_r(&t, &tmv);
    strftime(hoy, sizeof(hoy), "%Y-%m-%d", &tmv);

    Vacuna *vs;
    int n;
    if (vacuna_listar(&vs, &n) != 0) return;

    for (int i = 0; i < n; i++) {
        if (vs[i].cliente_id != ctx->cliente.id) continue;

        Mascota m;
        const char *nombre_mascota = "(mascota desconocida)";
        if (mascota_buscar_por_id(vs[i].mascota_id, &m) == 0) nombre_mascota = m.nombre;

        const char *estado, *color;
        calcular_estado(vs[i].fecha_proxima, hoy, &estado, &color);

        GtkTreeIter iter;
        gtk_list_store_append(ctx->store_vacunas, &iter);
        gtk_list_store_set(ctx->store_vacunas, &iter,
            COL_V_MASCOTA, nombre_mascota,
            COL_V_VACUNA, vs[i].nombre_vacuna,
            COL_V_PROXIMA, vs[i].fecha_proxima,
            COL_V_ESTADO, estado,
            COL_V_COLOR, color,
            -1);
    }
    free(vs);
}

static void on_actualizar_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    cargar_mis_vacunas((ContextoApp *)datos);
}

/* ---------- Foto de perfil ---------- */

static void poner_avatar_placeholder(ContextoApp *ctx) {
    gtk_image_set_from_icon_name(GTK_IMAGE(ctx->imagen_avatar), "avatar-default-symbolic", GTK_ICON_SIZE_DIALOG);
}

/* Trae la foto guardada (texto base64) desde db.c, la decodifica y la
 * muestra en ctx->imagen_avatar. Si el cliente no tiene foto, o algo
 * sale mal al decodificarla, muestra un icono generico en su lugar. */
static void cargar_avatar(ContextoApp *ctx) {
    char *foto_b64 = NULL;
    if (cliente_obtener_foto(ctx->cliente.id, &foto_b64) != 0 || !foto_b64 || foto_b64[0] == '\0') {
        free(foto_b64);
        poner_avatar_placeholder(ctx);
        return;
    }

    gsize len_bin = 0;
    guchar *datos_bin = g_base64_decode(foto_b64, &len_bin);
    free(foto_b64);
    if (!datos_bin || len_bin == 0) {
        g_free(datos_bin);
        poner_avatar_placeholder(ctx);
        return;
    }

    GdkPixbufLoader *loader = gdk_pixbuf_loader_new();
    gboolean ok = gdk_pixbuf_loader_write(loader, datos_bin, len_bin, NULL);
    ok = ok && gdk_pixbuf_loader_close(loader, NULL);
    GdkPixbuf *pix = ok ? gdk_pixbuf_loader_get_pixbuf(loader) : NULL;
    if (pix) {
        GdkPixbuf *escalado = gdk_pixbuf_scale_simple(pix, FOTO_AVATAR_SIZE, FOTO_AVATAR_SIZE, GDK_INTERP_BILINEAR);
        gtk_image_set_from_pixbuf(GTK_IMAGE(ctx->imagen_avatar), escalado);
        g_object_unref(escalado);
    } else {
        poner_avatar_placeholder(ctx);
    }
    g_object_unref(loader);
    g_free(datos_bin);
}

/* Estado del dialogo de recorte: deja al usuario arrastrar el mouse
 * sobre la imagen para elegir libremente que region quiere usar como
 * foto de perfil, y despues MOVER el recuadro o agrandarlo/achicarlo
 * desde sus 4 esquinas (como en el recorte de foto de perfil de
 * cualquier red social), en vez de tener que volver a dibujarlo. */
typedef enum {
    MODO_NINGUNO = 0,
    MODO_DIBUJANDO,
    MODO_MOVIENDO,
    MODO_REDIM_TL,
    MODO_REDIM_TR,
    MODO_REDIM_BL,
    MODO_REDIM_BR
} ModoRecorte;

typedef struct {
    GdkPixbuf  *pixbuf;
    int         ancho_img, alto_img;
    gboolean    hay_seleccion;
    double      x, y, w, h;        /* seleccion actual (normalizada) */
    ModoRecorte modo;
    double      ancla_x, ancla_y;  /* MODO_DIBUJANDO: punto donde empezo el arrastre */
    double      offset_x, offset_y; /* MODO_MOVIENDO: desfase click -> esquina sup-izq */
    GtkWidget  *btn_ok;
} ContextoRecorte;

#define RECORTE_TAM_ASA 10.0 /* radio (en pixeles) para "agarrar" una esquina */

static ModoRecorte recorte_detectar_modo(ContextoRecorte *r, double px, double py) {
    if (!r->hay_seleccion) return MODO_DIBUJANDO;
    double x0 = r->x, y0 = r->y, x1 = r->x + r->w, y1 = r->y + r->h;
    const double m = RECORTE_TAM_ASA;
    if (fabs(px - x0) <= m && fabs(py - y0) <= m) return MODO_REDIM_TL;
    if (fabs(px - x1) <= m && fabs(py - y0) <= m) return MODO_REDIM_TR;
    if (fabs(px - x0) <= m && fabs(py - y1) <= m) return MODO_REDIM_BL;
    if (fabs(px - x1) <= m && fabs(py - y1) <= m) return MODO_REDIM_BR;
    if (px >= x0 && px <= x1 && py >= y0 && py <= y1) return MODO_MOVIENDO;
    return MODO_DIBUJANDO;
}

static gboolean recorte_on_draw(GtkWidget *widget, cairo_t *cr, gpointer datos) {
    (void)widget;
    ContextoRecorte *r = datos;
    int w = gdk_pixbuf_get_width(r->pixbuf);
    int h = gdk_pixbuf_get_height(r->pixbuf);
    gdk_cairo_set_source_pixbuf(cr, r->pixbuf, 0, 0);
    cairo_paint(cr);

    if (r->hay_seleccion || r->modo == MODO_DIBUJANDO) {
        double x = r->x, y = r->y, sw = r->w, sh = r->h;

        cairo_set_fill_rule(cr, CAIRO_FILL_RULE_EVEN_ODD);
        cairo_set_source_rgba(cr, 0, 0, 0, 0.45);
        cairo_rectangle(cr, 0, 0, w, h);
        cairo_rectangle(cr, x, y, sw, sh);
        cairo_fill(cr);

        cairo_set_source_rgb(cr, 1, 1, 1);
        cairo_set_line_width(cr, 2.0);
        cairo_rectangle(cr, x, y, sw, sh);
        cairo_stroke(cr);

        /* Asas en las 4 esquinas: avisan que se puede agrandar/achicar */
        double esquinas[4][2] = { {x, y}, {x + sw, y}, {x, y + sh}, {x + sw, y + sh} };
        for (int i = 0; i < 4; i++) {
            cairo_rectangle(cr, esquinas[i][0] - 4, esquinas[i][1] - 4, 8, 8);
            cairo_set_source_rgb(cr, 1, 1, 1);
            cairo_fill_preserve(cr);
            cairo_set_source_rgb(cr, 0.137, 0.573, 0.294); /* verde PawOS */
            cairo_set_line_width(cr, 1.5);
            cairo_stroke(cr);
        }
    }
    return FALSE;
}

static gboolean recorte_on_press(GtkWidget *widget, GdkEventButton *evento, gpointer datos) {
    ContextoRecorte *r = datos;
    r->modo = recorte_detectar_modo(r, evento->x, evento->y);
    if (r->modo == MODO_DIBUJANDO) {
        r->ancla_x = evento->x;
        r->ancla_y = evento->y;
        r->x = evento->x; r->y = evento->y; r->w = 0; r->h = 0;
        r->hay_seleccion = FALSE;
        gtk_widget_set_sensitive(r->btn_ok, FALSE);
    } else if (r->modo == MODO_MOVIENDO) {
        r->offset_x = evento->x - r->x;
        r->offset_y = evento->y - r->y;
    }
    gtk_widget_queue_draw(widget);
    return TRUE;
}

static gboolean recorte_on_motion(GtkWidget *widget, GdkEventMotion *evento, gpointer datos) {
    ContextoRecorte *r = datos;
    if (r->modo == MODO_NINGUNO) return FALSE;

    double px = evento->x, py = evento->y;
    if (px < 0) px = 0;
    if (px > r->ancho_img) px = r->ancho_img;
    if (py < 0) py = 0;
    if (py > r->alto_img) py = r->alto_img;

    switch (r->modo) {
        case MODO_DIBUJANDO:
            r->x = MIN(r->ancla_x, px);
            r->y = MIN(r->ancla_y, py);
            r->w = fabs(px - r->ancla_x);
            r->h = fabs(py - r->ancla_y);
            break;
        case MODO_MOVIENDO: {
            double nx = px - r->offset_x, ny = py - r->offset_y;
            if (nx < 0) nx = 0;
            if (ny < 0) ny = 0;
            if (nx + r->w > r->ancho_img) nx = r->ancho_img - r->w;
            if (ny + r->h > r->alto_img) ny = r->alto_img - r->h;
            r->x = nx; r->y = ny;
            break;
        }
        case MODO_REDIM_TL: {
            double x1 = r->x + r->w, y1 = r->y + r->h;
            double nx = MIN(px, x1 - RECORTE_TAM_ASA), ny = MIN(py, y1 - RECORTE_TAM_ASA);
            r->x = nx; r->y = ny; r->w = x1 - nx; r->h = y1 - ny;
            break;
        }
        case MODO_REDIM_TR: {
            double x0 = r->x, y1 = r->y + r->h;
            double nx1 = MAX(px, x0 + RECORTE_TAM_ASA), ny = MIN(py, y1 - RECORTE_TAM_ASA);
            r->y = ny; r->w = nx1 - x0; r->h = y1 - ny;
            break;
        }
        case MODO_REDIM_BL: {
            double x1 = r->x + r->w, y0 = r->y;
            double nx = MIN(px, x1 - RECORTE_TAM_ASA), ny1 = MAX(py, y0 + RECORTE_TAM_ASA);
            r->x = nx; r->w = x1 - nx; r->h = ny1 - y0;
            break;
        }
        case MODO_REDIM_BR: {
            double x0 = r->x, y0 = r->y;
            double nx1 = MAX(px, x0 + RECORTE_TAM_ASA), ny1 = MAX(py, y0 + RECORTE_TAM_ASA);
            r->w = nx1 - x0; r->h = ny1 - y0;
            break;
        }
        default:
            return FALSE;
    }
    gtk_widget_queue_draw(widget);
    return TRUE;
}

static gboolean recorte_on_release(GtkWidget *widget, GdkEventButton *evento, gpointer datos) {
    (void)evento;
    ContextoRecorte *r = datos;
    r->modo = MODO_NINGUNO;
    r->hay_seleccion = (r->w >= 15 && r->h >= 15);
    gtk_widget_set_sensitive(r->btn_ok, r->hay_seleccion);
    gtk_widget_queue_draw(widget);
    return TRUE;
}

/* Muestra la imagen cargada y deja que el usuario dibuje un recuadro
 * de tamano libre, y luego lo MUEVA (arrastrando por dentro) o lo
 * AGRANDE/ACHIQUE (arrastrando cualquiera de sus 4 esquinas) tantas
 * veces como quiera antes de confirmar. Devuelve un GdkPixbuf nuevo
 * (liberar con g_object_unref) con solo esa region, o NULL si
 * cancelo o no llego a dejar una seleccion valida. */
static GdkPixbuf *mostrar_dialogo_recorte(GtkWindow *padre, GdkPixbuf *imagen_original) {
    int ow = gdk_pixbuf_get_width(imagen_original);
    int oh = gdk_pixbuf_get_height(imagen_original);
    double escala = 1.0;
    if (ow > RECORTE_MAX_DIM || oh > RECORTE_MAX_DIM) {
        escala = (double)RECORTE_MAX_DIM / (double)(ow > oh ? ow : oh);
    }
    int dw = (int)(ow * escala), dh = (int)(oh * escala);
    GdkPixbuf *mostrado = (escala < 1.0)
        ? gdk_pixbuf_scale_simple(imagen_original, dw, dh, GDK_INTERP_BILINEAR)
        : GDK_PIXBUF(g_object_ref(imagen_original));

    ContextoRecorte r;
    memset(&r, 0, sizeof(r));
    r.pixbuf = mostrado;
    r.ancho_img = dw;
    r.alto_img = dh;

    GtkWidget *dialogo = gtk_dialog_new_with_buttons("Recortar foto de perfil", padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL, "_Usar esta seleccion", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area), 10);

    GtkWidget *lbl_ayuda = gtk_label_new(
        "Dibuja un recuadro arrastrando el mouse. Luego puedes moverlo (arrastra por dentro) o "
        "agrandarlo/achicarlo (arrastra cualquier esquina).");
    gtk_label_set_line_wrap(GTK_LABEL(lbl_ayuda), TRUE);
    gtk_box_pack_start(GTK_BOX(area), lbl_ayuda, FALSE, FALSE, 4);

    GtkWidget *drawing = gtk_drawing_area_new();
    gtk_widget_set_size_request(drawing, dw, dh);
    gtk_widget_add_events(drawing, GDK_BUTTON_PRESS_MASK | GDK_BUTTON_RELEASE_MASK | GDK_POINTER_MOTION_MASK);
    gtk_box_pack_start(GTK_BOX(area), drawing, TRUE, TRUE, 4);

    r.btn_ok = gtk_dialog_get_widget_for_response(GTK_DIALOG(dialogo), GTK_RESPONSE_OK);
    gtk_widget_set_sensitive(r.btn_ok, FALSE);

    g_signal_connect(drawing, "draw", G_CALLBACK(recorte_on_draw), &r);
    g_signal_connect(drawing, "button-press-event", G_CALLBACK(recorte_on_press), &r);
    g_signal_connect(drawing, "motion-notify-event", G_CALLBACK(recorte_on_motion), &r);
    g_signal_connect(drawing, "button-release-event", G_CALLBACK(recorte_on_release), &r);

    gtk_widget_show_all(dialogo);
    int resp = gtk_dialog_run(GTK_DIALOG(dialogo));

    GdkPixbuf *resultado = NULL;
    if (resp == GTK_RESPONSE_OK && r.hay_seleccion) {
        int x = (int)r.x, y = (int)r.y;
        int sw = (int)r.w, sh = (int)r.h;
        if (x < 0) x = 0;
        if (y < 0) y = 0;
        if (x + sw > dw) sw = dw - x;
        if (y + sh > dh) sh = dh - y;
        if (sw > 0 && sh > 0) {
            GdkPixbuf *sub = gdk_pixbuf_new_subpixbuf(mostrado, x, y, sw, sh);
            resultado = gdk_pixbuf_copy(sub);
            g_object_unref(sub);
        }
    }

    gtk_widget_destroy(dialogo);
    g_object_unref(mostrado);
    return resultado;
}

static void on_cambiar_foto_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;

    GtkWidget *selector = gtk_file_chooser_dialog_new("Elegir foto de perfil", GTK_WINDOW(ctx->ventana),
        GTK_FILE_CHOOSER_ACTION_OPEN, "_Cancelar", GTK_RESPONSE_CANCEL, "_Abrir", GTK_RESPONSE_ACCEPT, NULL);

    GtkFileFilter *filtro = gtk_file_filter_new();
    gtk_file_filter_set_name(filtro, "Imagenes (PNG, JPG)");
    gtk_file_filter_add_mime_type(filtro, "image/png");
    gtk_file_filter_add_mime_type(filtro, "image/jpeg");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(selector), filtro);

    if (gtk_dialog_run(GTK_DIALOG(selector)) != GTK_RESPONSE_ACCEPT) {
        gtk_widget_destroy(selector);
        return;
    }
    char *ruta = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(selector));
    gtk_widget_destroy(selector);
    if (!ruta) return;

    GError *error = NULL;
    GdkPixbuf *original = gdk_pixbuf_new_from_file(ruta, &error);
    g_free(ruta);
    if (!original) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo abrir esa imagen.", TRUE);
        if (error) g_error_free(error);
        return;
    }

    GdkPixbuf *recortada = mostrar_dialogo_recorte(GTK_WINDOW(ctx->ventana), original);
    g_object_unref(original);
    if (!recortada) return; /* cancelo el recorte, o no selecciono nada */

    /* Limita el maximo en pixeles para no inflar la BD remota con
     * fotos enormes -- el usuario ya eligio la forma/tamano relativo
     * que quiere en el recorte, esto solo evita archivos gigantes. */
    int rw = gdk_pixbuf_get_width(recortada), rh = gdk_pixbuf_get_height(recortada);
    if (rw > 512 || rh > 512) {
        double esc = 512.0 / (double)(rw > rh ? rw : rh);
        GdkPixbuf *mas_chica = gdk_pixbuf_scale_simple(recortada, (int)(rw * esc), (int)(rh * esc), GDK_INTERP_BILINEAR);
        g_object_unref(recortada);
        recortada = mas_chica;
    }

    gchar *buffer = NULL;
    gsize tam_buffer = 0;
    if (!gdk_pixbuf_save_to_buffer(recortada, &buffer, &tam_buffer, "png", &error, NULL)) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo procesar la imagen recortada.", TRUE);
        if (error) g_error_free(error);
        g_object_unref(recortada);
        return;
    }
    g_object_unref(recortada);

    gchar *b64 = g_base64_encode((const guchar *)buffer, tam_buffer);
    g_free(buffer);

    int ok = cliente_guardar_foto(ctx->cliente.id, b64);
    g_free(b64);

    if (ok != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo guardar la foto en el servidor.", TRUE);
        return;
    }
    cargar_avatar(ctx);
    mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Foto de perfil actualizada.", FALSE);
}

/* ---------- Editar mi perfil ---------- */

static void refrescar_datos_contacto(ContextoApp *ctx) {
    gchar *t = g_strdup_printf("Correo: %s\nTelefono: %s", ctx->cliente.correo,
        ctx->cliente.telefono[0] ? ctx->cliente.telefono : "(no registrado)");
    gtk_label_set_text(GTK_LABEL(ctx->lbl_datos), t);
    g_free(t);
}

static void on_editar_perfil_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Editar mi perfil", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL, "_Guardar", GTK_RESPONSE_OK, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 360, -1);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area), 14);
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 8);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 10);
    gtk_container_add(GTK_CONTAINER(area), grid);

    GtkWidget *entry_nombre = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(entry_nombre), ctx->cliente.nombre);
    GtkWidget *entry_pass_nueva = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(entry_pass_nueva), FALSE);
    gtk_entry_set_placeholder_text(GTK_ENTRY(entry_pass_nueva), "Dejar vacia para no cambiarla");

    GtkWidget *entry_telefono = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(entry_telefono), ctx->cliente.telefono);
    gtk_entry_set_placeholder_text(GTK_ENTRY(entry_telefono), "Numero de WhatsApp");
    GtkWidget *error_nombre = crear_etiqueta_error();
    GtkWidget *error_telefono = crear_etiqueta_error();

    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Nombre:", TRUE), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), error_nombre, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Telefono:", TRUE), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_telefono, 1, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), error_telefono, 1, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Nueva contrasena:"), 0, 4, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_pass_nueva, 1, 4, 1, 1);

    gtk_widget_show_all(dialogo);
    for (;;) {
        if (gtk_dialog_run(GTK_DIALOG(dialogo)) != GTK_RESPONSE_OK) break;

        const char *nombre = gtk_entry_get_text(GTK_ENTRY(entry_nombre));
        const char *telefono = gtk_entry_get_text(GTK_ENTRY(entry_telefono));
        const char *pass_nueva = gtk_entry_get_text(GTK_ENTRY(entry_pass_nueva));

        marcar_error_campo(error_nombre, NULL);
        marcar_error_campo(error_telefono, NULL);

        gboolean ok = TRUE;
        if (nombre[0] == '\0') {
            marcar_error_campo(error_nombre, "Este campo es obligatorio");
            ok = FALSE;
        }
        if (telefono[0] == '\0') {
            marcar_error_campo(error_telefono, "Este campo es obligatorio");
            ok = FALSE;
        } else {
            char digitos[64];
            solo_digitos(telefono, digitos, sizeof(digitos));
            if (strlen(digitos) < 8) {
                marcar_error_campo(error_telefono, "Escribe un telefono valido (minimo 8 digitos)");
                ok = FALSE;
            }
        }
        if (!ok) continue;

        if (cliente_actualizar(ctx->cliente.id, nombre, pass_nueva) != 0) {
            mostrar_mensaje(GTK_WINDOW(dialogo), "No se pudo actualizar el perfil.", TRUE);
            continue;
        }
        if (strcmp(telefono, ctx->cliente.telefono) != 0
            && cliente_actualizar_telefono(ctx->cliente.id, telefono) != 0) {
            mostrar_mensaje(GTK_WINDOW(dialogo),
                "Se guardo el nombre, pero no se pudo guardar el telefono. Intenta de nuevo.", TRUE);
            snprintf(ctx->cliente.nombre, sizeof(ctx->cliente.nombre), "%s", nombre);
            continue;
        }
        snprintf(ctx->cliente.nombre, sizeof(ctx->cliente.nombre), "%s", nombre);
        snprintf(ctx->cliente.telefono, sizeof(ctx->cliente.telefono), "%s", telefono);
        refrescar_datos_contacto(ctx);
        mostrar_mensaje(GTK_WINDOW(dialogo), "Perfil actualizado.", FALSE);
        break;
    }
    gtk_widget_destroy(dialogo);
}

/* ---------- Pestanas del Cliente: adopcion, mis mascotas y donaciones ---------- */

static void fecha_hoy(char *buf, size_t n) {
    time_t t = time(NULL);
    struct tm tmv;
    localtime_r(&t, &tmv);
    strftime(buf, n, "%Y-%m-%d", &tmv);
}

static void anadir_columna(GtkWidget *tv, const char *titulo, int col, int col_color, gboolean expandir) {
    GtkCellRenderer *r = gtk_cell_renderer_text_new();
    GtkTreeViewColumn *c;
    if (col_color >= 0)
        c = gtk_tree_view_column_new_with_attributes(titulo, r, "text", col, "foreground", col_color, NULL);
    else
        c = gtk_tree_view_column_new_with_attributes(titulo, r, "text", col, NULL);
    gtk_tree_view_column_set_resizable(c, TRUE);
    gtk_tree_view_column_set_expand(c, expandir);
    gtk_tree_view_append_column(GTK_TREE_VIEW(tv), c);
}

/* Mete una tabla dentro de una tarjeta blanca con scroll. */
static GtkWidget *tarjeta_con_tabla(GtkWidget *treeview) {
    GtkWidget *tarjeta = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_style_context_add_class(gtk_widget_get_style_context(tarjeta), "pawos-tarjeta");
    gtk_widget_set_vexpand(tarjeta, TRUE);
    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_scrolled_window_set_overlay_scrolling(GTK_SCROLLED_WINDOW(scroll), FALSE);
    gtk_widget_set_vexpand(scroll, TRUE);
    gtk_container_add(GTK_CONTAINER(scroll), treeview);
    gtk_box_pack_start(GTK_BOX(tarjeta), scroll, TRUE, TRUE, 0);
    return tarjeta;
}

static void cargar_catalogo(ContextoApp *ctx) {
    gtk_list_store_clear(ctx->store_catalogo);
    Mascota *ms = NULL;
    int n = 0;
    if (mascota_listar_disponibles(&ms, &n) != 0) {
        gtk_label_set_text(GTK_LABEL(ctx->lbl_catalogo), "No se pudo cargar el catalogo (revisa la conexion).");
        return;
    }
    for (int i = 0; i < n; i++) {
        gchar *edad = g_strdup_printf("%d", ms[i].edad);
        GtkTreeIter iter;
        gtk_list_store_append(ctx->store_catalogo, &iter);
        gtk_list_store_set(ctx->store_catalogo, &iter,
            COL_CAT_ID, ms[i].id,
            COL_CAT_NOMBRE, ms[i].nombre,
            COL_CAT_ESPECIE, ms[i].especie,
            COL_CAT_RAZA, ms[i].raza,
            COL_CAT_EDAD, edad,
            COL_CAT_INGRESO, ms[i].fecha_ingreso,
            -1);
        g_free(edad);
    }
    free(ms);
    if (n == 0) {
        gtk_label_set_text(GTK_LABEL(ctx->lbl_catalogo), "Por ahora no hay mascotas disponibles para adopcion.");
    } else {
        gchar *txt = g_strdup_printf("%d mascota%s esperando un hogar. Elige una y pulsa \"Solicitar adopcion\".",
            n, n == 1 ? "" : "s");
        gtk_label_set_text(GTK_LABEL(ctx->lbl_catalogo), txt);
        g_free(txt);
    }
}

static void cargar_solicitudes(ContextoApp *ctx) {
    gtk_list_store_clear(ctx->store_solicitudes);
    SolicitudAdopcion *ss = NULL;
    int n = 0;
    if (solicitud_listar_cliente(ctx->cliente.id, &ss, &n) != 0) {
        gtk_label_set_text(GTK_LABEL(ctx->lbl_solicitudes), "No se pudieron cargar tus solicitudes (revisa la conexion).");
        return;
    }
    int aprobadas = 0;
    for (int i = 0; i < n; i++) {
        Mascota m;
        const char *nombre = "(mascota no disponible)";
        if (mascota_buscar_por_id(ss[i].mascota_id, &m) == 0) nombre = m.nombre;

        const char *color = "#555555";
        if (strcmp(ss[i].estado, "Pendiente") == 0) color = "#D68910";
        else if (strcmp(ss[i].estado, "Aprobada") == 0) { color = "#1E8449"; aprobadas++; }
        else if (strcmp(ss[i].estado, "Rechazada") == 0) color = "#C0392B";

        GtkTreeIter iter;
        gtk_list_store_append(ctx->store_solicitudes, &iter);
        gtk_list_store_set(ctx->store_solicitudes, &iter,
            COL_SOL_MASCOTA, nombre,
            COL_SOL_FECHA, ss[i].fecha,
            COL_SOL_ESTADO, ss[i].estado,
            COL_SOL_COLOR, color,
            COL_SOL_MENSAJE, ss[i].mensaje,
            -1);
    }
    free(ss);
    if (n == 0) {
        gtk_label_set_text(GTK_LABEL(ctx->lbl_solicitudes),
            "Aun no has solicitado ninguna adopcion. Mira la pestana \"Mascotas en adopcion\".");
    } else {
        gchar *txt = g_strdup_printf("%d solicitud%s, %d aprobada%s. Cuando el refugio la revise, el estado cambia aqui.",
            n, n == 1 ? "" : "es", aprobadas, aprobadas == 1 ? "" : "s");
        gtk_label_set_text(GTK_LABEL(ctx->lbl_solicitudes), txt);
        g_free(txt);
    }
}

static void cargar_donaciones(ContextoApp *ctx) {
    gtk_list_store_clear(ctx->store_donaciones);
    Donante *ds = NULL;
    int n = 0;
    if (donante_listar(&ds, &n) != 0) {
        gtk_label_set_text(GTK_LABEL(ctx->lbl_total_donado), "No se pudo cargar tu historial (revisa la conexion).");
        return;
    }
    double total = 0.0;
    int mias = 0;
    char buf[G_ASCII_DTOSTR_BUF_SIZE];
    for (int i = 0; i < n; i++) {
        /* Solo las donaciones hechas con el correo de este Cliente */
        if (strcmp(ds[i].contacto, ctx->cliente.correo) != 0) continue;
        g_ascii_formatd(buf, sizeof(buf), "%.2f", ds[i].monto);
        GtkTreeIter iter;
        gtk_list_store_append(ctx->store_donaciones, &iter);
        gtk_list_store_set(ctx->store_donaciones, &iter,
            COL_DON_FECHA, ds[i].fecha,
            COL_DON_MONTO, buf,
            -1);
        total += ds[i].monto;
        mias++;
    }
    free(ds);
    g_ascii_formatd(buf, sizeof(buf), "%.2f", total);
    gchar *txt = g_strdup_printf("Has hecho %d donacion%s. Total donado: %s. Gracias por ayudar a los animales.",
        mias, mias == 1 ? "" : "es", buf);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_total_donado), txt);
    g_free(txt);
}

static void on_actualizar_catalogo_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    cargar_catalogo((ContextoApp *)datos);
}

static void on_solicitar_adopcion_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;

    GtkTreeModel *modelo;
    GtkTreeIter iter;
    if (!gtk_tree_selection_get_selected(ctx->sel_catalogo, &modelo, &iter)) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Elige primero una mascota de la lista.", TRUE);
        return;
    }
    gint id = 0;
    gchar *nombre = NULL;
    gtk_tree_model_get(modelo, &iter, COL_CAT_ID, &id, COL_CAT_NOMBRE, &nombre, -1);

    int ya = solicitud_existe_activa(id, ctx->cliente.id);
    if (ya < 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo revisar tus solicitudes (revisa la conexion).", TRUE);
        g_free(nombre);
        return;
    }
    if (ya == 1) {
        gchar *msg = g_strdup_printf("Ya tienes una solicitud en curso para %s. Mira la pestana \"Mis mascotas\".", nombre);
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, FALSE);
        g_free(msg);
        g_free(nombre);
        return;
    }

    gchar *titulo = g_strdup_printf("Solicitar adopcion de %s", nombre);
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(titulo, GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL, "_Enviar solicitud", GTK_RESPONSE_OK, NULL);
    g_free(titulo);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 440, -1);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area), 14);
    gtk_box_set_spacing(GTK_BOX(area), 6);
    GtkWidget *lbl = gtk_label_new("Cuentanos por que quieres adoptar (opcional):");
    gtk_widget_set_halign(lbl, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(area), lbl, FALSE, FALSE, 0);
    GtkWidget *entrada = gtk_entry_new();
    gtk_entry_set_max_length(GTK_ENTRY(entrada), 400);
    gtk_entry_set_activates_default(GTK_ENTRY(entrada), TRUE);
    gtk_box_pack_start(GTK_BOX(area), entrada, FALSE, FALSE, 0);
    gtk_dialog_set_default_response(GTK_DIALOG(dialogo), GTK_RESPONSE_OK);
    gtk_widget_show_all(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        gchar *mensaje = g_strstrip(g_strdup(gtk_entry_get_text(GTK_ENTRY(entrada))));
        char fecha[16];
        fecha_hoy(fecha, sizeof(fecha));
        gtk_widget_destroy(dialogo);
        if (solicitud_crear(id, ctx->cliente.id, fecha, mensaje) == 0) {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana),
                "Solicitud enviada. El refugio la revisara y veras el resultado en la pestana \"Mis mascotas\".", FALSE);
            cargar_solicitudes(ctx);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo enviar la solicitud (revisa la conexion).", TRUE);
        }
        g_free(mensaje);
    } else {
        gtk_widget_destroy(dialogo);
    }
    g_free(nombre);
}

static void on_actualizar_solicitudes_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    cargar_solicitudes((ContextoApp *)datos);
}

static void on_donar_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;

    gchar *texto = g_strstrip(g_strdup(gtk_entry_get_text(GTK_ENTRY(ctx->entry_monto))));
    g_strdelimit(texto, ",", '.');
    char *fin = NULL;
    double monto = g_ascii_strtod(texto, &fin);
    gboolean valido = texto[0] != '\0' && fin && *fin == '\0' && monto > 0.0 && monto <= 1000000.0;
    g_free(texto);
    if (!valido) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Escribe un monto valido, mayor que 0. Ejemplo: 50 o 25.50", TRUE);
        return;
    }

    char buf[G_ASCII_DTOSTR_BUF_SIZE];
    g_ascii_formatd(buf, sizeof(buf), "%.2f", monto);
    gchar *pregunta = g_strdup_printf("Registrar una donacion de %s?", buf);
    GtkWidget *dialogo = gtk_message_dialog_new(GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        GTK_MESSAGE_QUESTION, GTK_BUTTONS_YES_NO, "%s", pregunta);
    g_free(pregunta);
    int resp = gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);
    if (resp != GTK_RESPONSE_YES) return;

    Donante d;
    memset(&d, 0, sizeof(d));
    snprintf(d.nombre, sizeof(d.nombre), "%s", ctx->cliente.nombre);
    snprintf(d.contacto, sizeof(d.contacto), "%s", ctx->cliente.correo);
    d.monto = monto;
    fecha_hoy(d.fecha, sizeof(d.fecha));
    if (donante_agregar(&d) == 0) {
        gtk_entry_set_text(GTK_ENTRY(ctx->entry_monto), "");
        cargar_donaciones(ctx);
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Donacion registrada. Muchas gracias!", FALSE);
    } else {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo registrar la donacion (revisa la conexion).", TRUE);
    }
}

/* Al cambiar de pestana se vuelven a cargar los datos de esa pestana. */
static void on_pestana_cambiada(GtkNotebook *nb, GtkWidget *pagina, guint num, gpointer datos) {
    (void)nb; (void)pagina;
    ContextoApp *ctx = datos;
    switch (num) {
        case 0: cargar_mis_vacunas(ctx); break;
        case 1: cargar_catalogo(ctx); break;
        case 2: cargar_solicitudes(ctx); break;
        case 3: cargar_donaciones(ctx); break;
        default: break;
    }
}

/* ---------- PDF: carnet de vacunas y comprobantes ----------
 * El PDF se genera con pawos-generar-pdf-documento.py y se guarda donde
 * el Cliente elija. Despues se puede abrir, enviar por correo o por
 * WhatsApp (pawos-enviar-documento, las mismas credenciales que los
 * recordatorios de citas), o simplemente llevarlo en la carpeta elegida. */

#define SCRIPT_PDF   "/usr/local/bin/pawos-generar-pdf-documento.py"
#define SCRIPT_ENVIO "/usr/local/bin/pawos-enviar-documento"

typedef enum { PDF_CARNET, PDF_DONACIONES, PDF_SOLICITUDES } TipoPdf;

static gchar *limpiar_celda(const char *t) {
    gchar *c = g_strdup(t ? t : "");
    g_strdelimit(c, "|\n", ' ');
    return g_strstrip(c);
}

/* Lee todas las filas de una tabla y las deja como "a|b|c". */
static GPtrArray *filas_desde_store(GtkListStore *store, const int *cols, int ncols) {
    GPtrArray *filas = g_ptr_array_new_with_free_func(g_free);
    GtkTreeModel *m = GTK_TREE_MODEL(store);
    GtkTreeIter it;
    gboolean hay = gtk_tree_model_get_iter_first(m, &it);
    while (hay) {
        GString *fila = g_string_new("");
        for (int i = 0; i < ncols; i++) {
            gchar *v = NULL;
            gtk_tree_model_get(m, &it, cols[i], &v, -1);
            gchar *lim = limpiar_celda(v);
            g_free(v);
            if (i > 0) g_string_append_c(fila, '|');
            g_string_append(fila, lim);
            g_free(lim);
        }
        g_ptr_array_add(filas, g_string_free(fila, FALSE));
        hay = gtk_tree_model_iter_next(m, &it);
    }
    return filas;
}

static gchar *pedir_destino(GtkWindow *padre, const char *titulo, const char *etiqueta, const char *inicial) {
    GtkWidget *d = gtk_dialog_new_with_buttons(titulo, padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL, "_Enviar", GTK_RESPONSE_OK, NULL);
    gtk_window_set_default_size(GTK_WINDOW(d), 400, -1);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(d));
    gtk_container_set_border_width(GTK_CONTAINER(area), 14);
    gtk_box_set_spacing(GTK_BOX(area), 6);
    GtkWidget *lbl = gtk_label_new(etiqueta);
    gtk_label_set_line_wrap(GTK_LABEL(lbl), TRUE);
    gtk_widget_set_halign(lbl, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(area), lbl, FALSE, FALSE, 0);
    GtkWidget *entrada = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(entrada), inicial ? inicial : "");
    gtk_entry_set_activates_default(GTK_ENTRY(entrada), TRUE);
    gtk_box_pack_start(GTK_BOX(area), entrada, FALSE, FALSE, 0);
    gtk_dialog_set_default_response(GTK_DIALOG(d), GTK_RESPONSE_OK);
    gtk_widget_show_all(d);
    gchar *res = NULL;
    if (gtk_dialog_run(GTK_DIALOG(d)) == GTK_RESPONSE_OK) {
        res = g_strstrip(g_strdup(gtk_entry_get_text(GTK_ENTRY(entrada))));
        if (res[0] == '\0') { g_free(res); res = NULL; }
    }
    gtk_widget_destroy(d);
    return res;
}

static void enviar_documento(GtkWindow *padre, const char *canal, const char *destino,
                             const char *ruta, const char *asunto, const char *mensaje) {
    gchar *argv[] = { "sudo", "-n", (gchar *)SCRIPT_ENVIO,
        "--canal", (gchar *)canal, "--destino", (gchar *)destino, "--pdf", (gchar *)ruta,
        "--asunto", (gchar *)asunto, "--mensaje", (gchar *)mensaje, NULL };
    gchar *salida = NULL, *err = NULL;
    gint estado = 0;
    GError *gerr = NULL;

    gtk_widget_set_sensitive(GTK_WIDGET(padre), FALSE);
    while (gtk_events_pending()) gtk_main_iteration();
    gboolean lanzado = g_spawn_sync(NULL, argv, NULL, G_SPAWN_SEARCH_PATH, NULL, NULL,
                                    &salida, &err, &estado, &gerr);
    gtk_widget_set_sensitive(GTK_WIDGET(padre), TRUE);

    if (lanzado && estado == 0) {
        gchar *msg = g_strdup_printf("Enviado a %s.", destino);
        mostrar_mensaje(padre, msg, FALSE);
        g_free(msg);
    } else if (err && (strstr(err, "password is required") || strstr(err, "terminal is required"))) {
        mostrar_mensaje(padre,
            "Falta instalar el permiso de envio. En una terminal ejecuta:\n"
            "sudo bash instalar-documentos.sh", TRUE);
    } else {
        gchar *detalle = (err && err[0]) ? g_strstrip(g_strndup(err, 300))
                                         : g_strdup(gerr ? gerr->message : "Error desconocido.");
        gchar *msg = g_strdup_printf("No se pudo enviar.\n\n%s", detalle);
        mostrar_mensaje(padre, msg, TRUE);
        g_free(msg);
        g_free(detalle);
    }
    if (gerr) g_error_free(gerr);
    g_free(salida);
    g_free(err);
}

/* Ventana que sale cuando el PDF ya esta guardado: abrir o enviar. */
static void acciones_pdf(ContextoApp *ctx, const char *ruta, const char *nombre_doc) {
    GtkWidget *d = gtk_dialog_new_with_buttons("PDF listo", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cerrar", GTK_RESPONSE_CLOSE, NULL);
    gtk_dialog_add_button(GTK_DIALOG(d), "Abrir PDF", 1);
    gtk_dialog_add_button(GTK_DIALOG(d), "Enviar por correo", 2);
    gtk_dialog_add_button(GTK_DIALOG(d), "Enviar por WhatsApp", 3);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(d));
    gtk_container_set_border_width(GTK_CONTAINER(area), 14);
    gchar *texto = g_strdup_printf("%s guardado en:\n%s\n\nQue quieres hacer ahora?", nombre_doc, ruta);
    GtkWidget *lbl = gtk_label_new(texto);
    g_free(texto);
    gtk_label_set_line_wrap(GTK_LABEL(lbl), TRUE);
    gtk_label_set_selectable(GTK_LABEL(lbl), TRUE);
    gtk_widget_set_halign(lbl, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(area), lbl, FALSE, FALSE, 0);
    gtk_widget_show_all(d);

    for (;;) {
        int r = gtk_dialog_run(GTK_DIALOG(d));
        if (r == 1) {
            gchar *uri = g_filename_to_uri(ruta, NULL, NULL);
            GError *e = NULL;
            if (!uri || !g_app_info_launch_default_for_uri(uri, NULL, &e)) {
                mostrar_mensaje(GTK_WINDOW(d), "No se pudo abrir el PDF (no hay un visor instalado).", TRUE);
                if (e) g_error_free(e);
            }
            g_free(uri);
        } else if (r == 2) {
            gchar *dest = pedir_destino(GTK_WINDOW(d), "Enviar por correo",
                "Enviar el PDF a este correo:", ctx->cliente.correo);
            if (dest) {
                if (!strchr(dest, '@') || !strchr(strchr(dest, '@'), '.')) {
                    mostrar_mensaje(GTK_WINDOW(d), "Escribe un correo valido.", TRUE);
                } else {
                    gchar *asunto = g_strdup_printf("%s - PawOS Refugio", nombre_doc);
                    gchar *mensaje = g_strdup_printf("Hola %s,\n\nAdjuntamos tu documento: %s.\n\n-- PawOS Refugio",
                        ctx->cliente.nombre, nombre_doc);
                    enviar_documento(GTK_WINDOW(d), "correo", dest, ruta, asunto, mensaje);
                    g_free(asunto);
                    g_free(mensaje);
                }
                g_free(dest);
            }
        } else if (r == 3) {
            gchar *dest = pedir_destino(GTK_WINDOW(d), "Enviar por WhatsApp",
                "Numero de WhatsApp, con codigo de pais y sin signos.\nEjemplo: 50258381311",
                ctx->cliente.telefono);
            if (dest) {
                char digitos[64];
                solo_digitos(dest, digitos, sizeof(digitos));
                if (strlen(digitos) < 10) {
                    mostrar_mensaje(GTK_WINDOW(d),
                        "Escribe el numero completo, con el codigo de pais (por ejemplo 502...).", TRUE);
                } else {
                    gchar *mensaje = g_strdup_printf("Hola %s, te enviamos tu documento: %s. -- PawOS Refugio",
                        ctx->cliente.nombre, nombre_doc);
                    enviar_documento(GTK_WINDOW(d), "whatsapp", digitos, ruta, nombre_doc, mensaje);
                    g_free(mensaje);
                }
                g_free(dest);
            }
        } else {
            break;
        }
    }
    gtk_widget_destroy(d);
}

static void generar_y_ofrecer_pdf(ContextoApp *ctx, TipoPdf tipo) {
    const char *titulo = "", *columnas = "", *base = "documento";
    GPtrArray *filas = NULL;
    gchar *resumen = NULL;

    if (tipo == PDF_CARNET) {
        static const int cols[] = { COL_V_MASCOTA, COL_V_VACUNA, COL_V_PROXIMA, COL_V_ESTADO };
        cargar_mis_vacunas(ctx);
        titulo = "Carnet de vacunas";
        columnas = "Mascota|Vacuna|Proxima dosis|Estado";
        base = "carnet_vacunas";
        filas = filas_desde_store(ctx->store_vacunas, cols, 4);
        resumen = g_strdup_printf("%u vacuna(s) registrada(s).", filas->len);
    } else if (tipo == PDF_SOLICITUDES) {
        static const int cols[] = { COL_SOL_MASCOTA, COL_SOL_FECHA, COL_SOL_ESTADO, COL_SOL_MENSAJE };
        cargar_solicitudes(ctx);
        titulo = "Comprobante de solicitudes de adopcion";
        columnas = "Mascota|Fecha|Estado|Mi mensaje";
        base = "solicitudes_adopcion";
        filas = filas_desde_store(ctx->store_solicitudes, cols, 4);
        resumen = g_strdup_printf("%u solicitud(es) de adopcion.", filas->len);
    } else {
        static const int cols[] = { COL_DON_FECHA, COL_DON_MONTO };
        cargar_donaciones(ctx);
        titulo = "Comprobante de donaciones";
        columnas = "Fecha|Monto";
        base = "donaciones";
        filas = filas_desde_store(ctx->store_donaciones, cols, 2);
        double total = 0.0;
        for (guint i = 0; i < filas->len; i++) {
            const char *barra = strchr(g_ptr_array_index(filas, i), '|');
            if (barra) total += g_ascii_strtod(barra + 1, NULL);
        }
        char buf[G_ASCII_DTOSTR_BUF_SIZE];
        g_ascii_formatd(buf, sizeof(buf), "%.2f", total);
        resumen = g_strdup_printf("Total donado: %s. Gracias por ayudar a los animales.", buf);
    }

    /* Donde guardarlo */
    char hoy[16];
    fecha_hoy(hoy, sizeof(hoy));
    GtkWidget *selector = gtk_file_chooser_dialog_new("Guardar PDF", GTK_WINDOW(ctx->ventana),
        GTK_FILE_CHOOSER_ACTION_SAVE, "_Cancelar", GTK_RESPONSE_CANCEL, "_Guardar", GTK_RESPONSE_ACCEPT, NULL);
    gtk_file_chooser_set_do_overwrite_confirmation(GTK_FILE_CHOOSER(selector), TRUE);
    gchar *nombre_sugerido = g_strdup_printf("%s_%s.pdf", base, hoy);
    gtk_file_chooser_set_current_name(GTK_FILE_CHOOSER(selector), nombre_sugerido);
    g_free(nombre_sugerido);
    GtkFileFilter *filtro = gtk_file_filter_new();
    gtk_file_filter_set_name(filtro, "Documentos PDF");
    gtk_file_filter_add_pattern(filtro, "*.pdf");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(selector), filtro);

    gchar *ruta = NULL;
    if (gtk_dialog_run(GTK_DIALOG(selector)) == GTK_RESPONSE_ACCEPT) {
        gchar *elegida = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(selector));
        if (elegida) {
            ruta = g_str_has_suffix(elegida, ".pdf") ? g_strdup(elegida) : g_strconcat(elegida, ".pdf", NULL);
            g_free(elegida);
        }
    }
    gtk_widget_destroy(selector);

    if (ruta) {
        const char *script = SCRIPT_PDF;
        if (!g_file_test(script, G_FILE_TEST_EXISTS)) {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana),
                "Falta instalar el generador de PDF. En una terminal ejecuta:\n"
                "sudo bash instalar-documentos.sh", TRUE);
        } else {
            gchar *cliente = g_strdup_printf("%s (%s)", ctx->cliente.nombre, ctx->cliente.correo);
            /* Para el carnet: foto de perfil (archivo temporal) y datos del titular */
            gchar *foto_tmp = NULL;
            gchar *id_txt = g_strdup_printf("%d", ctx->cliente.id);
            if (tipo == PDF_CARNET) {
                char *b64 = NULL;
                if (cliente_obtener_foto(ctx->cliente.id, &b64) == 0 && b64 && b64[0]) {
                    gsize largo = 0;
                    guchar *bytes = g_base64_decode(b64, &largo);
                    gchar *nombre_tmp = g_strdup_printf("pawos_foto_%d.png", (int)getpid());
                    gchar *ruta_tmp = g_build_filename(g_get_tmp_dir(), nombre_tmp, NULL);
                    if (largo > 0 && g_file_set_contents(ruta_tmp, (const gchar *)bytes, (gssize)largo, NULL))
                        foto_tmp = g_strdup(ruta_tmp);
                    g_free(ruta_tmp);
                    g_free(nombre_tmp);
                    g_free(bytes);
                }
                free(b64);
            }

            GPtrArray *argv = g_ptr_array_new();
            g_ptr_array_add(argv, (gpointer)"python3");
            g_ptr_array_add(argv, (gpointer)script);
            g_ptr_array_add(argv, (gpointer)"--titulo");   g_ptr_array_add(argv, (gpointer)titulo);
            g_ptr_array_add(argv, (gpointer)"--cliente");  g_ptr_array_add(argv, cliente);
            g_ptr_array_add(argv, (gpointer)"--columnas"); g_ptr_array_add(argv, (gpointer)columnas);
            for (guint i = 0; i < filas->len; i++) {
                g_ptr_array_add(argv, (gpointer)"--fila");
                g_ptr_array_add(argv, g_ptr_array_index(filas, i));
            }
            g_ptr_array_add(argv, (gpointer)"--resumen");  g_ptr_array_add(argv, resumen);
            g_ptr_array_add(argv, (gpointer)"--salida");   g_ptr_array_add(argv, ruta);
            if (tipo == PDF_CARNET) {
                g_ptr_array_add(argv, (gpointer)"--estilo");      g_ptr_array_add(argv, (gpointer)"carnet");
                g_ptr_array_add(argv, (gpointer)"--nombre");      g_ptr_array_add(argv, ctx->cliente.nombre);
                g_ptr_array_add(argv, (gpointer)"--correo");      g_ptr_array_add(argv, ctx->cliente.correo);
                g_ptr_array_add(argv, (gpointer)"--telefono");    g_ptr_array_add(argv, ctx->cliente.telefono);
                g_ptr_array_add(argv, (gpointer)"--cliente-id");  g_ptr_array_add(argv, id_txt);
                if (foto_tmp) {
                    g_ptr_array_add(argv, (gpointer)"--foto");    g_ptr_array_add(argv, foto_tmp);
                }
            }
            g_ptr_array_add(argv, NULL);

            gchar *err = NULL;
            gint estado = 0;
            GError *gerr = NULL;
            gboolean ok = g_spawn_sync(NULL, (gchar **)argv->pdata, NULL, G_SPAWN_SEARCH_PATH,
                                       NULL, NULL, NULL, &err, &estado, &gerr);
            if (ok && estado == 0) {
                acciones_pdf(ctx, ruta, titulo);
            } else {
                gchar *detalle = (err && err[0]) ? g_strstrip(g_strndup(err, 300))
                                                 : g_strdup(gerr ? gerr->message : "Error desconocido.");
                gchar *msg = g_strdup_printf("No se pudo generar el PDF.\n\n%s", detalle);
                mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, TRUE);
                g_free(msg);
                g_free(detalle);
            }
            if (gerr) g_error_free(gerr);
            g_free(err);
            g_ptr_array_free(argv, TRUE);
            if (foto_tmp) { g_unlink(foto_tmp); g_free(foto_tmp); }
            g_free(id_txt);
            g_free(cliente);
        }
        g_free(ruta);
    }
    g_ptr_array_free(filas, TRUE);
    g_free(resumen);
}

static void on_pdf_carnet_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    generar_y_ofrecer_pdf((ContextoApp *)datos, PDF_CARNET);
}

static void on_pdf_solicitudes_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    generar_y_ofrecer_pdf((ContextoApp *)datos, PDF_SOLICITUDES);
}

static void on_pdf_donaciones_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    generar_y_ofrecer_pdf((ContextoApp *)datos, PDF_DONACIONES);
}

static GtkWidget *nueva_pagina(void) {
    GtkWidget *p = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_set_border_width(GTK_CONTAINER(p), 16);
    return p;
}

static GtkWidget *nueva_etiqueta_info(void) {
    GtkWidget *l = gtk_label_new("");
    gtk_widget_set_halign(l, GTK_ALIGN_START);
    gtk_widget_set_hexpand(l, TRUE);
    gtk_label_set_line_wrap(GTK_LABEL(l), TRUE);
    return l;
}

static void agregar_pestanas_cliente(ContextoApp *ctx, GtkWidget *notebook) {
    /* ----- Mascotas en adopcion ----- */
    GtkWidget *pag_cat = nueva_pagina();
    GtkWidget *barra_cat = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    ctx->lbl_catalogo = nueva_etiqueta_info();
    gtk_box_pack_start(GTK_BOX(barra_cat), ctx->lbl_catalogo, TRUE, TRUE, 0);
    GtkWidget *btn_act_cat = gtk_button_new_with_label("Actualizar");
    g_signal_connect(btn_act_cat, "clicked", G_CALLBACK(on_actualizar_catalogo_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra_cat), btn_act_cat, FALSE, FALSE, 0);
    GtkWidget *btn_solicitar = gtk_button_new_with_label("Solicitar adopcion");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_solicitar), "pawos-accion");
    g_signal_connect(btn_solicitar, "clicked", G_CALLBACK(on_solicitar_adopcion_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra_cat), btn_solicitar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(pag_cat), barra_cat, FALSE, FALSE, 0);

    ctx->store_catalogo = gtk_list_store_new(N_COLUMNAS_CATALOGO,
        G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    GtkWidget *tv_cat = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store_catalogo));
    anadir_columna(tv_cat, "Nombre", COL_CAT_NOMBRE, -1, TRUE);
    anadir_columna(tv_cat, "Especie", COL_CAT_ESPECIE, -1, FALSE);
    anadir_columna(tv_cat, "Raza", COL_CAT_RAZA, -1, FALSE);
    anadir_columna(tv_cat, "Edad", COL_CAT_EDAD, -1, FALSE);
    anadir_columna(tv_cat, "Ingreso al refugio", COL_CAT_INGRESO, -1, FALSE);
    ctx->sel_catalogo = gtk_tree_view_get_selection(GTK_TREE_VIEW(tv_cat));
    gtk_tree_selection_set_mode(ctx->sel_catalogo, GTK_SELECTION_SINGLE);
    gtk_box_pack_start(GTK_BOX(pag_cat), tarjeta_con_tabla(tv_cat), TRUE, TRUE, 0);
    gtk_notebook_append_page(GTK_NOTEBOOK(notebook), pag_cat, gtk_label_new("Mascotas en adopcion"));

    /* ----- Mis mascotas (solicitudes y su estado) ----- */
    GtkWidget *pag_sol = nueva_pagina();
    GtkWidget *barra_sol = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    ctx->lbl_solicitudes = nueva_etiqueta_info();
    gtk_box_pack_start(GTK_BOX(barra_sol), ctx->lbl_solicitudes, TRUE, TRUE, 0);
    GtkWidget *btn_pdf_sol = gtk_button_new_with_label("Comprobante en PDF");
    g_signal_connect(btn_pdf_sol, "clicked", G_CALLBACK(on_pdf_solicitudes_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra_sol), btn_pdf_sol, FALSE, FALSE, 0);
    GtkWidget *btn_act_sol = gtk_button_new_with_label("Actualizar");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_act_sol), "pawos-accion");
    g_signal_connect(btn_act_sol, "clicked", G_CALLBACK(on_actualizar_solicitudes_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra_sol), btn_act_sol, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(pag_sol), barra_sol, FALSE, FALSE, 0);

    ctx->store_solicitudes = gtk_list_store_new(N_COLUMNAS_SOLICITUD,
        G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    GtkWidget *tv_sol = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store_solicitudes));
    anadir_columna(tv_sol, "Mascota", COL_SOL_MASCOTA, -1, FALSE);
    anadir_columna(tv_sol, "Fecha", COL_SOL_FECHA, -1, FALSE);
    anadir_columna(tv_sol, "Estado", COL_SOL_ESTADO, COL_SOL_COLOR, FALSE);
    anadir_columna(tv_sol, "Mi mensaje", COL_SOL_MENSAJE, -1, TRUE);
    gtk_box_pack_start(GTK_BOX(pag_sol), tarjeta_con_tabla(tv_sol), TRUE, TRUE, 0);
    gtk_notebook_append_page(GTK_NOTEBOOK(notebook), pag_sol, gtk_label_new("Mis mascotas"));

    /* ----- Donar ----- */
    GtkWidget *pag_don = nueva_pagina();
    GtkWidget *tarjeta_form = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 10);
    gtk_style_context_add_class(gtk_widget_get_style_context(tarjeta_form), "pawos-tarjeta");
    GtkWidget *lbl_monto = gtk_label_new("Monto a donar:");
    gtk_box_pack_start(GTK_BOX(tarjeta_form), lbl_monto, FALSE, FALSE, 0);
    ctx->entry_monto = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(ctx->entry_monto), "Ej. 50 o 25.50");
    gtk_entry_set_width_chars(GTK_ENTRY(ctx->entry_monto), 16);
    gtk_box_pack_start(GTK_BOX(tarjeta_form), ctx->entry_monto, FALSE, FALSE, 0);
    GtkWidget *btn_donar = gtk_button_new_with_label("Donar");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_donar), "pawos-accion");
    g_signal_connect(btn_donar, "clicked", G_CALLBACK(on_donar_clicked), ctx);
    g_signal_connect(ctx->entry_monto, "activate", G_CALLBACK(on_donar_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(tarjeta_form), btn_donar, FALSE, FALSE, 0);
    GtkWidget *btn_pdf_don = gtk_button_new_with_label("Comprobante en PDF");
    g_signal_connect(btn_pdf_don, "clicked", G_CALLBACK(on_pdf_donaciones_clicked), ctx);
    gtk_box_pack_end(GTK_BOX(tarjeta_form), btn_pdf_don, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(pag_don), tarjeta_form, FALSE, FALSE, 0);

    ctx->lbl_total_donado = nueva_etiqueta_info();
    gtk_box_pack_start(GTK_BOX(pag_don), ctx->lbl_total_donado, FALSE, FALSE, 0);

    ctx->store_donaciones = gtk_list_store_new(N_COLUMNAS_DONACION, G_TYPE_STRING, G_TYPE_STRING);
    GtkWidget *tv_don = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store_donaciones));
    anadir_columna(tv_don, "Fecha", COL_DON_FECHA, -1, FALSE);
    anadir_columna(tv_don, "Monto", COL_DON_MONTO, -1, TRUE);
    gtk_box_pack_start(GTK_BOX(pag_don), tarjeta_con_tabla(tv_don), TRUE, TRUE, 0);
    gtk_notebook_append_page(GTK_NOTEBOOK(notebook), pag_don, gtk_label_new("Donar"));

    g_signal_connect(notebook, "switch-page", G_CALLBACK(on_pestana_cambiada), ctx);
}

/* ---------- Ventana principal ---------- */

static void construir_ventana(ContextoApp *ctx) {
    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Portal de Clientes");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 900, 620);
    gtk_window_set_position(GTK_WINDOW(ctx->ventana), GTK_WIN_POS_CENTER);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *caja_raiz = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja_raiz);

    GtkWidget *encabezado = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 10);
    gtk_style_context_add_class(gtk_widget_get_style_context(encabezado), "pawos-header");
    GtkWidget *lbl_titulo = gtk_label_new(NULL);
    gchar *markup_titulo = g_strdup_printf(
        "<span size='large' weight='bold'>\xF0\x9F\x90\xBE Hola, %s</span>  <span size='small'>(%s)</span>",
        ctx->cliente.nombre, cliente_rol_nombre(ctx->cliente.rol));
    gtk_label_set_markup(GTK_LABEL(lbl_titulo), markup_titulo);
    g_free(markup_titulo);
    gtk_box_pack_start(GTK_BOX(encabezado), lbl_titulo, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja_raiz), encabezado, FALSE, FALSE, 0);

    GtkWidget *contenido = gtk_box_new(GTK_ORIENTATION_VERTICAL, 14);
    gtk_container_set_border_width(GTK_CONTAINER(contenido), 16);
    gtk_widget_set_vexpand(contenido, TRUE);
    /* Pestanas: Mi perfil (lo de siempre) + adopcion, mis mascotas y donar */
    GtkWidget *notebook = gtk_notebook_new();
    gtk_box_pack_start(GTK_BOX(caja_raiz), notebook, TRUE, TRUE, 0);
    gtk_notebook_append_page(GTK_NOTEBOOK(notebook), contenido, gtk_label_new("Mi perfil"));

    /* Tarjeta de datos de contacto (foto + correo/telefono + acciones) */
    GtkWidget *tarjeta_perfil = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 10);
    gtk_style_context_add_class(gtk_widget_get_style_context(tarjeta_perfil), "pawos-tarjeta");

    GtkWidget *caja_avatar = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    ctx->imagen_avatar = gtk_image_new();
    gtk_widget_set_size_request(ctx->imagen_avatar, FOTO_AVATAR_SIZE, FOTO_AVATAR_SIZE);
    gtk_box_pack_start(GTK_BOX(caja_avatar), ctx->imagen_avatar, FALSE, FALSE, 0);
    GtkWidget *btn_cambiar_foto = gtk_button_new_with_label("Cambiar foto");
    g_signal_connect(btn_cambiar_foto, "clicked", G_CALLBACK(on_cambiar_foto_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(caja_avatar), btn_cambiar_foto, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(tarjeta_perfil), caja_avatar, FALSE, FALSE, 0);

    GtkWidget *caja_datos = gtk_box_new(GTK_ORIENTATION_VERTICAL, 2);
    gtk_widget_set_hexpand(caja_datos, TRUE);
    gtk_widget_set_valign(caja_datos, GTK_ALIGN_CENTER);
    gchar *texto_datos = g_strdup_printf("Correo: %s\nTelefono: %s",
        ctx->cliente.correo, ctx->cliente.telefono[0] ? ctx->cliente.telefono : "(no registrado)");
    GtkWidget *lbl_datos = gtk_label_new(texto_datos);
    ctx->lbl_datos = lbl_datos;
    g_free(texto_datos);
    gtk_widget_set_halign(lbl_datos, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja_datos), lbl_datos, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(tarjeta_perfil), caja_datos, TRUE, TRUE, 0);

    GtkWidget *btn_editar_perfil = gtk_button_new_with_label("Editar mi perfil");
    g_signal_connect(btn_editar_perfil, "clicked", G_CALLBACK(on_editar_perfil_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(tarjeta_perfil), btn_editar_perfil, FALSE, FALSE, 0);

    GtkWidget *btn_cerrar_sesion = gtk_button_new_with_label("Cerrar sesion");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_cerrar_sesion), "pawos-peligro");
    g_signal_connect_swapped(btn_cerrar_sesion, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    gtk_box_pack_start(GTK_BOX(tarjeta_perfil), btn_cerrar_sesion, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(contenido), tarjeta_perfil, FALSE, FALSE, 0);

    /* Seccion de recordatorios de vacunas */
    GtkWidget *barra_vacunas = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *lbl_seccion = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(lbl_seccion), "<span weight='bold' size='medium'>Mis recordatorios de vacunas</span>");
    gtk_widget_set_halign(lbl_seccion, GTK_ALIGN_START);
    gtk_widget_set_hexpand(lbl_seccion, TRUE);
    gtk_box_pack_start(GTK_BOX(barra_vacunas), lbl_seccion, TRUE, TRUE, 0);

    GtkWidget *btn_pdf_carnet = gtk_button_new_with_label("Carnet en PDF");
    g_signal_connect(btn_pdf_carnet, "clicked", G_CALLBACK(on_pdf_carnet_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra_vacunas), btn_pdf_carnet, FALSE, FALSE, 0);

    GtkWidget *btn_actualizar = gtk_button_new_with_label("Actualizar");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_actualizar), "pawos-accion");
    g_signal_connect(btn_actualizar, "clicked", G_CALLBACK(on_actualizar_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra_vacunas), btn_actualizar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(contenido), barra_vacunas, FALSE, FALSE, 0);

    GtkWidget *tarjeta_vacunas = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_style_context_add_class(gtk_widget_get_style_context(tarjeta_vacunas), "pawos-tarjeta");
    gtk_widget_set_vexpand(tarjeta_vacunas, TRUE);

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_vexpand(scroll, TRUE);

    ctx->store_vacunas = gtk_list_store_new(N_COLUMNAS_VACUNA,
        G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    GtkWidget *treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store_vacunas));

    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(treeview),
        -1, "Mascota", gtk_cell_renderer_text_new(), "text", COL_V_MASCOTA, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(treeview),
        -1, "Vacuna", gtk_cell_renderer_text_new(), "text", COL_V_VACUNA, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(treeview),
        -1, "Proxima dosis", gtk_cell_renderer_text_new(), "text", COL_V_PROXIMA, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(treeview),
        -1, "Estado", gtk_cell_renderer_text_new(), "text", COL_V_ESTADO, "foreground", COL_V_COLOR, NULL);

    gtk_container_add(GTK_CONTAINER(scroll), treeview);
    gtk_box_pack_start(GTK_BOX(tarjeta_vacunas), scroll, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(contenido), tarjeta_vacunas, TRUE, TRUE, 0);

    agregar_pestanas_cliente(ctx, notebook);

    gtk_widget_show_all(ctx->ventana);
}

int main(int argc, char *argv[]) {
    gtk_init(&argc, &argv);

    const char *ruta_bd = (argc > 1) ? argv[1] : RUTA_BD_DEFECTO;
    if (db_init(ruta_bd) != 0) {
        fprintf(stderr, "Aviso: no se pudo usar %s, usando ./pawos.db\n", ruta_bd);
        if (db_init("pawos.db") != 0) {
            fprintf(stderr, "No se pudo inicializar la base de datos.\n");
            return 1;
        }
    }

    aplicar_estilos_simples();

    ContextoApp ctx;
    memset(&ctx, 0, sizeof(ctx));

    if (!mostrar_login(&ctx.cliente)) {
        db_close();
        return 0;
    }

    construir_ventana(&ctx);
    cargar_avatar(&ctx);
    cargar_mis_vacunas(&ctx);

    gtk_main();
    db_close();
    return 0;
}
