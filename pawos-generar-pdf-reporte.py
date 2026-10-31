#!/usr/bin/env python3
"""
pawos-generar-pdf-reporte.py

Convierte un reporte de PawOS Refugio (el .txt que genera el modulo
Reportes) en un PDF con diseno: encabezado verde con el nombre del refugio,
tarjetas con los totales, tablas por mes con subtotales y un recuadro con
el total final. Requiere fpdf2 (ya lo instala PawOS).

Reconoce los reportes de Mascotas, Vacunas, Adopciones, Donantes y Alertas
de Sensores (por mes o de todos los meses) y el reporte general. Si alguna
linea no coincide con el formato esperado, la deja como texto normal, asi
nunca se pierde informacion.

Uso:
    python3 pawos-generar-pdf-reporte.py --entrada reporte.txt --salida reporte.pdf
"""

import argparse
import re
import sys

try:
    from fpdf import FPDF, XPos, YPos
except ImportError:
    print("ERROR: falta la libreria fpdf2. Instala con: pip install fpdf2 --break-system-packages", file=sys.stderr)
    sys.exit(1)

VERDE_CLARO = (35, 146, 75)
VERDE_OSCURO = (18, 69, 31)
VERDE_FONDO = (232, 243, 236)
GRIS = (110, 110, 110)
COLORES_ESTADO = {
    "pendiente": (214, 137, 16),
    "atendida": (30, 132, 73),
    "disponible": (30, 132, 73),
    "adoptado": (41, 128, 185),
    "en_proceso": (214, 137, 16),
    "tratamiento": (192, 57, 43),
}
ANCHO_UTIL = 190.0  # Carta (215.9 mm) con margenes de 12.9 mm; se usa 190 de tabla


def L(texto):
    """Las fuentes base de PDF solo admiten Latin-1; lo demas se reemplaza."""
    return str(texto).encode("latin-1", "replace").decode("latin-1")


# ------------------------------------------------------------------
# Tipos de reporte: columnas, anchos relativos, expresion regular de cada fila
# ------------------------------------------------------------------

TIPOS = {
    "donantes": {
        "columnas": ["Fecha", "Donante", "Contacto", "Monto"],
        "pesos": [28, 56, 60, 28],
        "alinear_derecha": [3],
        "regex": re.compile(r"^\s+(.+?) \(contacto: (.*?)\) - Q([\d.,]+) - fecha: (\S+)$"),
        "armar": lambda m: [m.group(4), m.group(1), m.group(2), "Q" + m.group(3)],
    },
    "vacunas": {
        "columnas": ["Mascota", "Vacuna", "Aplicada", "Proxima", "Observaciones"],
        "pesos": [22, 42, 26, 26, 74],
        "alinear_derecha": [],
        "regex": re.compile(r"^\s+Mascota #(\d+) - (.+?) \| aplicada: (\S*) \| proxima: (\S*)(?: \| obs: (.*))?$"),
        "armar": lambda m: ["#" + m.group(1), m.group(2), m.group(3), m.group(4), m.group(5) or ""],
    },
    "adopciones": {
        "columnas": ["Fecha", "Mascota", "Adoptante", "Contacto"],
        "pesos": [30, 26, 84, 50],
        "alinear_derecha": [],
        "regex": re.compile(r"^\s+Mascota #(\d+) -> (.+?) \(contacto: (.*?)\), fecha: (\S*)$"),
        "armar": lambda m: [m.group(4), "#" + m.group(1), m.group(2), m.group(3)],
    },
    "alertas": {
        "columnas": ["Fecha y hora", "Animal", "Tipo", "Detalle", "Valor", "Estado"],
        "pesos": [37, 18, 28, 60, 17, 30],
        "alinear_derecha": [4],
        "estado": 5,
        "regex": re.compile(r"^\s+\[(.+?)\] animal (.*?) - (.*?): (.*) \(valor: ([\d.\-]+)\) - (atendida|pendiente)$"),
        "armar": lambda m: [m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)],
    },
    "mascotas": {
        "columnas": ["ID", "Nombre", "Especie", "Raza", "Edad", "Estado", "Ingreso"],
        "pesos": [12, 34, 24, 38, 18, 30, 34],
        "alinear_derecha": [],
        "estado": 5,
        "regex": re.compile(r"^\s+#(\d+) (.+?) - (.+?) \((.*?)\), (\d+) anios, estado: (\S+), ingreso: (.*)$"),
        "armar": lambda m: ["#" + m.group(1), m.group(2), m.group(3), m.group(4),
                            m.group(5) + " anios", m.group(6), m.group(7)],
    },
}


def detectar_tipo(titulo):
    t = titulo.lower()
    for clave, palabra in (("donantes", "donantes"), ("vacunas", "vacunas"), ("adopciones", "adopciones"),
                           ("alertas", "alertas"), ("mascotas", "mascotas")):
        if palabra in t:
            return clave
    return None  # reporte general: las filas quedan como texto


# ------------------------------------------------------------------
# Lectura del .txt en bloques
# ------------------------------------------------------------------

def leer_bloques(texto):
    titulo = "Reporte"
    meta = {}
    bloques = []
    tipo = None
    filas = None
    kv = None

    def cerrar():
        nonlocal filas, kv
        if filas:
            bloques.append(("filas", filas))
        if kv:
            bloques.append(("kv", kv))
        filas = None
        kv = None

    for linea in texto.splitlines():
        s = linea.strip()
        if not s:
            cerrar()
            continue
        if s.startswith("====="):
            titulo = s.strip("= ").strip()
            titulo = re.sub(r"\s*-\s*PawOS\s*$", "", titulo)
            tipo = detectar_tipo(titulo)
            continue
        if s.startswith("Periodo:") or s.startswith("Generado:"):
            clave, valor = s.split(":", 1)
            meta[clave] = valor.strip()
            continue
        if s.startswith("== ") and s.endswith(" =="):
            cerrar()
            bloques.append(("mes", s.strip("= ").strip()))
            continue
        if s.startswith("--") and s.endswith("--") and len(s) > 4:
            cerrar()
            etiqueta = s.strip("- ").strip()
            if etiqueta.lower() != "detalle":
                bloques.append(("seccion", etiqueta))
            continue
        m = re.match(r"^(TOTAL DEL MES|TOTAL GENERAL): (.*)$", s)
        if m:
            cerrar()
            bloques.append(("total", m.group(1), m.group(2)))
            continue
        m = re.match(r"^Subtotal: (.*)$", s)
        if m:
            if filas:
                bloques.append(("filas", filas))
                filas = None
            bloques.append(("subtotal", m.group(1)))
            continue
        if s.startswith("No hay "):
            cerrar()
            bloques.append(("nota", s))
            continue
        if linea.startswith("  ") and tipo:
            m = TIPOS[tipo]["regex"].match(linea)
            if m:
                if kv:
                    bloques.append(("kv", kv)); kv = None
                if filas is None:
                    filas = []
                filas.append(TIPOS[tipo]["armar"](m))
                continue
        if linea.startswith("  "):
            cerrar()
            bloques.append(("texto", s))
            continue
        m = re.match(r"^([^:]+?)\s*:\s*(.+)$", s)
        if m:
            if filas:
                bloques.append(("filas", filas)); filas = None
            if kv is None:
                kv = []
            kv.append((m.group(1).strip(), m.group(2).strip()))
            continue
        cerrar()
        bloques.append(("texto", s))
    cerrar()
    return titulo, meta, tipo, bloques


# ------------------------------------------------------------------
# PDF
# ------------------------------------------------------------------

class PDFReporte(FPDF):
    def __init__(self, titulo, refugio):
        super().__init__(orientation="P", unit="mm", format="Letter")
        self.titulo_rep = titulo
        self.refugio = refugio
        self.set_margins(13, 13, 13)
        self.set_auto_page_break(auto=False)
        self.alias_nb_pages()

    def degradado(self, x, y, w, h, c1, c2, pasos=40):
        for i in range(pasos):
            t = i / (pasos - 1)
            color = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
            self.set_fill_color(*color)
            self.rect(x, y + h * i / pasos, w, h / pasos + 0.3, style="F")

    def huella(self, cx, cy, escala, color):
        self.set_fill_color(*color)
        self.ellipse(cx - 6 * escala, cy - 1 * escala, 12 * escala, 9 * escala, style="F")
        for dx, dy, w, h in ((-10.5, -8, 4.6, 6.4), (-4.8, -13, 4.6, 6.8), (0.2, -13, 4.6, 6.8), (5.9, -8, 4.6, 6.4)):
            self.ellipse(cx + dx * escala, cy + dy * escala, w * escala, h * escala, style="F")

    def header(self):
        ancho = self.w
        if self.page_no() == 1:
            self.degradado(0, 0, ancho, 36, VERDE_CLARO, VERDE_OSCURO)
            self.huella(ancho - 24, 24, 1.4, (70, 170, 105))
            self.set_text_color(255, 255, 255)
            self.set_font("Helvetica", "B", 22)
            self.set_xy(13, 8)
            self.cell(150, 10, L(self.refugio))
            self.set_font("Helvetica", "", 13)
            self.set_xy(13, 20)
            self.cell(150, 8, L(self.titulo_rep))
            self.set_y(44)
        else:
            self.degradado(0, 0, ancho, 11, VERDE_CLARO, VERDE_OSCURO)
            self.set_text_color(255, 255, 255)
            self.set_font("Helvetica", "B", 9)
            self.set_xy(13, 3)
            self.cell(150, 5, L(f"{self.refugio} - {self.titulo_rep}"))
            self.set_y(18)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRIS)
        self.cell(0, 5, L(f"{self.refugio} - Reporte generado automaticamente"), align="L")
        self.set_xy(-60, -12)
        self.cell(47, 5, f"Pagina {self.page_no()} de {{nb}}", align="R")

    @property
    def limite_y(self):
        return self.h - 18

    def asegurar_espacio(self, alto):
        if self.get_y() + alto > self.limite_y:
            self.add_page()

    def recortar(self, texto, ancho):
        texto = L(texto)
        limite = ancho - 2
        if self.get_string_width(texto) <= limite:
            return texto
        while texto and self.get_string_width(texto + "...") > limite:
            texto = texto[:-1]
        return texto + "..."


def anchos_tipo(info):
    total = float(sum(info["pesos"]))
    return [ANCHO_UTIL * p / total for p in info["pesos"]]


def dibujar_encabezado_tabla(pdf, info, anchos):
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*VERDE_OSCURO)
    pdf.set_text_color(255, 255, 255)
    x0 = pdf.l_margin
    pdf.set_x(x0)
    for i, nombre in enumerate(info["columnas"]):
        pdf.cell(anchos[i], 7, pdf.recortar(nombre, anchos[i]), fill=True,
                 align="R" if i in info["alinear_derecha"] else "L")
    pdf.ln(7)


def dibujar_filas(pdf, tipo, filas):
    info = TIPOS[tipo]
    anchos = anchos_tipo(info)
    pdf.asegurar_espacio(7 + 7 * min(len(filas), 2))
    dibujar_encabezado_tabla(pdf, info, anchos)
    for n, celdas in enumerate(filas):
        if pdf.get_y() + 6.5 > pdf.limite_y:
            pdf.add_page()
            dibujar_encabezado_tabla(pdf, info, anchos)
        pdf.set_x(pdf.l_margin)
        pdf.set_fill_color(*VERDE_FONDO) if n % 2 == 0 else pdf.set_fill_color(255, 255, 255)
        for i, valor in enumerate(celdas):
            color = COLORES_ESTADO.get(valor.lower()) if i == info.get("estado", -1) else None
            if color:
                pdf.set_text_color(*color)
                pdf.set_font("Helvetica", "B", 8.5)
                valor = valor.replace("_", " ")
            else:
                pdf.set_text_color(30, 30, 30)
                pdf.set_font("Helvetica", "", 8.5)
            pdf.cell(anchos[i], 6.5, pdf.recortar(valor, anchos[i]), fill=True,
                     align="R" if i in info["alinear_derecha"] else "L")
        pdf.ln(6.5)
    pdf.set_text_color(0, 0, 0)


def dibujar_tarjetas(pdf, pares):
    por_fila = 3
    ancho = (pdf.w - pdf.l_margin - pdf.r_margin - 6 * (por_fila - 1)) / por_fila
    alto = 17
    for inicio in range(0, len(pares), por_fila):
        pdf.asegurar_espacio(alto + 4)
        y = pdf.get_y()
        for k, (etiqueta, valor) in enumerate(pares[inicio:inicio + por_fila]):
            x = pdf.l_margin + k * (ancho + 6)
            pdf.set_fill_color(*VERDE_FONDO)
            try:
                pdf.rect(x, y, ancho, alto, style="F", round_corners=True, corner_radius=2.5)
            except TypeError:
                pdf.rect(x, y, ancho, alto, style="F")
            pdf.set_xy(x + 3, y + 2)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*GRIS)
            pdf.cell(ancho - 6, 4, pdf.recortar(etiqueta, ancho - 6))
            pdf.set_xy(x + 3, y + 7.5)
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(*VERDE_OSCURO)
            pdf.cell(ancho - 6, 7, pdf.recortar(valor, ancho - 6))
        pdf.set_y(y + alto + 3)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)


def generar(entrada, salida, refugio):
    with open(entrada, "r", encoding="utf-8", errors="replace") as f:
        texto = f.read()
    titulo, meta, tipo, bloques = leer_bloques(texto)

    pdf = PDFReporte(titulo, refugio)
    pdf.add_page()

    # Periodo y fecha de generacion
    if "Periodo" in meta:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*VERDE_OSCURO)
        pdf.cell(pdf.w - 26, 7, L("Periodo: " + meta["Periodo"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if "Generado" in meta:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*GRIS)
        pdf.cell(pdf.w - 26, 5, L("Generado: " + meta["Generado"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    for b in bloques:
        clase = b[0]
        if clase == "kv":
            dibujar_tarjetas(pdf, b[1])
        elif clase == "seccion":
            pdf.asegurar_espacio(16)
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(*VERDE_OSCURO)
            pdf.cell(0, 7, L(b[1]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_draw_color(*VERDE_CLARO)
            pdf.set_line_width(0.4)
            y = pdf.get_y()
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(3)
        elif clase == "mes":
            pdf.asegurar_espacio(32)
            pdf.ln(2)
            pdf.set_fill_color(*VERDE_CLARO)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_x(pdf.l_margin)
            pdf.cell(ANCHO_UTIL, 8, "  " + L(b[1]), fill=True)
            pdf.ln(9)
        elif clase == "filas":
            dibujar_filas(pdf, tipo, b[1])
        elif clase == "subtotal":
            pdf.asegurar_espacio(9)
            pdf.set_fill_color(214, 233, 221)
            pdf.set_text_color(*VERDE_OSCURO)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_x(pdf.l_margin)
            pdf.cell(ANCHO_UTIL, 7, L("Subtotal: " + b[1]) + "  ", fill=True, align="R")
            pdf.ln(10)
        elif clase == "total":
            pdf.asegurar_espacio(18)
            pdf.ln(3)
            y = pdf.get_y()
            pdf.set_fill_color(*VERDE_OSCURO)
            try:
                pdf.rect(pdf.l_margin, y, ANCHO_UTIL, 13, style="F", round_corners=True, corner_radius=3)
            except TypeError:
                pdf.rect(pdf.l_margin, y, ANCHO_UTIL, 13, style="F")
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_xy(pdf.l_margin + 5, y + 3)
            pdf.cell(ANCHO_UTIL - 10, 7, L(f"{b[1]}: {b[2]}"))
            pdf.set_y(y + 16)
        elif clase == "nota":
            pdf.asegurar_espacio(14)
            pdf.ln(6)
            pdf.set_font("Helvetica", "I", 11)
            pdf.set_text_color(*GRIS)
            pdf.cell(0, 8, L(b[1]), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:  # texto
            pdf.asegurar_espacio(7)
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(40, 40, 40)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 5.5, L("  " + b[1]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.output(salida)
    print(f"PDF generado: {salida}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--entrada", required=True, help="Reporte en texto (.txt)")
    p.add_argument("--salida", required=True, help="PDF de salida")
    p.add_argument("--refugio", default="PawOS Refugio")
    args = p.parse_args()
    try:
        generar(args.entrada, args.salida, args.refugio)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: no se pudo generar el PDF: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
