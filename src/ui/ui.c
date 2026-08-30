/*
 * ui.c - Utilidades de interfaz de texto con ncurses para PawOS.
 */

#include <ncurses.h>
#include <string.h>
#include <stdlib.h>
#include "ui.h"

/* Barra superior solida (todo el ancho) con el titulo centrado,
 * mas los bordes laterales y las lineas que cierran arriba/abajo. */
static void marco(const char *titulo) {
    attron(COLOR_PAIR(CP_TITULO) | A_BOLD);
    for (int x = 0; x < COLS; x++) mvaddch(0, x, ' ');
    mvprintw(0, (COLS - (int)strlen(titulo)) / 2, "%s", titulo);
    attroff(COLOR_PAIR(CP_TITULO) | A_BOLD);

    attron(COLOR_PAIR(CP_BORDE));
    for (int y = 1; y < LINES - 1; y++) {
        mvaddch(y, 0, ACS_VLINE);
        mvaddch(y, COLS - 1, ACS_VLINE);
    }
    mvhline(1, 1, ACS_HLINE, COLS - 2);
    mvhline(LINES - 2, 1, ACS_HLINE, COLS - 2);
    mvaddch(1, 0, ACS_LTEE);
    mvaddch(1, COLS - 1, ACS_RTEE);
    mvaddch(LINES - 2, 0, ACS_LTEE);
    mvaddch(LINES - 2, COLS - 1, ACS_RTEE);
    attroff(COLOR_PAIR(CP_BORDE));
}

/* Linea de ayuda centrada, debajo del marco */
static void pie(const char *texto) {
    attron(COLOR_PAIR(CP_BORDE));
    mvprintw(LINES - 1, (COLS - (int)strlen(texto)) / 2, "%s", texto);
    attroff(COLOR_PAIR(CP_BORDE));
}

void ui_iniciar(void) {
    initscr();
    cbreak();
    noecho();
    keypad(stdscr, TRUE);
    curs_set(0);

    if (has_colors()) {
        start_color();
        init_pair(CP_TITULO, COLOR_WHITE, COLOR_BLUE);
        init_pair(CP_MENU,   COLOR_WHITE, COLOR_BLACK);
        init_pair(CP_SEL,    COLOR_BLACK, COLOR_CYAN);
        init_pair(CP_OK,     COLOR_GREEN, COLOR_BLACK);
        init_pair(CP_ERROR,  COLOR_RED,   COLOR_BLACK);
        init_pair(CP_BORDE,  COLOR_CYAN,  COLOR_BLACK);
    }
}

void ui_finalizar(void) {
    endwin();
}

int ui_menu(const char *titulo, const char *opciones[], int n) {
    int sel = 0;
    int ch;

    while (1) {
        clear();
        marco(titulo);

        int inicio = 3;
        int ancho = COLS - 6;
        if (ancho > 60) ancho = 60;

        for (int i = 0; i < n; i++) {
            int fila = inicio + i * 2;
            char linea[80];
            snprintf(linea, sizeof(linea), "%02d. %s", i + 1, opciones[i]);

            if (i == sel) {
                attron(COLOR_PAIR(CP_SEL) | A_BOLD);
                mvprintw(fila, 3, " %-*s", ancho, linea);
                attroff(COLOR_PAIR(CP_SEL) | A_BOLD);
            } else {
                attron(COLOR_PAIR(CP_MENU));
                mvprintw(fila, 3, " %-*s", ancho, linea);
                attroff(COLOR_PAIR(CP_MENU));
            }
        }

        pie("Flechas: moverse | Enter: seleccionar | q: salir/volver");
        refresh();

        ch = getch();
        if (ch == KEY_UP)   sel = (sel - 1 + n) % n;
        else if (ch == KEY_DOWN) sel = (sel + 1) % n;
        else if (ch == '\n' || ch == KEY_ENTER) return sel;
        else if (ch == 'q' || ch == 27) return -1;
    }
}

void ui_mensaje(const char *msg, int es_error) {
    clear();
    marco(es_error ? "Aviso" : "Listo");

    int fila = LINES / 2;
    int len = (int)strlen(msg);
    attron(COLOR_PAIR(es_error ? CP_ERROR : CP_OK) | A_BOLD);
    mvprintw(fila, (COLS - len) / 2, "%s", msg);
    attroff(COLOR_PAIR(es_error ? CP_ERROR : CP_OK) | A_BOLD);

    pie("Presione una tecla para continuar...");
    refresh();
    getch();
}

static int g_cancelado = 0;

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
    if (maxlen > 0) out[0] = '\0';
    g_cancelado = 0;

    while (1) {
        move(5, 3 + pos);
        refresh();
        int ch = getch();
        if (ch == 27) { /* ESC */
            g_cancelado = 1;
            if (maxlen > 0) out[0] = '\0';
            break;
        } else if (ch == '\n' || ch == '\r' || ch == KEY_ENTER) {
            g_cancelado = 0;
            break;
        } else if (ch == KEY_BACKSPACE || ch == 127 || ch == 8) {
            if (pos > 0) {
                pos--;
                out[pos] = '\0';
                mvaddch(5, 3 + pos, ' ');
            }
        } else if (ch >= 32 && ch < 256 && pos < maxlen - 1) {
            out[pos] = (char)ch;
            pos++;
            out[pos] = '\0';
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
}

void ui_bienvenida(const char *usuario, const char *rol) {
    clear();
    marco("PawOS - Refugio de Proteccion Animal");

    int fila = LINES / 2 - 5;
    const char *arte[] = {
        " /\\_/\\ ",
        "( o.o )",
        " > ^ < "
    };
    for (int i = 0; i < 3; i++) {
        attron(COLOR_PAIR(CP_OK) | A_BOLD);
        mvprintw(fila + i, (COLS - (int)strlen(arte[i])) / 2, "%s", arte[i]);
        attroff(COLOR_PAIR(CP_OK) | A_BOLD);
    }

    attron(COLOR_PAIR(CP_TITULO) | A_BOLD);
    mvprintw(fila + 4, (COLS - 11) / 2, " P a w O S ");
    attroff(COLOR_PAIR(CP_TITULO) | A_BOLD);

    attron(A_BOLD);
    mvprintw(fila + 6, (COLS - 40) / 2, "Bienvenido/a, %s", usuario);
    mvprintw(fila + 7, (COLS - 40) / 2, "Rol: %s", rol);
    attroff(A_BOLD);

    pie("Presione una tecla para continuar...");
    refresh();
    getch();
}