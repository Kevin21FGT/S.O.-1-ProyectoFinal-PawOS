/*
 * pantallas.c - Pantallas (submenus) de cada modulo del refugio.
 * Aqui se conecta la interfaz ncurses (ui.h) con la capa de datos (db.h),
 * respetando el rol del usuario que inicio sesion (auth.h).
 */
#include <ncurses.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include "../include/pantallas.h"
#include "../include/ui.h"
#include "../include/db.h"
#include "../include/integridad.h"
static void hoy(char *buf, int len) {
    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    strftime(buf, len, "%Y-%m-%d", &tmv);
}
/* ---------------- Mascotas ---------------- */
static void listar_mascotas_pantalla(void) {
    Mascota *ms; int n;
    mascota_listar(&ms, &n);
    clear();
    mvprintw(1, 2, "Mascotas registradas (%d)", n);
    mvprintw(3, 2, "%-4s %-14s %-10s %-6s %-12s", "ID", "Nombre", "Especie", "Edad", "Estado");
    int filas_disp = LINES - 6;
    for (int i = 0; i < n && i < filas_disp; i++) {
        mvprintw(4 + i, 2, "%-4d %-14s %-10s %-6d %-12s",
                 ms[i].id, ms[i].nombre, ms[i].especie, ms[i].edad, ms[i].estado);
    }
    if (n > filas_disp) mvprintw(4 + filas_disp, 2, "... y %d mas", n - filas_disp);
    mvprintw(LINES - 1, 2, "Presione una tecla para continuar...");
    refresh();
    getch();
    free(ms);
}
static void agregar_mascota_pantalla(void) {
    Mascota m; memset(&m, 0, sizeof(m));
    ui_pedir_texto("Nombre de la mascota:", m.nombre, sizeof(m.nombre));
    if (ui_fue_cancelado()) return;
    ui_pedir_texto("Especie (perro/gato/otro):", m.especie, sizeof(m.especie));
    if (ui_fue_cancelado()) return;
    ui_pedir_texto("Raza (opcional):", m.raza, sizeof(m.raza));
    if (ui_fue_cancelado()) return;
    m.edad = ui_pedir_entero("Edad (anios):");
    if (ui_fue_cancelado()) return;
    strcpy(m.estado, "disponible");
    hoy(m.fecha_ingreso, sizeof(m.fecha_ingreso));
    if (mascota_agregar(&m) == 0)
        ui_mensaje("Mascota registrada correctamente.", 0);
    else
        ui_mensaje("Error al registrar la mascota.", 1);
}
static void cambiar_estado_pantalla(void) {
    int id = ui_pedir_entero("ID de la mascota:");
    if (ui_fue_cancelado()) return;
    Mascota m;
    if (mascota_buscar_por_id(id, &m) != 0) {
        ui_mensaje("No existe una mascota con ese ID.", 1);
        return;
    }
    const char *opciones[] = {"disponible", "en_proceso", "adoptado", "tratamiento"};
    int sel = ui_menu("Nuevo estado", opciones, 4);
    if (sel < 0) return;
    if (mascota_actualizar_estado(id, opciones[sel]) == 0)
        ui_mensaje("Estado actualizado.", 0);
    else
        ui_mensaje("No se pudo actualizar.", 1);
}
static void eliminar_mascota_pantalla(void) {
    int id = ui_pedir_entero("ID de la mascota a eliminar:");
    if (ui_fue_cancelado()) return;
    if (mascota_eliminar(id) == 0)
        ui_mensaje("Mascota eliminada.", 0);
    else
        ui_mensaje("No se pudo eliminar.", 1);
}
void pantalla_mascotas(Rol rol) {
    while (1) {
        const char *base[] = {
            "Ver listado de mascotas",
            "Registrar nueva mascota",
            "Cambiar estado de una mascota",
            "Eliminar mascota",
            "Volver"
        };
        int n = (rol == ROL_VOLUNTARIO) ? 3 : 5;
        const char *opciones[5];
        opciones[0] = base[0];
        opciones[1] = base[1];
        if (rol == ROL_VOLUNTARIO) {
            opciones[2] = base[4];
        } else {
            opciones[2] = base[2];
            opciones[3] = base[3];
            opciones[4] = base[4];
        }
        int sel = ui_menu("Gestion de Mascotas", opciones, n);
        if (sel < 0 || opciones[sel] == base[4]) return;
        if (opciones[sel] == base[0]) listar_mascotas_pantalla();
        else if (opciones[sel] == base[1]) agregar_mascota_pantalla();
        else if (opciones[sel] == base[2]) cambiar_estado_pantalla();
        else if (opciones[sel] == base[3]) eliminar_mascota_pantalla();
    }
}
/* ---------------- Vacunas ---------------- */
static void listar_vacunas_pantalla(int solo_pendientes) {
    Vacuna *vs; int n;
    if (solo_pendientes) vacuna_pendientes(&vs, &n);
    else vacuna_listar(&vs, &n);
    clear();
    mvprintw(1, 2, solo_pendientes ? "Vacunas pendientes/vencidas (%d)" : "Todas las vacunas (%d)", n);
    mvprintw(3, 2, "%-4s %-6s %-18s %-12s %-12s", "ID", "MascID", "Vacuna", "Aplicada", "Proxima");
    int filas_disp = LINES - 6;
    for (int i = 0; i < n && i < filas_disp; i++) {
        mvprintw(4 + i, 2, "%-4d %-6d %-18s %-12s %-12s",
                 vs[i].id, vs[i].mascota_id, vs[i].nombre_vacuna, vs[i].fecha_aplicacion, vs[i].fecha_proxima);
    }
    if (n > filas_disp) mvprintw(4 + filas_disp, 2, "... y %d mas", n - filas_disp);
    mvprintw(LINES - 1, 2, "Presione una tecla para continuar...");
    refresh();
    getch();
    free(vs);
}
static void agregar_vacuna_pantalla(void) {
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
    if (vacuna_agregar(&v) == 0)
        ui_mensaje("Vacuna registrada.", 0);
    else
        ui_mensaje("Error al registrar la vacuna.", 1);
}
static void editar_vacuna_pantalla(void) {
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
    if (vacuna_actualizar(&v) == 0)
        ui_mensaje("Vacuna actualizada.", 0);
    else
        ui_mensaje("Error al actualizar la vacuna.", 1);
}
static void eliminar_vacuna_pantalla(void) {
    int id = ui_pedir_entero("ID de la vacuna a eliminar:");
    if (ui_fue_cancelado()) return;
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
}
/* ---------------- Adopciones ---------------- */
static void listar_adopciones_pantalla(void) {
    Adopcion *ad; int n;
    adopcion_listar(&ad, &n);
    clear();
    mvprintw(1, 2, "Adopciones registradas (%d)", n);
    mvprintw(3, 2, "%-4s %-6s %-18s %-12s", "ID", "MascID", "Adoptante", "Fecha");
    int filas_disp = LINES - 6;
    for (int i = 0; i < n && i < filas_disp; i++) {
        mvprintw(4 + i, 2, "%-4d %-6d %-18s %-12s",
                 ad[i].id, ad[i].mascota_id, ad[i].adoptante_nombre, ad[i].fecha_adopcion);
    }
    if (n > filas_disp) mvprintw(4 + filas_disp, 2, "... y %d mas", n - filas_disp);
    mvprintw(LINES - 1, 2, "Presione una tecla para continuar...");
    refresh();
    getch();
    free(ad);
}
static void registrar_adopcion_pantalla(void) {
    Adopcion a; memset(&a, 0, sizeof(a));
    a.mascota_id = ui_pedir_entero("ID de la mascota a adoptar:");
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
    hoy(a.fecha_adopcion, sizeof(a.fecha_adopcion));
    if (adopcion_registrar(&a) == 0)
        ui_mensaje("Adopcion registrada. La mascota ahora figura como adoptada.", 0);
    else
        ui_mensaje("Error al registrar la adopcion.", 1);
}
void pantalla_adopciones(Rol rol) {
    (void)rol;
    while (1) {
        const char *opciones[] = {"Ver listado", "Registrar adopcion", "Volver"};
        int sel = ui_menu("Control de Adopciones", opciones, 3);
        if (sel < 0 || sel == 2) return;
        if (sel == 0) listar_adopciones_pantalla();
        else if (sel == 1) registrar_adopcion_pantalla();
    }
}
/* ---------------- Donantes ---------------- */
static void listar_donantes_pantalla(void) {
    Donante *ds; int n;
    donante_listar(&ds, &n);
    clear();
    mvprintw(1, 2, "Donantes registrados (%d)", n);
    mvprintw(3, 2, "%-4s %-16s %-10s %-12s", "ID", "Nombre", "Monto", "Fecha");
    int filas_disp = LINES - 6;
    for (int i = 0; i < n && i < filas_disp; i++) {
        mvprintw(4 + i, 2, "%-4d %-16s %-10.2f %-12s",
                 ds[i].id, ds[i].nombre, ds[i].monto, ds[i].fecha);
    }
    if (n > filas_disp) mvprintw(4 + filas_disp, 2, "... y %d mas", n - filas_disp);
    mvprintw(LINES - 2, 2, "Total recaudado: %.2f", donante_total_recaudado());
    mvprintw(LINES - 1, 2, "Presione una tecla para continuar...");
    refresh();
    getch();
    free(ds);
}
static void agregar_donante_pantalla(void) {
    Donante d; memset(&d, 0, sizeof(d));
    ui_pedir_texto("Nombre del donante:", d.nombre, sizeof(d.nombre));
    if (ui_fue_cancelado()) return;
    ui_pedir_texto("Contacto:", d.contacto, sizeof(d.contacto));
    if (ui_fue_cancelado()) return;
    d.monto = ui_pedir_double("Monto donado:");
    if (ui_fue_cancelado()) return;
    hoy(d.fecha, sizeof(d.fecha));
    if (donante_agregar(&d) == 0)
        ui_mensaje("Donante registrado.", 0);
    else
        ui_mensaje("Error al registrar el donante.", 1);
}
static void verificar_integridad_donantes_pantalla(void) {
    int r = integridad_verificar_donantes();
    if (r == 0)
        ui_mensaje("Integridad verificada: los datos de donantes no han cambiado.", 0);
    else if (r == 2)
        ui_mensaje("No habia checksum previo. Se guardo uno nuevo como base.", 0);
    else if (r == 1)
        ui_mensaje("ALERTA: los datos de donantes cambiaron desde la ultima verificacion.", 1);
    else
        ui_mensaje("No se pudo verificar la integridad.", 1);
}
static void actualizar_checksum_donantes_pantalla(void) {
    if (integridad_actualizar_checksum_donantes() == 0)
        ui_mensaje("Checksum actualizado. Los cambios actuales quedan como nueva base.", 0);
    else
        ui_mensaje("No se pudo actualizar el checksum.", 1);
}
/* Donantes: informacion sensible -> solo Admin y Veterinario, no Voluntario */
void pantalla_donantes(Rol rol) {
    if (rol == ROL_VOLUNTARIO) {
        ui_mensaje("Acceso restringido: este modulo requiere rol Admin o Veterinario.", 1);
        return;
    }
    while (1) {
        const char *opciones[] = {"Ver listado", "Registrar donante", "Verificar integridad", "Actualizar checksum (aceptar cambios)", "Volver"};
        int sel = ui_menu("Base de Donantes", opciones, 5);
        if (sel < 0 || sel == 4) return;
        if (sel == 0) listar_donantes_pantalla();
        else if (sel == 1) agregar_donante_pantalla();
        else if (sel == 2) verificar_integridad_donantes_pantalla();
        else if (sel == 3) actualizar_checksum_donantes_pantalla();
    }
}
/* ---------------- Reportes ---------------- */
void pantalla_reportes(Rol rol) {
    if (rol == ROL_VOLUNTARIO) {
        ui_mensaje("Acceso restringido: este modulo requiere rol Admin o Veterinario.", 1);
        return;
    }
    const char *ruta = "/var/pawos/reportes/reporte_actual.txt";
    if (reporte_generar(ruta) == 0) {
        char msg[160];
        snprintf(msg, sizeof(msg), "Reporte generado en: %s", ruta);
        ui_mensaje(msg, 0);
    } else {
        if (reporte_generar("reporte_actual.txt") == 0)
            ui_mensaje("Reporte generado en: ./reporte_actual.txt", 0);
        else
            ui_mensaje("No se pudo generar el reporte.", 1);
    }
}
