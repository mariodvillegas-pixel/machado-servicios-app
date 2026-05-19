import re
import pdfplumber


def parse_num(s):
    """Convierte número colombiano a float. Ej: '151.000,14' → 151000.14"""
    if not s:
        return 0.0
    s = str(s).strip().replace(" ", "")
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def extract_from_pdf(pdf_file):
    """Lee el PDF del recibo EPM y extrae todos los valores del resumen de facturación."""
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"

    data = {
        "periodo": "",
        "mes": "",
        "año": 0,
        "energia_kwh": 0.0,
        "energia_val": 0.0,
        "gas_m3": 0.0,
        "gas_val": 0.0,
        "agua_m3": 0.0,
        "agua_val": 0.0,
        "alc_val": 0.0,
        "acuerdo_val": 0.0,
        "otras_val": 0.0,
    }

    # Período: "del 13 mar al 14 abr"
    m = re.search(r"del\s+(\d+\s+\w+\s+al\s+\d+\s+\w+)", text, re.IGNORECASE)
    if m:
        data["periodo"] = m.group(1).upper().strip()

    # Mes de liquidación: "Resumen de facturación mayo de 2026"
    m = re.search(r"Resumen de facturaci[oó]n\s+(\w+)\s+de\s+(\d{4})", text, re.IGNORECASE)
    if m:
        data["mes"] = m.group(1).upper()
        data["año"] = int(m.group(2))

    # Acueducto: "Acueducto 38 m3 $ 151.000,14"
    m = re.search(r"Acueducto\s+([\d,\.]+)\s*m3\s+\$\s*([\d\.,]+)", text, re.IGNORECASE)
    if m:
        data["agua_m3"] = parse_num(m.group(1))
        data["agua_val"] = parse_num(m.group(2))

    # Alcantarillado: "Alcantarillado 38 m3 $ 119.724,26"
    m = re.search(r"Alcantarillado\s+([\d,\.]+)\s*m3\s+\$\s*([\d\.,]+)", text, re.IGNORECASE)
    if m:
        data["alc_val"] = parse_num(m.group(2))

    # Energía: "Energía 57 kwh $ 23.107,63"
    m = re.search(r"Energ[ií]a\s+([\d,\.]+)\s*kwh\s+\$\s*([\d\.,]+)", text, re.IGNORECASE)
    if m:
        data["energia_kwh"] = parse_num(m.group(1))
        data["energia_val"] = parse_num(m.group(2))

    # Gas: "Gas 5,9 m3 $ 8.825,07"
    m = re.search(r"Gas\s+([\d,\.]+)\s*m3\s+\$\s*([\d\.,]+)", text, re.IGNORECASE)
    if m:
        data["gas_m3"] = parse_num(m.group(1))
        data["gas_val"] = parse_num(m.group(2))

    # Otras entidades: "Otras entidades $ 44.017,40"
    m = re.search(r"Otras entidades\s+\$\s*([\d\.,]+)", text, re.IGNORECASE)
    if m:
        data["otras_val"] = parse_num(m.group(1))

    # Acuerdos de pago: "Acuerdos de pago $ 3.932,31"
    m = re.search(r"Acuerdos de pago\s+\$\s*([\d\.,]+)", text, re.IGNORECASE)
    if m:
        data["acuerdo_val"] = parse_num(m.group(1))

    return data
