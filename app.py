import streamlit as st
from docx import Document
from docx.shared import Inches, Mm
import google.generativeai as genai
from io import BytesIO
import time
import os
import re

# --- 1. CONFIGURACIÓN GLOBAL ---
st.set_page_config(page_title="Suite Autores 360", page_icon="📚", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. BARRA LATERAL (NAVEGACIÓN) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3145/3145765.png", width=80)
    st.title("Centro de Mando")
    
    # --- API KEY (Compartida para todos los módulos) ---
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("✅ Motor IA Activo")
    except:
        st.error("❌ Falta API Key")
        st.stop()
        
    st.divider()
    
    # --- MENÚ DE SELECCIÓN DE MÓDULO ---
    selected_module = st.radio(
        "Selecciona Herramienta:",
        [
            "1. 💎 Corrector & Auditor (Texto)",
            "2. 📏 Maquetador KDP (Diseño)",
            "3. 📲 Workbook Cleaner (Interactivo)"
        ]
    )
    
    st.divider()
    
    # --- CONFIGURACIÓN COMPARTIDA (MODELO) ---
    MODEL_NAME = 'models/gemini-flash-latest' 
    model = genai.GenerativeModel(MODEL_NAME)

# --- 3. FUNCIONES COMPARTIDAS (UTILIDADES) ---

def clean_markdown(text):
    """Limpieza profunda: Markdown, Negritas y Dobles Espacios"""
    # 1. Eliminar Markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) 
    text = re.sub(r'\*(.*?)\*', r'\1', text)     
    text = re.sub(r'__(.*?)__', r'\1', text)     
    text = re.sub(r'^#+\s*', '', text) 
    if text.strip().startswith("- "): text = text.strip()[2:] 
    
    # 2. ELIMINAR DOBLES ESPACIOS (Corrección visual)
    text = re.sub(r'[ ]{2,}', ' ', text)
    
    return text.strip()

def call_api(prompt, temp=0.7):
    for _ in range(3):
        try:
            return model.generate_content(prompt, generation_config={"temperature": temp}).text.strip()
        except:
            time.sleep(1)
    return "[ERROR API]"

# ==============================================================================
# MÓDULO 1: CORRECTOR Y AUDITOR (NativeFlow)
# ==============================================================================
if selected_module == "1. 💎 Corrector & Auditor (Texto)":
    st.header("💎 Corrector de Estilo & Auditoría")
    st.info("Este módulo reescribe tu texto a inglés nativo y elimina símbolos extraños.")

    tone_option = st.selectbox("Tono:", ["Warm & Kid-Friendly (Infantil)", "Strict Grammar (Neutro)"])
    if "Kid-Friendly" in tone_option:
        tone_prompt = "Tone: Warm, empathetic. Simple vocabulary (Age 6-10)."
        temp = 0.7
    else:
        tone_prompt = "Tone: Neutral. Keep author's voice exact."
        temp = 0.3

    uploaded_file = st.file_uploader("Sube manuscrito (.docx)", type=["docx"], key="mod1")

    if uploaded_file:
        doc = Document(uploaded_file)
        st.write(f"📖 Párrafos detectados: {len(doc.paragraphs)}")
        
        tab1, tab2 = st.tabs(["📊 Auditoría", "🚀 Corrección Final"])
        
        # Auditoría
        with tab1:
            if st.button("🔍 Auditar"):
                audit_doc = Document()
                audit_doc.add_heading("Reporte Auditoría", 0)
                p_bar = st.progress(0)
                
                for i, p in enumerate(doc.paragraphs):
                    if len(p.text) > 5:
                        prompt = f"AUDIT this text. RULES: Whirlwind=HE. No 'outsourcing'. Output issues or 'CLEAN'. Text: '{p.text}'"
                        res = call_api(prompt, temp)
                        if "CLEAN" not in res:
                            audit_doc.add_paragraph(f"Párrafo {i+1}: {res}")
                    p_bar.progress((i+1)/len(doc.paragraphs))
                
                bio = BytesIO()
                audit_doc.save(bio)
                st.download_button("⬇️ Descargar Reporte", bio.getvalue(), "Reporte.docx")

        # Corrección
        with tab2:
            if st.button("🚀 Corregir Libro"):
                uploaded_file.seek(0)
                new_doc = Document(uploaded_file) # Clonar para mantener fotos
                p_bar = st.progress(0)
                
                for i, (p_orig, p_dest) in enumerate(zip(doc.paragraphs, new_doc.paragraphs)):
                    if len(p_orig.text) > 2:
                        prompt = f"""
                        Rewrite to native US English. 
                        RULES: NO Markdown (**). Whirlwind=He. Tone: {tone_prompt}.
                        Text: "{p_orig.text}"
                        """
                        res = call_api(prompt, temp)
                        clean_res = clean_markdown(res) # Limpieza de espacios y símbolos
                        if "[ERROR" not in clean_res:
                            p_dest.text = clean_res
                    p_bar.progress((i+1)/len(doc.paragraphs))
                
                bio = BytesIO()
                new_doc.save(bio)
                st.download_button("⬇️ Descargar Libro Corregido", bio.getvalue(), "Libro_Corregido.docx")

# ==============================================================================
# MÓDULO 2: MAQUETADOR KDP (Márgenes y Tamaño)
# ==============================================================================
elif selected_module == "2. 📏 Maquetador KDP (Diseño)":
    st.header("📏 Maquetador KDP Automático")
    st.info("Redimensiona tu documento para Amazon KDP (Tapa Blanda).")

    col1, col2 = st.columns(2)
    with col1:
        size = st.selectbox("Tamaño:", ["6 x 9 pulgadas (Estándar)", "5 x 8 pulgadas", "8.5 x 11 pulgadas"])
    with col2:
        margins = st.radio("Tipo de Márgenes:", ["Normales", "Espejo (Impresión Doble Cara)"])

    uploaded_file = st.file_uploader("Sube manuscrito corregido (.docx)", type=["docx"], key="mod2")

    if uploaded_file and st.button("🛠️ Aplicar Formato KDP"):
        doc = Document(uploaded_file)
        
        # Lógica de medidas
        if "6 x 9" in size: w, h = Inches(6), Inches(9)
        elif "5 x 8" in size: w, h = Inches(5), Inches(8)
        else: w, h = Inches(8.5), Inches(11)

        for section in doc.sections:
            section.page_width = w
            section.page_height = h
            section.top_margin = Inches(0.75)
            section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.75)
            section.right_margin = Inches(0.6)
            
            if margins == "Espejo (Impresión Doble Cara)":
                section.mirror_margins = True
                section.gutter = Inches(0.13)

        bio = BytesIO()
        doc.save(bio)
        st.success("✅ Formato aplicado correctamente.")
        st.download_button("⬇️ Descargar Libro Maquetado", bio.getvalue(), "Libro_KDP_6x9.docx")

# ==============================================================================
# MÓDULO 3: WORKBOOK CLEANER (Limpieza de Líneas)
# ==============================================================================
elif selected_module == "3. 📲 Workbook Cleaner (Interactivo)":
    st.header("📲 Convertidor Workbook -> eBook")
    st.info("Detecta líneas de escritura (_____) y las reemplaza por enlaces de descarga.")

    cta_text = st.text_area(
        "Texto de Reemplazo (Call to Action):", 
        "🛑 (Ejercicio Interactivo): Completa esto en tu Cuaderno de Actividades. Descárgalo gratis aquí: [LINK]",
        height=80
    )
    threshold = st.slider("Sensibilidad de detección", 3, 15, 4)

    uploaded_file = st.file_uploader("Sube manuscrito (.docx)", type=["docx"], key="mod3")

    if uploaded_file and st.button("🧹 Limpiar Líneas"):
        doc = Document(uploaded_file)
        count = 0
        p_bar = st.progress(0)
        
        for i, p in enumerate(doc.paragraphs):
            # Regex: Busca guiones bajos, medios o puntos seguidos
            if re.search(f"([_.\-]){{{threshold},}}", p.text):
                prompt = f"""
                TASK: Identify the question in this text. Remove the fill-in-the-blank lines (____ or ----).
                Insert this CTA after the question: "{cta_text}".
                INPUT: "{p.text}"
                OUTPUT (Text only):
                """
                new_text = call_api(prompt)
                if new_text != p.text:
                    p.text = new_text
                    count += 1
            p_bar.progress((i+1)/len(doc.paragraphs))
            
        st.success(f"✅ Se limpiaron {count} ejercicios.")
        bio = BytesIO()
        doc.save(bio)
        st.download_button("⬇️ Descargar Ebook Limpio", bio.getvalue(), "Ebook_Ready.docx")
