#ifndef PROCESOS_H
#define PROCESOS_H

#define PROCESOS_MAX 200

typedef struct {
    int  pid;
    char nombre[64];
    char estado[16];
} ProcesoInfo;

/* Lee /proc y llena 'lista' con hasta 'max' procesos activos.
   Devuelve la cantidad de procesos encontrados, o -1 si hubo error. */
int procesos_obtener_lista(ProcesoInfo *lista, int max);

/* Crea un proceso hijo de ejemplo (fork) que simula una tarea en segundo
   plano (por ejemplo, generar un respaldo). Devuelve el PID del hijo,
   o -1 si fork() fallo. */
int procesos_crear_ejemplo(void);

/* Envia una senal para terminar un proceso por su PID.
   forzar = 0 -> SIGTERM (pedido educado de cierre)
   forzar = 1 -> SIGKILL (cierre forzado inmediato)
   Devuelve 0 si se envio bien, -1 si hubo error. */
int procesos_terminar(int pid, int forzar);

#endif