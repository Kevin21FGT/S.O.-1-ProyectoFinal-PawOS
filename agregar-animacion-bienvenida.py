#!/usr/bin/env python3
"""
agregar-animacion-bienvenida.py

Agrega la secuencia de bienvenida al selector inicial:
  1. Al abrir, se ve centrado "Bienvenid@ a PawOS" (con transicion de
     fundido, usando GtkRevealer -- el mecanismo nativo de GTK para
     este tipo de animacion).
  2. Despues de un momento, ese texto se desvanece y aparece (tambien
     con fundido) la pregunta "Como quieres entrar?" junto con los
     botones.

La pregunta tambien queda centrada verticalmente (antes estaba pegada
abajo). Los botones, por como GTK arma internamente los dialogos,
siempre se quedan anclados en la franja de hasta abajo -- moverlos
junto con el texto exigiria reconstruir como se crean (mas riesgo),
asi que se dejan igual: aparecen con fundido pero en su misma posicion.

No se toca ninguna logica de negocio: los botones siguen siendo los
mismos, con las mismas respuestas (RESPUESTA_COLABORADOR, etc.).

Uso: parado en la raiz del repo:
    python3 agregar-animacion-bienvenida.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------------------
# Parche 1: struct + funcion de apoyo para la transicion, antes de la funcion
# ---------------------------------------------------------------------------
ANCLA_HELPER = '''/* Primera pantalla al abrir PawOS Refugio: elegir si quien entra es
 * personal del refugio (Colaborador, login existente contra la tabla
 * "usuarios") o publico externo (Cliente, tabla "clientes" aparte). */
static TipoEntrada mostrar_selector_entrada(void) {
'''
NUEVO_HELPER = '''/* Datos para la secuencia de bienvenida del selector inicial: primero
 * se ve "Bienvenid@ a PawOS" centrado, y despues de un momento se
 * desvanece para dar paso a la pregunta y los botones. */
typedef struct {
    GtkRevealer *bienvenida;
    GtkRevealer *pregunta;
    GtkRevealer *botones;
} DatosBienvenidaSelector;

static gboolean revelar_pregunta_selector(gpointer datos) {
    DatosBienvenidaSelector *d = (DatosBienvenidaSelector *)datos;
    gtk_revealer_set_reveal_child(d->bienvenida, FALSE);
    gtk_revealer_set_reveal_child(d->pregunta, TRUE);
    gtk_revealer_set_reveal_child(d->botones, TRUE);
    g_free(d);
    return G_SOURCE_REMOVE;
}

/* Primera pantalla al abrir PawOS Refugio: elegir si quien entra es
 * personal del refugio (Colaborador, login existente contra la tabla
 * "usuarios") o publico externo (Cliente, tabla "clientes" aparte). */
static TipoEntrada mostrar_selector_entrada(void) {
'''

# ---------------------------------------------------------------------------
# Parche 2: agregar el revelador de "Bienvenid@ a PawOS" antes de "caja"
# ---------------------------------------------------------------------------
ANCLA_BIENVENIDA = '''    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_style_context_add_class(gtk_widget_get_style_context(area), "pawos-fondo-dinamico");
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
'''
NUEVO_BIENVENIDA = '''    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_style_context_add_class(gtk_widget_get_style_context(area), "pawos-fondo-dinamico");

    GtkWidget *revelador_bienvenida = gtk_revealer_new();
    gtk_revealer_set_transition_type(GTK_REVEALER(revelador_bienvenida), GTK_REVEALER_TRANSITION_TYPE_CROSSFADE);
    gtk_revealer_set_transition_duration(GTK_REVEALER(revelador_bienvenida), 700);
    GtkWidget *bienvenida = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(bienvenida),
        "<span size='xx-large' weight='bold'>Bienvenid@ a PawOS</span>");
    gtk_widget_set_halign(bienvenida, GTK_ALIGN_CENTER);
    gtk_container_add(GTK_CONTAINER(revelador_bienvenida), bienvenida);
    gtk_widget_set_valign(revelador_bienvenida, GTK_ALIGN_CENTER);
    gtk_widget_set_halign(revelador_bienvenida, GTK_ALIGN_CENTER);
    gtk_widget_set_vexpand(revelador_bienvenida, TRUE);
    gtk_container_add(GTK_CONTAINER(area), revelador_bienvenida);
    gtk_revealer_set_reveal_child(GTK_REVEALER(revelador_bienvenida), TRUE);

    GtkWidget *revelador_pregunta = gtk_revealer_new();
    gtk_revealer_set_transition_type(GTK_REVEALER(revelador_pregunta), GTK_REVEALER_TRANSITION_TYPE_CROSSFADE);
    gtk_revealer_set_transition_duration(GTK_REVEALER(revelador_pregunta), 700);
    gtk_widget_set_valign(revelador_pregunta, GTK_ALIGN_CENTER);
    gtk_widget_set_vexpand(revelador_pregunta, TRUE);
    gtk_container_add(GTK_CONTAINER(area), revelador_pregunta);
    gtk_revealer_set_reveal_child(GTK_REVEALER(revelador_pregunta), FALSE);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
'''

# ---------------------------------------------------------------------------
# Parche 3: "caja" ahora va dentro del revelador de la pregunta (centrada,
# ya no pegada abajo), y ya no necesita su propio valign/vexpand
# ---------------------------------------------------------------------------
ANCLA_CAJA = '''    gtk_container_set_border_width(GTK_CONTAINER(caja), 16);
    gtk_container_add(GTK_CONTAINER(area), caja);
    gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-panel-inferior");
    /* La imagen ya trae el logo y el nombre "PawOS" dibujados, asi que
     * no repetimos el titulo aqui -- solo la pregunta, agrupada cerca
     * de los botones en vez de quedar pegada arriba. */
    gtk_widget_set_valign(caja, GTK_ALIGN_END);
    gtk_widget_set_vexpand(caja, TRUE);
    gtk_widget_set_halign(caja, GTK_ALIGN_FILL);
'''
NUEVO_CAJA = '''    gtk_container_set_border_width(GTK_CONTAINER(caja), 16);
    gtk_container_add(GTK_CONTAINER(revelador_pregunta), caja);
    gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-panel-inferior");
    /* La imagen ya trae el logo y el nombre "PawOS" dibujados, asi que
     * no repetimos el titulo aqui -- solo la pregunta. Ya no necesita
     * valign/vexpand propios: el revelador de arriba se encarga de
     * centrarla verticalmente. */
    gtk_widget_set_halign(caja, GTK_ALIGN_FILL);
'''

# ---------------------------------------------------------------------------
# Parche 4: botones -> se envuelven en su propio revelador (aparecen con
# fundido junto con la pregunta), quedan escondidos hasta la transicion
# ---------------------------------------------------------------------------
ANCLA_BOTONES = '''    GtkWidget *panel_botones = gtk_dialog_get_action_area(GTK_DIALOG(dialogo));
    if (panel_botones) {
        gtk_style_context_add_class(gtk_widget_get_style_context(panel_botones), "pawos-panel-inferior");
        gtk_button_box_set_layout(GTK_BUTTON_BOX(panel_botones), GTK_BUTTONBOX_CENTER);
    }
'''
NUEVO_BOTONES = '''    GtkWidget *panel_botones = gtk_dialog_get_action_area(GTK_DIALOG(dialogo));
    GtkWidget *revelador_botones = gtk_revealer_new();
    gtk_revealer_set_transition_type(GTK_REVEALER(revelador_botones), GTK_REVEALER_TRANSITION_TYPE_CROSSFADE);
    gtk_revealer_set_transition_duration(GTK_REVEALER(revelador_botones), 700);
    if (panel_botones) {
        gtk_style_context_add_class(gtk_widget_get_style_context(panel_botones), "pawos-panel-inferior");
        gtk_button_box_set_layout(GTK_BUTTON_BOX(panel_botones), GTK_BUTTONBOX_CENTER);
        GtkWidget *padre_botones = gtk_widget_get_parent(panel_botones);
        if (padre_botones) {
            g_object_ref(panel_botones);
            gtk_container_remove(GTK_CONTAINER(padre_botones), panel_botones);
            gtk_container_add(GTK_CONTAINER(revelador_botones), panel_botones);
            g_object_unref(panel_botones);
            gtk_container_add(GTK_CONTAINER(padre_botones), revelador_botones);
        }
    }
    gtk_revealer_set_reveal_child(GTK_REVEALER(revelador_botones), FALSE);
'''

# ---------------------------------------------------------------------------
# Parche 5: arrancar el temporizador de la transicion justo antes de mostrar
# ---------------------------------------------------------------------------
ANCLA_TIMER = '''    mostrar_con_fundido(dialogo);
    gint respuesta = gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);

    if (respuesta == RESPUESTA_COLABORADOR) return ENTRADA_COLABORADOR;
    if (respuesta == RESPUESTA_CLIENTE) return ENTRADA_CLIENTE;
    return ENTRADA_CANCELAR;
}
'''
NUEVO_TIMER = '''    DatosBienvenidaSelector *datos_bienvenida = g_new0(DatosBienvenidaSelector, 1);
    datos_bienvenida->bienvenida = GTK_REVEALER(revelador_bienvenida);
    datos_bienvenida->pregunta = GTK_REVEALER(revelador_pregunta);
    datos_bienvenida->botones = GTK_REVEALER(revelador_botones);
    g_timeout_add(1600, revelar_pregunta_selector, datos_bienvenida);

    mostrar_con_fundido(dialogo);
    gint respuesta = gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);

    if (respuesta == RESPUESTA_COLABORADOR) return ENTRADA_COLABORADOR;
    if (respuesta == RESPUESTA_CLIENTE) return ENTRADA_CLIENTE;
    return ENTRADA_CANCELAR;
}
'''

PARCHES = [
    ("funcion de apoyo para la transicion", ANCLA_HELPER, NUEVO_HELPER),
    ("revelador de bienvenida", ANCLA_BIENVENIDA, NUEVO_BIENVENIDA),
    ("caja dentro del revelador de la pregunta", ANCLA_CAJA, NUEVO_CAJA),
    ("revelador de los botones", ANCLA_BOTONES, NUEVO_BOTONES),
    ("temporizador de la transicion", ANCLA_TIMER, NUEVO_TIMER),
]


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    for nombre, ancla, _ in PARCHES:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: el bloque de '{nombre}' se encontro {n} veces (se esperaba 1). No se cambio nada.")
            sys.exit(1)

    for _, ancla, nuevo in PARCHES:
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak18")
    print(f"Backup creado: {ARCHIVO}.bak18")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: bienvenida animada agregada.")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
