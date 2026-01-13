import streamlit as st
from docx import Document
from docx.shared import Inches, Mm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
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
    div[data-testid="stSidebar"] { background-color: #f0f2f6; }
</style>
""", unsafe_allow_html=True)

# --- 2. BARRA LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3145/3145765.png", width=80)
    st.title("Centro de Mando")
    
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("✅ Motor IA Activo")
    except:
        st.error("❌ Falta API Key")
        st.stop()
        
    st.divider()
    
    # --- MENÚ DE SELECCIÓN ---
    selected_module = st.radio(
        "Selecciona Herramienta:",
        [
            "1. 💎 Corrector & Auditor (Texto)",
            "2. 📏 Maquetador KDP PRO (Diseño)",
            "3. 📲 Workbook Cleaner (Líneas)",
            "4. 🧼 Limpiador Rápido"
        ]
    )
    
    st.divider()
    MODEL_NAME = 'models/gemini-flash-latest' 
    model = genai.GenerativeModel(MODEL_NAME)

# --- 3. FUNCIONES DE LÓGICA ---

def fix_irregular_spacing(text):
    """Elimina dobles espacios y espacios invisibles."""
    if not text: return text
    return re.sub(r'[ \t\xA0]{2,}', ' ', text).strip()

def clean_markdown(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) 
    text = re.sub(r'\*(.*?)\*', r'\1', text)     
    text = re.sub(r'__(.*?)__', r'\1', text)     
    text = re.sub(r'^#+\s*', '', text) 
    if text.strip().startswith("- "): text = text.strip()[2:] 
    text = fix_irregular_spacing(text)
    return text.strip()

def call_api(prompt, temp=0.7):
    for _ in range(3):
        try:
            return model.generate_content(prompt, generation_config={"temperature": temp}).text.strip()
        except:
            time.sleep(1)
    return "[ERROR API]"

# ==============================================================================
# MÓDULO 1: CORRECTOR
# ==============================================================================
if "Corrector" in selected_module:
    st.header("💎 Corrector de Estilo & Auditoría")
    st.info("Reescribe a inglés nativo y elimina símbolos extraños.")

    tone_option = st.selectbox("Tono:", ["Warm & Kid-Friendly", "Strict Grammar"])
    temp = 0.7 if "Kid-Friendly" in tone_option else 0.3
    tone_prompt = "Tone: Warm, empathetic" if temp == 0.7 else "Tone: Neutral"

    uploaded_file = st.file_uploader("Sube manuscrito (.docx)", type=["docx"], key="mod1")

    if uploaded_file:
        doc = Document(uploaded_file)
        tab1, tab2 = st.tabs(["📊 Auditoría", "🚀 Corrección Final"])
        
        with tab1:
            if st.button("🔍 Auditar"):
                audit_doc = Document()
                audit_doc.add_heading("Reporte", 0)
                p_bar = st.progress(0)
                for i, p in enumerate(doc.paragraphs):
                    if len(p.text) > 5:
                        res = call_api(f"AUDIT this. RULES: Whirlwind=HE. Output issues or 'CLEAN'. Text: '{p.text}'", temp)
                        if "CLEAN" not in res: audit_doc.add_paragraph(f"Párrafo {i+1}: {res}")
                    p_bar.progress((i+1)/len(doc.paragraphs))
                bio = BytesIO(); audit_doc.save(bio)
                st.download_button("⬇️ Descargar Reporte", bio.getvalue(), "Reporte.docx")

        with tab2:
            if st.button("🚀 Corregir Libro"):
                uploaded_file.seek(0)
                new_doc = Document(uploaded_file)
                p_bar = st.progress(0)
                for i, (p_orig, p_dest) in enumerate(zip(doc.paragraphs, new_doc.paragraphs)):
                    if len(p_orig.text) > 2:
                        res = call_api(f"Rewrite to native US English. NO Markdown. Tone: {tone_prompt}. Text: '{p_orig.text}'", temp)
                        clean_res = clean_markdown(res)
                        if "[ERROR" not in clean_res: p_dest.text = clean_res
                    p_bar.progress((i+1)/len(doc.paragraphs))
                bio = BytesIO(); new_doc.save(bio)
                st.download_button("⬇️ Descargar Corregido", bio.getvalue(), "Libro_Corregido.docx")

# ==============================================================================
# MÓDULO 2: MAQUETADOR KDP PRO (CON PROTECCIÓN DE HUÉRFANAS)
# ==============================================================================
elif "Maquetador" in selected_module:
    st.header("📏 Maquetador KDP PRO")
    st.markdown("Ajusta tamaño, limpia espacios y evita líneas huérfanas.")

    col1, col2 = st.columns(2)
    with col1:
        size = st.selectbox("Tamaño:", ["6 x 9 pulgadas (Estándar)", "5 x 8 pulgadas", "8.5 x 11 pulgadas"])
    with col2:
        margins = st.radio("Márgenes:", ["Normales", "Espejo (Doble Cara)"])

    st.markdown("---")
    st.subheader("⚙️ Ajustes de Tipografía")
    
    col3, col4 = st.columns(2)
    with col3:
        fix_orphans = st.checkbox("🛡️ Proteger líneas huérfanas/viudas", value=True, help="Evita que queden líneas solas al principio o final de la hoja.")
        fix_titles = st.checkbox("📎 Pegar Títulos", value=True, help="Evita que un título quede solo al final de la hoja.")
    with col4:
        fix_spaces = st.checkbox("🧼 Reparar espacios dobles", value=True)
        justify_text = st.checkbox("📄 Justificar texto completo", value=False)
    
    uploaded_file = st.file_uploader("Sube manuscrito (.docx)", type=["docx"], key="mod2")

    if uploaded_file and st.button("🛠️ Procesar Libro"):
        doc = Document(uploaded_file)
        
        # 1. Ajuste de Página (Papel)
        if "6 x 9" in size: w, h = Inches(6), Inches(9)
        elif "5 x 8" in size: w, h = Inches(5), Inches(8)
        else: w, h = Inches(8.5), Inches(11)

        for section in doc.sections:
            section.page_width = w
            section.page_height = h
            section.top_margin = Inches(0.75); section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.75); section.right_margin = Inches(0.6)
            if "Espejo" in margins: section.mirror_margins = True; section.gutter = Inches(0.13)

        # 2. Procesamiento de Texto y Párrafos
        count_fixed = 0
        
        for p in doc.paragraphs:
            # A. Limpieza de Espacios
            if fix_spaces and len(p.text) > 0:
                original_len = len(p.text)
                cleaned_text = fix_irregular_spacing(p.text)
                if len(cleaned_text) < original_len:
                    p.text = cleaned_text
                    count_fixed += 1
            
            # B. Protección Huérfanas/Viudas (LA MAGIA NUEVA ✨)
            if fix_orphans:
                p.paragraph_format.widow_control = True 
            
            # C. Protección de Títulos (Keep with Next)
            # Detectamos títulos si son cortos y no terminan en punto (heurística simple)
            # O si tienen estilo 'Heading'
            if fix_titles:
                is_heading = p.style.name.startswith('Heading') or (len(p.text) < 60 and len(p.text) > 3 and not p.text.endswith('.'))
                if is_heading:
                    p.paragraph_format.keep_with_next = True

            # D. Justificación
            if justify_text and len(p.text) > 50:
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        bio = BytesIO(); doc.save(bio)
        
        st.success(f"✅ Formato KDP aplicado. Se optimizaron {len(doc.paragraphs)} párrafos.")
        if count_fixed > 0: st.info(f"🧼 Se limpiaron espacios extra en {count_fixed} lugares.")
            
        st.download_button("⬇️ Descargar Libro Profesional", bio.getvalue(), "Libro_KDP_Pro.docx")

# ==============================================================================
# MÓDULO 3: WORKBOOK CLEANER
# ==============================================================================
elif "Workbook" in selected_module:
    st.header("📲 Workbook Cleaner")
    
    cta_text = st.text_area("Texto CTA:", "🛑 (Ejercicio): Completa esto en tu Cuaderno. Descarga: [LINK]", height=80)
    threshold = st.slider("Sensibilidad", 3, 15, 4)
    uploaded_file = st.file_uploader("Sube manuscrito (.docx)", type=["docx"], key="mod3")

    if uploaded_file and st.button("🧹 Limpiar Líneas"):
        doc = Document(uploaded_file)
        count = 0; p_bar = st.progress(0)
        for i, p in enumerate(doc.paragraphs):
            if re.search(f"([_.\-]){{{threshold},}}", p.text):
                prompt = f"Identify question. Remove lines. Add CTA: '{cta_text}'. Input: '{p.text}'"
                new_text = call_api(prompt)
                if new_text != p.text: p.text = new_text; count += 1
            p_bar.progress((i+1)/len(doc.paragraphs))
        bio = BytesIO(); doc.save(bio)
        st.download_button("⬇️ Descargar eBook", bio.getvalue(), "Ebook_Ready.docx")

# ==============================================================================
# MÓDULO 4: LIMPIADOR RÁPIDO
# ==============================================================================
elif "Limpiador" in selected_module:
    st.header("🧼 Limpiador Rápido")
    uploaded_file = st.file_uploader("Sube docx", type=["docx"], key="mod4")
    if uploaded_file and st.button("🧹 Limpiar"):
        doc = Document(uploaded_file)
        for p in doc.paragraphs: p.text = fix_irregular_spacing(p.text)
        bio = BytesIO(); doc.save(bio)
        st.download_button("⬇️ Descargar", bio.getvalue(), "Limpio.docx")
