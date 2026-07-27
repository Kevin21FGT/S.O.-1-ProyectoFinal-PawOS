
CC      = gcc
CFLAGS  = -Wall -Wextra -std=c11 -D_DEFAULT_SOURCE -Iinclude
LDFLAGS = -lncurses -lsqlite3 -lm

SRC = src/main.c src/db.c src/ui.c src/auth.c src/pantallas.c src/procesos.c src/pantalla_procesos.c src/memoria.c src/pantalla_memoria.c src/pantalla_login.c src/archivos.c src/pantalla_archivos.c
OBJ = $(SRC:.c=.o)
BIN = pawos-refugio

DEMONIO_SRC = src/vacunas_demonio.c src/db.c
DEMONIO_OBJ = $(DEMONIO_SRC:.c=.o)
DEMONIO_BIN = pawos-vacunas-check

all: $(BIN) $(DEMONIO_BIN)
$(BIN): $(OBJ)
	$(CC) $(OBJ) -o $(BIN) $(LDFLAGS)

$(DEMONIO_BIN): $(DEMONIO_OBJ)
	$(CC) $(DEMONIO_OBJ) -o $(DEMONIO_BIN) -lsqlite3 -lm

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ) $(DEMONIO_OBJ) $(BIN) $(DEMONIO_BIN)

.PHONY: all clean
