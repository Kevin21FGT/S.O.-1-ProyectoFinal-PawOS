/*
 * servidor_monitoreo.c - Servidor de monitoreo de PawOS.
 * Expone un dashboard HTML por HTTP con CPU, memoria, swap, disco,
 * tiempo activo y procesos, leyendo directo de /proc. Protegido con
 * autenticacion basica HTTP (usuario/contrasena).
 *
 * Ademas expone POST /api/alerta: el endpoint que usa el modulo de
 * sensores del ESP32 (ver pawos_sensor_animal.ino) para reportar
 * posibles senales de lesion, fiebre o maltrato. Ese endpoint NO pide
 * autenticacion (el ESP32 no la envia) y guarda cada alerta en la
 * tabla alertas_sensores via alerta_registrar(), la misma que usa el
 * modulo "Alertas de Sensores" de la GUI y del CLI.
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
#include "db.h"
#define PUERTO 8080
#define USUARIO "admin"
#define CONTRASENA "pawos2026"
#define RUTA_BD_DEFECTO "/var/pawos/pawos.db"
#define TAM_BUF_PETICION 4096

/* Se pone en 1 solo si db_init() funciono; si la BD no esta disponible
 * el dashboard sigue funcionando igual, pero /api/alerta responde con
 * error en vez de intentar escribir. */
static int db_disponible = 0;

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

/* =================================================================
 * POST /api/alerta - puente para las alertas del ESP32
 * ================================================================= */

/* Busca "clave":"valor de texto" en un JSON plano (sin objetos
 * anidados) y copia el valor a out. Formato fijo, generado siempre
 * por nuestro propio firmware, asi que no hace falta un parser
 * completo de JSON. */
static int extraer_campo_texto_json(const char *json, const char *clave, char *out, size_t out_size) {
    char patron[64];
    snprintf(patron, sizeof(patron), "\"%s\"", clave);
    const char *p = strstr(json, patron);
    out[0] = '\0';
    if (!p) return 0;
    p += strlen(patron);
    while (*p == ' ' || *p == '\t') p++;
    if (*p != ':') return 0;
    p++;
    while (*p == ' ' || *p == '\t') p++;
    if (*p != '"') return 0;
    p++;
    size_t i = 0;
    while (*p && *p != '"' && i < out_size - 1) {
        out[i++] = *p++;
    }
    out[i] = '\0';
    return 1;
}

/* Igual que arriba pero para un campo numerico sin comillas (ej. "valor":39.8). */
static int extraer_campo_numero_json(const char *json, const char *clave, double *out) {
    char patron[64];
    snprintf(patron, sizeof(patron), "\"%s\"", clave);
    const char *p = strstr(json, patron);
    if (!p) return 0;
    p += strlen(patron);
    while (*p == ' ' || *p == '\t') p++;
    if (*p != ':') return 0;
    p++;
    while (*p == ' ' || *p == '\t') p++;
    char *fin = NULL;
    double v = strtod(p, &fin);
    if (fin == p) return 0;
    *out = v;
    return 1;
}

static long extraer_content_length(const char *peticion) {
    const char *p = strstr(peticion, "Content-Length:");
    if (!p) p = strstr(peticion, "content-length:");
    if (!p) return -1;
    p = strchr(p, ':');
    if (!p) return -1;
    p++;
    while (*p == ' ') p++;
    return atol(p);
}

static char *buscar_cuerpo(char *peticion) {
    char *p = strstr(peticion, "\r\n\r\n");
    return p ? p + 4 : NULL;
}

/* Recibe la peticion POST /api/alerta, la parsea y guarda la alerta.
 * peticion/recibidos: lo que ya se leyo del socket en el buffer
 * principal (puede incluir parte o todo el cuerpo JSON). Si hace
 * falta, sigue leyendo del socket hasta completar Content-Length. */
static void manejar_alerta_esp32(int cliente_fd, char *peticion, ssize_t recibidos) {
    long content_length = extraer_content_length(peticion);
    char *cuerpo = buscar_cuerpo(peticion);
    char respuesta[512];

    if (cuerpo && content_length > 0) {
        ssize_t ya_en_cuerpo = recibidos - (cuerpo - peticion);
        while (ya_en_cuerpo < content_length && recibidos < (ssize_t)(TAM_BUF_PETICION - 1)) {
            ssize_t extra = read(cliente_fd, peticion + recibidos, TAM_BUF_PETICION - 1 - recibidos);
            if (extra <= 0) break;
            recibidos += extra;
            peticion[recibidos] = '\0';
            ya_en_cuerpo += extra;
            cuerpo = buscar_cuerpo(peticion);
        }
    }

    if (!cuerpo) {
        int len = snprintf(respuesta, sizeof(respuesta),
            "HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");
        write(cliente_fd, respuesta, len);
        fprintf(stderr, "[pawos-monitoreo] POST /api/alerta sin cuerpo, se descarto.\n");
        return;
    }

    Alerta a;
    memset(&a, 0, sizeof(a));
    char animal_id[sizeof(a.animal_id)] = {0};
    char tipo[sizeof(a.tipo)] = {0};
    char detalle[sizeof(a.detalle)] = {0};
    double valor = 0;

    extraer_campo_texto_json(cuerpo, "animal_id", animal_id, sizeof(animal_id));
    extraer_campo_texto_json(cuerpo, "tipo", tipo, sizeof(tipo));
    extraer_campo_texto_json(cuerpo, "detalle", detalle, sizeof(detalle));
    extraer_campo_numero_json(cuerpo, "valor", &valor);

    if (!db_disponible || strlen(animal_id) == 0 || strlen(tipo) == 0) {
        int len = snprintf(respuesta, sizeof(respuesta),
            "HTTP/1.1 422 Unprocessable Entity\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");
        write(cliente_fd, respuesta, len);
        fprintf(stderr, "[pawos-monitoreo] Alerta ESP32 invalida o BD no disponible, se descarto.\n");
        return;
    }

    snprintf(a.animal_id, sizeof(a.animal_id), "%s", animal_id);
    snprintf(a.tipo, sizeof(a.tipo), "%s", tipo);
    snprintf(a.detalle, sizeof(a.detalle), "%s", detalle);
    a.valor = valor;

    if (alerta_registrar(&a) == 0) {
        printf("[pawos-monitoreo] Alerta ESP32 guardada: animal=%s tipo=%s valor=%.2f\n",
               animal_id, tipo, valor);
        const char *cuerpo_resp = "{\"estado\":\"ok\"}";
        int len = snprintf(respuesta, sizeof(respuesta),
            "HTTP/1.1 201 Created\r\nContent-Type: application/json\r\nContent-Length: %zu\r\nConnection: close\r\n\r\n%s",
            strlen(cuerpo_resp), cuerpo_resp);
        write(cliente_fd, respuesta, len);
    } else {
        fprintf(stderr, "[pawos-monitoreo] Error al guardar la alerta ESP32 en la base de datos.\n");
        int len = snprintf(respuesta, sizeof(respuesta),
            "HTTP/1.1 500 Internal Server Error\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");
        write(cliente_fd, respuesta, len);
    }
}

int main(void) {
    if (db_init(RUTA_BD_DEFECTO) == 0) {
        db_disponible = 1;
    } else {
        fprintf(stderr, "[pawos-monitoreo] Aviso: no se pudo usar %s, probando ./pawos.db\n", RUTA_BD_DEFECTO);
        if (db_init("pawos.db") == 0) {
            db_disponible = 1;
        } else {
            fprintf(stderr, "[pawos-monitoreo] No se pudo inicializar la base de datos: "
                            "las alertas del ESP32 no se podran guardar (el dashboard si sigue funcionando).\n");
        }
    }

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
    printf("[pawos-monitoreo] Escuchando en el puerto %d (dashboard con auth + POST /api/alerta para el ESP32)...\n", PUERTO);
    fflush(stdout);
    char pagina[8192];
    char respuesta[8600];
    while (1) {
        int cliente_fd = accept(servidor_fd, NULL, NULL);
        if (cliente_fd < 0) continue;

        static char buf_peticion[TAM_BUF_PETICION];
        ssize_t leidos = read(cliente_fd, buf_peticion, sizeof(buf_peticion) - 1);
        if (leidos > 0) buf_peticion[leidos] = '\0';
        else { buf_peticion[0] = '\0'; leidos = 0; }

        char metodo[8] = {0};
        char ruta[256] = {0};
        sscanf(buf_peticion, "%7s %255s", metodo, ruta);

        if (strcmp(metodo, "POST") == 0 && strcmp(ruta, "/api/alerta") == 0) {
            manejar_alerta_esp32(cliente_fd, buf_peticion, leidos);
            close(cliente_fd);
            continue;
        }

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
    if (db_disponible) db_close();
    close(servidor_fd);
    return 0;
}
