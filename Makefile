CC      = gcc
CFLAGS  = -Wall -Wextra -std=c11 -D_DEFAULT_SOURCE -Iinclude
LDFLAGS = -lncurses -lsqlite3 -lm

SRC = src/main.c src/db.c src/ui.c src/auth.c src/pantallas.c src/procesos.c src/pantalla_procesos.c
OBJ = $(SRC:.c=.o)
BIN = pawos-refugio

all: $(BIN)

$(BIN): $(OBJ)
	$(CC) $(OBJ) -o $(BIN) $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ) $(BIN)

