#!/usr/bin/env python3
"""
agregar-roles-rescatista-recepcionista.py

Agrega dos roles nuevos de Colaborador, pensados para el enfoque de
"Proteccion Animal" de PawOS:

  - Rescatista: acceso a Gestion de Mascotas (registrar rescatados) y
    Alertas de Sensores. Bloqueado en Vacunas, Adopciones, Donantes,
    Reportes, Procesos, Memoria, Respaldo y Administrar Colaboradores.
  - Recepcionista: acceso a Control de Adopciones y Base de Donantes.
    Bloqueado en el resto.

Alcance: SOLO el GUI (main_gtk.c) y auth.h/auth.c (compartido). El CLI
(ncurses) no se toca en este parche -- sus propias pantallas tendrian
que revisarse aparte si tambien se quiere soportar estos roles ahi.

Requisito: correr DESPUES de agregar-administrar-colaboradores.py.

Uso: parado en la raiz del repo:
    python3 agregar-roles-rescatista-recepcionista.py
"""

import shutil
import sys

ARCHIVO_AUTH_H = "src/auth/auth.h"
ARCHIVO_AUTH_C = "src/auth/auth.c"
ARCHIVO_GTK = "src/main_gtk.c"

# ---------------------------------------------------------------
# auth.h
# ---------------------------------------------------------------
ANCLA_AUTH_H = """typedef enum {
    ROL_ADMIN = 0,
    ROL_VETERINARIO,
    ROL_VOLUNTARIO
} Rol;"""
NUEVO_AUTH_H = """typedef enum {
    ROL_ADMIN = 0,
    ROL_VETERINARIO,
    ROL_VOLUNTARIO,
    ROL_RESCATISTA,     /* responde alertas de sensores, registra animales rescatados */
    ROL_RECEPCIONISTA   /* atiende adopciones y donantes */
} Rol;"""

# ---------------------------------------------------------------
# auth.c
# ---------------------------------------------------------------
ANCLA_AUTH_C = """const char *auth_rol_nombre(Rol r) {
    switch (r) {
        case ROL_ADMIN: return "Administrador";
        case ROL_VETERINARIO: return "Veterinario";
        default: return "Voluntario";
    }
}"""
NUEVO_AUTH_C = """const char *auth_rol_nombre(Rol r) {
    switch (r) {
        case ROL_ADMIN: return "Administrador";
        case ROL_VETERINARIO: return "Veterinario";
        case ROL_RESCATISTA: return "Rescatista";
        case ROL_RECEPCIONISTA: return "Recepcionista";
        default: return "Voluntario";
    }
}"""

# ---------------------------------------------------------------
# main_gtk.c
# ---------------------------------------------------------------

ANCLA_GTK_NOMBRE_ROL = """static const char *nombre_rol_colaborador(int rol) {
    switch (rol) {
        case ROL_ADMIN: return "Administrador";
        case ROL_VETERINARIO: return "Veterinario";
        default: return "Voluntario";
    }
}"""
NUEVO_GTK_NOMBRE_ROL = """static const char *nombre_rol_colaborador(int rol) {
    switch (rol) {
        case ROL_ADMIN: return "Administrador";
        case ROL_VETERINARIO: return "Veterinario";
        case ROL_RESCATISTA: return "Rescatista";
        case ROL_RECEPCIONISTA: return "Recepcionista";
        default: return "Voluntario";
    }
}"""

ANCLA_GTK_COMBO = """    GtkWidget *combo_rol = gtk_combo_box_text_new();
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo_rol), "0", "Administrador");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo_rol), "1", "Veterinario");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo_rol), "2", "Voluntario");
    gtk_combo_box_set_active(GTK_COMBO_BOX(combo_rol), 2);"""
NUEVO_GTK_COMBO = """    GtkWidget *combo_rol = gtk_combo_box_text_new();
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo_rol), "0", "Administrador");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo_rol), "1", "Veterinario");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo_rol), "2", "Voluntario");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo_rol), "3", "Rescatista");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo_rol), "4", "Recepcionista");
    gtk_combo_box_set_active(GTK_COMBO_BOX(combo_rol), 2);"""

ANCLA_GTK_CSS = """        ".badge-admin       { background-color: #E8B23D; color: #3B2A05; }"
        ".badge-veterinario { background-color: #2C8C99; color: #FFFFFF; }"
        ".badge-voluntario  { background-color: #6C7A76; color: #FFFFFF; }\""""
NUEVO_GTK_CSS = """        ".badge-admin       { background-color: #E8B23D; color: #3B2A05; }"
        ".badge-veterinario { background-color: #2C8C99; color: #FFFFFF; }"
        ".badge-voluntario  { background-color: #6C7A76; color: #FFFFFF; }"
        ".badge-rescatista    { background-color: #C1440E; color: #FFFFFF; }"
        ".badge-recepcionista { background-color: #7A4FA3; color: #FFFFFF; }\""""

ANCLA_GTK_BADGE = """    const char *clase_badge =
        (rol == ROL_ADMIN)       ? "badge-admin" :
        (rol == ROL_VETERINARIO) ? "badge-veterinario" : "badge-voluntario";"""
NUEVO_GTK_BADGE = """    const char *clase_badge =
        (rol == ROL_ADMIN)         ? "badge-admin" :
        (rol == ROL_VETERINARIO)   ? "badge-veterinario" :
        (rol == ROL_RESCATISTA)    ? "badge-rescatista" :
        (rol == ROL_RECEPCIONISTA) ? "badge-recepcionista" : "badge-voluntario";"""

ANCLA_GTK_FUNCION_PERMISOS = """static void construir_ventana_principal(Rol rol, const char *usuario) {"""
NUEVO_GTK_FUNCION_PERMISOS = """/* Dice si el rol dado tiene acceso al modulo "indice" (mismo orden
 * que nombres_modulos[] mas abajo):
 *   0=Mascotas 1=Vacunas 2=Adopciones 3=Donantes 4=Reportes
 *   5=Procesos 6=Memoria 7=Respaldo 8=Alertas 9=AdministrarColaboradores
 * Administrador siempre tiene acceso a todo. Veterinario y Voluntario
 * mantienen las mismas reglas de antes; Rescatista y Recepcionista
 * son roles mas acotados, pensados para tareas especificas. */
static gboolean modulo_permitido(Rol rol, int indice) {
    if (rol == ROL_ADMIN) return TRUE;

    switch (rol) {
        case ROL_VETERINARIO:
            return !(indice == 5 || indice == 6 || indice == 9);
        case ROL_VOLUNTARIO:
            return !(indice == 3 || indice == 4 || indice == 5 || indice == 6 || indice == 9);
        case ROL_RESCATISTA:
            return (indice == 0 || indice == 8);
        case ROL_RECEPCIONISTA:
            return (indice == 2 || indice == 3);
        default:
            return FALSE;
    }
}

static void construir_ventana_principal(Rol rol, const char *usuario) {"""

ANCLA_GTK_GATING = """        gboolean bloqueado_voluntario = (i == 3 || i == 4);           /* Donantes, Reportes */
        gboolean bloqueado_no_admin   = (i == 5 || i == 6 || i == 9); /* Procesos, Memoria, Administrar Colaboradores */

        if (bloqueado_voluntario && rol == ROL_VOLUNTARIO) {
            gtk_widget_set_sensitive(boton, FALSE);
            gtk_widget_set_tooltip_text(boton, "Requiere rol Admin o Veterinario.");
        } else if (bloqueado_no_admin && rol != ROL_ADMIN) {
            gtk_widget_set_sensitive(boton, FALSE);
            gtk_widget_set_tooltip_text(boton, "Requiere rol Administrador.");
        }"""
NUEVO_GTK_GATING = """        if (!modulo_permitido(rol, i)) {
            gtk_widget_set_sensitive(boton, FALSE);
            gtk_widget_set_tooltip_text(boton, "Tu rol no tiene acceso a este modulo.");
        }"""


def main():
    archivos = [
        (ARCHIVO_AUTH_H, [(ANCLA_AUTH_H, NUEVO_AUTH_H, "enum Rol")], ".bak"),
        (ARCHIVO_AUTH_C, [(ANCLA_AUTH_C, NUEVO_AUTH_C, "auth_rol_nombre")], ".bak"),
        (ARCHIVO_GTK, [
            (ANCLA_GTK_NOMBRE_ROL, NUEVO_GTK_NOMBRE_ROL, "nombre_rol_colaborador"),
            (ANCLA_GTK_COMBO, NUEVO_GTK_COMBO, "combo de roles"),
            (ANCLA_GTK_CSS, NUEVO_GTK_CSS, "CSS de badges"),
            (ANCLA_GTK_BADGE, NUEVO_GTK_BADGE, "clase_badge"),
            (ANCLA_GTK_FUNCION_PERMISOS, NUEVO_GTK_FUNCION_PERMISOS, "modulo_permitido"),
            (ANCLA_GTK_GATING, NUEVO_GTK_GATING, "gating de botones"),
        ], ".bak12"),
    ]

    for ruta, pares, _ in archivos:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
        except FileNotFoundError:
            print(f"ERROR: no se encontro {ruta}. Corre este script desde la raiz del repo.")
            sys.exit(1)
        for ancla, nuevo, nombre in pares:
            if contenido.count(ancla) != 1:
                print(f"ERROR: en {ruta}, no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
                print("       Puede que agregar-administrar-colaboradores.py no se haya aplicado todavia,")
                print("       o que el archivo ya haya sido modificado. No se cambio nada.")
                sys.exit(1)

    for ruta, pares, backup_sufijo in archivos:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
        for ancla, nuevo, nombre in pares:
            contenido = contenido.replace(ancla, nuevo, 1)
        shutil.copy(ruta, ruta + backup_sufijo)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"{ruta}: OK (backup en {ruta}{backup_sufijo})")

    print("")
    print("Listo. Ahora:  make clean-gui && make gui && make gui-producto")
    print("(y make clean && make all para el CLI, aunque el CLI no tiene estos roles todavia)")


if __name__ == "__main__":
    main()
