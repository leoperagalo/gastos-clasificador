
import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime

st.set_page_config(page_title="Clasificador de Gastos V3", layout="centered")

st.title("📊 Clasificador de Gastos por Mes y Categoría (Multi-PDF + Auto Año)")
st.write("Sube uno o más estados de cuenta en PDF. Agrupamos por categoría y por mes, detectando el año automáticamente.")

uploaded_files = st.file_uploader(
    "Carga uno o más estados de cuenta bancarios (PDF)",
    type="pdf",
    accept_multiple_files=True
)

def clasificar_gasto(descripcion):
    desc = descripcion.lower()
    if "amazon" in desc:
        return "Amazon"
    elif "uber eats" in desc:
        return "Uber Eats"
    elif any(keyword in desc for keyword in ["spotify", "netflix", "hbo", "prime video"]):
        return "Suscripciones Stream"
    elif any(keyword in desc for keyword in ["bp orquidea", "pemex", "gasolineras"]):
        return "Gasolineras"
    elif "oxxo" in desc or "7-eleven" in desc:
        return "Conveniencia"
    elif "restaurante" in desc or "toks" in desc:
        return "Restaurantes"
    elif any(keyword in desc for keyword in ["barraca valenciana", "valenciana"]):
        return "Barraca Valenciana"
    else:
        return "Otros"

def detectar_anio(texto):
    match = re.search(r"(20[2-3][0-9])", texto)
    if match:
        return int(match.group(1))
    return datetime.now().year

def convertir_fecha(fecha_raw, anio):
    meses = {
        "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
        "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
        "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
    }

    match = re.match(r"(\d{1,2}) de ([A-Za-záéíóúñÑ]+)", fecha_raw.lower())
    if match:
        dia, mes_texto = match.groups()
        mes_num = meses.get(mes_texto, "01")
        return f"{int(dia):02d}/{mes_num}/{anio}"
    else:
        return None

def procesar_pdfs(files):
    datos = []

    for file in files:
        with pdfplumber.open(file) as pdf:
            texto_total = ""
            for page in pdf.pages:
                texto_total += page.extract_text()

        anio_detectado = detectar_anio(texto_total)

        lineas = texto_total.split('\n')
        for linea in lineas:
            partes = linea.strip().split()
            if len(partes) >= 3:
                fecha = partes[0]
                monto_str = partes[-1].replace("$", "").replace(",", "")
                try:
                    monto = float(monto_str)
                    descripcion = " ".join(partes[1:-1])
                    fecha_convertida = convertir_fecha(fecha, anio_detectado)
                    datos.append({
                        "Fecha": fecha,
                        "FechaConvertida": fecha_convertida,
                        "Descripción": descripcion,
                        "Monto": monto
                    })
                except ValueError:
                    continue

    df = pd.DataFrame(datos)
    df["Categoría"] = df["Descripción"].apply(clasificar_gasto)
    df["Mes"] = pd.to_datetime(df["FechaConvertida"], format="%d/%m/%Y", errors='coerce').dt.to_period("M")
    return df

if uploaded_files:
    try:
        df_gastos = procesar_pdfs(uploaded_files)

        st.success("✅ Archivos procesados correctamente.")
        st.dataframe(df_gastos)

        st.subheader("📌 Resumen por Categoría")
        resumen_cat = df_gastos.groupby("Categoría")["Monto"].sum().reset_index()
        st.bar_chart(resumen_cat.set_index("Categoría"))

        st.subheader("📅 Resumen por Mes")
        resumen_mes = df_gastos.groupby("Mes")["Monto"].sum().reset_index()
        st.bar_chart(resumen_mes.set_index("Mes"))

        st.subheader("📊 Tabla por Mes y Categoría")
        pivot = pd.pivot_table(df_gastos, values="Monto", index="Mes", columns="Categoría", aggfunc="sum", fill_value=0)
        st.dataframe(pivot)

        st.subheader("⬇️ Descargar Datos")
        exportar = st.button("Descargar como Excel")
        if exportar:
            excel_file = "gastos_categorizados_v3.xlsx"
            with pd.ExcelWriter(excel_file) as writer:
                df_gastos.to_excel(writer, sheet_name="Transacciones", index=False)
                resumen_cat.to_excel(writer, sheet_name="Por Categoría", index=False)
                resumen_mes.to_excel(writer, sheet_name="Por Mes", index=False)
                pivot.to_excel(writer, sheet_name="Mes-Categoría")
            with open(excel_file, "rb") as f:
                st.download_button(
                    label="📥 Descargar Excel",
                    data=f,
                    file_name=excel_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"❌ Error al procesar los archivos: {e}")
