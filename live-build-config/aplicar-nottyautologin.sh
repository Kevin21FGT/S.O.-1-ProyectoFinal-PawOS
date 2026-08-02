
#!/bin/bash
# Aplica el parametro nottyautologin al arranque, para arreglar el login
# roto en las consolas de texto (tty2-6). Correr despues de que exista
# config/binary (es decir, despues de "sudo lb config" o "sudo lb build").
set -e
sudo sed -i 's/LB_BOOTAPPEND_LIVE="boot=live components quiet splash"/LB_BOOTAPPEND_LIVE="boot=live components quiet splash nottyautologin"/' config/binary
echo "Verificando:"
grep -i BOOTAPPEND config/binary
