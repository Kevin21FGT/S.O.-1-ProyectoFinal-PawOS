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

# =========================================================
# src/ui.c  (version corregida, con las lineas en blanco reales)
# =========================================================
old = '''void ui_pedir_texto(const char *etiqueta, char *out, int maxlen) {
    clear();
    marco("Ingresar datos");
    echo();
    curs_set(1);
    mvprintw(3, 3, "%s", etiqueta);
    move(5, 3);
    getnstr(out, maxlen - 1);
    noecho();
    curs_set(0);
}

int ui_pedir_entero(const char *etiqueta) {
    char buf[32];
    ui_pedir_texto(etiqueta, buf, sizeof(buf));
    return atoi(buf);
}

double ui_pedir_double(const char *etiqueta) {
    char buf[32];
    ui_pedir_texto(etiqueta, buf, sizeof(buf));
    return atof(buf);
}'''
new = '''static int g_cancelado = 0;

int ui_fue_cancelado(void) {
    return g_cancelado;
}

int ui_pedir_texto(const char *etiqueta, char *out, int maxlen) {
    clear();
    marco("Ingresar datos");
    mvprintw(3, 3, "%s", etiqueta);
    pie("Escriba el valor | Enter: confirmar | ESC: cancelar");
    curs_set(1);

    int pos = 0;
    if (maxlen > 0) out[0] = '\\0';
    g_cancelado = 0;

    while (1) {
        move(5, 3 + pos);
        refresh();
        int ch = getch();
        if (ch == 27) { /* ESC */
            g_cancelado = 1;
            if (maxlen > 0) out[0] = '\\0';
            break;
        } else if (ch == '\\n' || ch == '\\r' || ch == KEY_ENTER) {
            g_cancelado = 0;
            break;
        } else if (ch == KEY_BACKSPACE || ch == 127 || ch == 8) {
            if (pos > 0) {
                pos--;
                out[pos] = '\\0';
                mvaddch(5, 3 + pos, ' ');
            }
        } else if (ch >= 32 && ch < 256 && pos < maxlen - 1) {
            out[pos] = (char)ch;
            pos++;
            out[pos] = '\\0';
            mvaddch(5, 3 + pos - 1, ch);
        }
    }
    curs_set(0);
    return g_cancelado ? -1 : 0;
}

int ui_pedir_entero(const char *etiqueta) {
    char buf[32];
    ui_pedir_texto(etiqueta, buf, sizeof(buf));
    if (g_cancelado) return 0;
    return atoi(buf);
}

double ui_pedir_double(const char *etiqueta) {
    char buf[32];
    ui_pedir_texto(etiqueta, buf, sizeof(buf));
    if (g_cancelado) return 0.0;
    return atof(buf);
}'''
replace_or_die("src/ui.c", old, new, "ui_pedir_texto con ESC-cancelar")

# =========================================================
# src/pantallas.c
# =========================================================

# --- agregar_mascota_pantalla ---
old = '''static void agregar_mascota_pantalla(void) {
    Mascota m; memset(&m, 0, sizeof(m));
    ui_pedir_texto("Nombre de la mascota:", m.nombre, sizeof(m.nombre));
    ui_pedir_texto("Especie (perro/gato/otro):", m.especie, sizeof(m.especie));
    ui_pedir_texto("Raza (opcional):", m.raza, sizeof(m.raza));
    m.edad = ui_pedir_entero("Edad (anios):");
    strcpy(m.estado, "disponible");'''
new = '''static void agregar_mascota_pantalla(void) {
    Mascota m; memset(&m, 0, sizeof(m));
    ui_pedir_texto("Nombre de la mascota:", m.nombre, sizeof(m.nombre));
    if (ui_fue_cancelado()) return;
    ui_pedir_texto("Especie (perro/gato/otro):", m.especie, sizeof(m.especie));
    if (ui_fue_cancelado()) return;
    ui_pedir_texto("Raza (opcional):", m.raza, sizeof(m.raza));
    if (ui_fue_cancelado()) return;
    m.edad = ui_pedir_entero("Edad (anios):");
    if (ui_fue_cancelado()) return;
    strcpy(m.estado, "disponible");'''
replace_or_die("src/pantallas.c", old, new, "agregar_mascota_pantalla")

# --- cambiar_estado_pantalla ---
old = '''static void cambiar_estado_pantalla(void) {
    int id = ui_pedir_entero("ID de la mascota:");
    Mascota m;
    if (mascota_buscar_por_id(id, &m) != 0) {'''
new = '''static void cambiar_estado_pantalla(void) {
    int id = ui_pedir_entero("ID de la mascota:");
    if (ui_fue_cancelado()) return;
    Mascota m;
    if (mascota_buscar_por_id(id, &m) != 0) {'''
replace_or_die("src/pantallas.c", old, new, "cambiar_estado_pantalla")

# --- eliminar_mascota_pantalla ---
old = '''static void eliminar_mascota_pantalla(void) {
    int id = ui_pedir_entero("ID de la mascota a eliminar:");
    if (mascota_eliminar(id) == 0)'''
new = '''static void eliminar_mascota_pantalla(void) {
    int id = ui_pedir_entero("ID de la mascota a eliminar:");
    if (ui_fue_cancelado()) return;
    if (mascota_eliminar(id) == 0)'''
replace_or_die("src/pantallas.c", old, new, "eliminar_mascota_pantalla")

# --- agregar_vacuna_pantalla ---
old = '''static void agregar_vacuna_pantalla(void) {
    Vacuna v; memset(&v, 0, sizeof(v));
    v.mascota_id = ui_pedir_entero("ID de la mascota:");
    Mascota m;
    if (mascota_buscar_por_id(v.mascota_id, &m) != 0) {
        ui_mensaje("No existe una mascota con ese ID.", 1);
        return;
    }
    ui_pedir_texto("Nombre de la vacuna:", v.nombre_vacuna, sizeof(v.nombre_vacuna));
    ui_pedir_texto("Fecha de aplicacion (YYYY-MM-DD):", v.fecha_aplicacion, sizeof(v.fecha_aplicacion));
    ui_pedir_texto("Proxima dosis (YYYY-MM-DD, opcional):", v.fecha_proxima, sizeof(v.fecha_proxima));
    if (vacuna_agregar(&v) == 0)'''
new = '''static void agregar_vacuna_pantalla(void) {
    Vacuna v; memset(&v, 0, sizeof(v));
    v.mascota_id = ui_pedir_entero("ID de la mascota:");
    if (ui_fue_cancelado()) return;
    Mascota m;
    if (mascota_buscar_por_id(v.mascota_id, &m) != 0) {
        ui_mensaje("No existe una mascota con ese ID.", 1);
        return;
    }
    ui_pedir_texto("Nombre de la vacuna:", v.nombre_vacuna, sizeof(v.nombre_vacuna));
    if (ui_fue_cancelado()) return;
    ui_pedir_texto("Fecha de aplicacion (YYYY-MM-DD):", v.fecha_aplicacion, sizeof(v.fecha_aplicacion));
    if (ui_fue_cancelado()) return;
    ui_pedir_texto("Proxima dosis (YYYY-MM-DD, opcional):", v.fecha_proxima, sizeof(v.fecha_proxima));
    if (ui_fue_cancelado()) return;
    if (vacuna_agregar(&v) == 0)'''
replace_or_die("src/pantallas.c", old, new, "agregar_vacuna_pantalla")

# --- editar_vacuna_pantalla ---
old = '''static void editar_vacuna_pantalla(void) {
    int id = ui_pedir_entero("ID de la vacuna a editar:");
    Vacuna v;
    if (vacuna_buscar_por_id(id, &v) != 0) {
        ui_mensaje("No existe una vacuna con ese ID.", 1);
        return;
    }
    ui_pedir_texto("Nombre de la vacuna:", v.nombre_vacuna, sizeof(v.nombre_vacuna));
    ui_pedir_texto("Fecha de aplicacion (YYYY-MM-DD):", v.fecha_aplicacion, sizeof(v.fecha_aplicacion));
    ui_pedir_texto("Proxima dosis (YYYY-MM-DD, opcional):", v.fecha_proxima, sizeof(v.fecha_proxima));
    if (vacuna_actualizar(&v) == 0)'''
new = '''static void editar_vacuna_pantalla(void) {
    int id = ui_pedir_entero("ID de la vacuna a editar:");
    if (ui_fue_cancelado()) return;
    Vacuna v;
    if (vacuna_buscar_por_id(id, &v) != 0) {
        ui_mensaje("No existe una vacuna con ese ID.", 1);
        return;
    }
    ui_pedir_texto("Nombre de la vacuna:", v.nombre_vacuna, sizeof(v.nombre_vacuna));
    if (ui_fue_cancelado()) return;
    ui_pedir_texto("Fecha de aplicacion (YYYY-MM-DD):", v.fecha_aplicacion, sizeof(v.fecha_aplicacion));
    if (ui_fue_cancelado()) return;
    ui_pedir_texto("Proxima dosis (YYYY-MM-DD, opcional):", v.fecha_proxima, sizeof(v.fecha_proxima));
    if (ui_fue_cancelado()) return;
    if (vacuna_actualizar(&v) == 0)'''
replace_or_die("src/pantallas.c", old, new, "editar_vacuna_pantalla")

# --- eliminar_vacuna_pantalla ---
old = '''static void eliminar_vacuna_pantalla(void) {
    int id = ui_pedir_entero("ID de la vacuna a eliminar:");
    Vacuna v;
    if (vacuna_buscar_por_id(id, &v) != 0) {'''
new = '''static void eliminar_vacuna_pantalla(void) {
    int id = ui_pedir_entero("ID de la vacuna a eliminar:");
    if (ui_fue_cancelado()) return;
    Vacuna v;
    if (vacuna_buscar_por_id(id, &v) != 0) {'''
replace_or_die("src/pantallas.c", old, new, "eliminar_vacuna_pantalla")

# --- registrar_adopcion_pantalla ---
old = '''    a.mascota_id = ui_pedir_entero("ID de la mascota a adoptar:");
    Mascota m;
    if (mascota_buscar_por_id(a.mascota_id, &m) != 0) {
        ui_mensaje("No existe una mascota con ese ID.", 1);
        return;
    }
    if (strcmp(m.estado, "adoptado") == 0) {
        ui_mensaje("Esa mascota ya fue adoptada.", 1);
        return;
    }
    ui_pedir_texto("Nombre del adoptante:", a.adoptante_nombre, sizeof(a.adoptante_nombre));
    ui_pedir_texto("Contacto del adoptante:", a.adoptante_contacto, sizeof(a.adoptante_contacto));
    hoy(a.fecha_adopcion, sizeof(a.fecha_adopcion));'''
new = '''    a.mascota_id = ui_pedir_entero("ID de la mascota a adoptar:");
    if (ui_fue_cancelado()) return;
    Mascota m;
    if (mascota_buscar_por_id(a.mascota_id, &m) != 0) {
        ui_mensaje("No existe una mascota con ese ID.", 1);
        return;
    }
    if (strcmp(m.estado, "adoptado") == 0) {
        ui_mensaje("Esa mascota ya fue adoptada.", 1);
        return;
    }
    ui_pedir_texto("Nombre del adoptante:", a.adoptante_nombre, sizeof(a.adoptante_nombre));
    if (ui_fue_cancelado()) return;
    ui_pedir_texto("Contacto del adoptante:", a.adoptante_contacto, sizeof(a.adoptante_contacto));
    if (ui_fue_cancelado()) return;
    hoy(a.fecha_adopcion, sizeof(a.fecha_adopcion));'''
replace_or_die("src/pantallas.c", old, new, "registrar_adopcion_pantalla")

# --- agregar_donante_pantalla ---
old = '''static void agregar_donante_pantalla(void) {
    Donante d; memset(&d, 0, sizeof(d));
    ui_pedir_texto("Nombre del donante:", d.nombre, sizeof(d.nombre));
    ui_pedir_texto("Contacto:", d.contacto, sizeof(d.contacto));
    d.monto = ui_pedir_double("Monto donado:");
    hoy(d.fecha, sizeof(d.fecha));'''
new = '''static void agregar_donante_pantalla(void) {
    Donante d; memset(&d, 0, sizeof(d));
    ui_pedir_texto("Nombre del donante:", d.nombre, sizeof(d.nombre));
    if (ui_fue_cancelado()) return;
    ui_pedir_texto("Contacto:", d.contacto, sizeof(d.contacto));
    if (ui_fue_cancelado()) return;
    d.monto = ui_pedir_double("Monto donado:");
    if (ui_fue_cancelado()) return;
    hoy(d.fecha, sizeof(d.fecha));'''
replace_or_die("src/pantallas.c", old, new, "agregar_donante_pantalla")

print("Listo, todos los formularios ahora soportan ESC para cancelar.")
