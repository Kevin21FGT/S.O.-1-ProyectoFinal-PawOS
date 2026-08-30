
CC      = gcc
NASM    = nasm
CFLAGS  = -Wall -Wextra -std=c11 -D_DEFAULT_SOURCE -Iinclude -Isrc
NASMFLAGS = -f elf64
LDFLAGS = -lncurses -lsqlite3 -lm -lcrypt

SRC = src/main.c src/db/db.c src/ui/ui.c src/auth/auth.c src/pantallas/pantallas.c src/procesos/procesos.c src/pantalla_procesos/pantalla_procesos.c src/memoria/memoria.c src/pantalla_memoria/pantalla_memoria.c src/pantalla_login/pantalla_login.c src/archivos/archivos.c src/pantalla_archivos/pantalla_archivos.c src/integridad/integridad.c
OBJ = $(SRC:.c=.o)

ASM_SRC = src/integridad/checksum.asm
ASM_OBJ = $(ASM_SRC:.asm=.o)

BIN = pawos-refugio

DEMONIO_SRC = src/vacunas_demonio.c src/db/db.c
DEMONIO_OBJ = $(DEMONIO_SRC:.c=.o)
DEMONIO_BIN = pawos-vacunas-check

MONITOR_SRC = src/servidor_monitoreo.c src/db/db.c
MONITOR_OBJ = $(MONITOR_SRC:.c=.o)
MONITOR_BIN = pawos-monitoreo

all: $(BIN) $(DEMONIO_BIN) $(MONITOR_BIN)

$(BIN): $(OBJ) $(ASM_OBJ)
	$(CC) $(OBJ) $(ASM_OBJ) -o $(BIN) $(LDFLAGS)
$(DEMONIO_BIN): $(DEMONIO_OBJ)
	$(CC) $(DEMONIO_OBJ) -o $(DEMONIO_BIN) -lsqlite3 -lm -lcrypt

$(MONITOR_BIN): $(MONITOR_OBJ)
	$(CC) $(MONITOR_OBJ) -o $(MONITOR_BIN) -lsqlite3 -lm -lcrypt

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

%.o: %.asm
	$(NASM) $(NASMFLAGS) $< -o $@

clean:
	rm -f $(OBJ) $(ASM_OBJ) $(DEMONIO_OBJ) $(MONITOR_OBJ) $(BIN) $(DEMONIO_BIN) $(MONITOR_BIN)

.PHONY: all clean
# =====================================================================
# Agregar este bloque al FINAL del Makefile que ya tienes
# (no reemplaza nada de lo que ya existe: "make all" y "make clean"
#  del programa CLI siguen funcionando exactamente igual que antes)
# =====================================================================

# ---- Interfaz grafica (GTK3) ----
GTK_CFLAGS = $(shell pkg-config --cflags gtk+-3.0)
GTK_LIBS   = $(shell pkg-config --libs gtk+-3.0)

GUI_BIN = pawos-refugio-gui

gui: src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c
	$(CC) $(CFLAGS) $(GTK_CFLAGS) src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c -o $(GUI_BIN) $(GTK_LIBS) -lsqlite3 -lm -lcrypt

clean-gui:
	rm -f $(GUI_BIN)

.PHONY: gui clean-gui
