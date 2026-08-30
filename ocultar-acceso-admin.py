#!/usr/bin/env python3
"""
ocultar-acceso-admin.py

Saca al Administrador del login de Colaboradores (que se queda solo
para empleados: Veterinario y Voluntario), y lo deja con un acceso
OCULTO a proposito: sin boton en ningun lado. Si alguien escribe las
credenciales REALES del Administrador (las de la tabla "usuarios", no
"clientes") en el formulario de "Soy Cliente" -- que por fuera solo
pide "Correo" y "Contrasena" -- se le abre la ventana completa de
Administrador en vez de la ventana simple de Cliente. Nadie mas puede
entrar asi porque necesita las credenciales reales del Administrador,
no cualquier correo.

Si alguien intenta usar las credenciales del Administrador en el login
de Colaboradores, se trata igual que usuario/contrasena incorrectos
(no se le da ninguna pista de que existe ese camino oculto).

Requisito: correr DESPUES de agregar-login-gui.py,
agregar-clientes-colaboradores.py y agregar-boton-regresar.py.

Uso: parado en la raiz del repo:
    python3 ocultar-acceso-admin.py

Hace backup (.bak6) antes de tocar nada, y aborta sin cambiar nada si
algun texto esperado no aparece exactamente como se espera.
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# 1) Colaborador ya no acepta al Administrador
ANCLA_COLAB = '''        int rol_db = -1;
        gboolean ok = (usuario_autenticar(usuario_ingresado, password_ingresado, &rol_db) == 0);

        if (ok) {
            snprintf(usuario_out, usuario_len, "%s", usuario_ingresado);
            *rol_out = (Rol)rol_db;
            gtk_widget_destroy(dialogo);
            return TRUE;
        }'''

NUEVO_COLAB = '''        int rol_db = -1;
        /* El Administrador ya NO entra por aqui -- Colaborador es solo
         * para empleados (Veterinario, Voluntario). Si alguien intenta
         * usar las credenciales del Administrador en este login, se
         * trata igual que usuario/contrasena incorrectos. */
        gboolean ok = (usuario_autenticar(usuario_ingresado, password_ingresado, &rol_db) == 0
                       && rol_db != ROL_ADMIN);

        if (ok) {
            snprintf(usuario_out, usuario_len, "%s", usuario_ingresado);
            *rol_out = (Rol)rol_db;
            gtk_widget_destroy(dialogo);
            return TRUE;
        }'''

# 2) Firma de mostrar_login_cliente: agrega es_admin_out
ANCLA_FIRMA = '''static gboolean mostrar_login_cliente(char *nombre_out, size_t nombre_len) {'''
NUEVO_FIRMA = '''static gboolean mostrar_login_cliente(char *nombre_out, size_t nombre_len, gboolean *es_admin_out) {'''

# 3) Login de "Cliente": primero prueba si son credenciales reales del
#    Administrador (acceso oculto) antes de revisar la tabla clientes
ANCLA_CLIENTE = '''        const char *correo_ingresado = gtk_entry_get_text(GTK_ENTRY(entrada_correo));
        const char *password_ingresado = gtk_entry_get_text(GTK_ENTRY(entrada_password));

        Cliente c;
        gboolean ok = (cliente_autenticar(correo_ingresado, password_ingresado, &c) == 0);
        gtk_widget_destroy(dialogo);

        if (ok) {
            snprintf(nombre_out, nombre_len, "%s", c.nombre);
            return TRUE;
        }
        intentos++;'''

NUEVO_CLIENTE = '''        const char *correo_ingresado = gtk_entry_get_text(GTK_ENTRY(entrada_correo));
        const char *password_ingresado = gtk_entry_get_text(GTK_ENTRY(entrada_password));

        /* Acceso oculto para el Administrador: sin boton en ningun
         * lado, a proposito. Si lo que se escribio aqui coincide con
         * las credenciales REALES del Administrador (tabla "usuarios",
         * no "clientes"), se abre la ventana completa de Administrador
         * en vez de la de Cliente. */
        int rol_secreto = -1;
        if (usuario_autenticar(correo_ingresado, password_ingresado, &rol_secreto) == 0
            && rol_secreto == ROL_ADMIN) {
            gtk_widget_destroy(dialogo);
            snprintf(nombre_out, nombre_len, "%s", correo_ingresado);
            if (es_admin_out) *es_admin_out = TRUE;
            return TRUE;
        }

        Cliente c;
        gboolean ok = (cliente_autenticar(correo_ingresado, password_ingresado, &c) == 0);
        gtk_widget_destroy(dialogo);

        if (ok) {
            snprintf(nombre_out, nombre_len, "%s", c.nombre);
            if (es_admin_out) *es_admin_out = FALSE;
            return TRUE;
        }
        intentos++;'''

# 4) main(): usa el nuevo parametro y abre la ventana correcta
ANCLA_MAIN = '''        } else {
            if (mostrar_login_cliente(nombre_sesion, sizeof(nombre_sesion))) {
                construir_ventana_cliente(nombre_sesion);
                logueado = TRUE;
            }
        }'''

NUEVO_MAIN = '''        } else {
            gboolean es_admin = FALSE;
            if (mostrar_login_cliente(nombre_sesion, sizeof(nombre_sesion), &es_admin)) {
                if (es_admin) {
                    construir_ventana_principal(ROL_ADMIN, nombre_sesion);
                } else {
                    construir_ventana_cliente(nombre_sesion);
                }
                logueado = TRUE;
            }
        }'''


def aplicar(contenido, ancla, nuevo, nombre):
    if contenido.count(ancla) != 1:
        print(f"ERROR: no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
        print("       Puede que los scripts anteriores no se hayan aplicado todavia,")
        print("       o que el archivo ya haya sido modificado. No se cambio nada.")
        sys.exit(1)
    return contenido.replace(ancla, nuevo, 1)


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    contenido = aplicar(contenido, ANCLA_COLAB, NUEVO_COLAB, "login Colaboradores")
    contenido = aplicar(contenido, ANCLA_FIRMA, NUEVO_FIRMA, "firma mostrar_login_cliente")
    contenido = aplicar(contenido, ANCLA_CLIENTE, NUEVO_CLIENTE, "login Clientes (acceso oculto admin)")
    contenido = aplicar(contenido, ANCLA_MAIN, NUEVO_MAIN, "main()")

    shutil.copy(ARCHIVO, ARCHIVO + ".bak6")
    print(f"Backup creado: {ARCHIVO}.bak6")

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK.")
    print("")
    print("Ahora corre:  make clean-gui && make gui")
    print("")
    print("Prueba: en 'Soy Colaborador', admin_refugio/admin123 ya NO debe funcionar.")
    print("        en 'Soy Cliente', escribiendo admin_refugio/admin123 SI debe abrir")
    print("        la ventana completa de Administrador.")


if __name__ == "__main__":
    main()
