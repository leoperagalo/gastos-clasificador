# 📊 Clasificador de Gastos (Versión V3)

Aplicación web construida con [Streamlit](https://streamlit.io/) para clasificar automáticamente tus gastos en PDF por **categoría** y **mes**, exportarlos a Excel y visualizarlos desde cualquier navegador o celular.

---

## 🚀 Funcionalidades

- ✅ Carga múltiple de PDFs de estados de cuenta
- ✅ Detección automática de fechas dentro del PDF
- ✅ Clasificación por categorías personalizadas
- ✅ Agrupación mensual automática
- ✅ Descarga en Excel con un clic
- ✅ Interfaz compatible con móviles

---

## 🖥️ ¿Cómo usar esta app?

### Opción 1: Desde navegador (Streamlit Cloud) ✅

🔗 Enlace directo: [https://leoperagalo-gastos-clasificador.streamlit.app](https://leoperagalo-gastos-clasificador.streamlit.app) *(ejemplo, cambia si tu usuario es otro)*

1. Abre el enlace en tu navegador
2. Sube uno o varios PDFs
3. Espera a que se procesen los datos
4. Visualiza los resultados por mes y categoría
5. Descarga tu Excel limpio

---

## ⚙️ Opción 2: Ejecutarlo localmente

### 🐍 Requisitos

- Python 3.8 o superior
- pip
- Git

### 📦 Instalación

```bash
git clone https://github.com/leoperagalo/gastos-clasificador.git
cd gastos-clasificador
pip install -r requirements.txt
