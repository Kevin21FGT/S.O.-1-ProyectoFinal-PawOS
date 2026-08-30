
#include <ncurses.h>
#include <string.h>
#include <stdlib.h>
#include "pantalla_archivos.h"
#include "archivos/archivos.h"
#include "ui/ui.h"

static void ver_categoria_pantalla(const char *categoria) {
    ArchivoInfo *lista; int n;
    if (archivos_listar(categoria, &lista, &n) != 0) {
        ui_mensaje("No se pudo leer esa categoria.", 1);
        return;
    }
    clear();
    mvprintw(1, 2, "Archivos en '%s' (%d)", categoria, n);
    mvprintw(3, 2, "%-30s %-12s %-16s", "Nombre", "Tamano", "Modificado");
    int filas_disp = LINES - 6;
    for (int i = 0; i < n && i < filas_disp; i++) {
        mvprintw(4 + i, 2, "%-30s %-12ld %-16s",
                 lista[i].nombre, lista[i].tamano_bytes, lista[i].fecha_mod);
    }
    if (n > filas_disp) mvprintw(4 + filas_disp, 2, "... y %d mas", n - filas_disp);
    mvprintw(LINES - 1, 2, "Presione una tecla para continuar...");
    refresh();
    getch();
    free(lista);
}
static void explorar_por_categoria(void) {
    while (1) {
        const char *cats_menu[ARCHIVOS_NUM_CATEGORIAS + 1];
        for (int i = 0; i < ARCHIVOS_NUM_CATEGORIAS; i++) cats_menu[i] = ARCHIVOS_CATEGORIAS[i];
        cats_menu[ARCHIVOS_NUM_CATEGORIAS] = "Volver";
        int csel = ui_menu("Elija una categoria", cats_menu, ARCHIVOS_NUM_CATEGORIAS + 1);
        if (csel < 0 || csel == ARCHIVOS_NUM_CATEGORIAS) return;
        ver_categoria_pantalla(ARCHIVOS_CATEGORIAS[csel]);
    }
}

static void eliminar_archivo_pantalla(const char *categoria) {
    char nombre[ARCHIVOS_MAX_NOMBRE];
    ui_pedir_texto("Nombre exacto del archivo a eliminar:", nombre, sizeof(nombre));
    if (archivos_eliminar(categoria, nombre) == 0)
        ui_mensaje("Archivo eliminado.", 0);
    else
        ui_mensaje("No se pudo eliminar (verifique el nombre).", 1);
}
static void eliminar_por_categoria(void) {
    while (1) {
        const char *cats_menu[ARCHIVOS_NUM_CATEGORIAS + 1];
        for (int i = 0; i < ARCHIVOS_NUM_CATEGORIAS; i++) cats_menu[i] = ARCHIVOS_CATEGORIAS[i];
        cats_menu[ARCHIVOS_NUM_CATEGORIAS] = "Volver";
        int csel = ui_menu("Eliminar de que categoria?", cats_menu, ARCHIVOS_NUM_CATEGORIAS + 1);
        if (csel < 0 || csel == ARCHIVOS_NUM_CATEGORIAS) return;
        eliminar_archivo_pantalla(ARCHIVOS_CATEGORIAS[csel]);
    }
}
static void ver_espacio_pantalla(void) {
    clear();
    mvprintw(1, 2, "Espacio usado por categoria");
    for (int i = 0; i < ARCHIVOS_NUM_CATEGORIAS; i++) {
        long bytes = archivos_espacio_categoria(ARCHIVOS_CATEGORIAS[i]);
        mvprintw(3 + i, 2, "%-12s %8ld bytes", ARCHIVOS_CATEGORIAS[i], bytes < 0 ? 0 : bytes);
    }
    mvprintw(LINES - 1, 2, "Presione una tecla para continuar...");
    refresh();
    getch();
}

void pantalla_archivos(Rol rol) {
    while (1) {
        const char *op_admin[] = {
            "Ver archivos por categoria",
            "Eliminar un archivo",
            "Generar respaldo de la base de datos",
            "Ver espacio usado",
            "Volver"
        };
        const char *op_vol[] = { "Ver archivos por categoria", "Ver espacio usado", "Volver" };
        const char **opciones = (rol == ROL_VOLUNTARIO) ? op_vol : op_admin;
        int n = (rol == ROL_VOLUNTARIO) ? 3 : 5;
        int sel = ui_menu("Sistema de Archivos Organizado", opciones, n);
        if (sel < 0 || sel == n - 1) return;

        if (rol == ROL_VOLUNTARIO) {
            if (sel == 0) {
                explorar_por_categoria();
            }
else if (sel == 1) {
                ver_espacio_pantalla();
            }
        } else {
            if (sel == 0) {
                explorar_por_categoria();
            } else if (sel == 1) {
                eliminar_por_categoria();
            } else if (sel == 2) {
                if (archivos_respaldar_bd_auto() == 0)
                    ui_mensaje("Respaldo generado correctamente.", 0);
                else
                    ui_mensaje("No se pudo generar el respaldo.", 1);
            } 
else if (sel == 3) {
                ver_espacio_pantalla();
            }
        }
    }
}
