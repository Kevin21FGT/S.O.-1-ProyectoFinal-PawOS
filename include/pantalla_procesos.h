#ifndef PANTALLA_PROCESOS_H
#define PANTALLA_PROCESOS_H

#include "auth.h"

/* Muestra el submenu de Administracion de Procesos dentro del programa.
   Solo el rol Administrador puede usarlo; los demas roles ven un
   mensaje de acceso denegado. */
void pantalla_procesos(Rol rol);

#endif