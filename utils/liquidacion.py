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

    # Piso 1 concentra energía, gas, acuerdo y otras entidades
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
    """Genera el texto de liquidación listo para compartir por WhatsApp."""
    mes  = data.get("mes", "")
    año  = data.get("año", "")
    per  = data.get("periodo", "")
    SEP  = "━" * 42
    sep  = "─" * 42

    def linea_agua(label, m3, val):
        return f"  {label:<20} {fmt_m3(m3):>6} m³   {fmt_peso(val):>12}"

    def linea_serv(label, detalle, val):
        return f"  {label:<20} {detalle:>9}   {fmt_peso(val):>12}"

    lines = [
        f"📋 *LIQUIDACIÓN SERVICIOS — {mes} {año}*",
        f"   Período: {per}",
        SEP,
        "",
        "🏠 *PISO 1*",
    ]

    en_val  = float(data.get("energia_val", 0))
    gas_val = float(data.get("gas_val", 0))
    acu_val = float(data.get("acuerdo_val", 0))
    otr_val = float(data.get("otras_val", 0))

    if en_val:
        lines.append(linea_serv("⚡ Energía", f"{fmt_m3(data['energia_kwh'])} kWh", en_val))
    if gas_val:
        lines.append(linea_serv("🔥 Gas", f"{fmt_m3(data['gas_m3'])} m³", gas_val))

    lines.append(linea_agua("💧 Agua", res["m3_p1"], res["agua_p1"]))
    lines.append(linea_agua("🚿 Alcantarillado", res["m3_p1"], res["alc_p1"]))

    if acu_val:
        lines.append(linea_serv("📑 Acuerdo de pago", "", acu_val))
    if otr_val:
        lines.append(linea_serv("🏢 Otras entidades", "", otr_val))

    lines += [
        f"  {sep}",
        f"  💰 *TOTAL A PAGAR      {fmt_peso(res['total_p1']):>12}*",
        "",
        SEP,
        "",
        "🏠 *PISO 2*",
        linea_agua("💧 Agua", res["m3_p2"], res["agua_p2"]),
        linea_agua("🚿 Alcantarillado", res["m3_p2"], res["alc_p2"]),
        f"  {sep}",
        f"  💰 *TOTAL A PAGAR      {fmt_peso(res['total_p2']):>12}*",
        f"  ↩️  Reembolsar al Piso 1: {fmt_peso(res['total_p2'])}",
        "",
        SEP,
        "",
        "🏠 *PISO 3*",
        linea_agua("💧 Agua", res["m3_p3"], res["agua_p3"]),
        linea_agua("🚿 Alcantarillado", res["m3_p3"], res["alc_p3"]),
        f"  {sep}",
        f"  💰 *TOTAL A PAGAR      {fmt_peso(res['total_p3']):>12}*",
        f"  ↩️  Reembolsar al Piso 1: {fmt_peso(res['total_p3'])}",
        "",
        SEP,
        f"  🏗️  TOTAL EDIFICIO     {fmt_peso(res['total_ed']):>12}",
    ]

    return "\n".join(lines)
