
/*
 * archivos.c - Sistema de archivos organizado de PawOS.
 * Organiza los archivos del refugio en carpetas por categoria
 * dentro de /var/pawos/archivos (o ./archivos_pawos si se prueba
 * fuera de la ISO), y permite listar, eliminar y respaldar la BD.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <time.h>
#include "../include/archivos.h"
const char *ARCHIVOS_CATEGORIAS[ARCHIVOS_NUM_CATEGORIAS] = {
    "mascotas", "vacunas", "adopciones", "donantes", "reportes", "backups"
};

static char g_ruta_base[256] = "";

static int existe_o_crear(const char *ruta) {
    struct stat st;
    if (stat(ruta, &st) == 0) return 0;
    return mkdir(ruta, 0770);
}

int archivos_inicializar(void) {
    const char *candidatos[] = { "/var/pawos/archivos", "./archivos_pawos" };
    for (int c = 0; c < 2; c++) {
        if (existe_o_crear(candidatos[c]) == 0) {
            strncpy(g_ruta_base, candidatos[c], sizeof(g_ruta_base) - 1);
            int ok = 1;
            for (int i = 0; i < ARCHIVOS_NUM_CATEGORIAS; i++) {
                char sub[300];
                snprintf(sub, sizeof(sub), "%s/%s", g_ruta_base, ARCHIVOS_CATEGORIAS[i]);
                if (existe_o_crear(sub) != 0) ok = 0;
            }
            if (ok) return 0;
        }
    }
    return -1;
}
const char *archivos_ruta_base(void) {
    return g_ruta_base;
}

int archivos_listar(const char *categoria, ArchivoInfo **out, int *n) {
    char ruta[300];
    snprintf(ruta, sizeof(ruta), "%s/%s", g_ruta_base, categoria);
    DIR *d = opendir(ruta);
    if (!d) { *out = NULL; *n = 0; return -1; }
    ArchivoInfo *lista = NULL;
    int cuenta = 0, capacidad = 0;
    struct dirent *ent;
    while ((ent = readdir(d)) != NULL) {
        if (strcmp(ent->d_name, ".") == 0 || strcmp(ent->d_name, "..") == 0) continue;
        char completa[400];
        snprintf(completa, sizeof(completa), "%s/%s", ruta, ent->d_name);
        struct stat st;
        if (stat(completa, &st) != 0 || S_ISDIR(st.st_mode)) continue;
        if (cuenta >= capacidad) {
            capacidad = capacidad ? capacidad * 2 : 8;
            lista = realloc(lista, capacidad * sizeof(ArchivoInfo));
        }
        strncpy(lista[cuenta].nombre, ent->d_name, ARCHIVOS_MAX_NOMBRE - 1);
        lista[cuenta].nombre[ARCHIVOS_MAX_NOMBRE - 1] = '\0';
        lista[cuenta].tamano_bytes = (long)st.st_size;
        struct tm tmv; localtime_r(&st.st_mtime, &tmv);
        strftime(lista[cuenta].fecha_mod, sizeof(lista[cuenta].fecha_mod), "%Y-%m-%d %H:%M", &tmv);
        cuenta++;
    }
    closedir(d);
    *out = lista;
    *n = cuenta;
    return 0;
}
int archivos_eliminar(const char *categoria, const char *nombre) {
    char ruta[400];
    snprintf(ruta, sizeof(ruta), "%s/%s/%s", g_ruta_base, categoria, nombre);
    return unlink(ruta);
}

static int copiar_archivo(const char *origen, const char *destino) {
    FILE *in = fopen(origen, "rb");
    if (!in) return -1;
    FILE *out = fopen(destino, "wb");
    if (!out) { fclose(in); return -1; }
    char buf[4096];
    size_t leidos;
    while ((leidos = fread(buf, 1, sizeof(buf), in)) > 0) {
        fwrite(buf, 1, leidos, out);
    }
   fclose(in);
    fclose(out);
    return 0;
}
int archivos_respaldar_bd_auto(void) {
    const char *rutas_bd[] = { "/var/pawos/pawos.db", "pawos.db" };
    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char sello[32];
    strftime(sello, sizeof(sello), "%Y%m%d_%H%M%S", &tmv);
    char destino[400];
    snprintf(destino, sizeof(destino), "%s/backups/pawos_%s.db", g_ruta_base, sello);
    for (int i = 0; i < 2; i++) {
        if (copiar_archivo(rutas_bd[i], destino) == 0) return 0;
    }
    return -1;
}
long archivos_espacio_categoria(const char *categoria) {
    ArchivoInfo *lista; int n;
    if (archivos_listar(categoria, &lista, &n) != 0) return -1;
    long total = 0;
    for (int i = 0; i < n; i++) total += lista[i].tamano_bytes;
    free(lista);
    return total;
}
