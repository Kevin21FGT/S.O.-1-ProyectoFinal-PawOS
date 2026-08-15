/*
 * db.c - Capa de acceso a datos (SQLite) para PawOS - Gestion de Refugio
 *
 * Todas las operaciones de mascotas, vacunas, adopciones, donantes y
 * alertas de sensores pasan por aqui. El resto del programa (menus
 * ncurses, o la interfaz grafica) no toca SQL directamente.
 */
#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <crypt.h>
#include "../include/db.h"

static sqlite3 *g_db = NULL;

static const char *SCHEMA =
    "CREATE TABLE IF NOT EXISTS mascotas ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  nombre TEXT NOT NULL,"
    "  especie TEXT NOT NULL,"
    "  raza TEXT,"
    "  edad INTEGER,"
    "  estado TEXT NOT NULL DEFAULT 'disponible',"
    "  fecha_ingreso TEXT NOT NULL"
    ");"
    "CREATE TABLE IF NOT EXISTS vacunas ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  mascota_id INTEGER NOT NULL,"
    "  nombre_vacuna TEXT NOT NULL,"
    "  fecha_aplicacion TEXT NOT NULL,"
    "  fecha_proxima TEXT,"
    "  observaciones TEXT DEFAULT '',"
    "  FOREIGN KEY(mascota_id) REFERENCES mascotas(id)"
    ");"
    "CREATE TABLE IF NOT EXISTS adopciones ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  mascota_id INTEGER NOT NULL,"
    "  adoptante_nombre TEXT NOT NULL,"
    "  adoptante_contacto TEXT,"
    "  fecha_adopcion TEXT NOT NULL,"
    "  FOREIGN KEY(mascota_id) REFERENCES mascotas(id)"
    ");"
    "CREATE TABLE IF NOT EXISTS donantes ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  nombre TEXT NOT NULL,"
    "  contacto TEXT,"
    "  monto REAL NOT NULL,"
    "  fecha TEXT NOT NULL"
    ");"
    "CREATE TABLE IF NOT EXISTS usuarios ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  username TEXT NOT NULL UNIQUE,"
    "  password TEXT NOT NULL,"
    "  rol INTEGER NOT NULL"
    ");"
    "CREATE TABLE IF NOT EXISTS notas_veterinario ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  mascota_id INTEGER NOT NULL,"
    "  nota TEXT NOT NULL,"
    "  autor TEXT NOT NULL,"
    "  fecha TEXT NOT NULL"
    ");"
    "CREATE TABLE IF NOT EXISTS alertas_sensores ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  animal_id TEXT NOT NULL,"
    "  tipo TEXT NOT NULL,"
    "  detalle TEXT,"
    "  valor REAL,"
    "  fecha_hora TEXT NOT NULL,"
    "  atendida INTEGER NOT NULL DEFAULT 0"
    ");";

/* Genera un hash de una contrasena en texto plano usando crypt() con
 * SHA-512 (prefijo "$6$") y una sal aleatoria nueva cada vez. 'out'
 * debe tener al menos 128 bytes. Se usa tanto para sembrar los
 * usuarios por defecto como para migrar contrasenas viejas guardadas
 * en texto plano (ver mas abajo) - nunca se guarda ni se compara la
 * contrasena tal cual en la base de datos. */
static void pawos_hash_password(const char *plano, char *out, size_t out_len) {
    static int sembrado = 0;
    if (!sembrado) {
        srand((unsigned)time(NULL) ^ (unsigned)getpid());
        sembrado = 1;
    }
    static const char alfabeto[] =
        "./ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    char sal[20] = "$6$";
    for (int i = 0; i < 16; i++) {
        sal[3 + i] = alfabeto[rand() % (int)(sizeof(alfabeto) - 1)];
    }
    sal[19] = '\0';
    char *resultado = crypt(plano, sal);
    snprintf(out, out_len, "%s", resultado ? resultado : "");
}

int db_init(const char *ruta) {
    if (sqlite3_open(ruta, &g_db) != SQLITE_OK) {
        fprintf(stderr, "No se pudo abrir la base de datos: %s\n", sqlite3_errmsg(g_db));
        return -1;
    }
    char *err = NULL;
    if (sqlite3_exec(g_db, SCHEMA, NULL, NULL, &err) != SQLITE_OK) {
        fprintf(stderr, "Error creando esquema: %s\n", err);
        sqlite3_free(err);
        return -1;
    }
    sqlite3_exec(g_db, "PRAGMA foreign_keys = ON;", NULL, NULL, NULL);

    /* Semilla de usuarios por defecto: mismos usuarios y mismas
     * contrasenas de siempre (admin123/vet123/vol123), pero ahora se
     * guardan como hash (crypt(), SHA-512), nunca en texto plano.
     * "INSERT OR IGNORE" sigue funcionando igual que antes: si el
     * usuario ya existe (username es UNIQUE), no hace nada. */
    {
        struct { const char *user; const char *pass; int rol; } semilla[] = {
            {"admin_refugio", "admin123", 0},
            {"veterinario1",  "vet123",   1},
            {"voluntario1",   "vol123",   2},
        };
        const char *sql_seed =
            "INSERT OR IGNORE INTO usuarios (username, password, rol) VALUES (?,?,?);";
        for (size_t i = 0; i < sizeof(semilla) / sizeof(semilla[0]); i++) {
            char hash[128];
            pawos_hash_password(semilla[i].pass, hash, sizeof(hash));
            sqlite3_stmt *st;
            if (sqlite3_prepare_v2(g_db, sql_seed, -1, &st, NULL) == SQLITE_OK) {
                sqlite3_bind_text(st, 1, semilla[i].user, -1, SQLITE_STATIC);
                sqlite3_bind_text(st, 2, hash, -1, SQLITE_TRANSIENT);
                sqlite3_bind_int(st, 3, semilla[i].rol);
                sqlite3_step(st);
                sqlite3_finalize(st);
            }
        }
    }

    /* Migracion aditiva: si la base de datos ya existia de una version
     * anterior de PawOS con contrasenas en texto plano (los hashes de
     * crypt() siempre empiezan con "$"), las convierte a hash ahora
     * mismo, sin pedirle nada al usuario ni perder ninguna cuenta. */
    {
        sqlite3_stmt *st;
        if (sqlite3_prepare_v2(g_db, "SELECT id, password FROM usuarios;", -1, &st, NULL) == SQLITE_OK) {
            while (sqlite3_step(st) == SQLITE_ROW) {
                int id = sqlite3_column_int(st, 0);
                const unsigned char *pass_actual = sqlite3_column_text(st, 1);
                if (pass_actual && pass_actual[0] != '\0' && pass_actual[0] != '$') {
                    char hash[128];
                    pawos_hash_password((const char *)pass_actual, hash, sizeof(hash));
                    sqlite3_stmt *upd;
                    if (sqlite3_prepare_v2(g_db, "UPDATE usuarios SET password=? WHERE id=?;", -1, &upd, NULL) == SQLITE_OK) {
                        sqlite3_bind_text(upd, 1, hash, -1, SQLITE_TRANSIENT);
                        sqlite3_bind_int(upd, 2, id);
                        sqlite3_step(upd);
                        sqlite3_finalize(upd);
                    }
                }
            }
            sqlite3_finalize(st);
        }
    }

    /* Migracion aditiva: si la base de datos ya existia de una version
     * anterior de PawOS (tabla vacunas sin la columna observaciones), la
     * agrega ahora. Si la columna ya existe (bases nuevas, creadas ya con
     * el SCHEMA de arriba), sqlite devuelve error "duplicate column name",
     * que se ignora a proposito: no rompe nada, solo significa que ya
     * estaba aplicada. */
    sqlite3_exec(g_db, "ALTER TABLE vacunas ADD COLUMN observaciones TEXT DEFAULT '';", NULL, NULL, NULL);
    return 0;
}

void db_close(void) {
    if (g_db) sqlite3_close(g_db);
    g_db = NULL;
}

int usuario_autenticar(const char *username, const char *password, int *rol_out) {
    /* Ya no se compara la contrasena dentro del SQL (WHERE password=?):
     * se trae el hash guardado para ese usuario y se compara aca,
     * usando crypt() (que extrae la sal del propio hash guardado y
     * recalcula, sin necesitar guardarla aparte). */
    const char *sql = "SELECT rol, password FROM usuarios WHERE username=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, username, -1, SQLITE_STATIC);
    int ok = -1;
    if (sqlite3_step(st) == SQLITE_ROW) {
        int rol = sqlite3_column_int(st, 0);
        const unsigned char *hash_guardado = sqlite3_column_text(st, 1);
        if (hash_guardado) {
            char *resultado = crypt(password, (const char *)hash_guardado);
            if (resultado && strcmp(resultado, (const char *)hash_guardado) == 0) {
                if (rol_out) *rol_out = rol;
                ok = 0;
            }
        }
    }
    sqlite3_finalize(st);
    return ok;
}

/* ---------------- Mascotas ---------------- */

int mascota_agregar(const Mascota *m) {
    const char *sql =
        "INSERT INTO mascotas (nombre, especie, raza, edad, estado, fecha_ingreso) "
        "VALUES (?,?,?,?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, m->nombre, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, m->especie, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 3, m->raza, -1, SQLITE_STATIC);
    sqlite3_bind_int(st, 4, m->edad);
    sqlite3_bind_text(st, 5, m->estado[0] ? m->estado : "disponible", -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 6, m->fecha_ingreso, -1, SQLITE_STATIC);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}

int mascota_listar(Mascota **out, int *n) {
    const char *sql = "SELECT id,nombre,especie,raza,edad,estado,fecha_ingreso FROM mascotas ORDER BY id;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;

    int cap = 16, cnt = 0;
    Mascota *arr = malloc(sizeof(Mascota) * cap);
    while (sqlite3_step(st) == SQLITE_ROW) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(Mascota) * cap); }
        Mascota *m = &arr[cnt++];
        memset(m, 0, sizeof(*m));
        m->id = sqlite3_column_int(st, 0);
        snprintf(m->nombre, sizeof(m->nombre), "%s", (const char*)sqlite3_column_text(st, 1));
        snprintf(m->especie, sizeof(m->especie), "%s", (const char*)sqlite3_column_text(st, 2));
        const unsigned char *raza = sqlite3_column_text(st, 3);
        snprintf(m->raza, sizeof(m->raza), "%s", raza ? (const char*)raza : "");
        m->edad = sqlite3_column_int(st, 4);
        snprintf(m->estado, sizeof(m->estado), "%s", (const char*)sqlite3_column_text(st, 5));
        snprintf(m->fecha_ingreso, sizeof(m->fecha_ingreso), "%s", (const char*)sqlite3_column_text(st, 6));
    }
    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}

int mascota_actualizar_estado(int id, const char *nuevo_estado) {
    const char *sql = "UPDATE mascotas SET estado=? WHERE id=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, nuevo_estado, -1, SQLITE_STATIC);
    sqlite3_bind_int(st, 2, id);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}

int mascota_eliminar(int id) {
    const char *sql = "DELETE FROM mascotas WHERE id=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, id);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}

int mascota_buscar_por_id(int id, Mascota *out) {
    const char *sql = "SELECT id,nombre,especie,raza,edad,estado,fecha_ingreso FROM mascotas WHERE id=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, id);
    int found = -1;
    if (sqlite3_step(st) == SQLITE_ROW) {
        memset(out, 0, sizeof(*out));
        out->id = sqlite3_column_int(st, 0);
        snprintf(out->nombre, sizeof(out->nombre), "%s", (const char*)sqlite3_column_text(st, 1));
        snprintf(out->especie, sizeof(out->especie), "%s", (const char*)sqlite3_column_text(st, 2));
        const unsigned char *raza = sqlite3_column_text(st, 3);
        snprintf(out->raza, sizeof(out->raza), "%s", raza ? (const char*)raza : "");
        out->edad = sqlite3_column_int(st, 4);
        snprintf(out->estado, sizeof(out->estado), "%s", (const char*)sqlite3_column_text(st, 5));
        snprintf(out->fecha_ingreso, sizeof(out->fecha_ingreso), "%s", (const char*)sqlite3_column_text(st, 6));
        found = 0;
    }
    sqlite3_finalize(st);
    return found;
}

/* ---------------- Vacunas ---------------- */

int vacuna_agregar(const Vacuna *v) {
    const char *sql =
        "INSERT INTO vacunas (mascota_id, nombre_vacuna, fecha_aplicacion, fecha_proxima, observaciones) "
        "VALUES (?,?,?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, v->mascota_id);
    sqlite3_bind_text(st, 2, v->nombre_vacuna, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 3, v->fecha_aplicacion, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 4, v->fecha_proxima, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 5, v->observaciones, -1, SQLITE_STATIC);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}

int vacuna_buscar_por_id(int id, Vacuna *out) {
    const char *sql = "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima,observaciones FROM vacunas WHERE id=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, id);
    int found = -1;
    if (sqlite3_step(st) == SQLITE_ROW) {
        memset(out, 0, sizeof(*out));
        out->id = sqlite3_column_int(st, 0);
        out->mascota_id = sqlite3_column_int(st, 1);
        snprintf(out->nombre_vacuna, sizeof(out->nombre_vacuna), "%s", (const char*)sqlite3_column_text(st, 2));
        snprintf(out->fecha_aplicacion, sizeof(out->fecha_aplicacion), "%s", (const char*)sqlite3_column_text(st, 3));
        const unsigned char *fp = sqlite3_column_text(st, 4);
        snprintf(out->fecha_proxima, sizeof(out->fecha_proxima), "%s", fp ? (const char*)fp : "");
        const unsigned char *obs = sqlite3_column_text(st, 5);
        snprintf(out->observaciones, sizeof(out->observaciones), "%s", obs ? (const char*)obs : "");
        found = 0;
    }
    sqlite3_finalize(st);
    return found;
}

int vacuna_actualizar(const Vacuna *v) {
    const char *sql = "UPDATE vacunas SET nombre_vacuna=?, fecha_aplicacion=?, fecha_proxima=?, observaciones=? WHERE id=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, v->nombre_vacuna, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, v->fecha_aplicacion, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 3, v->fecha_proxima, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 4, v->observaciones, -1, SQLITE_STATIC);
    sqlite3_bind_int(st, 5, v->id);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}

int vacuna_eliminar(int id) {
    const char *sql = "DELETE FROM vacunas WHERE id=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, id);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}

static int vacuna_query(const char *sql, Vacuna **out, int *n) {
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    int cap = 16, cnt = 0;
    Vacuna *arr = malloc(sizeof(Vacuna) * cap);
    while (sqlite3_step(st) == SQLITE_ROW) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(Vacuna) * cap); }
        Vacuna *v = &arr[cnt++];
        memset(v, 0, sizeof(*v));
        v->id = sqlite3_column_int(st, 0);
        v->mascota_id = sqlite3_column_int(st, 1);
        snprintf(v->nombre_vacuna, sizeof(v->nombre_vacuna), "%s", (const char*)sqlite3_column_text(st, 2));
        snprintf(v->fecha_aplicacion, sizeof(v->fecha_aplicacion), "%s", (const char*)sqlite3_column_text(st, 3));
        const unsigned char *fp = sqlite3_column_text(st, 4);
        snprintf(v->fecha_proxima, sizeof(v->fecha_proxima), "%s", fp ? (const char*)fp : "");
        const unsigned char *obs = sqlite3_column_text(st, 5);
        snprintf(v->observaciones, sizeof(v->observaciones), "%s", obs ? (const char*)obs : "");
    }
    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}

int vacuna_listar(Vacuna **out, int *n) {
    return vacuna_query(
        "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima,observaciones FROM vacunas ORDER BY fecha_proxima;",
        out, n);
}

int vacuna_pendientes(Vacuna **out, int *n) {
    char sql[256];
    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char hoy[16];
    strftime(hoy, sizeof(hoy), "%Y-%m-%d", &tmv);
    snprintf(sql, sizeof(sql),
        "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima,observaciones FROM vacunas "
        "WHERE fecha_proxima IS NOT NULL AND fecha_proxima <= '%s' ORDER BY fecha_proxima;", hoy);
    return vacuna_query(sql, out, n);
}

/* ---------------- Adopciones ---------------- */

int adopcion_registrar(const Adopcion *a) {
    /* transaccion: registrar adopcion + marcar mascota como adoptada */
    char *err = NULL;
    sqlite3_exec(g_db, "BEGIN;", NULL, NULL, &err);

    const char *sql =
        "INSERT INTO adopciones (mascota_id, adoptante_nombre, adoptante_contacto, fecha_adopcion) "
        "VALUES (?,?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) {
        sqlite3_exec(g_db, "ROLLBACK;", NULL, NULL, NULL);
        return -1;
    }
    sqlite3_bind_int(st, 1, a->mascota_id);
    sqlite3_bind_text(st, 2, a->adoptante_nombre, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 3, a->adoptante_contacto, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 4, a->fecha_adopcion, -1, SQLITE_STATIC);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    if (rc != SQLITE_DONE) {
        sqlite3_exec(g_db, "ROLLBACK;", NULL, NULL, NULL);
        return -1;
    }

    if (mascota_actualizar_estado(a->mascota_id, "adoptado") != 0) {
        sqlite3_exec(g_db, "ROLLBACK;", NULL, NULL, NULL);
        return -1;
    }

    sqlite3_exec(g_db, "COMMIT;", NULL, NULL, &err);
    return 0;
}

int adopcion_listar(Adopcion **out, int *n) {
    const char *sql =
        "SELECT id,mascota_id,adoptante_nombre,adoptante_contacto,fecha_adopcion FROM adopciones ORDER BY id;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    int cap = 16, cnt = 0;
    Adopcion *arr = malloc(sizeof(Adopcion) * cap);
    while (sqlite3_step(st) == SQLITE_ROW) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(Adopcion) * cap); }
        Adopcion *a = &arr[cnt++];
        memset(a, 0, sizeof(*a));
        a->id = sqlite3_column_int(st, 0);
        a->mascota_id = sqlite3_column_int(st, 1);
        snprintf(a->adoptante_nombre, sizeof(a->adoptante_nombre), "%s", (const char*)sqlite3_column_text(st, 2));
        const unsigned char *c = sqlite3_column_text(st, 3);
        snprintf(a->adoptante_contacto, sizeof(a->adoptante_contacto), "%s", c ? (const char*)c : "");
        snprintf(a->fecha_adopcion, sizeof(a->fecha_adopcion), "%s", (const char*)sqlite3_column_text(st, 4));
    }
    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}

/* ---------------- Donantes ---------------- */

int donante_agregar(const Donante *d) {
    const char *sql = "INSERT INTO donantes (nombre, contacto, monto, fecha) VALUES (?,?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, d->nombre, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, d->contacto, -1, SQLITE_STATIC);
    sqlite3_bind_double(st, 3, d->monto);
    sqlite3_bind_text(st, 4, d->fecha, -1, SQLITE_STATIC);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}

int donante_listar(Donante **out, int *n) {
    const char *sql = "SELECT id,nombre,contacto,monto,fecha FROM donantes ORDER BY id;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    int cap = 16, cnt = 0;
    Donante *arr = malloc(sizeof(Donante) * cap);
    while (sqlite3_step(st) == SQLITE_ROW) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(Donante) * cap); }
        Donante *d = &arr[cnt++];
        memset(d, 0, sizeof(*d));
        d->id = sqlite3_column_int(st, 0);
        snprintf(d->nombre, sizeof(d->nombre), "%s", (const char*)sqlite3_column_text(st, 1));
        const unsigned char *c = sqlite3_column_text(st, 2);
        snprintf(d->contacto, sizeof(d->contacto), "%s", c ? (const char*)c : "");
        d->monto = sqlite3_column_double(st, 3);
        snprintf(d->fecha, sizeof(d->fecha), "%s", (const char*)sqlite3_column_text(st, 4));
    }
    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}

double donante_total_recaudado(void) {
    const char *sql = "SELECT COALESCE(SUM(monto),0) FROM donantes;";
    sqlite3_stmt *st;
    double total = 0.0;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) == SQLITE_OK) {
        if (sqlite3_step(st) == SQLITE_ROW) total = sqlite3_column_double(st, 0);
    }
    sqlite3_finalize(st);
    return total;
}

/* ---------------- Alertas de sensores (ESP32) ---------------- */

int alerta_registrar(const Alerta *a) {
    const char *sql =
        "INSERT INTO alertas_sensores (animal_id, tipo, detalle, valor, fecha_hora, atendida) "
        "VALUES (?,?,?,?, datetime('now','localtime'), 0);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, a->animal_id, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, a->tipo, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 3, a->detalle, -1, SQLITE_STATIC);
    sqlite3_bind_double(st, 4, a->valor);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}

static int alerta_query(const char *sql, Alerta **out, int *n) {
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    int cap = 16, cnt = 0;
    Alerta *arr = malloc(sizeof(Alerta) * cap);
    while (sqlite3_step(st) == SQLITE_ROW) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(Alerta) * cap); }
        Alerta *a = &arr[cnt++];
        memset(a, 0, sizeof(*a));
        a->id = sqlite3_column_int(st, 0);
        snprintf(a->animal_id, sizeof(a->animal_id), "%s", (const char*)sqlite3_column_text(st, 1));
        snprintf(a->tipo, sizeof(a->tipo), "%s", (const char*)sqlite3_column_text(st, 2));
        const unsigned char *det = sqlite3_column_text(st, 3);
        snprintf(a->detalle, sizeof(a->detalle), "%s", det ? (const char*)det : "");
        a->valor = sqlite3_column_double(st, 4);
        snprintf(a->fecha_hora, sizeof(a->fecha_hora), "%s", (const char*)sqlite3_column_text(st, 5));
        a->atendida = sqlite3_column_int(st, 6);
    }
    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}

int alerta_listar(Alerta **out, int *n) {
    return alerta_query(
        "SELECT id,animal_id,tipo,detalle,valor,fecha_hora,atendida FROM alertas_sensores ORDER BY id DESC;",
        out, n);
}

int alerta_pendientes(Alerta **out, int *n) {
    return alerta_query(
        "SELECT id,animal_id,tipo,detalle,valor,fecha_hora,atendida FROM alertas_sensores "
        "WHERE atendida = 0 ORDER BY id DESC;",
        out, n);
}

int alerta_marcar_atendida(int id) {
    const char *sql = "UPDATE alertas_sensores SET atendida = 1 WHERE id = ?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, id);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}

/* ---------------- Notas del veterinario ---------------- */

int nota_veterinario_agregar(const NotaVeterinario *n) {
    const char *sql =
        "INSERT INTO notas_veterinario (mascota_id, nota, autor, fecha) "
        "VALUES (?,?,?, datetime('now','localtime'));";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, n->mascota_id);
    sqlite3_bind_text(st, 2, n->nota, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 3, n->autor, -1, SQLITE_STATIC);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}

int nota_veterinario_listar(NotaVeterinario **out, int *n) {
    const char *sql =
        "SELECT id, mascota_id, nota, autor, fecha FROM notas_veterinario ORDER BY id DESC;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    int cap = 16, cnt = 0;
    NotaVeterinario *arr = malloc(sizeof(NotaVeterinario) * cap);
    while (sqlite3_step(st) == SQLITE_ROW) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(NotaVeterinario) * cap); }
        NotaVeterinario *x = &arr[cnt++];
        memset(x, 0, sizeof(*x));
        x->id = sqlite3_column_int(st, 0);
        x->mascota_id = sqlite3_column_int(st, 1);
        snprintf(x->nota, sizeof(x->nota), "%s", (const char*)sqlite3_column_text(st, 2));
        snprintf(x->autor, sizeof(x->autor), "%s", (const char*)sqlite3_column_text(st, 3));
        snprintf(x->fecha, sizeof(x->fecha), "%s", (const char*)sqlite3_column_text(st, 4));
    }
    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}

/* ---------------- Reportes ---------------- */

int reporte_generar(const char *ruta_salida) {
    FILE *f = fopen(ruta_salida, "w");
    if (!f) return -1;

    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char fecha[32];
    strftime(fecha, sizeof(fecha), "%Y-%m-%d %H:%M:%S", &tmv);

    fprintf(f, "===== Reporte PawOS - Refugio de Animales =====\n");
    fprintf(f, "Generado: %s\n\n", fecha);

    Mascota *ms; int nm;
    mascota_listar(&ms, &nm);
    int disponibles = 0, adoptados = 0, en_proceso = 0, tratamiento = 0;
    for (int i = 0; i < nm; i++) {
        if (!strcmp(ms[i].estado, "disponible")) disponibles++;
        else if (!strcmp(ms[i].estado, "adoptado")) adoptados++;
        else if (!strcmp(ms[i].estado, "en_proceso")) en_proceso++;
        else if (!strcmp(ms[i].estado, "tratamiento")) tratamiento++;
    }
    fprintf(f, "-- Mascotas --\n");
    fprintf(f, "Total registradas : %d\n", nm);
    fprintf(f, "Disponibles        : %d\n", disponibles);
    fprintf(f, "En proceso adopcion: %d\n", en_proceso);
    fprintf(f, "Adoptadas          : %d\n", adoptados);
    fprintf(f, "En tratamiento     : %d\n\n", tratamiento);
    free(ms);

    Vacuna *vp; int nv;
    vacuna_pendientes(&vp, &nv);
    fprintf(f, "-- Vacunas pendientes o vencidas: %d --\n", nv);
    for (int i = 0; i < nv; i++)
        fprintf(f, "  Mascota #%d - %s (proxima: %s)\n", vp[i].mascota_id, vp[i].nombre_vacuna, vp[i].fecha_proxima);
    free(vp);
    fprintf(f, "\n");

    Adopcion *ad; int na;
    adopcion_listar(&ad, &na);
    fprintf(f, "-- Adopciones registradas: %d --\n\n", na);
    free(ad);

    double total = donante_total_recaudado();
    fprintf(f, "-- Donantes --\n");
    fprintf(f, "Total recaudado: %.2f\n", total);

    Alerta *al; int nal;
    alerta_pendientes(&al, &nal);
    fprintf(f, "\n-- Alertas de sensores pendientes: %d --\n", nal);
    for (int i = 0; i < nal; i++)
        fprintf(f, "  [%s] %s - %s (valor: %.2f)\n", al[i].fecha_hora, al[i].tipo, al[i].detalle, al[i].valor);
    free(al);

    fclose(f);
    return 0;
}
