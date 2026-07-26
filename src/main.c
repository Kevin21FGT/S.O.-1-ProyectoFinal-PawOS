/*
 * main.c - Punto de entrada de PawOS Refugio.
 *
 * El login grafico (usuario/rol + contrasena) lo resuelve el display
 * manager del sistema operativo (LightDM) antes de llegar aqui; este
 * programa arranca ya dentro de la sesion del usuario, detecta su rol
 * segun sus grupos de Linux y muestra la bienvenida + menu principal.
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

#define RUTA_BD_DEFECTO "/var/pawos/pawos.db"

int main(int argc, char **argv) {
    const char *ruta_bd = (argc > 1) ? argv[1] : RUTA_BD_DEFECTO;

    if (db_init(ruta_bd) != 0) {
        /* Si no existe /var/pawos (por ejemplo probando fuera de la ISO),
         * caemos a un archivo local para no bloquear las pruebas. */
        fprintf(stderr, "Aviso: no se pudo usar %s, usando ./pawos.db\n", ruta_bd);
        if (db_init("pawos.db") != 0) {
            fprintf(stderr, "No se pudo inicializar la base de datos.\n");
            return 1;
        }
    }

        if (!memoria_inicializar()) {
        fprintf(stderr, "Aviso: no se pudo inicializar el sistema de memoria.\n");
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
            "Salir"
        };
        int sel = ui_menu("PawOS - Menu Principal", opciones, 8);
        if (sel < 0 || sel == 7) break;

        switch (sel) {
            case 0: pantalla_mascotas(rol); break;
            case 1: pantalla_vacunas(rol); break;
            case 2: pantalla_adopciones(rol); break;
            case 3: pantalla_donantes(rol); break;
            case 4: pantalla_reportes(rol); break;
            case 5: pantalla_procesos(rol); break;
            case 6: pantalla_memoria(rol); break;
        }
    }

    ui_finalizar();
    db_close();
    printf("Sesion de PawOS finalizada. Hasta pronto, %s.\n", usuario);
    return 0;
}
