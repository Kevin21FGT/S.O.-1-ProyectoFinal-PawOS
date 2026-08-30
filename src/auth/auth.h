#ifndef AUTH_H
#define AUTH_H

/* Roles reconocidos por PawOS, mapeados a grupos del sistema Linux
 * (creados por scripts/crear_usuarios.sh):
 *   pawos-admin        -> ROL_ADMIN
 *   pawos-veterinario  -> ROL_VETERINARIO
 *   pawos-voluntario   -> ROL_VOLUNTARIO (por defecto si no pertenece a otro grupo) */
typedef enum {
    ROL_ADMIN = 0,
    ROL_VETERINARIO,
    ROL_VOLUNTARIO
} Rol;

/* Devuelve el usuario Linux que ejecuta el programa (login actual). */
const char *auth_usuario_actual(void);

/* Determina el rol inspeccionando los grupos del usuario actual. */
Rol auth_rol_actual(void);

const char *auth_rol_nombre(Rol r);

#endif
