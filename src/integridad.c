/*
 * integridad.c - Verificacion de integridad de la base de donantes,
 * usando la rutina de checksum escrita en Ensamblador (checksum.asm).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../include/integridad.h"
#include "../include/checksum.h"
#include "../include/db.h"
#define RUTA_CHECKSUM_DEFECTO "/var/pawos/archivos/backups/donantes.checksum"
#define RUTA_CHECKSUM_LOCAL   "donantes.checksum"

uint64_t integridad_checksum_donantes(void) {
    Donante *ds; int n;
    if (donante_listar(&ds, &n) != 0) return 0;

    size_t capacidad = 4096;
    size_t usado = 0;
    unsigned char *buf = malloc(capacidad);
    char linea[256];

    for (int i = 0; i < n; i++) {
        int len = snprintf(linea, sizeof(linea), "%d|%s|%s|%.2f|%s;",
                            ds[i].id, ds[i].nombre, ds[i].contacto,
                            ds[i].monto, ds[i].fecha);
        if (len < 0) continue;
        if (usado + (size_t)len + 1 > capacidad) {
            capacidad = (usado + (size_t)len + 1) * 2;
            buf = realloc(buf, capacidad);
        }
        memcpy(buf + usado, linea, (size_t)len);
        usado += (size_t)len;
    }

    uint64_t resultado = pawos_checksum(buf, usado);
    free(buf);
    free(ds);
    return resultado;
}
int integridad_verificar_donantes(void) {
    uint64_t actual = integridad_checksum_donantes();

    FILE *f = fopen(RUTA_CHECKSUM_DEFECTO, "r");
    if (!f) f = fopen(RUTA_CHECKSUM_LOCAL, "r");

    if (!f) {
        FILE *w = fopen(RUTA_CHECKSUM_DEFECTO, "w");
        if (!w) w = fopen(RUTA_CHECKSUM_LOCAL, "w");
        if (!w) return -1;
        fprintf(w, "%llu\n", (unsigned long long)actual);
        fclose(w);
        return 2;
    }

    unsigned long long guardado = 0;
    if (fscanf(f, "%llu", &guardado) != 1) {
        fclose(f);
        return -1;
    }
    fclose(f);

    return (guardado == actual) ? 0 : 1;
}

int integridad_actualizar_checksum_donantes(void) {
    uint64_t actual = integridad_checksum_donantes();
    FILE *w = fopen(RUTA_CHECKSUM_DEFECTO, "w");
    if (!w) w = fopen(RUTA_CHECKSUM_LOCAL, "w");
    if (!w) return -1;
    fprintf(w, "%llu\n", (unsigned long long)actual);
    fclose(w);
    return 0;
}
