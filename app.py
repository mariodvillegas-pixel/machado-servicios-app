import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from utils.pdf_parser import extract_from_pdf
from utils.sheets import SheetsDB
from utils.liquidacion import calcular, generar_tabla, fmt_peso

# ── Configuración de página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Machado Servicios",
    page_icon="🏢",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    /* Botones ocupan todo el ancho en móvil */
    .stButton > button { width: 100%; }
    /* Reducir padding en móvil */
    .block-container { padding: 1rem 1rem 2rem; }
    /* Caja de liquidación */
    .caja-liqui {
        background: #0f172a;
        color: #e2e8f0;
        font-family: 'Courier New', monospace;
        font-size: 0.82rem;
        padding: 1.2rem;
        border-radius: 10px;
        white-space: pre;
        overflow-x: auto;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)


# ── Conexión a Google Sheets ─────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_db(_v=6):  # incrementar para forzar nuevo caché
    return SheetsDB(
        dict(st.secrets["gcp_service_account"]),
        st.secrets["sheet_id"],
    )

try:
    db = get_db()
    db_ok = True
except Exception as e:
    db_ok = False
    db_error = str(e)


# ── Navegación ───────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🏢 Edificio Machado")
pagina = st.sidebar.radio(
    "Ir a",
    ["📄 Nuevo Recibo", "📊 Historial", "👥 Residentes"],
    label_visibility="collapsed",
)

if not db_ok:
    st.error(f"⚠️ Sin conexión a Google Sheets. Verifica los secrets.\n\n`{db_error}`")
    st.stop()


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA: NUEVO RECIBO
# ════════════════════════════════════════════════════════════════════════════
if pagina == "📄 Nuevo Recibo":
    st.title("📄 Ingresar Recibo")
    st.caption("Sube el PDF del recibo EPM y la app extrae todo automáticamente.")

    pdf_file = st.file_uploader("Recibo EPM (PDF)", type="pdf", label_visibility="collapsed")

    if not pdf_file:
        st.info("⬆️ Sube el recibo PDF para comenzar.")
        st.stop()

    # ── Extracción del PDF ──────────────────────────────────────────────────
    with st.spinner("Leyendo el PDF..."):
        try:
            data = extract_from_pdf(pdf_file)
        except Exception as e:
            st.error(f"Error al leer el PDF: {e}")
            st.stop()

    if not data.get("mes"):
        st.error("No se encontró el resumen de facturación en el PDF. ¿Es un recibo EPM?")
        st.stop()

    st.success(f"✅ Recibo leído: **{data['mes']} {data['año']}** — Período: {data['periodo']}")

    # ── Datos extraídos ─────────────────────────────────────────────────────
    st.subheader("Datos del recibo")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("⚡ Energía",        f"{data['energia_kwh']} kWh",  fmt_peso(data['energia_val']))
        st.metric("🔥 Gas",            f"{data['gas_m3']} m³",        fmt_peso(data['gas_val']))
        st.metric("💧 Agua",           f"{data['agua_m3']} m³",       fmt_peso(data['agua_val']))
    with col2:
        st.metric("🚿 Alcantarillado", "",                             fmt_peso(data['alc_val']))
        st.metric("🏢 Otras entidades","",                             fmt_peso(data['otras_val']))
        if data['acuerdo_val']:
            st.metric("📑 Acuerdo pago", "",                           fmt_peso(data['acuerdo_val']))

    total_factura = (data['energia_val'] + data['gas_val'] + data['agua_val'] +
                     data['alc_val'] + data['otras_val'] + data['acuerdo_val'])
    st.metric("**TOTAL FACTURA**", fmt_peso(total_factura))

    st.divider()

    # ── Residentes ──────────────────────────────────────────────────────────
    st.subheader("👥 Residentes por piso")
    p1_def, p2_def, p3_def = db.get_residentes_ultimo()

    col1, col2, col3 = st.columns(3)
    with col1:
        pers_p1 = st.number_input("Piso 1", min_value=1, max_value=20, value=p1_def, key="p1")
    with col2:
        pers_p2 = st.number_input("Piso 2", min_value=1, max_value=20, value=p2_def, key="p2")
    with col3:
        pers_p3 = st.number_input("Piso 3", min_value=1, max_value=20, value=p3_def, key="p3")

    st.divider()

    # ── Guardar y calcular ──────────────────────────────────────────────────
    if st.button("💾 Guardar y generar liquidación", type="primary"):

        res = calcular(data, pers_p1, pers_p2, pers_p3)

        # Guardar en Google Sheets
        try:
            db.save_mes({
                **data,
                "pers_p1": pers_p1, "pers_p2": pers_p2, "pers_p3": pers_p3,
                "total_p1": res["total_p1"],
                "total_p2": res["total_p2"],
                "total_p3": res["total_p3"],
            })
            get_db.clear()  # Invalidar caché para que historial muestre datos frescos
            st.success("✅ Guardado correctamente.")
        except Exception as e:
            st.warning(f"No se pudo guardar en Sheets: {e}")

        # Mostrar tabla
        tabla = generar_tabla(data, res)
        st.subheader("📋 Liquidación para residentes")
        st.text_area(
            "Copia este texto y compártelo por WhatsApp",
            value=tabla,
            height=480,
            label_visibility="visible",
        )

        # Resumen de totales visual
        st.subheader("Resumen")
        c1, c2, c3 = st.columns(3)
        c1.metric("🏠 Piso 1", fmt_peso(res["total_p1"]))
        c2.metric("🏠 Piso 2", fmt_peso(res["total_p2"]), f"↩️ reembolsa al P1")
        c3.metric("🏠 Piso 3", fmt_peso(res["total_p3"]), f"↩️ reembolsa al P1")


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA: HISTORIAL
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "📊 Historial":
    st.title("📊 Historial de Consumos")

    df = db.get_all()

    if df.empty:
        st.info("Aún no hay datos. Ingresa el primer recibo en '📄 Nuevo Recibo'.")
        st.stop()

    df["etiqueta"] = df["mes"].astype(str) + " " + df["año"].astype(str)

    # ── Último mes ──────────────────────────────────────────────────────────
    ultimo = df.iloc[-1]
    st.subheader(f"Último mes registrado: {ultimo['etiqueta']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("🏠 Piso 1", fmt_peso(ultimo["total_p1"]))
    c2.metric("🏠 Piso 2", fmt_peso(ultimo["total_p2"]))
    c3.metric("🏠 Piso 3", fmt_peso(ultimo["total_p3"]))

    st.divider()

    # ── Gráfica: totales por piso ────────────────────────────────────────────
    st.subheader("💰 Total a pagar por piso")
    fig = go.Figure()
    colores = ["#2563EB", "#16a34a", "#dc2626"]
    for piso, col, color in zip(["Piso 1", "Piso 2", "Piso 3"],
                                 ["total_p1", "total_p2", "total_p3"], colores):
        fig.add_trace(go.Bar(name=piso, x=df["etiqueta"], y=df[col],
                             marker_color=color))
    fig.update_layout(barmode="group", height=300,
                      margin=dict(l=0, r=0, t=10, b=0),
                      legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)

    # ── Gráficas de consumo ──────────────────────────────────────────────────
    st.subheader("⚡ Energía (kWh)")
    fig2 = px.line(df, x="etiqueta", y="energia_kwh", markers=True, height=250,
                   color_discrete_sequence=["#f59e0b"])
    fig2.update_layout(margin=dict(l=0, r=0, t=5, b=0),
                       xaxis_title="", yaxis_title="kWh")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("💧 Agua (m³)")
    fig3 = px.line(df, x="etiqueta", y="agua_m3", markers=True, height=250,
                   color_discrete_sequence=["#0ea5e9"])
    fig3.update_layout(margin=dict(l=0, r=0, t=5, b=0),
                       xaxis_title="", yaxis_title="m³")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("🔥 Gas (m³)")
    fig4 = px.line(df, x="etiqueta", y="gas_m3", markers=True, height=250,
                   color_discrete_sequence=["#f97316"])
    fig4.update_layout(margin=dict(l=0, r=0, t=5, b=0),
                       xaxis_title="", yaxis_title="m³")
    st.plotly_chart(fig4, use_container_width=True)

    st.divider()

    # ── Tabla completa ───────────────────────────────────────────────────────
    st.subheader("📋 Tabla completa")
    cols_tabla = {
        "etiqueta":    "Mes",
        "periodo":     "Período",
        "energia_kwh": "Energía kWh",
        "gas_m3":      "Gas m³",
        "agua_m3":     "Agua m³",
        "total_p1":    "Piso 1 $",
        "total_p2":    "Piso 2 $",
        "total_p3":    "Piso 3 $",
    }
    st.dataframe(
        df[[c for c in cols_tabla if c in df.columns]].rename(columns=cols_tabla),
        use_container_width=True,
        hide_index=True,
    )


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA: RESIDENTES
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "👥 Residentes":
    st.title("👥 Residentes actuales")
    st.caption("Número de personas por piso según el último mes registrado.")

    p1, p2, p3 = db.get_residentes_ultimo()
    c1, c2, c3 = st.columns(3)
    c1.metric("🏠 Piso 1", f"{p1} personas")
    c2.metric("🏠 Piso 2", f"{p2} personas")
    c3.metric("🏠 Piso 3", f"{p3} personas")

    st.info("Para actualizar, cambia el número de personas al ingresar el próximo recibo.")
