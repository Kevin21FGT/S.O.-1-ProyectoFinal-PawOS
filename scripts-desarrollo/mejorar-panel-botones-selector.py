#!/usr/bin/env python3
"""
mejorar-panel-botones-selector.py

Le da un acabado mas profesional a la franja de abajo del selector
inicial: la pregunta queda centrada y mas grande, los botones se
agrupan al centro (en vez de pegados a la derecha) y cada uno usa un
color segun su funcion -- los mismos colores que ya usa el resto del
programa (Salir = rojo como el boton de salir del menu, Soy Colaborador
= azul como los modulos de gestion, Soy Cliente = verde de marca). Una
franja semitransparente agrupa todo en un solo bloque visual.

Uso: parado en la raiz del repo:
    python3 mejorar-panel-botones-selector.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------------------
# Parche 1: nueva clase CSS para la franja inferior
# ---------------------------------------------------------------------------
ANCLA_CSS = '''        ".pawos-fondo-transparente {"
        "  background-color: transparent;"
        "  background-image: none;"
        "}"
'''
NUEVO_CSS = '''        ".pawos-fondo-transparente {"
        "  background-color: transparent;"
        "  background-image: none;"
        "}"
        ".pawos-panel-inferior {"
        "  background-color: rgba(8,38,18,0.55);"
        "  padding: 14px 20px;"
        "}"
        ".pawos-panel-inferior label { color: #FFFFFF; }"
'''

# ---------------------------------------------------------------------------
# Parche 2: la caja de la pregunta usa la franja en vez de transparente,
# y la pregunta queda centrada y mas grande
# ---------------------------------------------------------------------------
ANCLA_CAJA = '''    gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-fondo-transparente");
    /* La imagen ya trae el logo y el nombre "PawOS" dibujados, asi que
     * no repetimos el titulo aqui -- solo la pregunta, agrupada cerca
     * de los botones en vez de quedar pegada arriba. */
    gtk_widget_set_valign(caja, GTK_ALIGN_END);
    gtk_widget_set_vexpand(caja, TRUE);

    GtkWidget *subtitulo = gtk_label_new("\\xC2\\xBF" "Como quieres entrar?");
    gtk_widget_set_halign(subtitulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), subtitulo, FALSE, FALSE, 0);
'''
NUEVO_CAJA = '''    gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-panel-inferior");
    /* La imagen ya trae el logo y el nombre "PawOS" dibujados, asi que
     * no repetimos el titulo aqui -- solo la pregunta, agrupada cerca
     * de los botones en vez de quedar pegada arriba. */
    gtk_widget_set_valign(caja, GTK_ALIGN_END);
    gtk_widget_set_vexpand(caja, TRUE);
    gtk_widget_set_halign(caja, GTK_ALIGN_FILL);

    GtkWidget *subtitulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(subtitulo),
        "<span size='large' weight='bold'>\\xC2\\xBF" "Como quieres entrar?</span>");
    gtk_widget_set_halign(subtitulo, GTK_ALIGN_CENTER);
    gtk_box_pack_start(GTK_BOX(caja), subtitulo, FALSE, FALSE, 0);
'''

# ---------------------------------------------------------------------------
# Parche 3: panel de botones -> centrado, con colores por funcion
# ---------------------------------------------------------------------------
ANCLA_BOTONES = '''    mostrar_con_fundido(dialogo);
    gint respuesta = gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);

    if (respuesta == RESPUESTA_COLABORADOR) return ENTRADA_COLABORADOR;
    if (respuesta == RESPUESTA_CLIENTE) return ENTRADA_CLIENTE;
    return ENTRADA_CANCELAR;
}
'''
NUEVO_BOTONES = '''    GtkWidget *panel_botones = gtk_dialog_get_action_area(GTK_DIALOG(dialogo));
    if (panel_botones) {
        gtk_style_context_add_class(gtk_widget_get_style_context(panel_botones), "pawos-panel-inferior");
        gtk_button_box_set_layout(GTK_BUTTON_BOX(panel_botones), GTK_BUTTONBOX_CENTER);
    }
    GtkWidget *boton_salir = gtk_dialog_get_widget_for_response(GTK_DIALOG(dialogo), GTK_RESPONSE_CANCEL);
    if (boton_salir) gtk_style_context_add_class(gtk_widget_get_style_context(boton_salir), "salir");
    GtkWidget *boton_colaborador = gtk_dialog_get_widget_for_response(GTK_DIALOG(dialogo), RESPUESTA_COLABORADOR);
    if (boton_colaborador) {
        gtk_style_context_add_class(gtk_widget_get_style_context(boton_colaborador), "modulo");
        gtk_style_context_add_class(gtk_widget_get_style_context(boton_colaborador), "cat-gestion");
    }
    GtkWidget *boton_cliente = gtk_dialog_get_widget_for_response(GTK_DIALOG(dialogo), RESPUESTA_CLIENTE);
    if (boton_cliente) {
        gtk_style_context_add_class(gtk_widget_get_style_context(boton_cliente), "modulo");
        gtk_style_context_add_class(gtk_widget_get_style_context(boton_cliente), "cat-refugio");
    }

    mostrar_con_fundido(dialogo);
    gint respuesta = gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);

    if (respuesta == RESPUESTA_COLABORADOR) return ENTRADA_COLABORADOR;
    if (respuesta == RESPUESTA_CLIENTE) return ENTRADA_CLIENTE;
    return ENTRADA_CANCELAR;
}
'''

PARCHES = [
    ("CSS panel inferior", ANCLA_CSS, NUEVO_CSS),
    ("caja de la pregunta (centrada)", ANCLA_CAJA, NUEVO_CAJA),
    ("panel de botones (centrado y con color)", ANCLA_BOTONES, NUEVO_BOTONES),
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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak17")
    print(f"Backup creado: {ARCHIVO}.bak17")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK.")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
