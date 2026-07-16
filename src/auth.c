/*
 * auth.c - Determina usuario y rol a partir de las cuentas/grupos reales
 * de Linux, para que el programa respete la gestion de usuarios y
 * permisos que ya provee el sistema operativo (no se duplica login aqui;
 * el login grafico lo hace el display manager antes de llegar a esto).
 */

#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <pwd.h>
#include <grp.h>
#include "../include/auth.h"

const char *auth_usuario_actual(void) {
    struct passwd *pw = getpwuid(getuid());
    return pw ? pw->pw_name : "desconocido";
}

Rol auth_rol_actual(void) {
    const char *user = auth_usuario_actual();
    struct passwd *pw = getpwuid(getuid());
    if (!pw) return ROL_VOLUNTARIO;

    gid_t grupos[64];
    int ngrupos = 64;
    getgrouplist(user, pw->pw_gid, grupos, &ngrupos);

    Rol rol = ROL_VOLUNTARIO;
    for (int i = 0; i < ngrupos; i++) {
        struct group *g = getgrgid(grupos[i]);
        if (!g) continue;
        if (strcmp(g->gr_name, "pawos-admin") == 0) return ROL_ADMIN;
        if (strcmp(g->gr_name, "pawos-veterinario") == 0) rol = ROL_VETERINARIO;
    }
    return rol;
}

const char *auth_rol_nombre(Rol r) {
    switch (r) {
        case ROL_ADMIN: return "Administrador";
        case ROL_VETERINARIO: return "Veterinario";
        default: return "Voluntario";
    }
}
