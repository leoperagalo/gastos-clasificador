# -*- coding: utf-8 -*-
import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime
import io

st.set_page_config(page_title="Clasificador de Gastos V6", layout="centered")

st.title("📊 Clasificador de Gastos por Mes y Categoría --- V6")
st.write("Sube **uno o más** estados de cuenta en PDF (BBVA, AMEX). Unimos todo, detectamos año, generamos Mes (YYYY-MM), y agrupamos por **Categoría** y **Mes**.")
st.warning("**ACTUALIZACIÓN:** Ahora los resúmenes y gráficos ocultan automáticamente la categoría 'Pagos y Abonos' y otras que no son gastos directos.")
st.warning("️️⚠️ **Advertencia de Privacidad:** No subas documentos con información sensible si no te sientes cómodo. Te recomiendo anonimizar NOMBRES y NUMERO DE CUENTA con un editor de PDF antes de usar la herramienta. Los archivos se procesan en un servidor externo y se eliminan después de cada sesión.")

uploaded_files = st.file_uploader(
    "Carga uno o más estados de cuenta bancarios (PDF), tanto de BBVA Como de AMEX",
    type="pdf",
    accept_multiple_files=True
)


def detect_year(text: str):
    """Busca un año de 4 dígitos razonable (2000-2099) en el PDF."""
    years = re.findall(r"(20\d{2})", text)
    if years:
        return max(set(years), key=years.count)
    return str(datetime.now().year)

def parse_amount(raw: str):
    """Convierte importes con formatos MX: separador miles , y decimal . o viceversa."""
    s = raw.strip()
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    s = s.replace("$", "").replace(" ", "")
    if re.search(r"\d+\.\d{3},\d{2}$", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        val = float(s)
        return -val if neg else val
    except:
        return None

def extract_transactions_from_pdf(file):
    """
    Extrae transacciones de un PDF (diseñado para BBVA y AMEX).
    Une descripciones de múltiples líneas (ej. RFC en AMEX) y maneja
    diferentes formatos de fecha y monto.
    """
    text_from_pdf = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text_from_pdf += (page.extract_text() or "") + "\n"
    except Exception as e:
        st.error(f"Error al leer el PDF {getattr(file, 'name', 'PDF')}: {e}")
        return pd.DataFrame()

    if st.sidebar.checkbox(f"🔍 Ver texto extraído de {getattr(file, 'name', 'PDF')}", value=False):
        st.text_area("Texto crudo extraído", text_from_pdf[:25000], height=300)

    # --- 1. Pre-procesamiento: Unir líneas de descripción (para AMEX) ---
    raw_lines = text_from_pdf.splitlines()
    processed_lines = []
    for i, line in enumerate(raw_lines):
        line_lower = line.lower().strip()
        if (line_lower.startswith("rfc") or line_lower.startswith("ref")) and processed_lines:
            processed_lines[-1] += " | " + line.strip()
        else:
            processed_lines.append(line)

    # --- 2. Inferencia de Año y Mapeo de Meses ---
    year_hint = detect_year(text_from_pdf)
    meses_map = {
        "ene": 1, "enero": 1, "feb": 2, "febrero": 2, "mar": 3, "marzo": 3,
        "abr": 4, "abril": 4, "may": 5, "mayo": 5, "jun": 6, "junio": 6,
        "jul": 7, "julio": 7, "ago": 8, "agosto": 8, "sep": 9, "sept": 9,
        "set": 9, "oct": 10, "octubre": 10, "nov": 11, "noviembre": 11,
        "dic": 12, "diciembre": 12,
    }

    # --- 3. Patrones de Expresiones Regulares ---
    date_pattern_str = r"\b(?P<d>\d{1,2})[/\s\.\-](?:de)?\s*(?P<m>(?:ene|feb|mar|abr|may|jun|jul|ago|sep|set|oct|nov|dic)[a-z]*|\d{1,2})[/\s\.\-]*(?P<y>\d{2,4})?\b"
    date_pat = re.compile(date_pattern_str, re.IGNORECASE)
    amount_pat = re.compile(r"([+-]?\s*\$?\s*\(?\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*\)?)\s*(CR)?\s*$", re.IGNORECASE)

    # --- 4. Extracción de Transacciones ---
    transactions = []
    for line in processed_lines:
        line_clean = re.sub(r'\s{2,}', ' ', line).strip()
        amount_match = amount_pat.search(line_clean)
        if not amount_match:
            continue
        amount_str = amount_match.group(1)
        is_credit = amount_match.group(2)
        amount = parse_amount(amount_str)
        if amount is None:
            continue
        if is_credit or any(w in line_clean.lower() for w in ["abono", "pago", "payment"]):
             amount = -abs(amount)
        date_match = date_pat.search(line_clean)
        if not date_match:
            continue
        try:
            day = int(date_match.group('d'))
            month_str = date_match.group('m').lower()
            month = int(month_str) if month_str.isdigit() else meses_map.get(month_str[:3])
            if not month: continue
            year_str = date_match.group('y')
            if year_str and len(year_str) == 2:
                year = int(year_str) + 2000
            elif year_str:
                year = int(year_str)
            else:
                year = int(year_hint)
            fecha = datetime(year, month, day)
        except (ValueError, TypeError):
            continue
        desc_part = line_clean[:amount_match.start()]
        desc_part = date_pat.sub("", desc_part, count=1).strip(" -–—|")
        transactions.append([fecha.strftime("%d/%m/%Y"), desc_part, amount])
    return pd.DataFrame(transactions, columns=["Fecha", "Descripción", "Monto"])

def guess_category(descripcion: str):
    desc = descripcion.lower()
    if "amazon" in desc:
        return "Amazon"
    elif "uber eats" in desc:
        return "Uber Eats"
    elif any(keyword in desc for keyword in ["spotify", "netflix", "hbo", "prime video", "mubi", "f1", "youtubepremium"]):
        return "Suscripciones Stream"
    elif any(keyword in desc for keyword in ["chatgpt", "chat-gpt", "tactiq.io", "gmail", "msft subscription", "microsoft", "icloud", "apple.com"]):
        return "Suscripciones Tools"
    elif any(keyword in desc for keyword in ["bp orquidea", "pemex", "gasolina", "g500", "shell", "bp", "hidrosina", "oxxo gas", "super serv echecaray"]):
        return "Gasolina"
    elif any(keyword in desc for keyword in ["oxxo", "7 eleven", "7-eleven"]):
        return "Conveniencia"
    elif "metlife" in desc or "seguro" in desc:
        return "Seguros"
    elif "melate" in desc or "tulotero" in desc:
        return "Melate"
    elif "moda" in desc or "sfera satelite" in desc:
        return "Moda"
    elif any(keyword in desc for keyword in ["intereses efi *", "efectivo inmediato 36"]):
        return "Deuda TDC"
    elif any(keyword in desc for keyword in ["toks", "rest macaroni satelite", "islaa", "maison kayser", "restaurante", "rest", "yoyocafe", "matisse", "launica"]):
        return "Restaurantes"
    elif any(keyword in desc for keyword in ["cinepolis", "cinemex", "dulceria"]):
        return "Cines"
    elif any(keyword in desc for keyword in ["wal-mart", "wal mart", "la comer", "soriana", "chedraui", "wm express", "cornershop"]):
        return "Supermercado"
    elif any(keyword in desc for keyword in ["liverpool", "sears"]):
        return "Tiendas Departamentales"
    elif any(keyword in desc for keyword in ["wsj", "the new york times"]):
        return "News"
    elif any(keyword in desc for keyword in ["barraca", "valenciana", "el palacio hierro sate", "el palacio hierro", "palaciodehierro"]):
        return "Palacio de Hierro"
    elif any(keyword in desc for keyword in ["home depot", "the home depot", "sodimac"]):
        return "Hogar y Ferretería"
    elif any(keyword in desc for keyword in ["aeromexico", "trip", "vivaaerobus", "volaris", "interjet", "aerolinea", "hotel", "hyatt", "marriott", "airbnb", "expedia", "booking"]):
        return "Viajes"
    elif any(keyword in desc for keyword in ["gandhi", "porrua", "libreria", "lumen", "office depot", "office max"]):
        return "Libros y Papelería"
    elif any(keyword in desc for keyword in ["farmacia", "farmacias", "f del ahorro", "farm guad", "san pablo", "benavides"]):
        return "Farmacias"
    elif any(keyword in desc for keyword in ["pase", "capufe", "tag", "aeropuerto", "estacionamiento", "parquimetro", "parco"]):
        return "Transporte y Peajes"
    elif any(keyword in desc for keyword in ["c.f.e.", "cfe", "sacmex", "tesoreria", "gdf sria"]):
        return "Gobierno"
    elif any(keyword in desc for keyword in ["naturgy", "telmex", "izzi", "totalplay", "AT&T", "ATT", "Telcel"]):
        return "Servicios"
    elif any(keyword in desc for keyword in ["pago", "pago recibido", "abono", "deposito", "transferencia", "reembolso", "devolucion"]):
        return "Pagos y Abonos"
    else:
        return "Otros"

if uploaded_files:
    frames = []
    for f in uploaded_files:
        df_file = extract_transactions_from_pdf(f)
        if not df_file.empty:
            frames.append(df_file.assign(_archivo=f.name))

    if not frames:
        st.warning("No se encontraron transacciones en los PDFs subidos.")
        st.stop()

    df_gastos = pd.concat(frames, ignore_index=True)

    df_gastos["Fecha"] = pd.to_datetime(df_gastos["Fecha"], dayfirst=True, errors="coerce")
    df_gastos = df_gastos.dropna(subset=["Fecha"])
    df_gastos["Mes"] = df_gastos["Fecha"].dt.strftime("%Y-%m")

    if "Categoría" not in df_gastos.columns:
        df_gastos["Categoría"] = df_gastos["Descripción"].apply(guess_category)

    st.subheader("🧾 Transacciones unificadas")
    st.dataframe(df_gastos[["Fecha", "Mes", "Descripción", "Categoría", "Monto", "_archivo"]])

    # --- FILTRO PARA MOSTRAR SOLO GASTOS EN RESÚMENES ---
    df_solo_gastos = df_gastos[df_gastos['Monto'] > 0].copy()
    
    # --- FILTRO ADICIONAL PARA OCULTAR CATEGORÍAS EN RESÚMENES ---
    categorias_a_excluir = ['Pagos y Abonos']
    df_resumen_final = df_solo_gastos[~df_solo_gastos['Categoría'].isin(categorias_a_excluir)]

    # Resúmenes
    st.subheader("📌 Resumen por Categoría")
    resumen_cat = df_resumen_final.groupby("Categoría", as_index=False)["Monto"].sum().sort_values("Monto", ascending=False)
    st.bar_chart(resumen_cat.set_index("Categoría"))

    st.subheader("📊 Tabla por Mes y Categoría")
    pivot = pd.pivot_table(
        df_resumen_final,
        values="Monto",
        index="Mes",
        columns="Categoría",
        aggfunc="sum",
        fill_value=0
    )
    st.dataframe(pivot.sort_index(key=lambda idx: pd.to_datetime(idx + "-01", errors="coerce")))

    # Exportar a Excel
    st.subheader("⬇️ Descargar Datos")
    excel_bytes = io.BytesIO()
    with pd.ExcelWriter(excel_bytes, engine="xlsxwriter") as writer:
        df_gastos.to_excel(writer, sheet_name="Transacciones", index=False)
        resumen_cat.to_excel(writer, sheet_name="Por Categoría", index=False)
        pivot.to_excel(writer, sheet_name="Mes-Categoría")
    st.download_button(
        label="📥 Descargar Excel",
        data=excel_bytes.getvalue(),
        file_name="gastos_resumen.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("💡 Sube uno o más PDFs para empezar.")
