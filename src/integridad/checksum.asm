
; checksum.asm - Rutina de integridad de datos de PawOS, en Ensamblador x86-64.
; uint64_t pawos_checksum(const unsigned char *datos, size_t len);
; Convencion System V AMD64: rdi = datos, rsi = len, retorna en rax.
; Algoritmo: rotate-left(5) + XOR por cada byte (checksum simple de mezcla).

global pawos_checksum

section .text
pawos_checksum:
    xor rax, rax            ; checksum = 0
    xor rcx, rcx            ; i = 0
    test rsi, rsi
    jz .fin                 ; si len == 0, retornar 0
.loop:
    cmp rcx, rsi
    jge .fin
    movzx rdx, byte [rdi + rcx]  ; rdx = datos[i]
    rol rax, 5                    ; checksum = rotate_left(checksum, 5)
    xor rax, rdx                  ; checksum ^= datos[i]
    inc rcx
    jmp .loop

.fin:
    ret

section .note.GNU-stack noalloc noexec nowrite progbits
