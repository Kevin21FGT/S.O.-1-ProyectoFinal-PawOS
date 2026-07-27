
/*
 * main.c - Punto de entrada de PawOS Refugio.
 */
#include <ncurses.h>
#include <stdio.h>
#include "../include/db.h"
#include "../include/ui.h"
#include "../include/auth.h"
#include "../include/pantallas.h"
#include "../include/pantalla_procesos.h"
#include "../include/pantalla_memoria.h"
#include "../include/memoria.h"
#include "../include/pantalla_login.h"
#include "../include/archivos.h"
#include "../include/pantalla_archivos.h"
#define RUTA_BD_DEFECTO "/var/pawos/pawos.db"

int main(int argc, char **argv) {
    const char *ruta_bd = (argc > 1) ? argv[1] : RUTA_BD_DEFECTO;
    if (db_init(ruta_bd) != 0) {
        fprintf(stderr, "Aviso: no se pudo usar %s, usando ./pawos.db\n", ruta_bd);
        if (db_init("pawos.db") != 0) {
            fprintf(stderr, "No se pudo inicializar la base de datos.\n");
            return 1;
        }
    }
    if (!memoria_inicializar()) {
        fprintf(stderr, "Aviso: no se pudo inicializar el sistema de memoria.\n");
    }
    if (archivos_inicializar() != 0) {
        fprintf(stderr, "Aviso: no se pudo inicializar el sistema de archivos organizado.\n");
    }
    ui_iniciar();
    char usuario[32];
    Rol rol;
    if (!pantalla_login(usuario, sizeof(usuario), &rol)) {
        ui_finalizar();
        db_close();
        return 0;
    }
    ui_bienvenida(usuario, auth_rol_nombre(rol));
    while (1) {
        const char *opciones[] = {
            "Gestion de Mascotas",
            "Agenda de Vacunas",
            "Control de Adopciones",
            "Base de Donantes",
            "Reportes",
            "Administracion de Procesos",
            "Administracion de Memoria",
            "Sistema de Archivos",
            "Salir"
        };
        int sel = ui_menu("PawOS - Menu Principal", opciones, 9);
        if (sel < 0 || sel == 8) break;
        switch (sel) {
            case 0: pantalla_mascotas(rol); break;
            case 1: pantalla_vacunas(rol); break;
            case 2: pantalla_adopciones(rol); break;
            case 3: pantalla_donantes(rol); break;
            case 4: pantalla_reportes(rol); break;
            case 5: pantalla_procesos(rol); break;
            case 6: pantalla_memoria(rol); break;
            case 7: pantalla_archivos(rol); break;
        }
    }
    ui_finalizar();
    db_close();
    printf("Sesion de PawOS finalizada. Hasta pronto, %s.\n", usuario);
    return 0;
}
