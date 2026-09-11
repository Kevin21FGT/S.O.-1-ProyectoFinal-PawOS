
#ifndef INTEGRIDAD_H
#include <stdint.h>
#define INTEGRIDAD_H

/* Calcula el checksum (en Ensamblador) de todos los registros de donantes */
uint64_t integridad_checksum_donantes(void);

/* Compara contra el checksum guardado; si no existe, lo crea.
 * Retorna: 0 = integro (coincide), 1 = ALERTA (no coincide),
 *          2 = se creo el checksum base ahora, -1 = error */
int integridad_verificar_donantes(void);


/* Recalcula y guarda el checksum actual como nueva base (acepta los cambios) */
int integridad_actualizar_checksum_donantes(void);

#endif
