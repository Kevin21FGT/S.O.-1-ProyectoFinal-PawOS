#!/usr/bin/env python3
"""
pawos-generar-pdf-documento.py

Genera un PDF con una tabla (carnet de vacunas, comprobante de
donaciones, comprobante de solicitudes de adopcion, reportes...). Lo usa
el Portal de Clientes de PawOS. Requiere fpdf2 (ya lo instala PawOS).

Uso:
    python3 pawos-generar-pdf-documento.py \
        --titulo "Carnet de vacunas" \
        --cliente "Kevin F (kevinfv792@gmail.com)" \
        --columnas "Mascota|Vacuna|Proxima dosis|Estado" \
        --fila "Firulais|Spuknik|2026-10-16|Al dia" \
        --resumen "1 vacuna registrada" \
        --salida /tmp/carnet.pdf

Las filas se pasan con --fila (se puede repetir). Las celdas se separan
con "|".
"""

import argparse
import io
import sys
from datetime import date, datetime

try:
    from fpdf import FPDF, XPos, YPos
except ImportError:
    print("ERROR: falta la libreria fpdf2. Instala con: pip install fpdf2 --break-system-packages", file=sys.stderr)
    sys.exit(1)

VERDE = (30, 90, 60)
COLORES_ESTADO = {
    "vencida": (192, 57, 43),
    "rechazada": (192, 57, 43),
    "hoy": (214, 137, 16),
    "pendiente": (214, 137, 16),
    "al dia": (30, 132, 73),
    "aprobada": (30, 132, 73),
}
ANCHO_UTIL = 180.0
ALTO_FILA = 8


def L(texto):
    """Las fuentes base de PDF solo admiten Latin-1; lo demas se reemplaza."""
    return str(texto).encode("latin-1", "replace").decode("latin-1")


def recortar(pdf, texto, ancho):
    """Corta el texto con '...' si no cabe en la celda."""
    texto = L(texto)
    limite = ancho - 2
    if pdf.get_string_width(texto) <= limite:
        return texto
    while texto and pdf.get_string_width(texto + "...") > limite:
        texto = texto[:-1]
    return texto + "..."


def calcular_anchos(columnas, filas):
    pesos = []
    for i, nombre in enumerate(columnas):
        mayor = len(nombre)
        for f in filas:
            if i < len(f):
                mayor = max(mayor, len(f[i]))
        pesos.append(min(max(mayor, 6), 40) + 2)
    total = float(sum(pesos))
    return [ANCHO_UTIL * p / total for p in pesos]


def dibujar_encabezado_tabla(pdf, columnas, anchos):
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(*VERDE)
    pdf.set_text_color(255, 255, 255)
    for i, nombre in enumerate(columnas):
        ultimo = i == len(columnas) - 1
        pdf.cell(anchos[i], ALTO_FILA, recortar(pdf, nombre, anchos[i]), border=0, fill=True,
                 new_x=XPos.LMARGIN if ultimo else XPos.RIGHT,
                 new_y=YPos.NEXT if ultimo else YPos.TOP)
    pdf.set_text_color(0, 0, 0)


# ---------------------------------------------------------------
# Carnet (estilo "carnet"): A6 horizontal, frente y reverso
# ---------------------------------------------------------------

VERDE_CLARO = (35, 146, 75)
VERDE_OSCURO = (18, 69, 31)


def degradado(pdf, x, y, w, h, c1, c2, pasos=48):
    """Degradado vertical hecho con franjas finas (funciona en cualquier fpdf2)."""
    for i in range(pasos):
        t = i / (pasos - 1)
        color = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
        pdf.set_fill_color(*color)
        pdf.rect(x, y + h * i / pasos, w, h / pasos + 0.3, style="F")


def caja(pdf, x, y, w, h, radio=2.5):
    try:
        pdf.rect(x, y, w, h, style="F", round_corners=True, corner_radius=radio)
    except TypeError:
        pdf.rect(x, y, w, h, style="F")


def huella(pdf, cx, cy, escala, color):
    """Huella de patita: una almohadilla grande y cuatro deditos."""
    pdf.set_fill_color(*color)
    pdf.ellipse(cx - 6 * escala, cy - 1 * escala, 12 * escala, 9 * escala, style="F")
    for dx, dy, w, h in ((-10.5, -8, 4.6, 6.4), (-4.8, -13, 4.6, 6.8), (0.2, -13, 4.6, 6.8), (5.9, -8, 4.6, 6.4)):
        pdf.ellipse(cx + dx * escala, cy + dy * escala, w * escala, h * escala, style="F")


def foto_circular(ruta, lado=360):
    """Recorta la foto en cuadrado desde el centro y la deja en circulo."""
    if not ruta:
        return None
    try:
        from PIL import Image, ImageDraw
        im = Image.open(ruta).convert("RGBA")
        w, h = im.size
        m = min(w, h)
        im = im.crop(((w - m) // 2, (h - m) // 2, (w + m) // 2, (h + m) // 2)).resize((lado, lado), Image.LANCZOS)
        mascara = Image.new("L", (lado * 3, lado * 3), 0)
        ImageDraw.Draw(mascara).ellipse((0, 0, lado * 3 - 1, lado * 3 - 1), fill=255)
        im.putalpha(mascara.resize((lado, lado), Image.LANCZOS))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception:
        return None


def dibujar_qr(pdf, datos, x, y, lado):
    """QR vectorial (nitido al imprimir). Devuelve False si falta 'segno'."""
    try:
        import segno
    except ImportError:
        return False
    qr = segno.make(datos, error="m", micro=False)
    matriz = [list(fila) for fila in qr.matrix]
    n = len(matriz)
    borde = 2
    mod = lado / (n + 2 * borde)
    pdf.set_fill_color(255, 255, 255)
    caja(pdf, x, y, lado, lado, 1.5)
    pdf.set_fill_color(15, 40, 25)
    for r, fila in enumerate(matriz):
        for c, v in enumerate(fila):
            if v:
                pdf.rect(x + (c + borde) * mod, y + (r + borde) * mod, mod + 0.02, mod + 0.02, style="F")
    return True


def generar_carnet(args, columnas, filas):
    W, H = 148.0, 105.0
    nombre = args.nombre or args.cliente or "Cliente"
    hoy = date.today().isoformat()

    mascotas = {f[0] for f in filas}
    vencidas = [f for f in filas if len(f) > 3 and f[3].lower() == "vencida"]
    futuras = sorted([f for f in filas if len(f) > 3 and f[2] and f[3].lower() != "vencida"], key=lambda f: f[2])
    proxima = futuras[0] if futuras else None

    # A6 horizontal (148 x 105 mm), con medidas explicitas porque algunas
    # versiones de fpdf2 no conocen el nombre "A6".
    pdf = FPDF(orientation="L", unit="mm", format=(105, 148))
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(0, 0, 0)

    # ===== FRENTE =====
    pdf.add_page()
    pdf.set_fill_color(250, 252, 251)
    pdf.rect(0, 0, W, H, style="F")

    # Panel izquierdo verde con la foto
    degradado(pdf, 0, 0, 52, H, VERDE_CLARO, VERDE_OSCURO)
    huella(pdf, 26, 101, 1.5, (58, 160, 96))
    pdf.set_fill_color(255, 255, 255)
    pdf.ellipse(8.5, 8.5, 35, 35, style="F")
    foto = foto_circular(args.foto)
    if foto:
        pdf.image(foto, x=10, y=10, w=32, h=32)
    else:
        pdf.set_fill_color(*VERDE_CLARO)
        pdf.ellipse(10, 10, 32, 32, style="F")
        pdf.set_font("Helvetica", "B", 26)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(10, 20)
        pdf.cell(32, 14, L(nombre[:1].upper()), align="C")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_xy(3, 47)
    pdf.multi_cell(46, 5, L(nombre), align="C")
    if args.cliente_id:
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(3, pdf.get_y() + 1)
        try:
            numero = f"{int(args.cliente_id):06d}"
        except ValueError:
            numero = args.cliente_id
        pdf.cell(46, 4, f"Miembro No. {numero}", align="C")
    pdf.set_font("Helvetica", "", 6.5)
    if args.correo:
        pdf.set_xy(3, 68)
        pdf.cell(46, 4, recortar(pdf, args.correo, 46), align="C")
    if args.telefono:
        pdf.set_xy(3, 72.5)
        pdf.cell(46, 4, recortar(pdf, "WhatsApp: " + args.telefono, 46), align="C")

    # Zona derecha
    huella(pdf, 88, 97, 1.5, (222, 238, 228))
    pdf.set_text_color(*VERDE_OSCURO)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_xy(60, 11)
    pdf.cell(80, 9, "PawOS Refugio")
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(90, 90, 90)
    pdf.set_xy(60, 21)
    pdf.cell(80, 5, "CARNET DE VACUNAS")
    pdf.set_draw_color(*VERDE_CLARO)
    pdf.set_line_width(0.6)
    pdf.line(60, 28, 140, 28)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(120, 120, 120)
    pdf.set_xy(60, 30)
    pdf.cell(80, 4, "Cada vacuna cuenta: protegiendo a cada patita.")

    # Datos de resumen
    pdf.set_text_color(40, 40, 40)
    y = 40
    for etiqueta, valor in (("Mascotas:", str(len(mascotas))), ("Vacunas registradas:", str(len(filas)))):
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_xy(60, y)
        pdf.cell(32, 5, etiqueta)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.cell(18, 5, valor)
        y += 5.5

    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_xy(60, y + 1)
    pdf.set_text_color(*VERDE_OSCURO)
    pdf.cell(50, 5, "Proxima dosis")
    pdf.set_text_color(30, 30, 30)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_xy(60, y + 6.5)
    if proxima:
        pdf.cell(50, 5, L(proxima[2]))
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_xy(60, y + 12)
        pdf.cell(50, 4, recortar(pdf, f"{proxima[0]} - {proxima[1]}", 50))
    else:
        pdf.set_font("Helvetica", "", 8.5)
        pdf.cell(50, 5, "Sin proximas dosis")
    if vencidas:
        pdf.set_text_color(192, 57, 43)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_xy(60, y + 18)
        pdf.cell(50, 4, f"{len(vencidas)} dosis vencida(s)")

    # QR con el resumen (cualquier celular puede leerlo)
    partes = ["PawOS Refugio - Carnet de vacunas", f"Cliente: {nombre}"]
    if args.correo:
        partes.append(f"Correo: {args.correo}")
    partes.append(f"Mascotas: {len(mascotas)} / Vacunas: {len(filas)}")
    if proxima:
        partes.append(f"Proxima dosis: {proxima[2]} - {proxima[0]} ({proxima[1]})")
    if vencidas:
        partes.append(f"Dosis vencidas: {len(vencidas)}")
    partes.append(f"Emitido: {hoy}")
    if dibujar_qr(pdf, "\n".join(partes), 111, 44, 30):
        pdf.set_text_color(110, 110, 110)
        pdf.set_font("Helvetica", "", 6)
        pdf.set_xy(108, 75)
        pdf.multi_cell(36, 3, "Escanea para ver\ntu resumen", align="C")

    pdf.set_text_color(130, 130, 130)
    pdf.set_font("Helvetica", "I", 6)
    pdf.set_xy(60, 98)
    pdf.cell(80, 4, L(f"Emitido el {hoy} - {args.refugio}"))

    # ===== REVERSO: registro de vacunas =====
    margen = 10.0
    ancho_tabla = W - 2 * margen
    alto = 6.5
    anchos = [a * ancho_tabla / ANCHO_UTIL for a in calcular_anchos(columnas, filas)]

    def pagina_reverso(continuacion):
        pdf.add_page()
        pdf.set_fill_color(250, 252, 251)
        pdf.rect(0, 0, W, H, style="F")
        degradado(pdf, 0, 0, W, 14, VERDE_CLARO, VERDE_OSCURO)
        huella(pdf, W - 12, 11, 0.55, (255, 255, 255))
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_xy(margen, 3.5)
        pdf.cell(100, 7, "Registro de vacunas" + (" (continuacion)" if continuacion else ""))
        pdf.set_text_color(130, 130, 130)
        pdf.set_font("Helvetica", "I", 6)
        pdf.set_xy(0, H - 7)
        pdf.cell(W, 4, L(f"Carnet de {nombre} - {args.refugio}"), align="C")
        # Encabezado de la tabla
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(*VERDE_OSCURO)
        pdf.set_text_color(255, 255, 255)
        x = margen
        pdf.set_xy(x, 19)
        for i, nombre_col in enumerate(columnas):
            pdf.cell(anchos[i], alto, recortar(pdf, nombre_col, anchos[i]), fill=True)
        return 19 + alto

    y = pagina_reverso(False)
    if not filas:
        pdf.set_xy(margen, y + 8)
        pdf.set_text_color(120, 120, 120)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(ancho_tabla, 8, "Aun no hay vacunas registradas.", align="C")
    for n, celdas in enumerate(filas):
        if y + alto > H - 12:
            y = pagina_reverso(True)
        pdf.set_fill_color(236, 244, 239)
        pdf.set_xy(margen, y)
        for i, valor in enumerate(celdas):
            color = COLORES_ESTADO.get(valor.lower())
            if color:
                pdf.set_text_color(*color)
                pdf.set_font("Helvetica", "B", 8)
            else:
                pdf.set_text_color(30, 30, 30)
                pdf.set_font("Helvetica", "", 8)
            pdf.cell(anchos[i], alto, recortar(pdf, valor, anchos[i]), fill=(n % 2 == 0))
        y += alto

    pdf.output(args.salida)
    print(f"PDF generado: {args.salida}")


def generar(args):
    columnas = [c.strip() for c in args.columnas.split("|")]
    filas = []
    for f in args.fila or []:
        celdas = [c.strip() for c in f.split("|")]
        celdas += [""] * (len(columnas) - len(celdas))
        filas.append(celdas[: len(columnas)])

    if args.estilo == "carnet":
        generar_carnet(args, columnas, filas)
        return

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    # Encabezado con el nombre del refugio
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*VERDE)
    pdf.cell(0, 12, L(args.refugio), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 9, L(args.titulo), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(2)
    pdf.set_draw_color(*VERDE)
    pdf.set_line_width(0.5)
    y = pdf.get_y()
    pdf.line(15, y, 195, y)
    pdf.ln(6)

    pdf.set_text_color(0, 0, 0)
    if args.cliente:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(22, 7, "Cliente:")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, L(args.cliente), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(22, 7, "Fecha:")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, datetime.now().strftime("%Y-%m-%d %H:%M"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    anchos = calcular_anchos(columnas, filas)
    dibujar_encabezado_tabla(pdf, columnas, anchos)

    pdf.set_font("Helvetica", "", 10)
    if not filas:
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 10, "No hay registros para mostrar.", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        pdf.set_text_color(0, 0, 0)

    for n, celdas in enumerate(filas):
        if pdf.get_y() + ALTO_FILA > 270:
            pdf.add_page()
            dibujar_encabezado_tabla(pdf, columnas, anchos)
            pdf.set_font("Helvetica", "", 10)
        relleno = n % 2 == 0
        pdf.set_fill_color(240, 245, 242)
        for i, valor in enumerate(celdas):
            ultimo = i == len(celdas) - 1
            color = COLORES_ESTADO.get(valor.lower())
            if color:
                pdf.set_text_color(*color)
                pdf.set_font("Helvetica", "B", 10)
            else:
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Helvetica", "", 10)
            pdf.cell(anchos[i], ALTO_FILA, recortar(pdf, valor, anchos[i]), border=0, fill=relleno,
                     new_x=XPos.LMARGIN if ultimo else XPos.RIGHT,
                     new_y=YPos.NEXT if ultimo else YPos.TOP)
    pdf.set_text_color(0, 0, 0)

    if args.resumen:
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*VERDE)
        pdf.multi_cell(0, 7, L(args.resumen), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(-20)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 8, L(f"Generado automaticamente por {args.refugio} el {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
             align="C")

    pdf.output(args.salida)
    print(f"PDF generado: {args.salida}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--titulo", required=True)
    p.add_argument("--cliente", default="")
    p.add_argument("--columnas", required=True, help='Nombres separados por "|"')
    p.add_argument("--fila", action="append", help='Una fila, celdas separadas por "|" (repetible)')
    p.add_argument("--resumen", default="")
    p.add_argument("--refugio", default="PawOS Refugio")
    p.add_argument("--salida", required=True)
    # Solo para --estilo carnet
    p.add_argument("--estilo", default="tabla", choices=["tabla", "carnet"])
    p.add_argument("--nombre", default="")
    p.add_argument("--correo", default="")
    p.add_argument("--telefono", default="")
    p.add_argument("--cliente-id", dest="cliente_id", default="")
    p.add_argument("--foto", default="", help="Ruta a la foto de perfil (PNG/JPG)")
    generar(p.parse_args())


if __name__ == "__main__":
    main()
