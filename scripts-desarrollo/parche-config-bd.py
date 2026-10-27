#!/usr/bin/env python3
"""
parche-config-bd.py

Hasta ahora el servidor, la base y el usuario de SQL Server estaban escritos
fijos en db.c (sql5111.site4now.net / db_ace27e_pawos). Con este parche se
leen de un archivo OPCIONAL ~/.pawos_db_config; si no existe, se usan los
valores de siempre. Asi se puede cambiar de cuenta o de servidor SIN
recompilar. La contrasena sigue en ~/.pawos_db_remota (como hasta ahora).

Formato de ~/.pawos_db_config (una clave por linea):
    SERVIDOR=sqlXXXX.site4now.net
    PUERTO=1433
    BASE=db_xxxxxx_pawos
    USUARIO=db_xxxxxx_pawos_admin

Uso (parado en la raiz del repo):
    python3 parche-config-bd.py
    make gui   (y make, para pawos-monitoreo / pawos-vacunas-check)
"""

import shutil
import sys

DB_C = "src/db/db.c"

ANCLA_FUNC = r"""static SQLHENV g_henv_remoto = NULL;"""
NUEVO_FUNC = r"""/* Lee ~/.pawos_db_config (opcional). Si falta o no trae una clave, se usa
 * el valor por defecto de arriba (#define API_SQL_*). */
static void api_leer_config_remota(char *srv, size_t ns, char *puerto, size_t np,
                                   char *base, size_t nb, char *usr, size_t nu) {
    snprintf(srv, ns, "%s", API_SQL_SERVIDOR);
    snprintf(puerto, np, "%s", API_SQL_PUERTO);
    snprintf(base, nb, "%s", API_SQL_BASE);
    snprintf(usr, nu, "%s", API_SQL_USUARIO);

    const char *home = getenv("HOME");
    char ruta[256];
    snprintf(ruta, sizeof(ruta), "%s/.pawos_db_config", home ? home : ".");
    FILE *f = fopen(ruta, "r");
    if (!f) return;
    char linea[256];
    while (fgets(linea, sizeof(linea), f)) {
        linea[strcspn(linea, "\r\n")] = '\0';
        if (linea[0] == '#') continue;
        char *eq = strchr(linea, '=');
        if (!eq) continue;
        *eq = '\0';
        const char *clave = linea;
        const char *valor = eq + 1;
        if (valor[0] == '\0') continue;
        if      (strcmp(clave, "SERVIDOR") == 0) snprintf(srv, ns, "%s", valor);
        else if (strcmp(clave, "PUERTO")   == 0) snprintf(puerto, np, "%s", valor);
        else if (strcmp(clave, "BASE")     == 0) snprintf(base, nb, "%s", valor);
        else if (strcmp(clave, "USUARIO")  == 0) snprintf(usr, nu, "%s", valor);
    }
    fclose(f);
}

static SQLHENV g_henv_remoto = NULL;"""

ANCLA_CONN = r"""    snprintf(connstr, sizeof(connstr),
        "DRIVER={FreeTDS};SERVER=%s;PORT=%s;DATABASE=%s;UID=%s;PWD=%s;TDS_Version=7.4;",
        API_SQL_SERVIDOR, API_SQL_PUERTO, API_SQL_BASE, API_SQL_USUARIO, pass);"""
NUEVO_CONN = r"""    char cfg_srv[128], cfg_puerto[16], cfg_base[128], cfg_usr[128];
    api_leer_config_remota(cfg_srv, sizeof(cfg_srv), cfg_puerto, sizeof(cfg_puerto),
                           cfg_base, sizeof(cfg_base), cfg_usr, sizeof(cfg_usr));
    snprintf(connstr, sizeof(connstr),
        "DRIVER={FreeTDS};SERVER=%s;PORT=%s;DATABASE=%s;UID=%s;PWD=%s;TDS_Version=7.4;",
        cfg_srv, cfg_puerto, cfg_base, cfg_usr, pass);"""

CAMBIOS = [
    (ANCLA_FUNC, NUEVO_FUNC, "inicio de las variables de conexion"),
    (ANCLA_CONN, NUEVO_CONN, "cadena de conexion"),
]


def main():
    try:
        with open(DB_C, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {DB_C}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if "api_leer_config_remota" in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ancla, _nuevo, nombre in CAMBIOS:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            sys.exit(1)

    shutil.copy(DB_C, DB_C + ".bak_config_bd")
    print(f"Backup: {DB_C}.bak_config_bd")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(DB_C, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{DB_C} parchado OK.")
    print("Listo. Compila:  make gui   (y make para los demas programas)")
    print("Crea ~/.pawos_db_config con SERVIDOR, PUERTO, BASE y USUARIO de la cuenta nueva.")


if __name__ == "__main__":
    main()
