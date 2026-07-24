// FASE DE MANEJO DE MEMORIA
#ifndef MEMORIA_H
#define MEMORIA_H

#include <stdint.h>
#include <stdbool.h>

// ==========================================
// CONSTANTES DEL SISTEMA DE MEMORIA
// ==========================================
#define TAMANIO_PAGINA 4096               // 4 KB (estandar de x86)
#define TAMANIO_MARCOS 1024              // 4 MB de RAM total (para pruebas)
#define TAMANIO_MEMORIA (TAMANIO_PAGINA * TAMANIO_MARCOS) // 4 MB de RAM total

#define MAX_PROCESOS 16                  // Maximo de procesos simultaneos
#define MAX_PAGINAS_POR_PROCESO 64       // 256 KB por proceso (64 paginas de 4 KB)

// ============================================
// ESTRUCTURAS DE DATOS
// ============================================

// Estructura de una página (entrada en la tabla de páginas)
typedef struct {
    uint32_t marco_fisico : 20;     // Número de marco (soporta hasta 1M marcos)
    uint32_t presente : 1;          // 1 = en RAM, 0 = en swap/desocupado
    uint32_t modificado : 1;        // 1 = ha cambiado (hay que guardarlo)
    uint32_t referenciado : 1;      // 1 = se ha usado recientemente (para LRU)
    uint32_t protegida : 1;         // 1 = solo lectura
    uint32_t swap_ubicacion : 8;    // Índice en disco si está en swap
} entrada_pagina_t;

// Tabla de páginas de un proceso
typedef struct {
    entrada_pagina_t paginas[MAX_PAGINAS_POR_PROCESO];
    uint32_t id_proceso;
    uint32_t contador_paginas_usadas;
} tabla_paginas_t;

// Estructura de un marco de memoria física
typedef struct {
    uint8_t datos[TAMANIO_PAGINA];   // Los datos reales
    uint32_t id_proceso;            // -1 si está libre
    uint32_t numero_pagina;         // Página virtual que contiene
    bool libre;                     // true si disponible
} marco_memoria_t;

// Estadísticas de memoria (para monitoreo)
typedef struct {
    uint32_t paginas_totales;
    uint32_t paginas_usadas;
    uint32_t paginas_libres;
    uint32_t page_faults;
    uint32_t swaps_realizados;
    uint32_t memoria_total_bytes;
    uint32_t memoria_usada_bytes;
} estadisticas_memoria_t;

// ============================================
// FUNCIONES PRINCIPALES
// ============================================

// Inicializar el sistema de memoria
bool memoria_inicializar(void);

// Crear una tabla de páginas para un nuevo proceso
tabla_paginas_t* memoria_crear_proceso(uint32_t id_proceso);

// Destruir la tabla de páginas de un proceso
bool memoria_destruir_proceso(uint32_t id_proceso);

// Asignar memoria a un proceso (malloc del SO)
void* memoria_asignar(uint32_t id_proceso, uint32_t tamaño_bytes);

// Liberar memoria previamente asignada
bool memoria_liberar(uint32_t id_proceso, void* direccion_virtual);

// Leer un byte de memoria virtual
uint8_t memoria_leer_byte(uint32_t id_proceso, void* direccion_virtual);

// Escribir un byte en memoria virtual
bool memoria_escribir_byte(uint32_t id_proceso, void* direccion_virtual, uint8_t valor);

// Obtener estadísticas del sistema
estadisticas_memoria_t memoria_obtener_estadisticas(void);

// Mostrar estado de la memoria (para debugging)
void memoria_imprimir_estado(void);

// ============================================
// FUNCIONES INTERNAS (no usar directamente)
// ============================================

// Traducir dirección virtual a física
uint32_t _memoria_traducir_direccion(tabla_paginas_t* tabla, uint32_t direccion_virtual);

// Manejar fallo de página
bool _memoria_manejar_page_fault(tabla_paginas_t* tabla, uint32_t direccion_virtual);

#endif // MEMORIA_H