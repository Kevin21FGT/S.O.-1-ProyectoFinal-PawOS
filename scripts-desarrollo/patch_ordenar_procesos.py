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

old = '''static void ver_procesos_activos(void) {
    ProcesoInfo lista[PROCESOS_MAX];
    int total = procesos_obtener_lista(lista, PROCESOS_MAX);

    clear();
    mvprintw(1, 2, "=== Procesos activos del sistema ===");

    if (total < 0) {
        mvprintw(3, 2, "No se pudo leer la lista de procesos (/proc).");
        pausar();
        return;
    }

    mvprintw(3, 2, "%-8s %-24s %-14s", "PID", "NOMBRE", "ESTADO");'''

new = '''static int comparar_pid_desc(const void *a, const void *b) {
    const ProcesoInfo *pa = (const ProcesoInfo *)a;
    const ProcesoInfo *pb = (const ProcesoInfo *)b;
    return pb->pid - pa->pid;
}

static void ver_procesos_activos(void) {
    ProcesoInfo lista[PROCESOS_MAX];
    int total = procesos_obtener_lista(lista, PROCESOS_MAX);

    clear();
    mvprintw(1, 2, "=== Procesos activos del sistema ===");

    if (total < 0) {
        mvprintw(3, 2, "No se pudo leer la lista de procesos (/proc).");
        pausar();
        return;
    }

    qsort(lista, total, sizeof(ProcesoInfo), comparar_pid_desc);

    mvprintw(3, 2, "%-8s %-24s %-14s", "PID", "NOMBRE", "ESTADO");'''

replace_or_die("src/pantalla_procesos.c", old, new, "ordenar procesos por PID descendente")
print("Listo.")
