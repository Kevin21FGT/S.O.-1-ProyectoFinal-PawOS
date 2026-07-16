/*
 * ui.c - Utilidades de interfaz de texto con ncurses para PawOS.
 */

#include <ncurses.h>
#include <string.h>
#include <stdlib.h>
#include "../include/ui.h"

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
        attron(COLOR_PAIR(CP_TITULO));
        mvprintw(1, 2, " %s ", titulo);
        for (int i = strlen(titulo) + 4; i < COLS - 2; i++) mvprintw(1, i, " ");
        attroff(COLOR_PAIR(CP_TITULO));

        for (int i = 0; i < n; i++) {
            if (i == sel) attron(COLOR_PAIR(CP_SEL));
            mvprintw(3 + i * 2, 4, "%-50s", opciones[i]);
            if (i == sel) attroff(COLOR_PAIR(CP_SEL));
        }
        mvprintw(3 + n * 2 + 1, 4, "Flechas: moverse | Enter: seleccionar | q: salir/volver");
        refresh();

        ch = getch();
        if (ch == KEY_UP)   sel = (sel - 1 + n) % n;
        else if (ch == KEY_DOWN) sel = (sel + 1) % n;
        else if (ch == '\n' || ch == KEY_ENTER) return sel;
        else if (ch == 'q' || ch == 27) return -1;
    }
}

void ui_mensaje(const char *msg, int es_error) {
    int fila = LINES / 2;
    clear();
    attron(COLOR_PAIR(es_error ? CP_ERROR : CP_OK));
    mvprintw(fila, 4, "%s", msg);
    attroff(COLOR_PAIR(es_error ? CP_ERROR : CP_OK));
    mvprintw(fila + 2, 4, "Presione una tecla para continuar...");
    refresh();
    getch();
}

void ui_pedir_texto(const char *etiqueta, char *out, int maxlen) {
    echo();
    curs_set(1);
    clear();
    mvprintw(2, 4, "%s", etiqueta);
    move(4, 4);
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
}

void ui_bienvenida(const char *usuario, const char *rol) {
    clear();
    int fila = LINES / 2 - 3;
    attron(COLOR_PAIR(CP_TITULO) | A_BOLD);
    mvprintw(fila, (COLS - 24) / 2, "  P a w O S  -  R e f u g i o  ");
    attroff(COLOR_PAIR(CP_TITULO) | A_BOLD);
    mvprintw(fila + 2, (COLS - 40) / 2, "Bienvenido/a, %s", usuario);
    mvprintw(fila + 3, (COLS - 40) / 2, "Rol: %s", rol);
    mvprintw(fila + 5, (COLS - 40) / 2, "Presione una tecla para continuar...");
    refresh();
    getch();
}
