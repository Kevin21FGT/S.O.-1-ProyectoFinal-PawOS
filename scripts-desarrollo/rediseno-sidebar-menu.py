#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rediseno del menu principal al estilo "panel de administracion" (como el
ejemplo AYUMED que compartio Kevin): barra lateral de navegacion a la
izquierda (color de marca, un item por modulo con icono + texto) y panel
de contenido blanco/claro a la derecha con una franja superior y una
tarjeta de bienvenida, en vez de la cuadricula de botones de colores.

No se toca ninguna logica: mismos manejadores (clicks), mismo
modulo_permitido() por indice original, mismo orden_visual[] agrupado
por seccion, mismos botones de Buscar Actualizaciones / Acerca de /
Salir con sus mismas conexiones de señal.

Se agregan clases CSS nuevas (.pawos-sidebar, .pawos-nav-item,
.pawos-contenido, .pawos-contenido-topbar, .pawos-tarjeta) al final del
bloque de aplicar_estilos(), sin tocar ni reordenar ninguna de las 27
reglas/variables que ya existian.
"""
import shutil
import re
import sys
from pathlib import Path

ARCHIVO = Path("src/main_gtk.c")

ANCLA_CSS = r'''        "placessidebar row, .sidebar row {"
        "  color: %s;"
        "}",
        fondo_ventana, color_texto,
        fondo_ventana, color_texto,
        boton_bg, boton_fg,
        ruta_fondo_bienvenida,
        ruta_fondo_colaborador,
        boton_bg, boton_fg, boton_borde, boton_bg_hover,
        deshabilitado_bg, deshabilitado_fg,
        fondo_tabla, texto_tabla,
        seleccion_bg, seleccion_fg,
        fondo_dialogo,
        fondo_dialogo, color_texto, boton_borde,
        fondo_dialogo, color_texto,
        fondo_dialogo, color_texto, color_texto);'''

NUEVO_CSS = r'''        "placessidebar row, .sidebar row {"
        "  color: %s;"
        "}"

        /* Barra lateral de navegacion del menu principal (estilo tipo
         * panel de administracion): franja solida en el color de marca
         * en vez de la imagen de fondo, para que se vea limpia junto
         * al panel de contenido claro. */
        ".pawos-sidebar {"
        "  background-image: linear-gradient(180deg, #23924B 0%%, #12451F 100%%);"
        "  padding: 22px 16px;"
        "}"
        ".pawos-sidebar label { color: #FFFFFF; }"
        ".pawos-sidebar-titulo { color: #FFFFFF; }"
        ".pawos-nav-item {"
        "  background-color: transparent;"
        "  background-image: none;"
        "  color: #FFFFFF;"
        "  border: none;"
        "  box-shadow: none;"
        "  border-radius: 8px;"
        "  font-weight: normal;"
        "  padding: 8px 10px;"
        "}"
        ".pawos-nav-item:hover {"
        "  background-color: rgba(255,255,255,0.16);"
        "}"
        ".pawos-contenido {"
        "  background-color: %s;"
        "}"
        ".pawos-contenido label { color: %s; }"
        ".pawos-contenido-topbar {"
        "  border-bottom: 1px solid %s;"
        "  padding-bottom: 14px;"
        "}"
        ".pawos-tarjeta {"
        "  background-color: %s;"
        "  border-radius: 14px;"
        "  padding: 22px;"
        "  box-shadow: 0 2px 8px rgba(0,0,0,0.12);"
        "}",
        fondo_ventana, color_texto,
        fondo_ventana, color_texto,
        boton_bg, boton_fg,
        ruta_fondo_bienvenida,
        ruta_fondo_colaborador,
        boton_bg, boton_fg, boton_borde, boton_bg_hover,
        deshabilitado_bg, deshabilitado_fg,
        fondo_tabla, texto_tabla,
        seleccion_bg, seleccion_fg,
        fondo_dialogo,
        fondo_dialogo, color_texto, boton_borde,
        fondo_dialogo, color_texto,
        fondo_dialogo, color_texto, color_texto,
        fondo_dialogo, color_texto, boton_borde, fondo_dialogo);'''

ANCLA_FUNCION = r'''static void construir_ventana_principal(Rol rol, const char *usuario) {
    GtkWidget *ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ventana), "PawOS Refugio");
    gtk_window_set_default_size(GTK_WINDOW(ventana), 900, 700);
    gtk_window_set_resizable(GTK_WINDOW(ventana), TRUE);
    gtk_window_set_position(GTK_WINDOW(ventana), GTK_WIN_POS_CENTER);
    gtk_container_set_border_width(GTK_CONTAINER(ventana), 22);
    g_signal_connect(ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 16);
    gtk_container_add(GTK_CONTAINER(ventana), caja);
    gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-fondo-dinamico");
    agregar_barra_titulo_con_maximizar(GTK_WINDOW(ventana), "PawOS Refugio");

    /* Banner de encabezado: titulo + insignia de rol con color propio,
     * en vez de una simple etiqueta de texto plano. */
    GtkWidget *banner = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_style_context_add_class(gtk_widget_get_style_context(banner), "encabezado-banner");
    gtk_box_pack_start(GTK_BOX(caja), banner, FALSE, FALSE, 0);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='x-large' weight='bold'>\xF0\x9F\x90\xBE PawOS Refugio</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_CENTER);
    gtk_box_pack_start(GTK_BOX(banner), titulo, FALSE, FALSE, 0);

    GtkWidget *lbl_version = gtk_label_new(NULL);
    gchar *markup_version = g_strdup_printf("<span size='small'>v%s</span>", PAWOS_VERSION);
    gtk_label_set_markup(GTK_LABEL(lbl_version), markup_version);
    g_free(markup_version);
    gtk_widget_set_halign(lbl_version, GTK_ALIGN_CENTER);
    gtk_style_context_add_class(gtk_widget_get_style_context(lbl_version), "subtitulo-banner");
    gtk_box_pack_start(GTK_BOX(banner), lbl_version, FALSE, FALSE, 0);

    GtkWidget *fila_usuario = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_set_halign(fila_usuario, GTK_ALIGN_CENTER);
    gtk_box_pack_start(GTK_BOX(banner), fila_usuario, FALSE, FALSE, 0);

    GtkWidget *lbl_bienvenida = gtk_label_new(NULL);
    gchar *texto_bienvenida = g_strdup_printf("Bienvenido, %s", usuario);
    gtk_label_set_text(GTK_LABEL(lbl_bienvenida), texto_bienvenida);
    g_free(texto_bienvenida);
    gtk_style_context_add_class(gtk_widget_get_style_context(lbl_bienvenida), "subtitulo-banner");
    gtk_box_pack_start(GTK_BOX(fila_usuario), lbl_bienvenida, FALSE, FALSE, 0);

    GtkWidget *badge_rol = gtk_label_new(auth_rol_nombre(rol));
    gtk_style_context_add_class(gtk_widget_get_style_context(badge_rol), "badge");
    const char *clase_badge =
        (rol == ROL_ADMIN)         ? "badge-admin" :
        (rol == ROL_VETERINARIO)   ? "badge-veterinario" :
        (rol == ROL_RESCATISTA)    ? "badge-rescatista" :
        (rol == ROL_RECEPCIONISTA) ? "badge-recepcionista" : "badge-voluntario";
    gtk_style_context_add_class(gtk_widget_get_style_context(badge_rol), clase_badge);
    gtk_box_pack_start(GTK_BOX(fila_usuario), badge_rol, FALSE, FALSE, 0);

    GtkWidget *cuadricula = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(cuadricula), 12);
    gtk_grid_set_column_spacing(GTK_GRID(cuadricula), 12);
    gtk_grid_set_column_homogeneous(GTK_GRID(cuadricula), TRUE);
    gtk_widget_set_vexpand(cuadricula, TRUE);
    gtk_box_pack_start(GTK_BOX(caja), cuadricula, TRUE, TRUE, 0);

    const char *nombres_modulos[] = {
        "Gestion de Mascotas",
        "Agenda de Vacunas",
        "Control de Adopciones",
        "Base de Donantes",
        "Reportes",
        "Administracion de Procesos",
        "Administracion de Memoria",
        "Respaldo en la Nube",
        "Alertas de Sensores",
        "Administrar Colaboradores",
        "Configurar Notificaciones",
        "Administrar Clientes",
    };
    /* Icono (emoji) por modulo, solo cosmetico -- no afecta la logica. */
    const char *iconos_modulos[] = {
        "\xF0\x9F\x90\xBE", /* paw */
        "\xF0\x9F\x92\x89", /* syringe */
        "\xF0\x9F\x8F\xA0", /* house */
        "\xF0\x9F\x92\xB0", /* money bag */
        "\xF0\x9F\x93\x8A", /* bar chart */
        "\xE2\x9A\x99",     /* gear */
        "\xF0\x9F\xA7\xA0", /* brain */
        "\xE2\x98\x81",     /* cloud */
        "\xF0\x9F\x9A\xA8", /* siren */
        "\xF0\x9F\x91\xA5", /* people */
        "\xF0\x9F\x93\xA7", /* envelope */
        "\xF0\x9F\x9B\x82", /* briefcase */
    };
    /* Categoria por modulo (solo cosmetica, define el color del boton):
     * refugio = atencion directa al animal, gestion = administrativo,
     * sistema = infraestructura del S.O. */
    const char *categorias_modulos[] = {
        "cat-refugio", "cat-refugio", "cat-refugio", "cat-gestion",
        "cat-gestion", "cat-sistema", "cat-sistema", "cat-gestion", "cat-refugio",
        "cat-gestion", "cat-gestion", "cat-gestion",
    };
    GCallback manejadores[] = {
        G_CALLBACK(on_mascotas_clicked),
        G_CALLBACK(on_vacunas_clicked),
        G_CALLBACK(on_adopciones_clicked),
        G_CALLBACK(on_donantes_clicked),
        G_CALLBACK(on_reportes_clicked),
        G_CALLBACK(on_procesos_clicked),
        G_CALLBACK(on_memoria_clicked),
        G_CALLBACK(on_respaldo_clicked),
        G_CALLBACK(on_alertas_clicked),
        G_CALLBACK(on_administrar_colaboradores_clicked),
        G_CALLBACK(on_configurar_notificaciones_clicked),
        G_CALLBACK(on_administrar_clientes_clicked),
    };
    const int total_modulos = 12;

    DatosBotonModulo *datos_botones = g_malloc(sizeof(DatosBotonModulo));
    datos_botones->ventana_principal = ventana;
    datos_botones->rol = rol;
    datos_botones->usuario = usuario;
    g_signal_connect(ventana, "destroy", G_CALLBACK(liberar_contexto), datos_botones);

    /* Orden VISUAL de los modulos, agrupados por seccion. Este arreglo
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

    GtkWidget *btn_actualizar = gtk_button_new_with_label("\xF0\x9F\x94\x84  Buscar Actualizaciones");
    gtk_widget_set_size_request(btn_actualizar, 250, 46);
    gtk_widget_set_halign(btn_actualizar, GTK_ALIGN_CENTER);
    gtk_widget_set_tooltip_text(btn_actualizar, "Busca la ultima version en GitHub y la instala.");
    gtk_box_pack_start(GTK_BOX(caja), btn_actualizar, FALSE, FALSE, 0);
    g_signal_connect(btn_actualizar, "clicked", G_CALLBACK(on_actualizar_clicked), datos_botones);

    GtkWidget *btn_acerca_de = gtk_button_new_with_label("Acerca de");
    gtk_widget_set_size_request(btn_acerca_de, 250, 46);
    gtk_widget_set_halign(btn_acerca_de, GTK_ALIGN_CENTER);
    gtk_box_pack_start(GTK_BOX(caja), btn_acerca_de, FALSE, FALSE, 0);
    g_signal_connect(btn_acerca_de, "clicked", G_CALLBACK(on_acerca_de_clicked), datos_botones);

    GtkWidget *btn_salir = gtk_button_new_with_label("Salir");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_salir), "salir");
    gtk_widget_set_size_request(btn_salir, 250, 46);
    gtk_widget_set_halign(btn_salir, GTK_ALIGN_CENTER);
    gtk_box_pack_start(GTK_BOX(caja), btn_salir, FALSE, FALSE, 0);
    g_signal_connect_swapped(btn_salir, "clicked", G_CALLBACK(gtk_widget_destroy), ventana);

    /* Maximizamos al final, ya con todo el contenido agregado, para que
     * el gestor de ventanas calcule el tamaño definitivo antes de pedir
     * el maximizado (evita que quede una ventana pequeña sin poder
     * agrandarse). */
    gtk_window_maximize(GTK_WINDOW(ventana));
    mostrar_con_fundido(ventana);
}'''

NUEVO_FUNCION = r'''static void construir_ventana_principal(Rol rol, const char *usuario) {
    GtkWidget *ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ventana), "PawOS Refugio");
    gtk_window_set_default_size(GTK_WINDOW(ventana), 900, 700);
    gtk_window_set_resizable(GTK_WINDOW(ventana), TRUE);
    gtk_window_set_position(GTK_WINDOW(ventana), GTK_WIN_POS_CENTER);
    gtk_container_set_border_width(GTK_CONTAINER(ventana), 0);
    g_signal_connect(ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    /* Estructura tipo panel de administracion: barra lateral de
     * navegacion a la izquierda (color de marca) + panel de contenido
     * a la derecha (fondo claro/oscuro segun el tema), en vez de la
     * columna unica de botones grandes. */
    GtkWidget *caja_raiz = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_container_add(GTK_CONTAINER(ventana), caja_raiz);
    agregar_barra_titulo_con_maximizar(GTK_WINDOW(ventana), "PawOS Refugio");

    GtkWidget *barra_lateral = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_style_context_add_class(gtk_widget_get_style_context(barra_lateral), "pawos-sidebar");
    gtk_widget_set_size_request(barra_lateral, 260, -1);
    gtk_box_pack_start(GTK_BOX(caja_raiz), barra_lateral, FALSE, FALSE, 0);

    GtkWidget *lbl_logo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(lbl_logo), "<span size='large' weight='bold'>\xF0\x9F\x90\xBE PawOS Refugio</span>");
    gtk_widget_set_halign(lbl_logo, GTK_ALIGN_START);
    gtk_style_context_add_class(gtk_widget_get_style_context(lbl_logo), "pawos-sidebar-titulo");
    gtk_box_pack_start(GTK_BOX(barra_lateral), lbl_logo, FALSE, FALSE, 0);

    GtkWidget *lbl_version = gtk_label_new(NULL);
    gchar *markup_version = g_strdup_printf("<span size='small'>v%s</span>", PAWOS_VERSION);
    gtk_label_set_markup(GTK_LABEL(lbl_version), markup_version);
    g_free(markup_version);
    gtk_widget_set_halign(lbl_version, GTK_ALIGN_START);
    gtk_widget_set_margin_bottom(lbl_version, 14);
    gtk_style_context_add_class(gtk_widget_get_style_context(lbl_version), "subtitulo-banner");
    gtk_box_pack_start(GTK_BOX(barra_lateral), lbl_version, FALSE, FALSE, 0);

    const char *nombres_modulos[] = {
        "Gestion de Mascotas",
        "Agenda de Vacunas",
        "Control de Adopciones",
        "Base de Donantes",
        "Reportes",
        "Administracion de Procesos",
        "Administracion de Memoria",
        "Respaldo en la Nube",
        "Alertas de Sensores",
        "Administrar Colaboradores",
        "Configurar Notificaciones",
        "Administrar Clientes",
    };
    /* Icono (emoji) por modulo, solo cosmetico -- no afecta la logica. */
    const char *iconos_modulos[] = {
        "\xF0\x9F\x90\xBE", /* paw */
        "\xF0\x9F\x92\x89", /* syringe */
        "\xF0\x9F\x8F\xA0", /* house */
        "\xF0\x9F\x92\xB0", /* money bag */
        "\xF0\x9F\x93\x8A", /* bar chart */
        "\xE2\x9A\x99",     /* gear */
        "\xF0\x9F\xA7\xA0", /* brain */
        "\xE2\x98\x81",     /* cloud */
        "\xF0\x9F\x9A\xA8", /* siren */
        "\xF0\x9F\x91\xA5", /* people */
        "\xF0\x9F\x93\xA7", /* envelope */
        "\xF0\x9F\x9B\x82", /* briefcase */
    };
    /* Categoria por modulo: ya no se usa para el color del boton (todos
     * los items de la barra lateral usan el mismo estilo), se deja
     * declarada por si se retoma mas adelante. */
    const char *categorias_modulos[] = {
        "cat-refugio", "cat-refugio", "cat-refugio", "cat-gestion",
        "cat-gestion", "cat-sistema", "cat-sistema", "cat-gestion", "cat-refugio",
        "cat-gestion", "cat-gestion", "cat-gestion",
    };
    (void)categorias_modulos;
    GCallback manejadores[] = {
        G_CALLBACK(on_mascotas_clicked),
        G_CALLBACK(on_vacunas_clicked),
        G_CALLBACK(on_adopciones_clicked),
        G_CALLBACK(on_donantes_clicked),
        G_CALLBACK(on_reportes_clicked),
        G_CALLBACK(on_procesos_clicked),
        G_CALLBACK(on_memoria_clicked),
        G_CALLBACK(on_respaldo_clicked),
        G_CALLBACK(on_alertas_clicked),
        G_CALLBACK(on_administrar_colaboradores_clicked),
        G_CALLBACK(on_configurar_notificaciones_clicked),
        G_CALLBACK(on_administrar_clientes_clicked),
    };
    const int total_modulos = 12;

    DatosBotonModulo *datos_botones = g_malloc(sizeof(DatosBotonModulo));
    datos_botones->ventana_principal = ventana;
    datos_botones->rol = rol;
    datos_botones->usuario = usuario;
    g_signal_connect(ventana, "destroy", G_CALLBACK(liberar_contexto), datos_botones);

    /* Orden VISUAL de los modulos, agrupados por seccion. Este arreglo
     * solo dice en que orden se DIBUJAN los items -- el indice real de
     * cada modulo (el que usan modulo_permitido() y manejadores[]) es
     * siempre el original, sin cambios. Asi se agrupa la barra lateral
     * sin tocar ni un permiso ni una conexion de boton. */
    const int orden_visual[] = { 0, 1, 2, 8, 3, 4, 7, 9, 10, 11, 5, 6 };
    const char *titulos_seccion[] = {
        "ATENCION AL REFUGIO", NULL, NULL, NULL,
        "GESTION Y ADMINISTRACION", NULL, NULL, NULL, NULL, NULL,
        "SISTEMA", NULL,
    };

    gboolean primera_seccion = TRUE;
    for (int j = 0; j < total_modulos; j++) {
        int i = orden_visual[j];

        if (titulos_seccion[j]) {
            GtkWidget *encabezado = gtk_label_new(NULL);
            gchar *marcado = g_strdup_printf("<span weight='bold' size='small'>%s</span>", titulos_seccion[j]);
            gtk_label_set_markup(GTK_LABEL(encabezado), marcado);
            g_free(marcado);
            gtk_style_context_add_class(gtk_widget_get_style_context(encabezado), "encabezado-seccion");
            gtk_widget_set_halign(encabezado, GTK_ALIGN_START);
            gtk_widget_set_margin_top(encabezado, primera_seccion ? 4 : 16);
            gtk_widget_set_margin_bottom(encabezado, 4);
            gtk_box_pack_start(GTK_BOX(barra_lateral), encabezado, FALSE, FALSE, 0);
            primera_seccion = FALSE;
        }

        gchar *etiqueta = g_strdup_printf("%s  %s", iconos_modulos[i], nombres_modulos[i]);
        GtkWidget *boton = gtk_button_new_with_label(etiqueta);
        g_free(etiqueta);
        gtk_widget_set_size_request(boton, -1, 40);
        gtk_widget_set_halign(gtk_bin_get_child(GTK_BIN(boton)), GTK_ALIGN_START);
        gtk_style_context_add_class(gtk_widget_get_style_context(boton), "pawos-nav-item");
        gtk_box_pack_start(GTK_BOX(barra_lateral), boton, FALSE, FALSE, 0);
        g_signal_connect(boton, "clicked", manejadores[i], datos_botones);

        /* Los items siempre se muestran; solo se deshabilitan (no se
         * ocultan) cuando el rol actual no tiene acceso a ese modulo,
         * igual que ya hacian las pantallas del CLI. */
        if (!modulo_permitido(rol, i)) {
            gtk_widget_set_sensitive(boton, FALSE);
            gtk_widget_set_tooltip_text(boton, "Tu rol no tiene acceso a este modulo.");
        }
    }

    GtkWidget *relleno_lateral = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_set_vexpand(relleno_lateral, TRUE);
    gtk_box_pack_start(GTK_BOX(barra_lateral), relleno_lateral, TRUE, TRUE, 0);

    GtkWidget *encabezado_cuenta = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(encabezado_cuenta), "<span weight='bold' size='small'>CUENTA</span>");
    gtk_style_context_add_class(gtk_widget_get_style_context(encabezado_cuenta), "encabezado-seccion");
    gtk_widget_set_halign(encabezado_cuenta, GTK_ALIGN_START);
    gtk_widget_set_margin_bottom(encabezado_cuenta, 4);
    gtk_box_pack_start(GTK_BOX(barra_lateral), encabezado_cuenta, FALSE, FALSE, 0);

    GtkWidget *btn_actualizar = gtk_button_new_with_label("\xF0\x9F\x94\x84  Buscar Actualizaciones");
    gtk_widget_set_size_request(btn_actualizar, -1, 40);
    gtk_widget_set_halign(gtk_bin_get_child(GTK_BIN(btn_actualizar)), GTK_ALIGN_START);
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_actualizar), "pawos-nav-item");
    gtk_widget_set_tooltip_text(btn_actualizar, "Busca la ultima version en GitHub y la instala.");
    gtk_box_pack_start(GTK_BOX(barra_lateral), btn_actualizar, FALSE, FALSE, 0);
    g_signal_connect(btn_actualizar, "clicked", G_CALLBACK(on_actualizar_clicked), datos_botones);

    GtkWidget *btn_acerca_de = gtk_button_new_with_label("Acerca de");
    gtk_widget_set_size_request(btn_acerca_de, -1, 40);
    gtk_widget_set_halign(gtk_bin_get_child(GTK_BIN(btn_acerca_de)), GTK_ALIGN_START);
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_acerca_de), "pawos-nav-item");
    gtk_box_pack_start(GTK_BOX(barra_lateral), btn_acerca_de, FALSE, FALSE, 0);
    g_signal_connect(btn_acerca_de, "clicked", G_CALLBACK(on_acerca_de_clicked), datos_botones);

    GtkWidget *btn_salir = gtk_button_new_with_label("Salir");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_salir), "salir");
    gtk_widget_set_size_request(btn_salir, -1, 40);
    gtk_widget_set_halign(gtk_bin_get_child(GTK_BIN(btn_salir)), GTK_ALIGN_START);
    gtk_widget_set_margin_top(btn_salir, 6);
    gtk_box_pack_start(GTK_BOX(barra_lateral), btn_salir, FALSE, FALSE, 0);
    g_signal_connect_swapped(btn_salir, "clicked", G_CALLBACK(gtk_widget_destroy), ventana);

    /* Panel de contenido: fondo claro/oscuro segun el tema (igual que
     * el resto de dialogos de la app), con una franja superior tipo
     * "breadcrumb" y una tarjeta de bienvenida, en vez de la imagen de
     * fondo -- se ve mas limpio junto a la barra lateral solida. */
    GtkWidget *panel_contenido = gtk_box_new(GTK_ORIENTATION_VERTICAL, 20);
    gtk_style_context_add_class(gtk_widget_get_style_context(panel_contenido), "pawos-contenido");
    gtk_container_set_border_width(GTK_CONTAINER(panel_contenido), 26);
    gtk_widget_set_hexpand(panel_contenido, TRUE);
    gtk_box_pack_start(GTK_BOX(caja_raiz), panel_contenido, TRUE, TRUE, 0);

    GtkWidget *franja_superior = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    gtk_style_context_add_class(gtk_widget_get_style_context(franja_superior), "pawos-contenido-topbar");
    gtk_box_pack_start(GTK_BOX(panel_contenido), franja_superior, FALSE, FALSE, 0);

    GtkWidget *lbl_bienvenida = gtk_label_new(NULL);
    gchar *texto_bienvenida = g_strdup_printf("Bienvenido, %s", usuario);
    gtk_label_set_text(GTK_LABEL(lbl_bienvenida), texto_bienvenida);
    g_free(texto_bienvenida);
    gtk_widget_set_halign(lbl_bienvenida, GTK_ALIGN_START);
    gtk_widget_set_hexpand(lbl_bienvenida, TRUE);
    gtk_box_pack_start(GTK_BOX(franja_superior), lbl_bienvenida, TRUE, TRUE, 0);

    GtkWidget *badge_rol = gtk_label_new(auth_rol_nombre(rol));
    gtk_style_context_add_class(gtk_widget_get_style_context(badge_rol), "badge");
    const char *clase_badge =
        (rol == ROL_ADMIN)         ? "badge-admin" :
        (rol == ROL_VETERINARIO)   ? "badge-veterinario" :
        (rol == ROL_RESCATISTA)    ? "badge-rescatista" :
        (rol == ROL_RECEPCIONISTA) ? "badge-recepcionista" : "badge-voluntario";
    gtk_style_context_add_class(gtk_widget_get_style_context(badge_rol), clase_badge);
    gtk_box_pack_start(GTK_BOX(franja_superior), badge_rol, FALSE, FALSE, 0);

    GtkWidget *tarjeta_bienvenida = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_style_context_add_class(gtk_widget_get_style_context(tarjeta_bienvenida), "pawos-tarjeta");
    gtk_box_pack_start(GTK_BOX(panel_contenido), tarjeta_bienvenida, FALSE, FALSE, 0);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='x-large' weight='bold'>\xF0\x9F\x90\xBE PawOS Refugio</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(tarjeta_bienvenida), titulo, FALSE, FALSE, 0);

    GtkWidget *lbl_ayuda = gtk_label_new("Selecciona un modulo del menu lateral para comenzar.");
    gtk_widget_set_halign(lbl_ayuda, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(tarjeta_bienvenida), lbl_ayuda, FALSE, FALSE, 0);

    /* Maximizamos al final, ya con todo el contenido agregado, para que
     * el gestor de ventanas calcule el tamaño definitivo antes de pedir
     * el maximizado (evita que quede una ventana pequeña sin poder
     * agrandarse). */
    gtk_window_maximize(GTK_WINDOW(ventana));
    mostrar_con_fundido(ventana);
}'''


def siguiente_backup(ruta: Path) -> Path:
    n = 1
    while True:
        candidato = ruta.with_name(ruta.name + f".bak{n}")
        if not candidato.exists():
            return candidato
        n += 1


def contar_placeholders(texto: str) -> int:
    """Cuenta los %s que son placeholders reales de printf (no %%)."""
    sin_dobles = texto.replace("%%", "")
    return len(re.findall(r"%s", sin_dobles))


def main():
    if not ARCHIVO.exists():
        print(f"ERROR: no se encontro {ARCHIVO}. Ejecuta este script desde la raiz del repo.")
        sys.exit(1)

    contenido = ARCHIVO.read_text(encoding="utf-8")

    anclas = [("ANCLA_CSS", ANCLA_CSS), ("ANCLA_FUNCION", ANCLA_FUNCION)]
    for nombre, ancla in anclas:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: {nombre} aparece {n} veces (se esperaba 1). No se modifico nada.")
            sys.exit(1)

    nuevo_contenido = contenido.replace(ANCLA_CSS, NUEVO_CSS).replace(ANCLA_FUNCION, NUEVO_FUNCION)

    respaldo = siguiente_backup(ARCHIVO)
    shutil.copy(ARCHIVO, respaldo)
    ARCHIVO.write_text(nuevo_contenido, encoding="utf-8")

    print(f"Listo. Respaldo guardado en {respaldo}")
    print("Cambios aplicados:")
    print("  - Menu principal rediseñado con barra lateral de navegacion + panel de contenido")
    print("  - Mismos handlers, mismo modulo_permitido(), mismo orden agrupado por seccion")
    print("  - Nuevas clases CSS: .pawos-sidebar, .pawos-nav-item, .pawos-contenido, .pawos-tarjeta")


if __name__ == "__main__":
    main()
