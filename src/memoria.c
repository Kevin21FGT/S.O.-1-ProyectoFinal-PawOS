#include "../include/memoria.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>     // Para sleep, getpid
#include <time.h>       // Para debugging

// ============================================
// VARIABLES GLOBALES DEL SISTEMA
// ============================================

// La RAM física: arreglo de marcos
static marco_memoria_t memoria_fisica[TAMANIO_MARCOS];

// Tablas de páginas de todos los procesos
static tabla_paginas_t* tablas_procesos[MAX_PROCESOS];

// Estadísticas globales
static estadisticas_memoria_t estadisticas;

// Archivo de swap (simulado)
static FILE* archivo_swap = NULL;
static const char* NOMBRE_SWAP = "refugio_swap.bin";

// ============================================
// FUNCIONES AUXILIARES (estáticas)
// ============================================

// Inicializar la memoria física
static void _inicializar_memoria_fisica(void) {
    for (int i = 0; i < TAMANIO_MARCOS; i++) {
        memset(memoria_fisica[i].datos, 0, TAMANIO_PAGINA);
        memoria_fisica[i].id_proceso = -1;
        memoria_fisica[i].numero_pagina = 0;
        memoria_fisica[i].libre = true;
    }
    
    // Reservar los primeros marcos para el kernel
    for (int i = 0; i < 4; i++) {
        memoria_fisica[i].libre = false;
        memoria_fisica[i].id_proceso = 0;  // Kernel
    }
    
    estadisticas.paginas_libres = TAMANIO_MARCOS - 4;
    estadisticas.paginas_usadas = 4;
}

// Buscar un marco libre
static int _buscar_marco_libre(void) {
    for (int i = 4; i < TAMANIO_MARCOS; i++) {
        if (memoria_fisica[i].libre) {
            return i;
        }
    }
    return -1;  // No hay marcos libres
}

// Algoritmo de reloj (Second-Chance / Clock) para reemplazo de páginas
static int _encontrar_victima_lru(void) {
    // Buscar el marco con el menor contador de referencia (LRU)
    int victima = -1;
    uint32_t menor_referencia = 0xFFFFFFFF;
    
    for (int i = 4; i < TAMANIO_MARCOS; i++) {
        if (!memoria_fisica[i].libre) {
            // Buscar la entrada de página correspondiente
            uint32_t id_proc = memoria_fisica[i].id_proceso;
            uint32_t num_pag = memoria_fisica[i].numero_pagina;
            
            if (id_proc < MAX_PROCESOS && tablas_procesos[id_proc] != NULL) {
                entrada_pagina_t* pag = &tablas_procesos[id_proc]->paginas[num_pag];
                if (pag->referenciado) {
                    pag->referenciado = 0;
                } else {
                    return manecilla;
                }
            } else {
                return manecilla;
            }
        }
    }
    
    // Si no encontramos, elegir la que tenga menos referencia
    if (victima == -1) {
        for (int i = 4; i < TAMANIO_MARCOS; i++) {
            if (!memoria_fisica[i].libre) {
                victima = i;
                break;
            }
        }
    }
    return -1;
}

// Escribir una página al swap (disco)
static bool _escribir_swap(uint32_t id_proceso, uint32_t num_pagina, uint8_t* datos) {
    if (archivo_swap == NULL) {
        archivo_swap = fopen(NOMBRE_SWAP, "r+b");
        if (archivo_swap == NULL) {
            archivo_swap = fopen(NOMBRE_SWAP, "w+b");
            if (archivo_swap == NULL) {
                return false;
            }
        }
    }
    
    // Calcular offset en el archivo swap
    // Formato: [id_proceso][num_pagina][datos]
    fseek(archivo_swap, (id_proceso * MAX_PAGINAS_POR_PROCESO + num_pagina) * TAMANIO_PAGINA, SEEK_SET);
    size_t escritos = fwrite(datos, 1, TAMANIO_PAGINA, archivo_swap);
    fflush(archivo_swap);
    
    return escritos == TAMANIO_PAGINA;
}

// Leer una página del swap
static bool _leer_swap(uint32_t id_proceso, uint32_t num_pagina, uint8_t* buffer) {
    if (archivo_swap == NULL) {
        return false;
    }
    
    fseek(archivo_swap, (id_proceso * MAX_PAGINAS_POR_PROCESO + num_pagina) * TAMANIO_PAGINA, SEEK_SET);
    size_t leidos = fread(buffer, 1, TAMANIO_PAGINA, archivo_swap);
    
    return leidos == TAMANIO_PAGINA;
}

// ============================================
// IMPLEMENTACIÓN DE FUNCIONES PÚBLICAS
// ============================================

bool memoria_inicializar(void) {
    printf("[MEMORIA] Inicializando sistema de memoria para RefugioOS...\n");
    
    // Inicializar estadísticas primero
    memset(&estadisticas, 0, sizeof(estadisticas_memoria_t));
    estadisticas.paginas_totales = TAMANIO_MARCOS;
    estadisticas.memoria_total_bytes = TAMANIO_MEMORIA;

    // Inicializar estructuras (esto configura paginas_usadas/libres reales)
    _inicializar_memoria_fisica();

    for (int i = 0; i < MAX_PROCESOS; i++) {
        tablas_procesos[i] = NULL;
    }

    // Abrir archivo swap
    archivo_swap = fopen(NOMBRE_SWAP, "w+b");
    if (archivo_swap == NULL) {
        printf("[MEMORIA] ERROR: No se pudo crear el archivo swap\n");
        return false;
    }
    
    printf("[MEMORIA] Sistema inicializado correctamente\n");
    printf("[MEMORIA] Memoria total: %d KB (%d páginas)\n", 
           TAMANIO_MEMORIA / 1024, TAMANIO_MARCOS);
    printf("[MEMORIA] Swap activo: %s\n", NOMBRE_SWAP);
    
    return true;
}

tabla_paginas_t* memoria_crear_proceso(uint32_t id_proceso) {
    if (id_proceso >= MAX_PROCESOS) {
        printf("[MEMORIA] ERROR: ID de proceso %u excede el máximo\n", id_proceso);
        return NULL;
    }
    
    if (tablas_procesos[id_proceso] != NULL) {
        printf("[MEMORIA] ERROR: El proceso %u ya tiene tabla de páginas\n", id_proceso);
        return NULL;
    }
    
    // Asignar memoria para la tabla
    tabla_paginas_t* tabla = (tabla_paginas_t*)malloc(sizeof(tabla_paginas_t));
    if (tabla == NULL) {
        printf("[MEMORIA] ERROR: No hay memoria para crear tabla de páginas\n");
        return NULL;
    }
    
    // Inicializar tabla
    memset(tabla->paginas, 0, sizeof(entrada_pagina_t) * MAX_PAGINAS_POR_PROCESO);
    tabla->id_proceso = id_proceso;
    tabla->contador_paginas_usadas = 0;
    
    // Asignar una página inicial para el proceso (código base)
    int marco = _buscar_marco_libre();
    if (marco == -1) {
        printf("[MEMORIA] ERROR: No hay marcos libres para el proceso %u\n", id_proceso);
        free(tabla);
        return NULL;
    }
    
    // Configurar primera página
    tabla->paginas[0].marco_fisico = marco;
    tabla->paginas[0].presente = 1;
    tabla->paginas[0].modificado = 0;
    tabla->paginas[0].referenciado = 1;
    tabla->paginas[0].protegida = 0;
    tabla->paginas[0].en_swap = 0;
    tabla->contador_paginas_usadas = 1;
    
    // Marcar el marco como usado
    memoria_fisica[marco].libre = false;
    memoria_fisica[marco].id_proceso = id_proceso;
    memoria_fisica[marco].numero_pagina = 0;
    
    // Guardar referencia
    tablas_procesos[id_proceso] = tabla;
    
    // Actualizar estadísticas
    estadisticas.paginas_usadas++;
    estadisticas.paginas_libres--;
    
    printf("[MEMORIA] Proceso %u creado con 1 página (marco %d)\n", id_proceso, marco);
    return tabla;
}

bool memoria_destruir_proceso(uint32_t id_proceso) {
    if (id_proceso >= MAX_PROCESOS || tablas_procesos[id_proceso] == NULL) {
        return false;
    }
    
    tabla_paginas_t* tabla = tablas_procesos[id_proceso];
    
    // Liberar todos los marcos usados por este proceso
    for (int i = 0; i < MAX_PAGINAS_POR_PROCESO; i++) {
        if (tabla->paginas[i].presente) {
            int marco = tabla->paginas[i].marco_fisico;
            if (marco >= 0 && marco < TAMANIO_MARCOS) {
                memoria_fisica[marco].libre = true;
                memoria_fisica[marco].id_proceso = -1;
                estadisticas.paginas_usadas--;
                estadisticas.paginas_libres++;
            }
        }
    }
    
    free(tabla);
    tablas_procesos[id_proceso] = NULL;
    
    printf("[MEMORIA] Proceso %u destruido, memoria liberada\n", id_proceso);
    return true;
}

void* memoria_asignar(uint32_t id_proceso, uint32_t tamaño_bytes) {
    if (id_proceso >= MAX_PROCESOS || tablas_procesos[id_proceso] == NULL) {
        return NULL;
    }
    
    tabla_paginas_t* tabla = tablas_procesos[id_proceso];
    uint32_t paginas_necesarias = (tamaño_bytes + TAMANIO_PAGINA - 1) / TAMANIO_PAGINA;
    uint32_t pagina_inicio = tabla->contador_paginas_usadas;
    
    // Verificar que no exceda el límite
    if (pagina_inicio + paginas_necesarias > MAX_PAGINAS_POR_PROCESO) {
        printf("[MEMORIA] ERROR: Proceso %u excede límite de páginas\n", id_proceso);
        return NULL;
    }
    
    // Asignar cada página
    for (uint32_t i = 0; i < paginas_necesarias; i++) {
        uint32_t num_pagina = pagina_inicio + i;
        int marco = _buscar_marco_libre();
        
        if (marco == -1) {
            // No hay marcos libres → usar swap con LRU
            printf("[MEMORIA] Sin marcos libres, usando LRU para proceso %u\n", id_proceso);
            marco = _encontrar_victima_lru();
            
            if (marco == -1) {
                printf("[MEMORIA] ERROR CRÍTICO: No se pudo encontrar víctima\n");
                return NULL;
            }
            
            // Guardar la página víctima al swap si está modificada
            uint32_t id_victima = memoria_fisica[marco].id_proceso;
            uint32_t num_pag_victima = memoria_fisica[marco].numero_pagina;
            
            if (id_victima < MAX_PROCESOS && tablas_procesos[id_victima] != NULL) {
                entrada_pagina_t* pag_victima = &tablas_procesos[id_victima]->paginas[num_pag_victima];
                if (pag_victima->modificado) {
                    _escribir_swap(id_victima, num_pag_victima, memoria_fisica[marco].datos);
                    estadisticas.swaps_realizados++;
                    pag_victima->swap_ubicacion = num_pag_victima;
                    pag_victima->en_swap = 1;
                }
                pag_victima->presente = 0;
                estadisticas.paginas_usadas--;
                estadisticas.paginas_libres++;
            }
        }
        
        // Inicializar la página nueva
        memset(memoria_fisica[marco].datos, 0, TAMANIO_PAGINA);
        memoria_fisica[marco].libre = false;
        memoria_fisica[marco].id_proceso = id_proceso;
        memoria_fisica[marco].numero_pagina = num_pagina;
        
        // Configurar entrada en tabla de páginas
        tabla->paginas[num_pagina].marco_fisico = marco;
        tabla->paginas[num_pagina].presente = 1;
        tabla->paginas[num_pagina].modificado = 0;
        tabla->paginas[num_pagina].referenciado = 1;
        tabla->paginas[num_pagina].protegida = 0;
        
        estadisticas.paginas_usadas++;
        estadisticas.paginas_libres--;
    }
    
    tabla->contador_paginas_usadas += paginas_necesarias;
    
    // Devolver la dirección virtual del inicio
    uint32_t direccion_virtual = pagina_inicio * TAMANIO_PAGINA;
    printf("[MEMORIA] Asignados %d bytes al proceso %d en dirección virtual 0x%X\n", 
           tamaño_bytes, id_proceso, direccion_virtual);
    
    return (void*)(uintptr_t)direccion_virtual;
}

bool memoria_liberar(uint32_t id_proceso, void* direccion_virtual) {
    if (id_proceso >= MAX_PROCESOS || tablas_procesos[id_proceso] == NULL) {
        return false;
    }
    
    uint32_t dir = (uint32_t)(uintptr_t)direccion_virtual;
    uint32_t num_pagina = dir / TAMANIO_PAGINA;
    
    if (num_pagina >= MAX_PAGINAS_POR_PROCESO) {
        return false;
    }
    
    tabla_paginas_t* tabla = tablas_procesos[id_proceso];
    
    if (!tabla->paginas[num_pagina].presente) {
        return false;  // Ya está en swap o liberada
    }
    
    int marco = tabla->paginas[num_pagina].marco_fisico;
    if (marco >= 0 && marco < TAMANIO_MARCOS) {
        memoria_fisica[marco].libre = true;
        memoria_fisica[marco].id_proceso = -1;
        estadisticas.paginas_usadas--;
        estadisticas.paginas_libres++;
    }
    
    // Limpiar entrada
    memset(&tabla->paginas[num_pagina], 0, sizeof(entrada_pagina_t));
    
    return true;
}

uint8_t memoria_leer_byte(uint32_t id_proceso, void* direccion_virtual) {
    if (id_proceso >= MAX_PROCESOS || tablas_procesos[id_proceso] == NULL) {
        return 0;
    }
    
    uint32_t dir = (uint32_t)(uintptr_t)direccion_virtual;
    uint32_t num_pagina = dir / TAMANIO_PAGINA;
    uint32_t offset = dir % TAMANIO_PAGINA;
    
    tabla_paginas_t* tabla = tablas_procesos[id_proceso];
    entrada_pagina_t* pag = &tabla->paginas[num_pagina];
    
    // Si no está presente, traer del swap
    if (!pag->presente) {
        _memoria_manejar_page_fault(tabla, dir);
    }
    
    // Marcar como referenciada (para LRU)
    pag->referenciado = 1;
    
    // Leer el byte
    uint32_t direccion_fisica = (pag->marco_fisico * TAMANIO_PAGINA) + offset;
    return memoria_fisica[pag->marco_fisico].datos[offset];
}

bool memoria_escribir_byte(uint32_t id_proceso, void* direccion_virtual, uint8_t valor) {
    if (id_proceso >= MAX_PROCESOS || tablas_procesos[id_proceso] == NULL) {
        return false;
    }
    
    uint32_t dir = (uint32_t)(uintptr_t)direccion_virtual;
    uint32_t num_pagina = dir / TAMANIO_PAGINA;
    uint32_t offset = dir % TAMANIO_PAGINA;
    
    tabla_paginas_t* tabla = tablas_procesos[id_proceso];
    entrada_pagina_t* pag = &tabla->paginas[num_pagina];
    
    // Si no está presente, traer del swap
    if (!pag->presente) {
        _memoria_manejar_page_fault(tabla, dir);
    }
    
    // Marcar como referenciada y modificada
    pag->referenciado = 1;
    pag->modificado = 1;
    
    // Escribir el byte
    uint32_t direccion_fisica = (pag->marco_fisico * TAMANIO_PAGINA) + offset;
    memoria_fisica[pag->marco_fisico].datos[offset] = valor;
    
    return true;
}

bool _memoria_manejar_page_fault(tabla_paginas_t* tabla, uint32_t direccion_virtual) {
    uint32_t num_pagina = direccion_virtual / TAMANIO_PAGINA;
    estadisticas.page_faults++;
    
    if (num_pagina >= MAX_PAGINAS_POR_PROCESO) {
        return false;
    }
    
    entrada_pagina_t* pag = &tabla->paginas[num_pagina];
    
    // Buscar un marco libre
    int marco = _buscar_marco_libre();
    
    if (marco == -1) {
        // Usar LRU para encontrar víctima
        marco = _encontrar_victima_lru();
        if (marco == -1) {
            printf("[MEMORIA] ERROR: Page fault sin marcos disponibles\n");
            return false;
        }
        
        // Guardar víctima al swap si es necesario
        uint32_t id_victima = memoria_fisica[marco].id_proceso;
        uint32_t num_pag_victima = memoria_fisica[marco].numero_pagina;
        
        if (id_victima < MAX_PROCESOS && tablas_procesos[id_victima] != NULL) {
            entrada_pagina_t* pag_victima = &tablas_procesos[id_victima]->paginas[num_pag_victima];
            if (pag_victima->modificado) {
                _escribir_swap(id_victima, num_pag_victima, memoria_fisica[marco].datos);
                estadisticas.swaps_realizados++;
                pag_victima->swap_ubicacion = num_pag_victima;
                pag_victima->en_swap = 1;
            }
            pag_victima->presente = 0;
            estadisticas.paginas_usadas--;
            estadisticas.paginas_libres++;
        }
    }
    
    // Leer del swap o iniciar página vacía
    if (pag->en_swap) {
        _leer_swap(tabla->id_proceso, num_pagina, memoria_fisica[marco].datos);
    } else {
        memset(memoria_fisica[marco].datos, 0, TAMANIO_PAGINA);
    }
    
    // Actualizar estructuras
    memoria_fisica[marco].libre = false;
    memoria_fisica[marco].id_proceso = tabla->id_proceso;
    memoria_fisica[marco].numero_pagina = num_pagina;
    
    pag->marco_fisico = marco;
    pag->presente = 1;
    pag->referenciado = 1;
    pag->modificado = 0;
    
    estadisticas.paginas_usadas++;
    estadisticas.paginas_libres--;
    
    return true;
}

estadisticas_memoria_t memoria_obtener_estadisticas(void) {
    return estadisticas;
}

void memoria_imprimir_estado(void) {
    printf("\n========================================\n");
    printf("      ESTADO DE MEMORIA - REFUGIO OS\n");
    printf("========================================\n");
    printf("Memoria total:       %d KB\n", TAMANIO_MEMORIA / 1024);
    printf("Páginas totales:     %d\n", estadisticas.paginas_totales);
    printf("Páginas usadas:      %d\n", estadisticas.paginas_usadas);
    printf("Páginas libres:      %d\n", estadisticas.paginas_libres);
    printf("Page faults:         %d\n", estadisticas.page_faults);
    printf("Swaps realizados:    %d\n", estadisticas.swaps_realizados);
    printf("Memoria usada:       %.2f KB\n", 
           (float)estadisticas.paginas_usadas * TAMANIO_PAGINA / 1024);
    
    printf("\nPROCESOS ACTIVOS:\n");
    for (int i = 0; i < MAX_PROCESOS; i++) {
        if (tablas_procesos[i] != NULL) {
            printf("  P%u: %u páginas usadas\n", i, tablas_procesos[i]->contador_paginas_usadas);
        }
    }
    printf("========================================\n\n");
}

// Función de limpieza al cerrar el sistema
void __attribute__((destructor)) _memoria_limpiar(void) {
    if (archivo_swap != NULL) {
        fclose(archivo_swap);
        // Opcional: eliminar archivo swap
        // remove(NOMBRE_SWAP);
    }
}