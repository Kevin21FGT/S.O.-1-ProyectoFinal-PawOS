#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <ctype.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <signal.h>
#include <errno.h>
#include "procesos.h"

/* Traduce el codigo de estado que usa Linux en /proc/[pid]/stat
   a una palabra entendible para el usuario. */
static const char *estado_legible(char c) {
    switch (c) {
        case 'R': return "Ejecutando";
        case 'S': return "Durmiendo";
        case 'D': return "Espera E/S";
        case 'Z': return "Zombie";
        case 'T': return "Detenido";
        default:  return "Desconocido";
    }
}

int procesos_obtener_lista(ProcesoInfo *lista, int max) {
    DIR *dir = opendir("/proc");
    if (!dir) return -1;

    struct dirent *entrada;
    int total = 0;

    while (total < max && (entrada = readdir(dir)) != NULL) {
        int es_numero = (entrada->d_name[0] != '\0');
        for (const char *p = entrada->d_name; *p; p++) {
            if (!isdigit((unsigned char)*p)) { es_numero = 0; break; }
        }
        if (!es_numero) continue;

        int pid = atoi(entrada->d_name);

        char ruta[64];
        snprintf(ruta, sizeof(ruta), "/proc/%d/comm", pid);
        FILE *f = fopen(ruta, "r");
        if (!f) continue;

        char nombre[64] = "";
        if (fgets(nombre, sizeof(nombre), f)) {
            nombre[strcspn(nombre, "\n")] = '\0';
        }
        fclose(f);

        char estado_c = '?';
        snprintf(ruta, sizeof(ruta), "/proc/%d/stat", pid);
        FILE *fs = fopen(ruta, "r");
        if (fs) {
            char linea[512];
            if (fgets(linea, sizeof(linea), fs)) {
                char *cierre = strrchr(linea, ')');
                if (cierre && *(cierre + 1) == ' ' && *(cierre + 2)) {
                    estado_c = *(cierre + 2);
                }
            }
            fclose(fs);
        }

        lista[total].pid = pid;
        strncpy(lista[total].nombre, nombre, sizeof(lista[total].nombre) - 1);
        lista[total].nombre[sizeof(lista[total].nombre) - 1] = '\0';
        strncpy(lista[total].estado, estado_legible(estado_c), sizeof(lista[total].estado) - 1);
        lista[total].estado[sizeof(lista[total].estado) - 1] = '\0';
        total++;
    }

    closedir(dir);
    return total;
}

int procesos_crear_ejemplo(void) {
    pid_t pid = fork();

    if (pid < 0) {
        return -1;
    }

    if (pid == 0) {
        FILE *log = fopen("/tmp/pawos_proceso_ejemplo.log", "a");
        if (log) {
            fprintf(log, "[hijo pid=%d] iniciando tarea de respaldo...\n", getpid());
            fflush(log);
        }
        sleep(5);
        if (log) {
            fprintf(log, "[hijo pid=%d] tarea de respaldo terminada.\n", getpid());
            fclose(log);
        }
        _exit(0);
    }

    return (int)pid;
}

int procesos_terminar(int pid, int forzar) {
    if (pid <= 1) {
        errno = EINVAL;
        return -1;
    }
    int senal = forzar ? SIGKILL : SIGTERM;
    if (kill((pid_t)pid, senal) != 0) {
        return -1;
    }
    return 0;
}