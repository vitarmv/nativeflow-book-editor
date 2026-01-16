import streamlit as st
from docx import Document
from docx.shared import Inches, Mm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import google.generativeai as genai
from io import BytesIO
import time
import os
import re
import pyphen  # <--- RECUERDA: pip install pyphen

# --- 1. CONFIGURACIÓN GLOBAL ---
st.set_page_config(page_title="Suite Autores 360 PRO", page_icon="📚", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    .block-container { padding-top: 2rem; }
    div[data-testid="stSidebar"] { background-color: #f0f2f6; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURACIÓN DE ESTILOS (TEMAS) ---
THEMES = {
    "Neutro (Estándar)": {"font": "Calibri", "header": "Calibri", "size": 11},
    "Romance / Fantasía (Serif)": {"font": "Garamond", "header": "Garamond", "size": 12},
    "Thriller / Crimen (Sharp)": {"font": "Georgia", "header": "Arial Black", "size": 11},
    "No Ficción / Negocios": {"font": "Arial", "header": "Arial", "size": 10}
}

# --- 3. BARRA LATERAL (TU CÓDIGO SEGURO) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3145/3145765.png", width=80)
    st.title("Centro de Mando")
    
    try:
        # MANTENEMOS TU CONFIGURACIÓN SEGURA ORIGINAL
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("✅ Motor IA Activo")
    except:
        st.error("❌ Falta API Key en Secrets")
        st.stop()
        
    st.divider()
    
    # --- MENÚ DE SELECCIÓN ---
    selected_module = st.radio(
        "Selecciona Herramienta:",
        [
            "1. 💎 Corrector & Auditor (Texto)",
            "2. 📏 Maquetador KDP PRO (Diseño)",
            "3. 📲 Workbook Cleaner (Líneas)",
            "4. 🧼 Limpiador 'Nuclear' de Espacios"
        ]
    )
    
    st.divider()
    MODEL_NAME = 'models/gemini-flash-latest' 
    model = genai.GenerativeModel(MODEL_NAME)

# --- 4. FUNCIONES DE LÓGICA (EL CEREBRO) ---

def apply_hyphenation(text, lang='es'):
    """
    NUEVA FUNCIÓN: Inserta guiones suaves para justificación perfecta.
    """
    if not text: return ""
    dic = pyphen.Pyphen(lang=lang)
    words = text.split()
    new_words = []
    for word in words:
        if len(word) > 6: # Solo silabeamos palabras largas
            inserted = dic.inserted(word, hyphen='\xad') # \xad es el soft-hyphen
            new_words.append(inserted)
        else:
            new_words.append(word)
    return " ".join(new_words)

def fix_irregular_spacing(text):
    """Limpieza Nuclear original"""
    if not text: return text
    return " ".join(text.split())

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
# MÓDULO 1: CORRECTOR (ORIGINAL)
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
# MÓDULO 2: MAQUETADOR KDP PRO (SUPER POTENCIADO 🚀)
# ==============================================================================
elif "Maquetador" in selected_module:
    st.header("📏 Maquetador KDP PRO 2.0")
    st.markdown("Ajusta tamaño, aplica temas visuales y justificación perfecta.")

    # --- CONTROLES VISUALES ---
    col1, col2 = st.columns(2)
    with col1:
        size = st.selectbox("Tamaño:", ["6 x 9 pulgadas (Estándar)", "5 x 8 pulgadas", "8.5 x 11 pulgadas"])
        theme_choice = st.selectbox("🎨 Tema Visual:", list(THEMES.keys())) # NUEVO: Selector de Tema
    with col2:
        margins = st.radio("Márgenes:", ["Normales", "Espejo (Doble Cara)"])

    st.markdown("---")
    st.subheader("⚙️ Ingeniería de Texto")
    
    col3, col4 = st.columns(2)
    with col3:
        fix_orphans = st.checkbox("🛡️ Proteger líneas huérfanas/viudas", value=True)
        fix_titles = st.checkbox("📎 Pegar Títulos (Keep with Next)", value=True)
        pro_start = st.checkbox("✨ Inicio Capítulo Pro (Small Caps)", value=True, help="Aplica estilo elegante al iniciar capítulo.") # NUEVO
    with col4:
        fix_spaces = st.checkbox("☢️ Limpieza Nuclear de Espacios", value=True)
        justify_text = st.checkbox("📄 Justificar + Silabeo (Hyphenation)", value=True, help="Evita ríos blancos usando guiones.") # NUEVO
    
    uploaded_file = st.file_uploader("Sube manuscrito (.docx)", type=["docx"], key="mod2")

    if uploaded_file and st.button("🛠️ Procesar Libro"):
        doc = Document(uploaded_file)
        theme = THEMES[theme_choice] # Cargar configuración del tema elegido
        
        # 1. AJUSTE DE PÁGINA (PAGE SETUP)
        if "6 x 9" in size: w, h = Inches(6), Inches(9)
        elif "5 x 8" in size: w, h = Inches(5), Inches(8)
        else: w, h = Inches(8.5), Inches(11)

        for section in doc.sections:
            section.page_width = w
            section.page_height = h
            section.top_margin = Inches(0.75); section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.75); section.right_margin = Inches(0.6)
            if "Espejo" in margins: section.mirror_margins = True; section.gutter = Inches(0.13)

        # 2. APLICAR ESTILOS DEL TEMA (FUENTES)
        style = doc.styles['Normal']
        style.font.name = theme['font']
        style.font.size = Pt(theme['size'])
        
        for h in ['Heading 1', 'Heading 2']:
            try:
                h_style = doc.styles[h]
                h_style.font.name = theme['header']
                h_style.font.color.rgb = RGBColor(0, 0, 0) # Negro estricto para KDP
            except: pass

        # 3. PROCESAMIENTO INTELIGENTE DE PÁRRAFOS
        count_fixed = 0
        p_bar = st.progress(0)
        total_p = len(doc.paragraphs)
        
        previous_was_heading = False # Bandera para detectar inicio de capítulo

        for i, p in enumerate(doc.paragraphs):
            
            # A. LIMPIEZA NUCLEAR
            if fix_spaces and len(p.text) > 0:
                original_text = p.text
                cleaned_text = " ".join(original_text.split()) # Borra basura web
                if cleaned_text != original_text:
                    p.text = cleaned_text
                    count_fixed += 1
            
            # Detectar si es Título
            if p.style.name.startswith('Heading'):
                previous_was_heading = True
                if fix_titles: p.paragraph_format.keep_with_next = True
            
            else:
                # Es texto normal (Cuerpo)
                if len(p.text) > 2:
                    
                    # B. JUSTIFICACIÓN + HYPHENATION (NUEVO)
                    if justify_text:
                        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                        # Aplicamos silabeo solo si es texto largo
                        if len(p.text) > 60:
                            p.text = apply_hyphenation(p.text, lang='es')

                    # C. INICIO CAPÍTULO PRO (SMALL CAPS) (NUEVO)
                    if pro_start and previous_was_heading:
                        words = p.text.split()
                        if len(words) > 4:
                            first_phrase = " ".join(words[:4])
                            rest = " ".join(words[4:])
                            p.text = "" # Limpiamos párrafo
                            
                            # Frase inicial en Small Caps (Versalitas)
                            run = p.add_run(first_phrase + " ")
                            run.font.name = theme['font']
                            run.font.small_caps = True 
                            run.bold = True
                            
                            # Resto normal
                            p.add_run(rest)
                
                previous_was_heading = False # Reset bandera

            # D. VIUDAS Y HUÉRFANAS
            if fix_orphans:
                p.paragraph_format.widow_control = True 

            p_bar.progress((i+1)/total_p)

        bio = BytesIO(); doc.save(bio)
        
        st.success(f"✅ Libro Maquetado con Tema: {theme_choice}")
        if count_fixed > 0: st.info(f"☢️ Se limpiaron {count_fixed} errores de formato web.")
            
        st.download_button("⬇️ Descargar Libro Profesional", bio.getvalue(), "Libro_KDP_Pro.docx")

# ==============================================================================
# MÓDULO 3: WORKBOOK CLEANER (ORIGINAL)
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
# MÓDULO 4: LIMPIADOR NUCLEAR (ORIGINAL)
# ==============================================================================
elif "Limpiador" in selected_module:
    st.header("☢️ Limpiador 'Nuclear' de Formato")
    st.info("Elimina saltos de línea manuales y espacios web que rompen la justificación.")

    uploaded_file = st.file_uploader("Sube docx", type=["docx"], key="mod4")
    if uploaded_file and st.button("🧹 Limpiar Formato Web"):
        doc = Document(uploaded_file)
        count = 0
        for p in doc.paragraphs:
            if p.text:
                new_text = " ".join(p.text.split())
                if new_text != p.text:
                    p.text = new_text
                    count += 1
        
        st.success(f"✅ Se arreglaron {count} párrafos con basura de formato web.")
        bio = BytesIO(); doc.save(bio)
        st.download_button("⬇️ Descargar Limpio", bio.getvalue(), "Limpio_Nuclear.docx")
