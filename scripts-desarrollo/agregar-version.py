#!/usr/bin/env python3
# agregar-version.py - Agrega el include de version.h y una etiqueta
# "vX.Y" debajo del titulo del banner en main_gtk.c. No toca nada mas.
import shutil

RUTA = "src/main_gtk.c"

with open(RUTA) as f:
    contenido = f.read()

if "version.h" in contenido:
    print("Ya estaba aplicado, no se toca nada.")
    raise SystemExit(0)

shutil.copy(RUTA, RUTA + ".bak")

# 1) agregar el include, junto a los otros includes propios de PawOS
viejo_include = '#include "../include/memoria.h"'
nuevo_include = '#include "../include/memoria.h"\n#include "../include/version.h"'
if viejo_include not in contenido:
    print("NO SE ENCONTRO el include de memoria.h -- abortando sin tocar nada")
    raise SystemExit(1)
contenido = contenido.replace(viejo_include, nuevo_include)

# 2) agregar la etiqueta de version debajo del titulo del banner
viejo_titulo = '''    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='x-large' weight='bold'>\\xF0\\x9F\\x90\\xBE PawOS Refugio</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_CENTER);
    gtk_box_pack_start(GTK_BOX(banner), titulo, FALSE, FALSE, 0);'''

nuevo_titulo = '''    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='x-large' weight='bold'>\\xF0\\x9F\\x90\\xBE PawOS Refugio</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_CENTER);
    gtk_box_pack_start(GTK_BOX(banner), titulo, FALSE, FALSE, 0);

    GtkWidget *lbl_version = gtk_label_new(NULL);
    gchar *markup_version = g_strdup_printf("<span size='small'>v%s</span>", PAWOS_VERSION);
    gtk_label_set_markup(GTK_LABEL(lbl_version), markup_version);
    g_free(markup_version);
    gtk_widget_set_halign(lbl_version, GTK_ALIGN_CENTER);
    gtk_style_context_add_class(gtk_widget_get_style_context(lbl_version), "subtitulo-banner");
    gtk_box_pack_start(GTK_BOX(banner), lbl_version, FALSE, FALSE, 0);'''

if viejo_titulo not in contenido:
    print("NO SE ENCONTRO el bloque del titulo -- restaurando backup y abortando")
    shutil.copy(RUTA + ".bak", RUTA)
    raise SystemExit(1)
contenido = contenido.replace(viejo_titulo, nuevo_titulo)

with open(RUTA, "w") as f:
    f.write(contenido)

print("Listo: version.h incluido y etiqueta agregada bajo el titulo.")
