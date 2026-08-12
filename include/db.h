#ifndef DB_H
#define DB_H

#include <sqlite3.h>

/* ---------- Estructuras de datos ---------- */

typedef struct {
    int  id;
    char nombre[64];
    char especie[32];
    char raza[32];
    int  edad;
    char estado[16];        /* disponible | en_proceso | adoptado | tratamiento */
    char fecha_ingreso[16]; /* YYYY-MM-DD */
} Mascota;

typedef struct {
    int  id;
    int  mascota_id;
    char nombre_vacuna[64];
    char fecha_aplicacion[16];
    char fecha_proxima[16];
} Vacuna;

typedef struct {
    int  id;
    int  mascota_id;
    char adoptante_nombre[64];
    char adoptante_contacto[64];
    char fecha_adopcion[16];
} Adopcion;

typedef struct {
    int    id;
    char   nombre[64];
    char   contacto[64];
    double monto;
    char   fecha[16];
} Donante;

typedef struct {
    int    id;
    char   animal_id[32];   /* identificador de la mascota/collar que reporto el ESP32 */
    char   tipo[32];        /* temperatura | movimiento | inactividad | sonido | combinada */
    char   detalle[128];
    double valor;
    char   fecha_hora[24];  /* YYYY-MM-DD HH:MM:SS, la genera el programa al insertar */
    int    atendida;        /* 0 = pendiente, 1 = ya revisada por el personal */
} Alerta;

/* ---------- Ciclo de vida ---------- */
int  db_init(const char *ruta);
void db_close(void);

/* ---------- Mascotas ---------- */
int  mascota_agregar(const Mascota *m);
int  mascota_listar(Mascota **out, int *n);
int  mascota_actualizar_estado(int id, const char *nuevo_estado);
int  mascota_eliminar(int id);
int  mascota_buscar_por_id(int id, Mascota *out);

/* ---------- Vacunas ---------- */
int  vacuna_agregar(const Vacuna *v);
int  vacuna_listar(Vacuna **out, int *n);
int  vacuna_pendientes(Vacuna **out, int *n); /* fecha_proxima <= hoy */

/* ---------- Adopciones ---------- */
int  adopcion_registrar(const Adopcion *a);
int  adopcion_listar(Adopcion **out, int *n);

/* ---------- Donantes ---------- */
int  donante_agregar(const Donante *d);
int  donante_listar(Donante **out, int *n);
double donante_total_recaudado(void);

/* ---------- Alertas de sensores (ESP32) ---------- */
int  alerta_registrar(const Alerta *a);       /* genera fecha_hora automaticamente, atendida=0 */
int  alerta_listar(Alerta **out, int *n);     /* todas, mas recientes primero */
int  alerta_pendientes(Alerta **out, int *n); /* atendida = 0, mas recientes primero */
int  alerta_marcar_atendida(int id);

/* ---------- Reportes ---------- */
int reporte_generar(const char *ruta_salida);

#endif
