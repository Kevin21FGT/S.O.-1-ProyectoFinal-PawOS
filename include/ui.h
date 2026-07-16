#ifndef UI_H
#define UI_H

/* Colores usados en toda la interfaz */
#define CP_TITULO   1
#define CP_MENU     2
#define CP_SEL      3
#define CP_OK       4
#define CP_ERROR    5

void ui_iniciar(void);
void ui_finalizar(void);

/* Muestra un menu vertical con 'n' opciones y devuelve el indice elegido
 * (0..n-1), o -1 si el usuario presiono 'q' / ESC. */
int  ui_menu(const char *titulo, const char *opciones[], int n);

/* Cuadro de dialogo simple con un mensaje y "Presione una tecla..." */
void ui_mensaje(const char *msg, int es_error);

/* Pide una linea de texto al usuario mostrando una etiqueta */
void ui_pedir_texto(const char *etiqueta, char *out, int maxlen);
int  ui_pedir_entero(const char *etiqueta);
double ui_pedir_double(const char *etiqueta);

/* Pantalla de bienvenida al iniciar el programa */
void ui_bienvenida(const char *usuario, const char *rol);

#endif
