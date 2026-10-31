
/*
 * vacunas_demonio.c - Servicio en segundo plano de PawOS.
 * Revisa la base de datos en busca de vacunas pendientes o vencidas
 * y genera una alerta (consola + log), sin necesidad de que un usuario
 * entre al menu del programa. Pensado para correr via systemd timer.
 */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include <sys/wait.h>
#include "db/db.h"

#define RUTA_BD_DEFECTO  "/var/pawos/pawos.db"
#define RUTA_LOG_DEFECTO "/var/pawos/archivos/reportes/alertas_vacunas.log"

// --- FUNCIÓN DE RESPALDO PARA CALCULAR HORAS SIN MOVIMIENTO ---
#include <sqlite3.h>

double alerta_horas_desde_ultimo_movimiento_pir(char *fecha_ultimo_out, size_t size) {
    sqlite3 *db;
    sqlite3_stmt *stmt;
    double horas = 0.0;
    
    // Abrimos la base de datos local
    if (sqlite3_open("pawos.db", &db) != SQLITE_OK) {
        return -1.0; 
    }
    
    // Consulta SQL para calcular la diferencia de horas con el último registro del PIR
    const char *sql = "SELECT detalles, (julianday('now', 'localtime') - julianday(fecha_hora)) * 24 FROM alertas_sensores WHERE sensor = 'PIR' ORDER BY id DESC LIMIT 1;";
    
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK) {
        if (sqlite3_step(stmt) == SQLITE_ROW) {
            const unsigned char *texto_fecha = sqlite3_column_text(stmt, 0);
            horas = sqlite3_column_double(stmt, 1);
            
            if (texto_fecha && fecha_ultimo_out) {
                snprintf(fecha_ultimo_out, size, "%s", texto_fecha);
            }
        } else {
            // Si no hay ningún registro previo en la tabla, asumimos 8 horas para disparar la primera alerta
            horas = 8.5; 
            if (fecha_ultimo_out) snprintf(fecha_ultimo_out, size, "Sin registros previos");
        }
        sqlite3_finalize(stmt);
    }
    sqlite3_close(db);
    return horas;
}


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
    Cliente *clientes = NULL; int n_clientes = 0;
    cliente_listar(&clientes, &n_clientes);
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
                    printf("[%s] Recordatorio automatico a %s (%s): %s\n",
                           sello, c->nombre, c->correo, ok ? "enviado" : "FALLO");
                    if (log) {
                        fprintf(log, "[%s] Recordatorio automatico a %s (%s): %s\n",
                                sello, c->nombre, c->correo, ok ? "enviado" : "FALLO");
                    }
                    if (ok) vacuna_marcar_recordatorio_enviado(pendientes[i].id);
                } else {
                    fprintf(stderr, "[pawos-vacunas-check] No se pudo crear el proceso para notificar a %s.\n", c->nombre);
                }
            }
        }
    }
        if (log) fclose(log);

    // =========================================================================
    // --- MONITOREO DEL PLATO DE COMIDA (TU PARTE DEL PROYECTO) ---
    // =========================================================================
        char fecha_ultimo_mov[32] = {0};
double horas_sin_comer = alerta_horas_desde_ultimo_movimiento_pir(fecha_ultimo_mov, sizeof(fecha_ultimo_mov));

    // Si la función devuelve un número negativo o error, no hacemos nada
    if (horas_sin_comer >= 0.0) {
        printf("[%s] [MONITOREO COMIDA] La mascota lleva %.2f horas sin acercarse al plato.\n", sello, horas_sin_comer);
        
        FILE *log_comida = fopen("alertas_comida.log", "a");
        if (log_comida) {
            fprintf(log_comida, "[%s] Alerta: %.2f horas sin movimiento. Último: %s\n", sello, horas_sin_comer, fecha_ultimo_mov);
            fclose(log_comida);
        }

        // Si han pasado 8 horas o más, disparamos la alerta automática del sistema operativo
        if (horas_sin_comer >= 8.0) {
            printf("[ALERTA PAWOS] ¡La mascota no ha comido en 8 horas!\n");
            
            pid_t pid_alerta = fork();
            if (pid_alerta == 0) {
                // Ejecuta de forma nativa el script de notificación que hicieron tus compañeros
                execlp("pawos-enviar-whatsapp-cita", "pawos-enviar-whatsapp-cita", 
                       "ALERTA PAWOS: El sensor no ha detectado movimiento en el plato de comida en más de 8 horas. La mascota podría no haber comido.", 
                       (char *)NULL);
                _exit(127);
            } else if (pid_alerta > 0) {
                int estado_alerta = 0;
                waitpid(pid_alerta, &estado_alerta, 0);
            }
        }
    }
    // =========================================================================

    free(clientes);
    free(pendientes);
    db_close();
    return 0;
}
