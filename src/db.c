
/*
 * db.c - Capa de acceso a datos (SQLite) para PawOS - Gestion de Refugio
 *
 * Todas las operaciones de mascotas, vacunas, adopciones y donantes
 * pasan por aqui. El resto del programa (menus ncurses) no toca SQL
 * directamente.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
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
    ");";

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

    sqlite3_exec(g_db,
        "INSERT OR IGNORE INTO usuarios (username, password, rol) VALUES "
        "('admin_refugio','admin123',0),"
        "('veterinario1','vet123',1),"
        "('voluntario1','vol123',2);",
        NULL, NULL, NULL);

    return 0;
}
void db_close(void) {
    if (g_db) sqlite3_close(g_db);
    g_db = NULL;
}
int usuario_autenticar(const char *username, const char *password, int *rol_out) {
    const char *sql = "SELECT rol FROM usuarios WHERE username=? AND password=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, username, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, password, -1, SQLITE_STATIC);
    int ok = -1;
    if (sqlite3_step(st) == SQLITE_ROW) {
        if (rol_out) *rol_out = sqlite3_column_int(st, 0);
        ok = 0;
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
        "INSERT INTO vacunas (mascota_id, nombre_vacuna, fecha_aplicacion, fecha_proxima) "
        "VALUES (?,?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, v->mascota_id);
    sqlite3_bind_text(st, 2, v->nombre_vacuna, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 3, v->fecha_aplicacion, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 4, v->fecha_proxima, -1, SQLITE_STATIC);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}
int vacuna_buscar_por_id(int id, Vacuna *out) {
    const char *sql = "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima FROM vacunas WHERE id=?;";
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
        found = 0;
    }
    sqlite3_finalize(st);
    return found;
}

int vacuna_actualizar(const Vacuna *v) {
    const char *sql = "UPDATE vacunas SET nombre_vacuna=?, fecha_aplicacion=?, fecha_proxima=? WHERE id=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, v->nombre_vacuna, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, v->fecha_aplicacion, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 3, v->fecha_proxima, -1, SQLITE_STATIC);
    sqlite3_bind_int(st, 4, v->id);
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
    }
    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}
int vacuna_listar(Vacuna **out, int *n) {
    return vacuna_query(
        "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima FROM vacunas ORDER BY fecha_proxima;",
        out, n);
}
int vacuna_pendientes(Vacuna **out, int *n) {
    char sql[256];
    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char hoy[16];
    strftime(hoy, sizeof(hoy), "%Y-%m-%d", &tmv);
    snprintf(sql, sizeof(sql),
        "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima FROM vacunas "
        "WHERE fecha_proxima IS NOT NULL AND fecha_proxima <= '%s' ORDER BY fecha_proxima;", hoy);
    return vacuna_query(sql, out, n);
}

/* ---------------- Adopciones ---------------- */
int adopcion_registrar(const Adopcion *a) {
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

    fclose(f);
    return 0;
}
