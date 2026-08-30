
#ifndef ARCHIVOS_H
#define ARCHIVOS_H

#define ARCHIVOS_MAX_NOMBRE 128
#define ARCHIVOS_NUM_CATEGORIAS 6

typedef struct {
    char nombre[ARCHIVOS_MAX_NOMBRE];
    long tamano_bytes;
    char fecha_mod[20];
} ArchivoInfo;
extern const char *ARCHIVOS_CATEGORIAS[ARCHIVOS_NUM_CATEGORIAS];

int archivos_inicializar(void);
const char *archivos_ruta_base(void);
int archivos_listar(const char *categoria, ArchivoInfo **out, int *n);
int archivos_eliminar(const char *categoria, const char *nombre);
int archivos_respaldar_bd_auto(void);
long archivos_espacio_categoria(const char *categoria);

#endif
