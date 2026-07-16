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

/* ---------- Reportes ---------- */
int reporte_generar(const char *ruta_salida);

#endif
