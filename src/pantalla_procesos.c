#include <ncurses.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include "pantalla_procesos.h"
#include "procesos.h"

static void pausar(void) {
    mvprintw(LINES - 2, 2, "Presione cualquier tecla para continuar...");
    refresh();
    getch();
}

static int pedir_entero(int fila, int col, const char *etiqueta) {
    char buffer[16];
    echo();
    curs_set(1);
    mvprintw(fila, col, "%s", etiqueta);
    getnstr(buffer, sizeof(buffer) - 1);
    noecho();
    curs_set(0);
    return atoi(buffer);
}

static void ver_procesos_activos(void) {
    ProcesoInfo lista[PROCESOS_MAX];
    int total = procesos_obtener_lista(lista, PROCESOS_MAX);

    clear();
    mvprintw(1, 2, "=== Procesos activos del sistema ===");

    if (total < 0) {
        mvprintw(3, 2, "No se pudo leer la lista de procesos (/proc).");
        pausar();
        return;
    }

    mvprintw(3, 2, "%-8s %-24s %-14s", "PID", "NOMBRE", "ESTADO");
    mvprintw(4, 2, "--------------------------------------------------");

    int fila = 5;
    int max_filas = LINES - 8;
    for (int i = 0; i < total && i < max_filas; i++) {
        mvprintw(fila++, 2, "%-8d %-24s %-14s",
                 lista[i].pid, lista[i].nombre, lista[i].estado);
    }

    mvprintw(fila + 1, 2, "Total de procesos encontrados: %d", total);
    if (total > max_filas) {
        mvprintw(fila + 2, 2, "(mostrando los primeros %d, hay mas)", max_filas);
    }

    pausar();
}

static void crear_proceso_ejemplo(void) {
    clear();
    mvprintw(1, 2, "=== Crear proceso de ejemplo (fork) ===");
    mvprintw(3, 2, "Esto crea un proceso hijo que simula una tarea en");
    mvprintw(4, 2, "segundo plano (por ejemplo, un respaldo de datos).");

    int pid_hijo = procesos_crear_ejemplo();

    if (pid_hijo < 0) {
        mvprintw(6, 2, "Error: no se pudo crear el proceso (fork fallo).");
    } else {
        mvprintw(6, 2, "Proceso hijo creado correctamente.");
        mvprintw(7, 2, "PID del nuevo proceso: %d", pid_hijo);
        mvprintw(8, 2, "El proceso padre (este menu) sigue funcionando");
        mvprintw(9, 2, "mientras el hijo trabaja por su cuenta.");
    }

    pausar();
}

static void terminar_proceso(void) {
    clear();
    mvprintw(1, 2, "=== Terminar un proceso ===");

    int pid = pedir_entero(3, 2, "PID del proceso a terminar: ");
    int forzar = pedir_entero(4, 2, "Forzar cierre? (0 = No / 1 = Si): ");

    int resultado = procesos_terminar(pid, forzar);

    if (resultado == 0) {
        mvprintw(6, 2, "Señal enviada correctamente al proceso %d.", pid);
    } else {
        mvprintw(6, 2, "No se pudo terminar el proceso %d.", pid);
        if (errno == ESRCH) {
            mvprintw(7, 2, "Motivo: ese proceso no existe (ya termino o el PID es incorrecto).");
        } else if (errno == EPERM) {
            mvprintw(7, 2, "Motivo: no tiene permisos para terminar ese proceso.");
        } else {
            mvprintw(7, 2, "Motivo: PID inválido.");
        }
    }

    pausar();
}

void pantalla_procesos(Rol rol) {
    if (rol != ROL_ADMIN) {
        clear();
        mvprintw(1, 2, "=== Administracion de Procesos ===");
        mvprintw(3, 2, "Acceso denegado: esta seccion es solo para el Administrador.");
        pausar();
        return;
    }

    const char *opciones[] = {
        "Ver procesos activos",
        "Crear proceso de ejemplo (fork)",
        "Terminar un proceso",
        "Volver al menu principal"
    };
    int n_opciones = 4;
    int seleccion = 0;
    int tecla;

    while (1) {
        clear();
        mvprintw(1, 2, "=== Administracion de Procesos ===");
        mvprintw(2, 2, "Flechas: moverse | Enter: seleccionar | q: volver");

        for (int i = 0; i < n_opciones; i++) {
            if (i == seleccion) {
                attron(A_REVERSE);
                mvprintw(4 + i, 4, "%s", opciones[i]);
                attroff(A_REVERSE);
            } else {
                mvprintw(4 + i, 4, "%s", opciones[i]);
            }
        }
        refresh();

        tecla = getch();
        if (tecla == KEY_UP) {
            seleccion = (seleccion - 1 + n_opciones) % n_opciones;
        } else if (tecla == KEY_DOWN) {
            seleccion = (seleccion + 1) % n_opciones;
        } else if (tecla == 'q' || tecla == 'Q') {
            return;
        } else if (tecla == '\n' || tecla == KEY_ENTER) {
            switch (seleccion) {
                case 0: ver_procesos_activos(); break;
                case 1: crear_proceso_ejemplo(); break;
                case 2: terminar_proceso(); break;
                case 3: return;
            }
        }
    }
}