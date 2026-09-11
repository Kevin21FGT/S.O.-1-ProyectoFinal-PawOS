#!/usr/bin/env python3
"""
agregar-boton-regresar.py

Hace que cancelar un login, o cerrar la ventana principal/de cliente,
regrese a la pantalla de elegir "Soy Colaborador" / "Soy Cliente" en
vez de cerrar el programa por completo. El programa solo se cierra de
verdad si le dan "Salir" en esa primera pantalla.

Cambios:
  - main() ahora es un ciclo: cuando se cierra la ventana que se abrio
    (o se cancela el login), vuelve a mostrar el selector, en vez de
    terminar el programa.
  - El boton "Salir" del login de Colaboradores y "Cancelar" del login
    de Clientes pasan a llamarse "Regresar" (ya no cierran todo el
    programa, solo regresan al selector).
  - El boton "Salir" de la ventana de Cliente pasa a llamarse "Cerrar
    sesion" (mismo motivo).

Requisito: correr DESPUES de agregar-login-gui.py y
agregar-clientes-colaboradores.py (este script parte de que
mostrar_selector_entrada(), mostrar_login_cliente() y
construir_ventana_cliente() ya existen en main_gtk.c).

Uso: parado en la raiz del repo:
    python3 agregar-boton-regresar.py

Hace backup (.bak5) antes de tocar nada, y aborta sin cambiar nada si
algun texto esperado no aparece exactamente como se espera.
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA_BTN_LOGIN_GTK = '''"Salir", GTK_RESPONSE_CANCEL,
            "Ingresar", GTK_RESPONSE_ACCEPT,'''
NUEVO_BTN_LOGIN_GTK = '''"Regresar", GTK_RESPONSE_CANCEL,
            "Ingresar", GTK_RESPONSE_ACCEPT,'''

ANCLA_BTN_LOGIN_CLIENTE = '''"Cancelar", GTK_RESPONSE_CANCEL,
            "Registrarme", RESPUESTA_REGISTRARME,'''
NUEVO_BTN_LOGIN_CLIENTE = '''"Regresar", GTK_RESPONSE_CANCEL,
            "Registrarme", RESPUESTA_REGISTRARME,'''

ANCLA_BTN_VENTANA_CLIENTE = '''GtkWidget *btn_salir     = gtk_button_new_with_label("Salir");'''
NUEVO_BTN_VENTANA_CLIENTE = '''GtkWidget *btn_salir     = gtk_button_new_with_label("Cerrar sesion");'''

ANCLA_MAIN = '''    TipoEntrada entrada = mostrar_selector_entrada();
    if (entrada == ENTRADA_CANCELAR) {
        db_close();
        return 0;
    }

    char nombre_sesion[64] = "";

    if (entrada == ENTRADA_COLABORADOR) {
        char usuario[32] = "";
        Rol rol;
        if (!mostrar_login_gtk(usuario, sizeof(usuario), &rol)) {
            db_close();
            return 0;
        }
        snprintf(nombre_sesion, sizeof(nombre_sesion), "%s", usuario);
        construir_ventana_principal(rol, usuario);
    } else {
        if (!mostrar_login_cliente(nombre_sesion, sizeof(nombre_sesion))) {
            db_close();
            return 0;
        }
        construir_ventana_cliente(nombre_sesion);
    }

    gtk_main();

    db_close();
    printf("Sesion grafica de PawOS finalizada. Hasta pronto, %s.\\n", nombre_sesion);
    return 0;
}'''

NUEVO_MAIN = '''    for (;;) {
        TipoEntrada entrada = mostrar_selector_entrada();
        if (entrada == ENTRADA_CANCELAR) {
            break;
        }

        char nombre_sesion[64] = "";
        gboolean logueado = FALSE;

        if (entrada == ENTRADA_COLABORADOR) {
            char usuario[32] = "";
            Rol rol;
            if (mostrar_login_gtk(usuario, sizeof(usuario), &rol)) {
                snprintf(nombre_sesion, sizeof(nombre_sesion), "%s", usuario);
                construir_ventana_principal(rol, usuario);
                logueado = TRUE;
            }
        } else {
            if (mostrar_login_cliente(nombre_sesion, sizeof(nombre_sesion))) {
                construir_ventana_cliente(nombre_sesion);
                logueado = TRUE;
            }
        }

        if (logueado) {
            gtk_main();
        }
        /* Si cancelo el login (boton "Regresar"), o si cerro la
         * ventana que se abrio, el ciclo vuelve a mostrar el selector
         * -- el programa NO se cierra solo por eso, unicamente con
         * "Salir" desde el selector inicial. */
    }

    db_close();
    printf("Sesion grafica de PawOS finalizada. Hasta pronto.\\n");
    return 0;
}'''


def aplicar(contenido, ancla, nuevo, nombre):
    if contenido.count(ancla) != 1:
        print(f"ERROR: no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
        print("       Puede que los scripts anteriores (agregar-login-gui.py,")
        print("       agregar-clientes-colaboradores.py) no se hayan aplicado todavia,")
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

    contenido = aplicar(contenido, ANCLA_BTN_LOGIN_GTK, NUEVO_BTN_LOGIN_GTK, "boton login Colaboradores")
    contenido = aplicar(contenido, ANCLA_BTN_LOGIN_CLIENTE, NUEVO_BTN_LOGIN_CLIENTE, "boton login Clientes")
    contenido = aplicar(contenido, ANCLA_BTN_VENTANA_CLIENTE, NUEVO_BTN_VENTANA_CLIENTE, "boton ventana Cliente")
    contenido = aplicar(contenido, ANCLA_MAIN, NUEVO_MAIN, "main()")

    shutil.copy(ARCHIVO, ARCHIVO + ".bak5")
    print(f"Backup creado: {ARCHIVO}.bak5")

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK.")
    print("")
    print("Ahora corre:  make clean-gui && make gui")


if __name__ == "__main__":
    main()
