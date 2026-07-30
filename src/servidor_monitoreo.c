/*
 * servidor_monitoreo.c - Servidor de monitoreo de PawOS.
 * Expone un dashboard HTML por HTTP con CPU/carga, memoria,
 * tiempo activo y cantidad de procesos, leyendo directo de /proc.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <ctype.h>
#include <dirent.h>
#include <sys/socket.h>
#include <netinet/in.h>

#define PUERTO 8080

static double leer_uptime(void) {
    FILE *f = fopen("/proc/uptime", "r");
    double up = 0;
    if (f) { if (fscanf(f, "%lf", &up) != 1) up = 0; fclose(f); }
    return up;
}
static void leer_memoria(long *total_kb, long *disponible_kb) {
    FILE *f = fopen("/proc/meminfo", "r");
    *total_kb = 0; *disponible_kb = 0;
    if (!f) return;
    char linea[256];
    while (fgets(linea, sizeof(linea), f)) {
        if (strncmp(linea, "MemTotal:", 9) == 0) sscanf(linea + 9, "%ld", total_kb);
        else if (strncmp(linea, "MemAvailable:", 13) == 0) sscanf(linea + 13, "%ld", disponible_kb);
    }
    fclose(f);
}

static void leer_carga(double *l1, double *l5, double *l15) {
    FILE *f = fopen("/proc/loadavg", "r");
    *l1 = *l5 = *l15 = 0;
    if (f) { if (fscanf(f, "%lf %lf %lf", l1, l5, l15) != 3) { *l1=*l5=*l15=0; } fclose(f); }
}

static int contar_procesos(void) {
    DIR *d = opendir("/proc");
    int contador = 0;
    if (!d) return -1;
    struct dirent *ent;
    while ((ent = readdir(d)) != NULL) {
        int es_numero = 1;
        for (char *p = ent->d_name; *p; p++) {
            if (!isdigit((unsigned char)*p)) { es_numero = 0; break; }
        }
        if (es_numero) contador++;
    }
    closedir(d);
    return contador;
}

static void generar_pagina(char *buf, size_t bufsize) {
    long mem_total, mem_disp;
    leer_memoria(&mem_total, &mem_disp);
    double l1, l5, l15;
    leer_carga(&l1, &l5, &l15);
    double uptime_seg = leer_uptime();
    int horas = (int)(uptime_seg / 3600);
    int minutos = (int)((uptime_seg - horas * 3600) / 60);
    int procesos = contar_procesos();
    long mem_usada = mem_total - mem_disp;
    double mem_pct = mem_total > 0 ? (100.0 * mem_usada / mem_total) : 0;
    snprintf(buf, bufsize,
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>PawOS - Monitoreo</title>"
        "<meta http-equiv='refresh' content='5'>"
        "<style>body{font-family:monospace;background:#111;color:#0f0;padding:20px;}"
        "h1{color:#fff;} .dato{margin:8px 0;font-size:18px;}</style></head><body>"
        "<h1>PawOS - Servidor de Monitoreo</h1>"
        "<div class='dato'>Tiempo activo: %dh %dm</div>"
        "<div class='dato'>Carga del sistema (1/5/15 min): %.2f / %.2f / %.2f</div>"
        "<div class='dato'>Memoria: %ld MB usados de %ld MB (%.1f%%)</div>"
        "<div class='dato'>Procesos activos: %d</div>"
        "<div class='dato' style='color:#888;font-size:12px;'>Se actualiza cada 5 segundos</div>"
        "</body></html>",
        horas, minutos, l1, l5, l15,
        mem_usada / 1024, mem_total / 1024, mem_pct,
        procesos);
}
int main(void) {
    int servidor_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (servidor_fd < 0) { perror("socket"); return 1; }

    int opt = 1;
    setsockopt(servidor_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in direccion;
    memset(&direccion, 0, sizeof(direccion));
    direccion.sin_family = AF_INET;
    direccion.sin_addr.s_addr = INADDR_ANY;
    direccion.sin_port = htons(PUERTO);

    if (bind(servidor_fd, (struct sockaddr *)&direccion, sizeof(direccion)) < 0) {
        perror("bind"); return 1;
    }
    if (listen(servidor_fd, 10) < 0) {
        perror("listen"); return 1;
    }
printf("[pawos-monitoreo] Escuchando en el puerto %d...\n", PUERTO);
    fflush(stdout);

    char pagina[4096];
    char respuesta[4400];

    while (1) {
        int cliente_fd = accept(servidor_fd, NULL, NULL);
        if (cliente_fd < 0) continue;

        char buf_peticion[1024];
        ssize_t leidos = read(cliente_fd, buf_peticion, sizeof(buf_peticion) - 1);
        (void)leidos;

        generar_pagina(pagina, sizeof(pagina));
        int len = snprintf(respuesta, sizeof(respuesta),
            "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: %zu\r\nConnection: close\r\n\r\n%s",
            strlen(pagina), pagina);

        write(cliente_fd, respuesta, len);
        close(cliente_fd);
    }

    close(servidor_fd);
    return 0;
}
