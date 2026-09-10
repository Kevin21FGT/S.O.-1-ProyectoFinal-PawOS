#!/usr/bin/env python3
"""
reordenar-menu-principal.py

Reorganiza los 12 botones de modulo del menu principal en 3 secciones
con encabezado (Atencion al Refugio, Gestion y Administracion, Sistema),
y les quita la mezcla de 3 colores distintos -- todos usan el mismo
verde de marca ahora, para que se vea mas limpio y menos "raro".

IMPORTANTE sobre seguridad de la logica: el ORDEN VISUAL cambia (donde
aparece cada boton en la pantalla), pero el INDICE real de cada modulo
(el que usa modulo_permitido() para permisos, y el que conecta cada
boton con su funcion en manejadores[]) NO CAMBIA. Solo se agrega un
mapa "orden_visual" que dice en que ORDEN dibujar los botones, sin
tocar a cual modulo/permiso/funcion corresponde cada uno.

Uso: parado en la raiz del repo:
    python3 reordenar-menu-principal.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------------------
# Parche 1: nueva clase CSS para los encabezados de seccion
# ---------------------------------------------------------------------------
ANCLA_CSS = '''        ".subtitulo-banner { color: #D9F2E0; }"
'''
NUEVO_CSS = '''        ".subtitulo-banner { color: #D9F2E0; }"
        ".encabezado-seccion { color: #D9F2E0; letter-spacing: 1px; }"
'''

# ---------------------------------------------------------------------------
# Parche 2: el ciclo que arma los botones -- agrupado en secciones,
# mismo color para todos, mismo indice real para logica y permisos.
# ---------------------------------------------------------------------------
ANCLA_LOOP = '''    for (int i = 0; i < total_modulos; i++) {
        gchar *etiqueta = g_strdup_printf("%s  %s", iconos_modulos[i], nombres_modulos[i]);
        GtkWidget *boton = gtk_button_new_with_label(etiqueta);
        g_free(etiqueta);
        gtk_widget_set_size_request(boton, 250, 58);
        gtk_style_context_add_class(gtk_widget_get_style_context(boton), "modulo");
        gtk_style_context_add_class(gtk_widget_get_style_context(boton), categorias_modulos[i]);
        gtk_grid_attach(GTK_GRID(cuadricula), boton, i % 2, i / 2, 1, 1);
        g_signal_connect(boton, "clicked", manejadores[i], datos_botones);

        /* Los botones siempre se muestran; solo se deshabilitan (no se
         * ocultan) cuando el rol actual no tiene acceso a ese modulo,
         * igual que ya hacian las pantallas del CLI. */
        if (!modulo_permitido(rol, i)) {
            gtk_widget_set_sensitive(boton, FALSE);
            gtk_widget_set_tooltip_text(boton, "Tu rol no tiene acceso a este modulo.");
        }
    }
'''
NUEVO_LOOP = '''    /* Orden VISUAL de los modulos, agrupados por seccion. Este arreglo
     * solo dice en que orden se DIBUJAN los botones -- el indice real
     * de cada modulo (el que usan modulo_permitido() y manejadores[])
     * es siempre el original, sin cambios. Asi se reordena la pantalla
     * sin tocar ni un permiso ni una conexion de boton. */
    const int orden_visual[] = { 0, 1, 2, 8, 3, 4, 7, 9, 10, 11, 5, 6 };
    const char *titulos_seccion[] = {
        "ATENCION AL REFUGIO", NULL, NULL, NULL,
        "GESTION Y ADMINISTRACION", NULL, NULL, NULL, NULL, NULL,
        "SISTEMA", NULL,
    };

    int fila = 0;
    int columna = 0;
    for (int j = 0; j < total_modulos; j++) {
        int i = orden_visual[j];

        if (titulos_seccion[j]) {
            GtkWidget *encabezado = gtk_label_new(NULL);
            gchar *marcado = g_strdup_printf("<span weight='bold' size='small'>%s</span>", titulos_seccion[j]);
            gtk_label_set_markup(GTK_LABEL(encabezado), marcado);
            g_free(marcado);
            gtk_style_context_add_class(gtk_widget_get_style_context(encabezado), "encabezado-seccion");
            gtk_widget_set_halign(encabezado, GTK_ALIGN_START);
            if (fila > 0) gtk_widget_set_margin_top(encabezado, 14);
            gtk_grid_attach(GTK_GRID(cuadricula), encabezado, 0, fila, 2, 1);
            fila++;
            columna = 0;
        }

        gchar *etiqueta = g_strdup_printf("%s  %s", iconos_modulos[i], nombres_modulos[i]);
        GtkWidget *boton = gtk_button_new_with_label(etiqueta);
        g_free(etiqueta);
        gtk_widget_set_size_request(boton, 250, 58);
        gtk_style_context_add_class(gtk_widget_get_style_context(boton), "modulo");
        /* Un solo color de marca para todos los modulos, en vez de la
         * mezcla de 3 colores distintos que se veia desordenada. */
        gtk_style_context_add_class(gtk_widget_get_style_context(boton), "cat-refugio");
        gtk_grid_attach(GTK_GRID(cuadricula), boton, columna, fila, 1, 1);
        g_signal_connect(boton, "clicked", manejadores[i], datos_botones);

        /* Los botones siempre se muestran; solo se deshabilitan (no se
         * ocultan) cuando el rol actual no tiene acceso a ese modulo,
         * igual que ya hacian las pantallas del CLI. */
        if (!modulo_permitido(rol, i)) {
            gtk_widget_set_sensitive(boton, FALSE);
            gtk_widget_set_tooltip_text(boton, "Tu rol no tiene acceso a este modulo.");
        }

        columna++;
        if (columna == 2) {
            columna = 0;
            fila++;
        }
    }
'''

PARCHES = [
    ("CSS de encabezados de seccion", ANCLA_CSS, NUEVO_CSS),
    ("ciclo de botones reagrupado", ANCLA_LOOP, NUEVO_LOOP),
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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak29")
    print(f"Backup creado: {ARCHIVO}.bak29")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: menu principal reagrupado en secciones, un solo color.")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
