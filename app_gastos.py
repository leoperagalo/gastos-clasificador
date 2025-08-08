import streamlit as st
import pdfplumber
import pandas as pd
import io

st.set_page_config(page_title="Clasificador de Gastos", layout="centered")

st.title("📊 Clasificador de Gastos Mensuales")
st.write("Carga tu estado de cuenta en PDF y clasifica tus gastos por categoría.")

# --- Cargar archivo PDF ---
uploaded_file = st.file_uploader("Carga tu estado de cuenta bancario (PDF)", type="pdf")

def clasificar_gasto(descripcion):
    desc = descripcion.lower()
    if "amazon" in desc:
        return "Amazon"
    elif "uber eats" in desc:
        return "Uber Eats"
    elif "spotify" in desc:
        return "Entretenimiento"
    elif "oxxo" in desc or "7-eleven" in desc:
        return "Conveniencia"
    elif "restaurante" in desc or "toks" in desc:
        return "Comida"
    else:
        return "Otros"

def procesar_pdf(file):
    with pdfplumber.open(file) as pdf:
        texto_total = ""
        for page in pdf.pages:
            texto_total += page.extract_text()

    # Suponiendo líneas tipo: 01/07/2025 AMAZON  -259.90
    lineas = texto_total.split('\n')
    datos = []

    for linea in lineas:
        partes = linea.strip().split()
        if len(partes) >= 3:
            fecha = partes[0]
            monto_str = partes[-1].replace("$", "").replace(",", "")
            try:
                monto = float(monto_str)
                descripcion = " ".join(partes[1:-1])
                datos.append({"Fecha": fecha, "Descripción": descripcion, "Monto": monto})
            except ValueError:
                continue

    df = pd.DataFrame(datos)
    df["Categoría"] = df["Descripción"].apply(clasificar_gasto)
    return df

if uploaded_file is not None:
    try:
        df_gastos = procesar_pdf(uploaded_file)

        st.success("✅ Archivo procesado correctamente.")
        st.dataframe(df_gastos)

        resumen = df_gastos.groupby("Categoría")["Monto"].sum().reset_index()
        st.subheader("Resumen por Categoría")
        st.bar_chart(resumen.set_index("Categoría"))

    except Exception as e:
        st.error(f"Ocurrió un error: {e}")
