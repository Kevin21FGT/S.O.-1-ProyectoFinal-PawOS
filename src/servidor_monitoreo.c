
/*
 * servidor_monitoreo.c - Servidor de monitoreo de PawOS.
 * Expone un dashboard HTML por HTTP con CPU, memoria, swap, disco,
 * tiempo activo y procesos, leyendo directo de /proc. Protegido con
 * autenticacion basica HTTP (usuario/contrasena).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <ctype.h>
#include <dirent.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/statvfs.h>

#define PUERTO 8080
#define USUARIO "admin"
#define CONTRASENA "pawos2026"

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

static void leer_swap(long *total_kb, long *usado_kb) {
    FILE *f = fopen("/proc/meminfo", "r");
    long swap_total = 0, swap_free = 0;
    if (f) {
        char linea[256];
        while (fgets(linea, sizeof(linea), f)) {
            if (strncmp(linea, "SwapTotal:", 10) == 0) sscanf(linea + 10, "%ld", &swap_total);
            else if (strncmp(linea, "SwapFree:", 9) == 0) sscanf(linea + 9, "%ld", &swap_free);
        }
        fclose(f);
    }
    *total_kb = swap_total;
    *usado_kb = swap_total - swap_free;
}
static void leer_carga(double *l1, double *l5, double *l15) {
    FILE *f = fopen("/proc/loadavg", "r");
    *l1 = *l5 = *l15 = 0;
    if (f) { if (fscanf(f, "%lf %lf %lf", l1, l5, l15) != 3) { *l1=*l5=*l15=0; } fclose(f); }
}

static int contar_cpus(void) {
    long n = sysconf(_SC_NPROCESSORS_ONLN);
    return (n > 0) ? (int)n : 1;
}

static void leer_disco(double *usado_gb, double *total_gb) {
    struct statvfs st;
    *usado_gb = 0; *total_gb = 0;
    if (statvfs("/", &st) == 0) {
        double total = (double)st.f_blocks * st.f_frsize;
        double libre = (double)st.f_bfree * st.f_frsize;
        *total_gb = total / (1024.0 * 1024.0 * 1024.0);
        *usado_gb = (total - libre) / (1024.0 * 1024.0 * 1024.0);
    }
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

static const char *color_por_pct(double pct) {
    if (pct < 60) return "#2ecc71";
    if (pct < 85) return "#f1c40f";
    return "#e74c3c";
}
static int base64_decode(const char *in, unsigned char *out, int max_out) {
    static const char tabla[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    int val = 0, valb = -8, len = 0;
    for (const char *p = in; *p && *p != '\r' && *p != '\n'; p++) {
        if (*p == '=') break;
        const char *pos = strchr(tabla, *p);
        if (!pos) continue;
        val = (val << 6) + (int)(pos - tabla);
        valb += 6;
        if (valb >= 0) {
            if (len < max_out) out[len++] = (unsigned char)((val >> valb) & 0xFF);
            valb -= 8;
        }
    }
    if (len < max_out) out[len] = '\0';
    return len;
}
static int autorizado(const char *peticion) {
    const char *encabezado = strstr(peticion, "Authorization: Basic ");
    if (!encabezado) return 0;
    encabezado += strlen("Authorization: Basic ");
    char token[256] = {0};
    int i = 0;
    while (encabezado[i] && encabezado[i] != '\r' && encabezado[i] != '\n' && i < (int)sizeof(token) - 1) {
        token[i] = encabezado[i];
        i++;
    }
    unsigned char decodificado[256];
    int n = base64_decode(token, decodificado, sizeof(decodificado) - 1);
    decodificado[n] = '\0';
    return strcmp((char *)decodificado, USUARIO ":" CONTRASENA) == 0;
}
static void generar_pagina(char *buf, size_t bufsize) {
    long mem_total, mem_disp;
    leer_memoria(&mem_total, &mem_disp);
    long swap_total, swap_usado;
    leer_swap(&swap_total, &swap_usado);
    double l1, l5, l15;
    leer_carga(&l1, &l5, &l15);
    double uptime_seg = leer_uptime();
    int horas = (int)(uptime_seg / 3600);
    int minutos = (int)((uptime_seg - horas * 3600) / 60);
    int procesos = contar_procesos();
    int cpus = contar_cpus();
    double disco_usado, disco_total;
    leer_disco(&disco_usado, &disco_total);

    long mem_usada = mem_total - mem_disp;
    double mem_pct = mem_total > 0 ? (100.0 * mem_usada / mem_total) : 0;
    double swap_pct = swap_total > 0 ? (100.0 * swap_usado / swap_total) : 0;
    double disco_pct = disco_total > 0 ? (100.0 * disco_usado / disco_total) : 0;
    double carga_pct = cpus > 0 ? (100.0 * l1 / cpus) : 0;
    if (carga_pct > 100) carga_pct = 100;
    snprintf(buf, bufsize,
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>PawOS - Monitoreo</title>"
        "<meta http-equiv='refresh' content='5'>"
        "<style>"
        "body{font-family:'Segoe UI',Consolas,monospace;background:#0d1117;color:#c9d1d9;padding:30px;margin:0;}"
        "h1{color:#ffffff;font-size:26px;margin-bottom:4px;}"
        "p.sub{color:#8b949e;margin-top:0;margin-bottom:28px;font-size:14px;}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;}"
        ".card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:18px 20px;}"
        ".card h2{margin:0 0 10px 0;font-size:14px;color:#8b949e;text-transform:uppercase;letter-spacing:1px;}"
        ".valor{font-size:24px;font-weight:bold;color:#ffffff;margin-bottom:10px;}"
        ".barra-fondo{background:#21262d;border-radius:6px;height:10px;overflow:hidden;}"
        ".barra{height:100%%;border-radius:6px;}"
        "</style></head><body>"
        "<h1>PawOS - Servidor de Monitoreo</h1>"
        "<p class='sub'>Refugio de Proteccion Animal | Se actualiza cada 5 segundos</p>"
        "<div class='grid'>"
        "<div class='card'><h2>Tiempo Activo</h2>"
        "<div class='valor'>%dh %dm</div></div>"

        "<div class='card'><h2>CPU (%d nucleos)</h2>"
        "<div class='valor'>%.2f (carga 1 min)</div>"
        "<div class='barra-fondo'><div class='barra' style='width:%.1f%%;background:%s;'></div></div></div>"

        "<div class='card'><h2>Memoria RAM</h2>"
        "<div class='valor'>%ld / %ld MB (%.1f%%)</div>"
        "<div class='barra-fondo'><div class='barra' style='width:%.1f%%;background:%s;'></div></div></div>"

        "<div class='card'><h2>Memoria Swap</h2>"
        "<div class='valor'>%ld / %ld MB (%.1f%%)</div>"
        "<div class='barra-fondo'><div class='barra' style='width:%.1f%%;background:%s;'></div></div></div>"

        "<div class='card'><h2>Disco (/)</h2>"
        "<div class='valor'>%.1f / %.1f GB (%.1f%%)</div>"
        "<div class='barra-fondo'><div class='barra' style='width:%.1f%%;background:%s;'></div></div></div>"

        "<div class='card'><h2>Procesos Activos</h2>"
        "<div class='valor'>%d</div></div>"
        "</div></body></html>",
        horas, minutos,
        cpus, l1, carga_pct, color_por_pct(carga_pct),
        mem_usada / 1024, mem_total / 1024, mem_pct, mem_pct, color_por_pct(mem_pct),
        swap_usado / 1024, swap_total / 1024, swap_pct, swap_pct, color_por_pct(swap_pct),
        disco_usado, disco_total, disco_pct, disco_pct, color_por_pct(disco_pct),
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

    printf("[pawos-monitoreo] Escuchando en el puerto %d (con autenticacion)...\n", PUERTO);
    fflush(stdout);
    char pagina[8192];
    char respuesta[8600];

    while (1) {
        int cliente_fd = accept(servidor_fd, NULL, NULL);
        if (cliente_fd < 0) continue;

        char buf_peticion[2048];
        ssize_t leidos = read(cliente_fd, buf_peticion, sizeof(buf_peticion) - 1);
        if (leidos > 0) buf_peticion[leidos] = '\0';
        else buf_peticion[0] = '\0';

        if (!autorizado(buf_peticion)) {
            const char *cuerpo = "<html><body><h1>401 - Acceso no autorizado</h1>"
                                  "<p>Ingrese usuario y contrasena para ver el monitoreo de PawOS.</p></body></html>";
            int len = snprintf(respuesta, sizeof(respuesta),
                "HTTP/1.1 401 Unauthorized\r\n"
                "WWW-Authenticate: Basic realm=\"PawOS Monitoreo\"\r\n"
                "Content-Type: text/html; charset=utf-8\r\n"
                "Content-Length: %zu\r\nConnection: close\r\n\r\n%s",
                strlen(cuerpo), cuerpo);
            write(cliente_fd, respuesta, len);
            close(cliente_fd);
            continue;
        }

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
