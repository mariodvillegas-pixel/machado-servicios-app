def calcular(data: dict, pers_p1: int, pers_p2: int, pers_p3: int) -> dict:
    """Distribuye agua y alcantarillado proporcionalmente y calcula totales por piso."""
    total_pers = max(pers_p1 + pers_p2 + pers_p3, 1)

    agua_val = float(data.get("agua_val", 0))
    alc_val  = float(data.get("alc_val", 0))
    agua_m3  = float(data.get("agua_m3", 0))

    def share(total, pers):
        return round(total / total_pers * pers, 2)

    res = {
        "agua_p1": share(agua_val, pers_p1),
        "alc_p1":  share(alc_val,  pers_p1),
        "m3_p1":   share(agua_m3,  pers_p1),
        "agua_p2": share(agua_val, pers_p2),
        "alc_p2":  share(alc_val,  pers_p2),
        "m3_p2":   share(agua_m3,  pers_p2),
        "agua_p3": share(agua_val, pers_p3),
        "alc_p3":  share(alc_val,  pers_p3),
        "m3_p3":   share(agua_m3,  pers_p3),
    }

    en_val  = float(data.get("energia_val",  0))
    gas_val = float(data.get("gas_val",      0))
    acu_val = float(data.get("acuerdo_val",  0))
    otr_val = float(data.get("otras_val",    0))

    res["total_p1"] = round(en_val + gas_val + acu_val + otr_val + res["agua_p1"] + res["alc_p1"], 2)
    res["total_p2"] = round(res["agua_p2"] + res["alc_p2"], 2)
    res["total_p3"] = round(res["agua_p3"] + res["alc_p3"], 2)
    res["total_ed"] = round(res["total_p1"] + res["total_p2"] + res["total_p3"], 2)
    return res


def fmt_peso(v) -> str:
    """$181.404  (miles con punto, sin decimales)"""
    return f"${float(v):,.0f}".replace(",", ".")


def fmt_m3(v) -> str:
    """14,25  (decimal con coma — formato colombiano)"""
    return str(round(float(v), 2)).replace(".", ",")


def generar_tabla(data: dict, res: dict) -> str:
    """Genera el texto de liquidación optimizado para WhatsApp (fuente proporcional)."""
    mes = data.get("mes", "")
    año = data.get("año", "")
    per = data.get("periodo", "")
    SEP = "━" * 32

    en_val  = float(data.get("energia_val", 0))
    gas_val = float(data.get("gas_val", 0))
    acu_val = float(data.get("acuerdo_val", 0))
    otr_val = float(data.get("otras_val", 0))

    def bloque_piso1():
        lines = ["🏠 *PISO 1*", ""]
        if en_val:
            lines.append(f"⚡ Energía ({fmt_m3(data['energia_kwh'])} kWh): *{fmt_peso(en_val)}*")
        if gas_val:
            lines.append(f"🔥 Gas ({fmt_m3(data['gas_m3'])} m³): *{fmt_peso(gas_val)}*")
        lines.append(f"💧 Agua ({fmt_m3(res['m3_p1'])} m³): *{fmt_peso(res['agua_p1'])}*")
        lines.append(f"🚿 Alcantarillado: *{fmt_peso(res['alc_p1'])}*")
        if acu_val:
            lines.append(f"📑 Acuerdo de pago: *{fmt_peso(acu_val)}*")
        if otr_val:
            lines.append(f"🏢 Otras entidades: *{fmt_peso(otr_val)}*")
        lines += ["", f"💰 *TOTAL: {fmt_peso(res['total_p1'])}*"]
        return lines

    def bloque_piso(num, agua, alc, m3, total):
        return [
            f"🏠 *PISO {num}*",
            "",
            f"💧 Agua ({fmt_m3(m3)} m³): *{fmt_peso(agua)}*",
            f"🚿 Alcantarillado: *{fmt_peso(alc)}*",
            "",
            f"💰 *TOTAL: {fmt_peso(total)}*",
            f"↩️ Reembolsar al Piso 1: *{fmt_peso(total)}*",
        ]

    lines = [
        f"📋 *LIQUIDACIÓN SERVICIOS — {mes} {año}*",
        f"📅 Período: {per}",
        SEP,
        "",
        *bloque_piso1(),
        "",
        SEP,
        "",
        *bloque_piso(2, res["agua_p2"], res["alc_p2"], res["m3_p2"], res["total_p2"]),
        "",
        SEP,
        "",
        *bloque_piso(3, res["agua_p3"], res["alc_p3"], res["m3_p3"], res["total_p3"]),
        "",
        SEP,
        f"🏗️ *TOTAL EDIFICIO: {fmt_peso(res['total_ed'])}*",
    ]

    return "\n".join(lines)


def generar_pdf(data: dict, res: dict) -> bytes:
    """Genera un PDF de la liquidación y lo retorna como bytes."""
    from fpdf import FPDF

    mes = data.get("mes", "")
    año = data.get("año", "")
    per = data.get("periodo", "")

    en_val  = float(data.get("energia_val", 0))
    gas_val = float(data.get("gas_val", 0))
    acu_val = float(data.get("acuerdo_val", 0))
    otr_val = float(data.get("otras_val", 0))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    # ── Encabezado ────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"LIQUIDACION DE SERVICIOS", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, f"{mes} {año}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Periodo: {per}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_draw_color(100, 100, 100)
    pdf.set_line_width(0.5)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)

    # ── Helper para filas de la tabla ─────────────────────────────────────────
    def fila(label, valor, negrita=False):
        pdf.set_font("Helvetica", "B" if negrita else "", 10)
        pdf.cell(120, 7, label, new_x="RIGHT", new_y="LAST")
        pdf.set_font("Helvetica", "B" if negrita else "", 10)
        pdf.cell(50, 7, valor, align="R", new_x="LMARGIN", new_y="NEXT")

    def titulo_piso(nombre):
        pdf.ln(2)
        pdf.set_fill_color(30, 58, 138)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, f"  {nombre}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    def linea_total(total):
        pdf.set_draw_color(30, 58, 138)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(30, 58, 138)
        pdf.cell(120, 8, "TOTAL A PAGAR", new_x="RIGHT", new_y="LAST")
        pdf.cell(50, 8, fmt_peso(total), align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

    # ── PISO 1 ────────────────────────────────────────────────────────────────
    titulo_piso("PISO 1")
    if en_val:
        fila(f"Energia ({fmt_m3(data['energia_kwh'])} kWh)", fmt_peso(en_val))
    if gas_val:
        fila(f"Gas ({fmt_m3(data['gas_m3'])} m3)", fmt_peso(gas_val))
    fila(f"Agua ({fmt_m3(res['m3_p1'])} m3)", fmt_peso(res["agua_p1"]))
    fila("Alcantarillado", fmt_peso(res["alc_p1"]))
    if acu_val:
        fila("Acuerdo de pago", fmt_peso(acu_val))
    if otr_val:
        fila("Otras entidades", fmt_peso(otr_val))
    linea_total(res["total_p1"])

    # ── PISO 2 ────────────────────────────────────────────────────────────────
    titulo_piso("PISO 2")
    fila(f"Agua ({fmt_m3(res['m3_p2'])} m3)", fmt_peso(res["agua_p2"]))
    fila("Alcantarillado", fmt_peso(res["alc_p2"]))
    linea_total(res["total_p2"])
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, f"  Reembolsar al Piso 1: {fmt_peso(res['total_p2'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    # ── PISO 3 ────────────────────────────────────────────────────────────────
    titulo_piso("PISO 3")
    fila(f"Agua ({fmt_m3(res['m3_p3'])} m3)", fmt_peso(res["agua_p3"]))
    fila("Alcantarillado", fmt_peso(res["alc_p3"]))
    linea_total(res["total_p3"])
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, f"  Reembolsar al Piso 1: {fmt_peso(res['total_p3'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # ── Total edificio ────────────────────────────────────────────────────────
    pdf.set_draw_color(30, 58, 138)
    pdf.set_line_width(1)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(120, 8, "TOTAL EDIFICIO", new_x="RIGHT", new_y="LAST")
    pdf.cell(50, 8, fmt_peso(res["total_ed"]), align="R", new_x="LMARGIN", new_y="NEXT")

    # ── Pie de página ─────────────────────────────────────────────────────────
    pdf.set_y(-20)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, f"Edificio Machado - Generado automaticamente", align="C")

    return bytes(pdf.output())
