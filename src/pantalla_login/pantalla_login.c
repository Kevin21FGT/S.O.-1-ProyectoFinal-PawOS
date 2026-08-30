
#include <ncurses.h>
#include <string.h>
#include "pantalla_login.h"
#include "db/db.h"

static void pedir_texto_login(int fila, int col, const char *etiqueta, char *out, int maxlen) {
    echo();
    curs_set(1);
    mvprintw(fila, col, "%s", etiqueta);
    getnstr(out, maxlen - 1);
    noecho();
    curs_set(0);
}
static void pedir_password(int fila, int col, const char *etiqueta, char *out, int maxlen) {
    mvprintw(fila, col, "%s", etiqueta);
    curs_set(1);
    int i = 0;
    int inicio_col = col + (int)strlen(etiqueta);
    while (1) {
        int ch = getch();
        if (ch == '\n' || ch == KEY_ENTER) break;
        if ((ch == KEY_BACKSPACE || ch == 127 || ch == 8) && i > 0) {
            i--;
            mvaddch(fila, inicio_col + i, ' ');
            move(fila, inicio_col + i);
        } else if (ch >= 32 && ch <= 126 && i < maxlen - 1) {
            out[i++] = (char)ch;
            mvaddch(fila, inicio_col + (i - 1), '*');
        }
        refresh();
    }
    out[i] = '\0';
    curs_set(0);
}
int pantalla_login(char *usuario_out, int usuario_len, Rol *rol_out) {
    int intentos = 0;

    while (intentos < 3) {
        clear();
        mvprintw(1, 2, "=== PawOS - Inicio de sesion ===");
        mvprintw(3, 2, "Ingrese sus credenciales");

        char usuario[32] = "";
        char password[32] = "";
        pedir_texto_login(5, 2, "Usuario:    ", usuario, sizeof(usuario));
        pedir_password(6, 2, "Contrasena: ", password, sizeof(password));

        int rol_db = -1;
        if (usuario_autenticar(usuario, password, &rol_db) == 0) {
            snprintf(usuario_out, usuario_len, "%s", usuario);
            *rol_out = (Rol)rol_db;
            return 1;
        }
        intentos++;
        mvprintw(8, 2, "Usuario o contrasena incorrectos. Intento %d de 3.", intentos);
        mvprintw(9, 2, "Presione una tecla para reintentar...");
        refresh();
        getch();
    }

    clear();
    mvprintw(1, 2, "Demasiados intentos fallidos. Cerrando PawOS.");
    refresh();
    napms(1500);
    return 0;
}
