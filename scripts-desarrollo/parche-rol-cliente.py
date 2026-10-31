#!/usr/bin/env python3
"""
parche-rol-cliente.py

Agrega el rol "Cliente" (persona normal) a las cuentas de cliente:

    Cliente (3)  -> persona normal, es el que queda al registrarse
    Jefe (0), Supervisor (1), Administrador (2) -> como antes

  - db.h / db.c: nuevo valor ROL_CLIENTE_NORMAL = 3 y su nombre "Cliente".
  - Portal de Clientes: el registro crea cuentas con rol Cliente; el saludo
    muestra "Cliente" (o Jefe / Supervisor / Administrador segun la cuenta).
  - PawOS Refugio: en "Administrar Clientes" aparece la opcion "Cliente" al
    cambiar el rol de una cuenta. El registro del login de clientes de la
    GUI tambien entra como Cliente.
  - Las comparaciones "rol >= SUPERVISOR / ADMIN" se cambian por igualdades
    para que "Cliente" (valor 3) NO herede permisos de nivel alto.

Las cuentas que ya existen NO cambian (siguen como Jefe, etc.).

Uso (parado en la raiz del repo):
    python3 parche-rol-cliente.py
    make gui portal-clientes
"""

import shutil
import sys

DB_H = "src/db/db.h"
DB_C = "src/db/db.c"
GTK_C = "src/main_gtk.c"
PORTAL_C = "src/main_portal_clientes.c"
MARCA = "ROL_CLIENTE_NORMAL"

CAMBIOS = {
    DB_H: [
        ("""    ROL_CLIENTE_ADMIN = 2
} RolCliente;""",
         """    ROL_CLIENTE_ADMIN = 2,
    ROL_CLIENTE_NORMAL = 3   /* persona normal (por defecto al registrarse) */
} RolCliente;""",
         "enum RolCliente"),
    ],
    DB_C: [
        ("""        case ROL_CLIENTE_SUPERVISOR: return "Supervisor";
        default: return "Jefe";""",
         """        case ROL_CLIENTE_SUPERVISOR: return "Supervisor";
        case ROL_CLIENTE_NORMAL: return "Cliente";
        default: return "Jefe";""",
         "cliente_rol_nombre"),
    ],
    GTK_C: [
        ("""    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), "0", "Jefe");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), "1", "Supervisor");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), "2", "Administrador");
    gtk_combo_box_set_active(GTK_COMBO_BOX(combo), 0);""",
         """    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), "3", "Cliente");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), "0", "Jefe");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), "1", "Supervisor");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), "2", "Administrador");
    gtk_combo_box_set_active(GTK_COMBO_BOX(combo), 0);""",
         "lista de roles en Administrar Clientes"),
        ("""    if (ctx->rol >= ROL_CLIENTE_SUPERVISOR) {""",
         """    if (ctx->rol == ROL_CLIENTE_SUPERVISOR || ctx->rol == ROL_CLIENTE_ADMIN) {""",
         "permiso Supervisor"),
        ("""    if (ctx->rol >= ROL_CLIENTE_ADMIN) {""",
         """    if (ctx->rol == ROL_CLIENTE_ADMIN) {""",
         "permiso Administrador"),
        ("""        RolCliente rol_elegido = ROL_CLIENTE_JEFE;""",
         """        RolCliente rol_elegido = ROL_CLIENTE_NORMAL;""",
         "rol por defecto del registro de la GUI"),
    ],
    PORTAL_C: [
        ("""cliente_registrar(correo, pass, nombre, telefono, ROL_CLIENTE_JEFE)""",
         """cliente_registrar(correo, pass, nombre, telefono, ROL_CLIENTE_NORMAL)""",
         "rol por defecto del registro del Portal"),
    ],
}


def main():
    contenidos = {}
    for ruta, cambios in CAMBIOS.items():
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenidos[ruta] = f.read()
        except FileNotFoundError:
            print(f"ERROR: no se encontro {ruta}. Corre esto desde la raiz del repo.")
            sys.exit(1)

    if MARCA in contenidos[DB_H]:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ruta, cambios in CAMBIOS.items():
        for ancla, _nuevo, nombre in cambios:
            n = contenidos[ruta].count(ancla)
            if n != 1:
                print(f"ERROR: en {ruta}, '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
                sys.exit(1)

    for ruta, cambios in CAMBIOS.items():
        shutil.copy(ruta, ruta + ".bak_rol_cliente")
        texto = contenidos[ruta]
        for ancla, nuevo, _nombre in cambios:
            texto = texto.replace(ancla, nuevo, 1)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)
        print(f"{ruta} parchado OK (backup .bak_rol_cliente)")

    print("Listo. Compila:  make gui portal-clientes")
    print("Las cuentas que ya existen siguen con su rol; las nuevas entran como Cliente.")


if __name__ == "__main__":
    main()
