#!/usr/bin/env python3
"""
pawos-generar-pdf-cita.py

Genera un PDF sencillo con los datos de una cita/vacuna, para
mandarselo al Cliente por correo y WhatsApp.

Uso:
    python3 pawos-generar-pdf-cita.py \
        --cliente "Juan Perez" \
        --mascota "Firulais" \
        --vacuna "Rabia" \
        --fecha "2026-09-15" \
        --refugio "PawOS Refugio" \
        --salida /tmp/cita.pdf
"""

import argparse
import sys
from datetime import datetime

try:
    from fpdf import FPDF, XPos, YPos
except ImportError:
    print("ERROR: falta la libreria fpdf2. Instala con: pip install fpdf2 --break-system-packages", file=sys.stderr)
    sys.exit(1)


def generar_pdf(cliente, mascota, vacuna, fecha, refugio, salida, observaciones=""):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 90, 60)
    pdf.cell(0, 14, refugio, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 8, "Recordatorio de cita", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(8)

    pdf.set_draw_color(30, 90, 60)
    pdf.set_line_width(0.5)
    y = pdf.get_y()
    pdf.line(15, y, 195, y)
    pdf.ln(10)

    pdf.set_text_color(0, 0, 0)
    filas = [
        ("Cliente:", cliente),
        ("Mascota:", mascota),
        ("Vacuna / servicio:", vacuna),
        ("Fecha de la cita:", fecha),
    ]
    if observaciones:
        filas.append(("Observaciones:", observaciones))

    for etiqueta, valor in filas:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, etiqueta, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 12)
        pdf.multi_cell(0, 8, valor, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(120, 120, 120)
    generado = datetime.now().strftime("%Y-%m-%d %H:%M")
    pdf.cell(0, 8, f"Generado automaticamente por PawOS Refugio el {generado}", align="C")

    pdf.output(salida)
    print(f"PDF generado: {salida}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cliente", required=True)
    p.add_argument("--mascota", required=True)
    p.add_argument("--vacuna", required=True)
    p.add_argument("--fecha", required=True)
    p.add_argument("--refugio", default="PawOS Refugio")
    p.add_argument("--observaciones", default="")
    p.add_argument("--salida", required=True)
    args = p.parse_args()
    generar_pdf(args.cliente, args.mascota, args.vacuna, args.fecha, args.refugio, args.salida, args.observaciones)


if __name__ == "__main__":
    main()
