#include <ncurses.h>
#include <string.h>
#include <stdlib.h>
#include "pantalla_memoria.h"
#include "memoria.h"

#define ID_PROCESO_DEMO 1

static void *direccion_demo = NULL;
static int proceso_demo_creado = 0;

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

static void ver_estadisticas(void) {
    estadisticas_memoria_t est = memoria_obtener_estadisticas();

    clear();
    mvprintw(1, 2, "=== Estado de la memoria del sistema ===");
    mvprintw(3, 2, "Memoria total:       %u KB", est.memoria_total_bytes / 1024);
    mvprintw(4, 2, "Paginas totales:     %u", est.paginas_totales);
    mvprintw(5, 2, "Paginas usadas:      %u", est.paginas_usadas);
    mvprintw(6, 2, "Paginas libres:      %u", est.paginas_libres);
    mvprintw(7, 2, "Page faults:         %u", est.page_faults);
    mvprintw(8, 2, "Swaps realizados:    %u", est.swaps_realizados);

    pausar();
}

static void crear_proceso_demo(void) {
    clear();
    mvprintw(1, 2, "=== Crear proceso de ejemplo (memoria) ===");

    if (proceso_demo_creado) {
        mvprintw(3, 2, "Ya existe un proceso de ejemplo activo (ID %d).", ID_PROCESO_DEMO);
        pausar();
        return;
    }

    tabla_paginas_t *tabla = memoria_crear_proceso(ID_PROCESO_DEMO);
    if (tabla == NULL) {
        mvprintw(3, 2, "Error: no se pudo crear el proceso de ejemplo.");
    } else {
        proceso_demo_creado = 1;
        mvprintw(3, 2, "Proceso de ejemplo creado (ID %d) con su tabla de paginas.", ID_PROCESO_DEMO);
    }

    pausar();
}

static void asignar_memoria(void) {
    clear();
    mvprintw(1, 2, "=== Asignar memoria al proceso de ejemplo ===");

    if (!proceso_demo_creado) {
        mvprintw(3, 2, "Primero cree el proceso de ejemplo (opcion anterior).");
        pausar();
        return;
    }

    int bytes = pedir_entero(3, 2, "Cuantos bytes desea asignar? ");
    void *direccion = memoria_asignar(ID_PROCESO_DEMO, (uint32_t)bytes);

    if (direccion == NULL) {
        mvprintw(5, 2, "Error: no se pudo asignar memoria (sin espacio disponible).");
    } else {
        direccion_demo = direccion;
        mvprintw(5, 2, "Memoria asignada correctamente en direccion virtual %p.", direccion);
    }

    pausar();
}

static void probar_lectura_escritura(void) {
    clear();
    mvprintw(1, 2, "=== Probar escritura y lectura ===");

    if (!proceso_demo_creado || direccion_demo == NULL) {
        mvprintw(3, 2, "Primero cree el proceso y asigne memoria.");
        pausar();
        return;
    }

    int valor = pedir_entero(3, 2, "Valor a escribir (0-255): ");
    memoria_escribir_byte(ID_PROCESO_DEMO, direccion_demo, (uint8_t)valor);
    uint8_t leido = memoria_leer_byte(ID_PROCESO_DEMO, direccion_demo);

    mvprintw(5, 2, "Valor escrito: %d", valor);
    mvprintw(6, 2, "Valor leido:   %d %s", leido, (leido == valor) ? "(coincide)" : "(no coincide)");

    pausar();
}

static void destruir_proceso_demo(void) {
    clear();
    mvprintw(1, 2, "=== Destruir proceso de ejemplo ===");

    if (!proceso_demo_creado) {
        mvprintw(3, 2, "No hay ningun proceso de ejemplo activo.");
        pausar();
        return;
    }

    memoria_destruir_proceso(ID_PROCESO_DEMO);
    proceso_demo_creado = 0;
    direccion_demo = NULL;

    mvprintw(3, 2, "Proceso de ejemplo destruido, memoria liberada.");
    pausar();
}

void pantalla_memoria(Rol rol) {
    if (rol != ROL_ADMIN) {
        clear();
        mvprintw(1, 2, "=== Administracion de Memoria ===");
        mvprintw(3, 2, "Acceso denegado: esta seccion es solo para el Administrador.");
        pausar();
        return;
    }

    const char *opciones[] = {
        "Ver estadisticas de memoria",
        "Crear proceso de ejemplo",
        "Asignar memoria al proceso",
        "Probar escritura/lectura",
        "Destruir proceso de ejemplo",
        "Volver al menu principal"
    };
    int n_opciones = 6;
    int seleccion = 0;
    int tecla;

    while (1) {
        clear();
        mvprintw(1, 2, "=== Administracion de Memoria ===");
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
                case 0: ver_estadisticas(); break;
                case 1: crear_proceso_demo(); break;
                case 2: asignar_memoria(); break;
                case 3: probar_lectura_escritura(); break;
                case 4: destruir_proceso_demo(); break;
                case 5: return;
            }
        }
    }
}