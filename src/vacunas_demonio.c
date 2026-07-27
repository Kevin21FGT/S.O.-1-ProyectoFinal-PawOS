
/*
 * vacunas_demonio.c - Servicio en segundo plano de PawOS.
 * Revisa la base de datos en busca de vacunas pendientes o vencidas
 * y genera una alerta (consola + log), sin necesidad de que un usuario
 * entre al menu del programa. Pensado para correr via systemd timer.
 */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "../include/db.h"

#define RUTA_BD_DEFECTO  "/var/pawos/pawos.db"
#define RUTA_LOG_DEFECTO "/var/pawos/archivos/reportes/alertas_vacunas.log"

static void hoy_texto(char *buf, int len) {
    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    strftime(buf, len, "%Y-%m-%d %H:%M:%S", &tmv);
}
int main(void) {
    if (db_init(RUTA_BD_DEFECTO) != 0) {
        if (db_init("pawos.db") != 0) {
            fprintf(stderr, "[pawos-vacunas-check] No se pudo abrir la base de datos.\n");
            return 1;
        }
    }

    Vacuna *pendientes; int n;
    if (vacuna_pendientes(&pendientes, &n) != 0) {
        fprintf(stderr, "[pawos-vacunas-check] No se pudo consultar vacunas pendientes.\n");
        db_close();
        return 1;
    }

    char sello[32];
    hoy_texto(sello, sizeof(sello));

    if (n == 0) {
        printf("[%s] Sin vacunas pendientes ni vencidas.\n", sello);
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

        printf("[ALERTA] [%s] Mascota '%s' (ID %d): vacuna '%s' vence/vencio el %s\n",
               sello, nombre_mascota, pendientes[i].mascota_id,
               pendientes[i].nombre_vacuna, pendientes[i].fecha_proxima);

        if (log) {
            fprintf(log, "[%s] Mascota '%s' (ID %d): vacuna '%s' vence/vencio el %s\n",
                    sello, nombre_mascota, pendientes[i].mascota_id,
                    pendientes[i].nombre_vacuna, pendientes[i].fecha_proxima);
        }
    }
    if (log) fclose(log);
    free(pendientes);
    db_close();
    return 0;
}
