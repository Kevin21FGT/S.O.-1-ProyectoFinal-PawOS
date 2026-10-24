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
    char observaciones[128]; /* notas libres sobre esta vacuna, opcional */
    int  cliente_id; /* 0 = sin Cliente asignado para notificar */
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

typedef struct {
    int  id;
    int  mascota_id;
    char nota[256];
    char autor[64];    /* usuario que dejo la nota */
    char fecha[24];    /* YYYY-MM-DD HH:MM:SS, la genera el programa al insertar */
} NotaVeterinario;

/* Datos basicos de un Colaborador (tabla "usuarios"), sin la
 * contrasena -- se usa para listarlos en la pantalla "Administrar
 * Colaboradores" (solo Administrador). */
typedef struct {
    int  id;
    char username[32];
    int  rol;
} UsuarioInfo;

/* Cliente = publico externo (adoptantes, donantes), NO es personal
 * del refugio. Tabla y login totalmente separados de "usuarios".
 *
 * "rol" aqui es el nivel del Cliente DENTRO de su propia organizacion
 * (otro refugio/veterinaria/negocio que usa PawOS) -- no tiene nada
 * que ver con los roles de Colaborador (Veterinario/Voluntario). */
typedef enum {
    ROL_CLIENTE_JEFE = 0,
    ROL_CLIENTE_SUPERVISOR = 1,
    ROL_CLIENTE_ADMIN = 2,
    ROL_CLIENTE_NORMAL = 3   /* persona normal (por defecto al registrarse) */
} RolCliente;

typedef struct {
    int        id;
    char       correo[128];
    char       nombre[64];
    char       telefono[32];  /* numero de WhatsApp, opcional */
    RolCliente rol;
} Cliente;

/* Solicitud de adopcion hecha por un Cliente desde el Portal de Clientes.
 * estado: Pendiente | Aprobada | Rechazada (lo cambia el personal). */
typedef struct {
    int  id;
    int  mascota_id;
    int  cliente_id;
    char fecha[16];     /* YYYY-MM-DD */
    char estado[20];
    char mensaje[501];  /* mensaje opcional del Cliente */
} SolicitudAdopcion;

/* Solicitud con los nombres ya resueltos (mascota y cliente), para la
 * pantalla del personal. */
typedef struct {
    int  id;
    int  mascota_id;
    char mascota_nombre[64];
    int  cliente_id;
    char cliente_nombre[64];
    char cliente_correo[128];
    char cliente_telefono[32];
    char fecha[16];
    char estado[20];     /* Pendiente | Aprobada | Rechazada */
    char mensaje[501];
} SolicitudInfo;

/* ---------- Ciclo de vida ---------- */
int  db_init(const char *ruta);
void db_close(void);

/* ---------- Autenticacion (tabla usuarios) ---------- */
int  usuario_autenticar(const char *username, const char *password, int *rol_out);
int  usuario_registrar(const char *username, const char *password, int rol, const char *foto_base64);
int  existe_admin(void);
int  usuario_listar(UsuarioInfo **out, int *n);

/* ---------- Clientes (publico externo: adoptantes y donantes) ---------- */
int  cliente_registrar(const char *correo, const char *password, const char *nombre, const char *telefono, RolCliente rol);
int  cliente_autenticar(const char *correo, const char *password, Cliente *out);
int  cliente_existe(const char *correo);
int  cliente_actualizar(int id, const char *nombre, const char *password_nueva);
int  cliente_actualizar_rol(int id, RolCliente nuevo_rol);
const char *cliente_rol_nombre(RolCliente rol);
int  cliente_listar(Cliente **out, int *n);
int  cliente_guardar_foto(int id, const char *foto_base64);
int  cliente_actualizar_telefono(int id, const char *telefono);
int  cliente_obtener_foto(int id, char **out_foto_base64); /* out_foto_base64: liberar con free() */
int  respaldo_existe_nombre(const char *nombre); /* 1 existe, 0 no, -1 error */
int  respaldo_borrar_nombre(const char *nombre); /* borra las filas de un respaldo por nombre */
int  respaldo_listar_nombres(char ***out, int *n); /* nombres de respaldos en la nube; liberar con free() */
int  respaldo_guardar(const char *fecha, const char *nombre, const char *tabla, const char *contenido); /* copia de una tabla (CSV) en la tabla remota respaldos */
int  mascota_listar_disponibles(Mascota **out, int *n);
int  solicitud_crear(int mascota_id, int cliente_id, const char *fecha, const char *mensaje);
int  solicitud_listar_cliente(int cliente_id, SolicitudAdopcion **out, int *n); /* liberar con free() */
int  solicitud_existe_activa(int mascota_id, int cliente_id); /* 1 si, 0 no, -1 error */
int  solicitud_listar_todas(SolicitudInfo **out, int *n); /* pendientes primero; liberar con free() */
int  solicitud_resolver(int id, int mascota_id, int aprobar); /* 1 aprueba (mascota -> en_proceso), 0 rechaza; 0 = ok */

/* ---------- Mascotas ---------- */
int  mascota_agregar(const Mascota *m);
int  mascota_listar(Mascota **out, int *n);
int  mascota_actualizar_estado(int id, const char *nuevo_estado);
int  mascota_eliminar(int id);
int  mascota_buscar_por_id(int id, Mascota *out);
/* Foto de la mascota: JPEG en base64 (columna foto_base64, SQL Server). */
int  mascota_guardar_foto(int id, const char *foto_base64);
int  mascota_obtener_foto(int id, char **out_foto_base64); /* liberar con free(); "" si no tiene */
int  mascota_ultimo_id(const char *nombre, const char *fecha_ingreso, int *id_out);

/* ---------- Vacunas ---------- */
int  vacuna_agregar(const Vacuna *v);
int  vacuna_buscar_por_id(int id, Vacuna *out);
int  vacuna_actualizar(const Vacuna *v);
int  vacuna_eliminar(int id);
int  vacuna_listar(Vacuna **out, int *n);
int  vacuna_pendientes(Vacuna **out, int *n); /* fecha_proxima <= hoy */
int  vacuna_recordatorio_enviado(int id);
int  vacuna_marcar_recordatorio_enviado(int id);

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

/* ---------- Notas del veterinario ---------- */
int  nota_veterinario_agregar(const NotaVeterinario *n); /* genera fecha automaticamente */
int  nota_veterinario_listar(NotaVeterinario **out, int *n); /* todas, mas recientes primero */

/* ---------- Reportes ---------- */
int reporte_generar(const char *ruta_salida);
int reporte_generar_mascotas(const char *ruta_salida);
int reporte_generar_vacunas(const char *ruta_salida);
int reporte_generar_adopciones(const char *ruta_salida);
int reporte_generar_donantes(const char *ruta_salida);
int reporte_generar_alertas(const char *ruta_salida);

#endif
