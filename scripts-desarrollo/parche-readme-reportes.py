#!/usr/bin/env python3
"""
parche-readme-reportes.py

README.md: reescribe la seccion "## Reportes" con lo nuevo (reportes por mes,
PDF con diseno, envio por correo y WhatsApp), actualiza la linea de pendientes
del menu lateral y el arbol de archivos (pawos-generar-pdf-reporte.py).

Idempotente (marca "<!-- readme-reportes -->"), backup README.md.bak_reportes.

Uso (parado en la raiz del repo):
    python3 parche-readme-reportes.py
"""

import shutil
import sys

ARCHIVO = "README.md"
MARCA = "<!-- readme-reportes -->"
TITULO = "## Reportes"

NUEVA = """## Reportes

El módulo **Reportes** de PawOS Refugio (panel embebido, visible para Administrador y Veterinario) genera resúmenes del refugio y los muestra en pantalla antes de guardarlos o enviarlos. <!-- readme-reportes -->

### Reportes disponibles

- **Generar reporte:** resumen general del refugio.
- **Por categoría:** Mascotas, Vacunas, Adopciones, Donantes y Alertas de Sensores.
- **Historial:** cada reporte generado queda registrado y se puede volver a abrir (carpeta `reportes` de PawOS Archivos y `historial_reportes.log`).

### Reportes por mes

Al pulsar **Donantes**, **Vacunas**, **Adopciones** o **Alertas de Sensores** se abre un selector de mes (`pedir_mes_donantes()` y `pedir_mes_reporte()` en `main_gtk.c`). La lista siempre incluye los **últimos 12 meses** (`reporte_completar_ultimos_meses()`, mes y año) más cualquier mes anterior que tenga registros (`reporte_listar_meses()`), y la opción **Todos los meses**.

| Reporte | Se agrupa por | Función |
|---|---|---|
| Donantes | fecha de la donación | `reporte_generar_donantes_mes()` |
| Vacunas | fecha de aplicación | `reporte_generar_mensual(REPORTE_VACUNAS)` |
| Adopciones | fecha de adopción | `reporte_generar_mensual(REPORTE_ADOPCIONES)` |
| Alertas | fecha de la alerta (cuenta además las pendientes) | `reporte_generar_mensual(REPORTE_ALERTAS)` |
| Mascotas | — (estado actual, sin mes) | `reporte_generar_mascotas()` |

- **Un mes:** solo los registros de ese mes y su `TOTAL DEL MES`. Si no hay, el reporte lo dice.
- **Todos los meses:** agrupado por mes, con subtotal por mes y `TOTAL GENERAL`. Los registros se ordenan por fecha.
- El mes elegido queda en el título y en el historial (por ejemplo "Donantes (Octubre 2026)").
- Los reportes originales (`reporte_generar_donantes()`, etc.) siguen existiendo sin cambios; las funciones por mes son nuevas.

### PDF con diseño

**Guardar como (.txt / .pdf)** usa `pawos-generar-pdf-reporte.py` (fpdf2) cuando se elige PDF: lee el texto del reporte y arma encabezado verde con el nombre del refugio, periodo, tarjetas con los totales, una tabla por mes con subtotales, recuadro con el total final y pie con número de página. Reconoce el formato de las cinco categorías y del reporte general; si una línea no coincide, la deja como texto normal. Si el script no está instalado o falla, `escribir_pdf_simple()` (Cairo) genera el PDF sencillo de antes, así que nunca se pierde la función. El script se instala en `/usr/local/bin` (`instalar-pawos.sh` y `construir-deb.sh`).

### Enviar por correo o WhatsApp

Junto a *Guardar como* hay dos botones, **Enviar por correo** y **Enviar por WhatsApp**, activos cuando ya hay un reporte en pantalla:

1. `enviar_reporte()` pide el destino. En WhatsApp, un número de 8 dígitos recibe el prefijo `502`.
2. Genera el PDF en una carpeta temporal (`g_dir_make_tmp`) con nombre legible, por ejemplo `reporte_de_donantes_octubre_2026.pdf`.
3. Lo envía con `sudo -n /usr/local/bin/pawos-enviar-documento` (mismas credenciales de `/etc/pawos/notificaciones.conf` y misma regla de sudo que el Portal de Clientes; si falta, avisa que se corra `instalar-documentos.sh`).
4. Borra el PDF temporal.

Se envía exactamente el reporte que está en pantalla: para mandar una categoría completa se elige **Todos los meses**.

"""

ARBOL_VIEJO = "pawos-enviar-documento, pawos-generar-pdf-documento.py          # PDF de carnet, comprobantes y reportes"
ARBOL_NUEVO = "pawos-enviar-documento, pawos-generar-pdf-documento.py, pawos-generar-pdf-reporte.py   # PDF de carnet, comprobantes y reportes"

MENU_VIEJO = "- **Pendientes de diseño:** evitar el scroll del menú lateral y el espacio vacío al maximizar."
MENU_NUEVO = "- **Menú lateral compacto:** los 12 módulos caben sin scroll; el menú va dentro de un área con scroll que solo aparece en pantallas muy bajas."


def dividir(texto):
    secciones, titulo, actual, en_codigo = [], None, [], False
    for linea in texto.splitlines(keepends=True):
        if linea.lstrip().startswith("```"):
            en_codigo = not en_codigo
        if not en_codigo and linea.startswith("## "):
            secciones.append((titulo, "".join(actual)))
            titulo = linea.rstrip()
            actual = [linea]
        else:
            actual.append(linea)
    secciones.append((titulo, "".join(actual)))
    return secciones


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if MARCA in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    secciones = dividir(contenido)
    titulos = [t for t, _ in secciones]
    if titulos.count(TITULO) != 1:
        print(f"ERROR: la seccion '{TITULO}' aparece {titulos.count(TITULO)} veces (debe ser 1). No se cambio nada.")
        sys.exit(1)

    salida = "".join(NUEVA if t == TITULO else cuerpo for t, cuerpo in secciones)

    # Cambios menores: solo si el texto esta (una vez); si no, se omiten sin error.
    for viejo, nuevo, nombre in ((ARBOL_VIEJO, ARBOL_NUEVO, "arbol de archivos"),
                                 (MENU_VIEJO, MENU_NUEVO, "nota del menu lateral")):
        if salida.count(viejo) == 1:
            salida = salida.replace(viejo, nuevo, 1)
        else:
            print(f"AVISO: no se encontro (una vez) el texto de '{nombre}'; se omite ese cambio.")

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_reportes")
    print(f"Backup: {ARCHIVO}.bak_reportes")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(salida)
    print(f"{ARCHIVO} actualizado: seccion Reportes reescrita.")


if __name__ == "__main__":
    main()
