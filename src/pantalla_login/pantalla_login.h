
#ifndef PANTALLA_LOGIN_H
#define PANTALLA_LOGIN_H

#include "auth/auth.h"

/* Muestra la pantalla de login del programa. Pide usuario y contrasena
 * hasta que acierte o se agoten los intentos. Devuelve 1 si inicio
 * sesion correctamente (llena usuario_out y rol_out), o 0 si no. */
int pantalla_login(char *usuario_out, int usuario_len, Rol *rol_out);

#endif
