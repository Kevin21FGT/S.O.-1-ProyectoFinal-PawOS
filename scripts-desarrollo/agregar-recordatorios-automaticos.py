#!/usr/bin/env python3
"""
agregar-recordatorios-automaticos.py

Conecta el servicio en segundo plano que ya existe (pawos-vacunas-check,
corre solo una vez al dia via pawos-vacunas.timer a las 08:00) para que,
ademas de loguear la alerta como hace ahora, mande el recordatorio real
por correo y WhatsApp (reusando pawos-notificar-cita) cuando la vacuna
pendiente/vencida tiene un Cliente asignado -- sin que un Colaborador
tenga que estar presente registrando nada.

Para no repetir el mismo correo/WhatsApp cada dia que corre el timer,
se agrega una columna recordatorio_enviado en vacunas: se manda una
sola vez por cita, y si el envio falla se reintenta al dia siguiente
(el flag solo se marca en 1 si el envio salio bien).

Cambios:
  1. src/db/db.h: declara vacuna_recordatorio_enviado() y
     vacuna_marcar_recordatorio_enviado().
  2. src/db/db.c:
     - migracion: ALTER TABLE vacunas ADD COLUMN recordatorio_enviado
     - vacuna_query() ahora tambien lee cliente_id (antes se perdia)
     - vacuna_listar() y vacuna_pendientes() ahora seleccionan cliente_id
     - nuevas funciones vacuna_recordatorio_enviado() /
       vacuna_marcar_recordatorio_enviado()
  3. src/vacunas_demonio.c: ademas de loguear, si la vacuna tiene
     cliente_id y no se le habia mandado recordatorio, hace fork+exec
     de pawos-notificar-cita (sin pasar por terminal, es un servicio
     sin sesion grafica) y marca el flag solo si el envio fue exitoso.
  4. pawos-notificar-cita: la pausa final ("Presiona Enter...") ahora
     solo ocurre si hay una terminal real (uso manual desde la GUI);
     cuando lo llama el servicio automatico se omite. Tambien se agrega
     "exit $HUBO_ERROR" al final para que el codigo de salida refleje
     de verdad si el envio funciono (antes siempre salia con exito,
     sin importar si el correo/WhatsApp habian fallado).

No cambia nada del flujo manual ya existente (boton en Agenda de
Vacunas): sigue funcionando exactamente igual.

Uso: parado en la raiz del repo:
    python3 agregar-recordatorios-automaticos.py
"""

import shutil
import sys

ARCHIVO_DB_H = "src/db/db.h"
ARCHIVO_DB_C = "src/db/db.c"
ARCHIVO_DEMONIO = "src/vacunas_demonio.c"
ARCHIVO_NOTIFICAR = "pawos-notificar-cita"

# ---------------------------------------------------------------
# src/db/db.h
# ---------------------------------------------------------------
ANCLA_H = "int  vacuna_pendientes(Vacuna **out, int *n); /* fecha_proxima <= hoy */"
NUEVO_H = """int  vacuna_pendientes(Vacuna **out, int *n); /* fecha_proxima <= hoy */
int  vacuna_recordatorio_enviado(int id);
int  vacuna_marcar_recordatorio_enviado(int id);"""

# ---------------------------------------------------------------
# src/db/db.c
# ---------------------------------------------------------------
ANCLA_C_MIGRACION = """    sqlite3_exec(g_db, "ALTER TABLE vacunas ADD COLUMN cliente_id INTEGER;", NULL, NULL, NULL);
    return 0;
}"""
NUEVO_C_MIGRACION = """    sqlite3_exec(g_db, "ALTER TABLE vacunas ADD COLUMN cliente_id INTEGER;", NULL, NULL, NULL);
    sqlite3_exec(g_db, "ALTER TABLE vacunas ADD COLUMN recordatorio_enviado INTEGER DEFAULT 0;", NULL, NULL, NULL);
    return 0;
}"""

ANCLA_C_QUERY = """        const unsigned char *obs = sqlite3_column_text(st, 5);
        snprintf(v->observaciones, sizeof(v->observaciones), "%s", obs ? (const char*)obs : "");
    }
    sqlite3_finalize(st);"""
NUEVO_C_QUERY = """        const unsigned char *obs = sqlite3_column_text(st, 5);
        snprintf(v->observaciones, sizeof(v->observaciones), "%s", obs ? (const char*)obs : "");
        v->cliente_id = sqlite3_column_int(st, 6);
    }
    sqlite3_finalize(st);"""

ANCLA_C_LISTAR = """int vacuna_listar(Vacuna **out, int *n) {
    return vacuna_query(
        "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima,observaciones FROM vacunas ORDER BY fecha_proxima;",
        out, n);
}"""
NUEVO_C_LISTAR = """int vacuna_listar(Vacuna **out, int *n) {
    return vacuna_query(
        "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima,observaciones,cliente_id FROM vacunas ORDER BY fecha_proxima;",
        out, n);
}"""

ANCLA_C_PENDIENTES = """int vacuna_pendientes(Vacuna **out, int *n) {
    char sql[256];
    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char hoy[16];
    strftime(hoy, sizeof(hoy), "%Y-%m-%d", &tmv);
    snprintf(sql, sizeof(sql),
        "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima,observaciones FROM vacunas "
        "WHERE fecha_proxima IS NOT NULL AND fecha_proxima <= '%s' ORDER BY fecha_proxima;", hoy);
    return vacuna_query(sql, out, n);
}

/* ---------------- Adopciones ---------------- */"""
NUEVO_C_PENDIENTES = """int vacuna_pendientes(Vacuna **out, int *n) {
    char sql[256];
    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char hoy[16];
    strftime(hoy, sizeof(hoy), "%Y-%m-%d", &tmv);
    snprintf(sql, sizeof(sql),
        "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima,observaciones,cliente_id FROM vacunas "
        "WHERE fecha_proxima IS NOT NULL AND fecha_proxima <= '%s' ORDER BY fecha_proxima;", hoy);
    return vacuna_query(sql, out, n);
}
int vacuna_recordatorio_enviado(int id) {
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, "SELECT recordatorio_enviado FROM vacunas WHERE id=?;", -1, &st, NULL) != SQLITE_OK) return 0;
    sqlite3_bind_int(st, 1, id);
    int enviado = 0;
    if (sqlite3_step(st) == SQLITE_ROW) enviado = sqlite3_column_int(st, 0);
    sqlite3_finalize(st);
    return enviado;
}
int vacuna_marcar_recordatorio_enviado(int id) {
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, "UPDATE vacunas SET recordatorio_enviado=1 WHERE id=?;", -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, id);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}

/* ---------------- Adopciones ---------------- */"""

# ---------------------------------------------------------------
# src/vacunas_demonio.c
# ---------------------------------------------------------------
ANCLA_DEMONIO_INCLUDES = """#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "db/db.h\""""
NUEVO_DEMONIO_INCLUDES = """#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include <sys/wait.h>
#include "db/db.h\""""

ANCLA_DEMONIO_MAIN = """int main(void) {
    if (db_init(RUTA_BD_DEFECTO) != 0) {
        if (db_init("pawos.db") != 0) {
            fprintf(stderr, "[pawos-vacunas-check] No se pudo abrir la base de datos.\\n");
            return 1;
        }
    }

    Vacuna *pendientes; int n;
    if (vacuna_pendientes(&pendientes, &n) != 0) {
        fprintf(stderr, "[pawos-vacunas-check] No se pudo consultar vacunas pendientes.\\n");
        db_close();
        return 1;
    }

    char sello[32];
    hoy_texto(sello, sizeof(sello));

    if (n == 0) {
        printf("[%s] Sin vacunas pendientes ni vencidas.\\n", sello);
        free(pendientes);
        db_close();
        return 0;
    }
    FILE *log = fopen(RUTA_LOG_DEFECTO, "a");
    if (!log) log = fopen("alertas_vacunas.log", "a");

    for (int i = 0; i < n; i++) {
        Mascota m;
        const char *nombre_mascota = "desconocida";
        if (mascota_buscar_por_id(pendientes[i].mascota_id, &m) == 0)
            nombre_mascota = m.nombre;

        printf("[ALERTA] [%s] Mascota '%s' (ID %d): vacuna '%s' vence/vencio el %s\\n",
               sello, nombre_mascota, pendientes[i].mascota_id,
               pendientes[i].nombre_vacuna, pendientes[i].fecha_proxima);

        if (log) {
            fprintf(log, "[%s] Mascota '%s' (ID %d): vacuna '%s' vence/vencio el %s\\n",
                    sello, nombre_mascota, pendientes[i].mascota_id,
                    pendientes[i].nombre_vacuna, pendientes[i].fecha_proxima);
        }
    }
    if (log) fclose(log);
    free(pendientes);
    db_close();
    return 0;
}"""
NUEVO_DEMONIO_MAIN = """int main(void) {
    if (db_init(RUTA_BD_DEFECTO) != 0) {
        if (db_init("pawos.db") != 0) {
            fprintf(stderr, "[pawos-vacunas-check] No se pudo abrir la base de datos.\\n");
            return 1;
        }
    }

    Vacuna *pendientes; int n;
    if (vacuna_pendientes(&pendientes, &n) != 0) {
        fprintf(stderr, "[pawos-vacunas-check] No se pudo consultar vacunas pendientes.\\n");
        db_close();
        return 1;
    }

    char sello[32];
    hoy_texto(sello, sizeof(sello));

    if (n == 0) {
        printf("[%s] Sin vacunas pendientes ni vencidas.\\n", sello);
        free(pendientes);
        db_close();
        return 0;
    }
    Cliente *clientes = NULL; int n_clientes = 0;
    cliente_listar(&clientes, &n_clientes);
    FILE *log = fopen(RUTA_LOG_DEFECTO, "a");
    if (!log) log = fopen("alertas_vacunas.log", "a");

    for (int i = 0; i < n; i++) {
        Mascota m;
        const char *nombre_mascota = "desconocida";
        if (mascota_buscar_por_id(pendientes[i].mascota_id, &m) == 0)
            nombre_mascota = m.nombre;

        printf("[ALERTA] [%s] Mascota '%s' (ID %d): vacuna '%s' vence/vencio el %s\\n",
               sello, nombre_mascota, pendientes[i].mascota_id,
               pendientes[i].nombre_vacuna, pendientes[i].fecha_proxima);

        if (log) {
            fprintf(log, "[%s] Mascota '%s' (ID %d): vacuna '%s' vence/vencio el %s\\n",
                    sello, nombre_mascota, pendientes[i].mascota_id,
                    pendientes[i].nombre_vacuna, pendientes[i].fecha_proxima);
        }

        /* Recordatorio automatico por correo/WhatsApp: solo si esta
         * vacuna tiene un Cliente asignado y todavia no se le habia
         * mandado (para no repetir el mismo correo/WhatsApp cada dia
         * que corre este servicio). Si el envio falla, el flag no se
         * marca y se reintenta manana. */
        if (pendientes[i].cliente_id > 0 && !vacuna_recordatorio_enviado(pendientes[i].id)) {
            Cliente *c = NULL;
            for (int j = 0; j < n_clientes; j++) {
                if (clientes[j].id == pendientes[i].cliente_id) { c = &clientes[j]; break; }
            }
            if (c) {
                pid_t pid = fork();
                if (pid == 0) {
                    execlp("pawos-notificar-cita", "pawos-notificar-cita",
                           c->correo, c->telefono, c->nombre, nombre_mascota,
                           pendientes[i].nombre_vacuna, pendientes[i].fecha_proxima,
                           (char *)NULL);
                    _exit(127);
                } else if (pid > 0) {
                    int estado = 0;
                    waitpid(pid, &estado, 0);
                    int ok = (WIFEXITED(estado) && WEXITSTATUS(estado) == 0);
                    printf("[%s] Recordatorio automatico a %s (%s): %s\\n",
                           sello, c->nombre, c->correo, ok ? "enviado" : "FALLO");
                    if (log) {
                        fprintf(log, "[%s] Recordatorio automatico a %s (%s): %s\\n",
                                sello, c->nombre, c->correo, ok ? "enviado" : "FALLO");
                    }
                    if (ok) vacuna_marcar_recordatorio_enviado(pendientes[i].id);
                } else {
                    fprintf(stderr, "[pawos-vacunas-check] No se pudo crear el proceso para notificar a %s.\\n", c->nombre);
                }
            }
        }
    }
    if (log) fclose(log);
    free(clientes);
    free(pendientes);
    db_close();
    return 0;
}"""

# ---------------------------------------------------------------
# pawos-notificar-cita
# ---------------------------------------------------------------
ANCLA_NOTIFICAR = """rm -f "$PDF"

echo ""
echo "======================================"
if [ "$HUBO_ERROR" = "1" ]; then
  echo "  Terminado, con al menos un error arriba."
else
  echo "  Recordatorio enviado."
fi
echo "======================================"
read -p "Presiona Enter para cerrar...\""""
NUEVO_NOTIFICAR = """rm -f "$PDF"

echo ""
echo "======================================"
if [ "$HUBO_ERROR" = "1" ]; then
  echo "  Terminado, con al menos un error arriba."
else
  echo "  Recordatorio enviado."
fi
echo "======================================"
# Solo pausa si hay una terminal real esperando (uso manual desde la
# GUI, vía x-terminal-emulator). Cuando lo llama el servicio
# automatico (pawos-vacunas-check, sin terminal) se omite, para no
# quedar esperando un Enter que nunca va a llegar.
if [ -t 0 ]; then
  read -p "Presiona Enter para cerrar..."
fi
exit "$HUBO_ERROR\""""


def parchar(ruta, pares):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ruta}. Corre este script desde la raiz del repo.")
        sys.exit(1)
    for ancla, _nuevo, nombre in pares:
        if contenido.count(ancla) != 1:
            print(f"ERROR: en {ruta}, no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
            print("       No se cambio nada.")
            sys.exit(1)
    return contenido


def main():
    archivos = [
        (ARCHIVO_DB_H, [(ANCLA_H, NUEVO_H, "declaraciones de vacuna_recordatorio_enviado")]),
        (ARCHIVO_DB_C, [
            (ANCLA_C_MIGRACION, NUEVO_C_MIGRACION, "migracion recordatorio_enviado"),
            (ANCLA_C_QUERY, NUEVO_C_QUERY, "lectura de cliente_id en vacuna_query"),
            (ANCLA_C_LISTAR, NUEVO_C_LISTAR, "SELECT de vacuna_listar"),
            (ANCLA_C_PENDIENTES, NUEVO_C_PENDIENTES, "vacuna_pendientes + nuevas funciones"),
        ]),
        (ARCHIVO_DEMONIO, [
            (ANCLA_DEMONIO_INCLUDES, NUEVO_DEMONIO_INCLUDES, "includes del demonio"),
            (ANCLA_DEMONIO_MAIN, NUEVO_DEMONIO_MAIN, "main() del demonio"),
        ]),
        (ARCHIVO_NOTIFICAR, [
            (ANCLA_NOTIFICAR, NUEVO_NOTIFICAR, "pausa final / exit status"),
        ]),
    ]

    contenidos = {}
    for ruta, pares in archivos:
        contenidos[ruta] = parchar(ruta, pares)

    for ruta, pares in archivos:
        contenido = contenidos[ruta]
        for ancla, nuevo, _nombre in pares:
            contenido = contenido.replace(ancla, nuevo, 1)
        shutil.copy(ruta, ruta + ".bak")
        print(f"Backup creado: {ruta}.bak")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"{ruta} parchado OK.")

    print("")
    print("Ahora recompila todo (el demonio tambien) y confirma que no hay warnings:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  make clean && make all")
    print("")
    print("Prueba manual del demonio (no espera al timer de las 08:00):")
    print("  sudo /usr/local/bin/pawos-vacunas-check   # (o ./pawos-vacunas-check si aun no reinstalaste)")


if __name__ == "__main__":
    main()
