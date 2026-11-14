"""
Genera una factura 100% ficticia de una página para probar prebuilt-invoice.

Proveedor ficticio: Plásticos Andinos Card S.A.C. -> Cliente: BancAnalytics S.A.
Todos los nombres, RUC, direcciones y montos son inventados.

Uso (desde la raíz del repo):
    .venv/bin/python scripts/generar_factura.py
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

SALIDA = Path(__file__).resolve().parent.parent / "documents" / "04_BancAnalytics_Factura_Proveedor.pdf"

AZUL = colors.HexColor("#0B2F5B")
GRIS = colors.HexColor("#E9EEF5")

ITEMS = [
    # (código, descripción, cantidad, precio unitario)
    ("PL-CLA", "Plásticos tarjeta de crédito Clásica (chip + contactless)", 5000, 4.80),
    ("PL-ORO", "Plásticos tarjeta de crédito Oro (chip + contactless)", 2000, 6.50),
    ("PL-PLA", "Plásticos tarjeta de crédito Platinum (metalizado)", 800, 12.00),
    ("PL-BLK", "Plásticos tarjeta de crédito Black (metal)", 150, 45.00),
    ("KT-BIE", "Kit de bienvenida impreso (sobre, carta y folleto)", 7950, 1.20),
]
IGV = 0.18


def soles(x: float) -> str:
    return f"S/ {x:,.2f}"


def construir():
    estilos = getSampleStyleSheet()
    normal = ParagraphStyle("n", parent=estilos["Normal"], fontSize=9, leading=12)
    titulo = ParagraphStyle("t", parent=estilos["Title"], fontSize=16, textColor=AZUL, alignment=0)
    pequeno = ParagraphStyle("p", parent=normal, fontSize=7.5, textColor=colors.grey)

    subtotal = round(sum(c * p for _, _, c, p in ITEMS), 2)
    igv = round(subtotal * IGV, 2)
    total = round(subtotal + igv, 2)

    doc = SimpleDocTemplate(str(SALIDA), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title="Factura E001-000358", author="Plásticos Andinos Card S.A.C. (ficticio)")
    h = []

    # Encabezado: emisor (izquierda) y recuadro de la factura (derecha)
    emisor = Paragraph(
        "<b>PLÁSTICOS ANDINOS CARD S.A.C.</b><br/>"
        "RUC: 20611122233<br/>"
        "Av. Argentina 2450, Callao, Perú<br/>"
        "Tel.: (01) 555-0101 · facturacion@plasticosandinos.example", normal)
    recuadro = Table([
        [Paragraph("<b>FACTURA ELECTRÓNICA</b>", normal)],
        [Paragraph("<b>E001-000358</b>", normal)],
        [Paragraph("RUC 20611122233", normal)],
    ], colWidths=[62 * mm])
    recuadro.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, AZUL),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 0), (-1, 0), GRIS),
    ]))
    cab = Table([[emisor, recuadro]], colWidths=[110 * mm, 64 * mm])
    cab.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    h += [cab, Spacer(1, 8)]

    # Datos del cliente y de la operación
    datos = Table([
        [Paragraph("<b>Cliente:</b> BancAnalytics S.A.", normal),
         Paragraph("<b>Fecha de emisión:</b> 05/11/2026", normal)],
        [Paragraph("<b>RUC:</b> 20600000001", normal),
         Paragraph("<b>Fecha de vencimiento:</b> 05/12/2026", normal)],
        [Paragraph("<b>Dirección:</b> Av. Javier Prado Este 1234, San Isidro, Lima", normal),
         Paragraph("<b>Orden de compra:</b> OC-BCA-2026-0457", normal)],
        [Paragraph("<b>Atención:</b> Gerencia de Medios de Pago", normal),
         Paragraph("<b>Moneda:</b> Soles (PEN) · <b>Pago:</b> crédito 30 días", normal)],
    ], colWidths=[100 * mm, 74 * mm])
    datos.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    h += [datos, Spacer(1, 10)]

    # Detalle
    filas = [["Código", "Descripción", "Cant.", "P. unitario", "Importe"]]
    for cod, desc, cant, pu in ITEMS:
        filas.append([cod, Paragraph(desc, normal), f"{cant:,}", soles(pu), soles(cant * pu)])
    detalle = Table(filas, colWidths=[18 * mm, 86 * mm, 18 * mm, 24 * mm, 28 * mm], repeatRows=1)
    detalle.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    h += [detalle, Spacer(1, 8)]

    # Totales
    totales = Table([
        ["Op. gravada (subtotal)", soles(subtotal)],
        ["IGV (18%)", soles(igv)],
        ["IMPORTE TOTAL", soles(total)],
    ], colWidths=[50 * mm, 32 * mm], hAlign="RIGHT")
    totales.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("LINEABOVE", (0, 2), (-1, 2), 1, AZUL),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
    ]))
    h += [totales, Spacer(1, 12)]

    h.append(Paragraph(
        "Son: setenta y cuatro mil doscientos diez con 20/100 soles. "
        "Depositar en la cuenta corriente BancAnalytics N.° 191-0000000-0-00 (ficticia) "
        "a nombre de Plásticos Andinos Card S.A.C.", normal))
    h.append(Spacer(1, 18))
    h.append(Paragraph(
        "DOCUMENTO 100% FICTICIO generado para un laboratorio académico. Ni el emisor, ni el cliente, "
        "ni los RUC, cuentas o montos corresponden a entidades o transacciones reales.", pequeno))

    doc.build(h)
    return subtotal, igv, total


if __name__ == "__main__":
    st, igv, tot = construir()
    print(f"Factura generada: {SALIDA}")
    print(f"Subtotal={st:.2f}  IGV={igv:.2f}  Total={tot:.2f}")
