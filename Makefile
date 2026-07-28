
CC      = gcc
NASM    = nasm
CFLAGS  = -Wall -Wextra -std=c11 -D_DEFAULT_SOURCE -Iinclude
NASMFLAGS = -f elf64
LDFLAGS = -lncurses -lsqlite3 -lm

SRC = src/main.c src/db.c src/ui.c src/auth.c src/pantallas.c src/procesos.c src/pantalla_procesos.c src/memoria.c src/pantalla_memoria.c src/pantalla_login.c src/archivos.c src/pantalla_archivos.c src/integridad.c
OBJ = $(SRC:.c=.o)

ASM_SRC = src/checksum.asm
ASM_OBJ = $(ASM_SRC:.asm=.o)

BIN = pawos-refugio
DEMONIO_SRC = src/vacunas_demonio.c src/db.c
DEMONIO_OBJ = $(DEMONIO_SRC:.c=.o)
DEMONIO_BIN = pawos-vacunas-check

all: $(BIN) $(DEMONIO_BIN)

$(BIN): $(OBJ) $(ASM_OBJ)
	$(CC) $(OBJ) $(ASM_OBJ) -o $(BIN) $(LDFLAGS)

$(DEMONIO_BIN): $(DEMONIO_OBJ)
	$(CC) $(DEMONIO_OBJ) -o $(DEMONIO_BIN) -lsqlite3 -lm

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

%.o: %.asm
	$(NASM) $(NASMFLAGS) $< -o $@
clean:
	rm -f $(OBJ) $(ASM_OBJ) $(DEMONIO_OBJ) $(BIN) $(DEMONIO_BIN)

.PHONY: all clean
