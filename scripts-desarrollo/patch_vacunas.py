import sys

def replace_or_die(path, old, new, label):
    with open(path, "r") as f:
        s = f.read()
    if old not in s:
        print(f"ERROR: no se encontro el ancla esperada en {path} ({label})")
        sys.exit(1)
    s = s.replace(old, new, 1)
    with open(path, "w") as f:
        f.write(s)
    print(f"OK: {path} ({label})")

# ---------- 1. include/db.h ----------
old_h = "int  vacuna_pendientes(Vacuna **out, int *n); /* fecha_proxima <= hoy */"
new_h = old_h + """
int  vacuna_buscar_por_id(int id, Vacuna *out);
int  vacuna_actualizar(const Vacuna *v);
int  vacuna_eliminar(int id);"""
replace_or_die("include/db.h", old_h, new_h, "declaraciones de vacunas")

# ---------- 2. src/db.c ----------
anchor_c = "static int vacuna_query(const char *sql, Vacuna **out, int *n) {"
insercion_c = '''int vacuna_buscar_por_id(int id, Vacuna *out) {
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

'''
replace_or_die("src/db.c", anchor_c, insercion_c + anchor_c, "funciones vacuna_actualizar/eliminar/buscar_por_id")

# ---------- 3. src/pantallas.c ----------
old_p = '''    if (vacuna_agregar(&v) == 0)
        ui_mensaje("Vacuna registrada.", 0);
    else
        ui_mensaje("Error al registrar la vacuna.", 1);
}
void pantalla_vacunas(Rol rol) {
    while (1) {
        const char *op_admin[] = {"Ver todas", "Ver pendientes/vencidas", "Registrar vacuna", "Volver"};
        const char *op_vol[]   = {"Ver todas", "Ver pendientes/vencidas", "Volver"};
        const char **opciones = (rol == ROL_VOLUNTARIO) ? op_vol : op_admin;
        int n = (rol == ROL_VOLUNTARIO) ? 3 : 4;
        int sel = ui_menu("Agenda de Vacunas", opciones, n);
        if (sel < 0 || sel == n - 1) return;
        if (sel == 0) listar_vacunas_pantalla(0);
        else if (sel == 1) listar_vacunas_pantalla(1);
        else if (sel == 2 && rol != ROL_VOLUNTARIO) agregar_vacuna_pantalla();
    }
}'''

new_p = '''    if (vacuna_agregar(&v) == 0)
        ui_mensaje("Vacuna registrada.", 0);
    else
        ui_mensaje("Error al registrar la vacuna.", 1);
}
static void editar_vacuna_pantalla(void) {
    int id = ui_pedir_entero("ID de la vacuna a editar:");
    Vacuna v;
    if (vacuna_buscar_por_id(id, &v) != 0) {
        ui_mensaje("No existe una vacuna con ese ID.", 1);
        return;
    }
    ui_pedir_texto("Nombre de la vacuna:", v.nombre_vacuna, sizeof(v.nombre_vacuna));
    ui_pedir_texto("Fecha de aplicacion (YYYY-MM-DD):", v.fecha_aplicacion, sizeof(v.fecha_aplicacion));
    ui_pedir_texto("Proxima dosis (YYYY-MM-DD, opcional):", v.fecha_proxima, sizeof(v.fecha_proxima));
    if (vacuna_actualizar(&v) == 0)
        ui_mensaje("Vacuna actualizada.", 0);
    else
        ui_mensaje("Error al actualizar la vacuna.", 1);
}
static void eliminar_vacuna_pantalla(void) {
    int id = ui_pedir_entero("ID de la vacuna a eliminar:");
    Vacuna v;
    if (vacuna_buscar_por_id(id, &v) != 0) {
        ui_mensaje("No existe una vacuna con ese ID.", 1);
        return;
    }
    if (vacuna_eliminar(id) == 0)
        ui_mensaje("Vacuna eliminada.", 0);
    else
        ui_mensaje("Error al eliminar la vacuna.", 1);
}
void pantalla_vacunas(Rol rol) {
    while (1) {
        const char *op_admin[] = {"Ver todas", "Ver pendientes/vencidas", "Registrar vacuna", "Editar vacuna", "Eliminar vacuna", "Volver"};
        const char *op_vol[]   = {"Ver todas", "Ver pendientes/vencidas", "Volver"};
        const char **opciones = (rol == ROL_VOLUNTARIO) ? op_vol : op_admin;
        int n = (rol == ROL_VOLUNTARIO) ? 3 : 6;
        int sel = ui_menu("Agenda de Vacunas", opciones, n);
        if (sel < 0 || sel == n - 1) return;
        if (sel == 0) listar_vacunas_pantalla(0);
        else if (sel == 1) listar_vacunas_pantalla(1);
        else if (sel == 2 && rol != ROL_VOLUNTARIO) agregar_vacuna_pantalla();
        else if (sel == 3 && rol != ROL_VOLUNTARIO) editar_vacuna_pantalla();
        else if (sel == 4 && rol != ROL_VOLUNTARIO) eliminar_vacuna_pantalla();
    }
}'''
replace_or_die("src/pantallas.c", old_p, new_p, "menu de vacunas con editar/eliminar")

print("Listo, los 3 archivos quedaron parcheados.")
