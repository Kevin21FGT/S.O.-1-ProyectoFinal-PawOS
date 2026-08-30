#include "include/memoria.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>

int main() {
    if (!memoria_inicializar()) {
        fprintf(stderr, "Fallo al inicializar memoria\n");
        return 1;
    }

    // Prueba 1: Crear proceso
    tabla_paginas_t* t1 = memoria_crear_proceso(1);
    assert(t1 != NULL);
    printf("P1: Proceso 1 creado OK\n");

    // Prueba 2: Crear proceso 2
    tabla_paginas_t* t2 = memoria_crear_proceso(2);
    assert(t2 != NULL);
    printf("P2: Proceso 2 creado OK\n");

    // Prueba 3: Escribir y leer byte
    void* dir = memoria_asignar(1, 100);
    assert(dir != NULL);
    printf("P3: Memoria asignada en %p\n", dir);

    bool ok = memoria_escribir_byte(1, dir, 0xAB);
    assert(ok);
    uint8_t val = memoria_leer_byte(1, dir);
    assert(val == 0xAB);
    printf("P4: Escritura/lectura OK: 0x%X\n", val);

    // Prueba 4: Escribir en página 0, forzar swap y recuperar (BUG #1)
    void* dir_pag0 = (void*)0;
    ok = memoria_escribir_byte(1, dir_pag0, 0x42);
    assert(ok);

    // Forzar swap creando muchos procesos que consuman memoria
    for (int i = 3; i <= 15; i++) {
        tabla_paginas_t* t = memoria_crear_proceso(i);
        assert(t != NULL);
        for (int j = 0; j < 10; j++)
            memoria_asignar(i, 5000);
    }

    // Verificar el dato original
    val = memoria_leer_byte(1, dir_pag0);
    printf("P5: Dato en pagina 0 tras swap: 0x%X (esperado 0x42)\n", val);
    assert(val == 0x42);  // Esto falla por el BUG #1

    memoria_imprimir_estado();

    // Prueba 5: Estadisticas
    estadisticas_memoria_t stats = memoria_obtener_estadisticas();
    printf("P6: Page faults: %u, Swaps: %u\n", stats.page_faults, stats.swaps_realizados);

    printf("\n=== TODAS LAS PRUEBAS PASARON ===\n");
    return 0;
}
