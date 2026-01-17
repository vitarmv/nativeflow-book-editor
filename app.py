import streamlit as st
from docx import Document
from docx.shared import Inches, Mm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import google.generativeai as genai
from io import BytesIO
import time
import os
import re
import uuid
import itertools

# --- LIBRERÍAS ---
import pyphen  # Solo para EPUB o si se activa explícitamente
import mammoth 
from bs4 import BeautifulSoup 
from ebooklib import epub 

# --- 1. CONFIGURACIÓN GLOBAL ---
st.set_page_config(page_title="Suite Autores 360 ULTIMATE", page_icon="📚", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    .block-container { padding-top: 2rem; }
    div[data-testid="stSidebar"] { background-color: #f8f9fa; }
    h1 { color: #2c3e50; }
</style>
""", unsafe_allow_html=True)

# --- 2. TEMAS ---
THEMES = {
    "Neutro (Estándar)": {"font": "Calibri", "header": "Calibri", "size": 11},
    "Romance / Fantasía (Serif)": {"font": "Garamond", "header": "Garamond", "size": 12},
    "Thriller / Crimen (Sharp)": {"font": "Georgia", "header": "Arial Black", "size": 11},
    "No Ficción / Negocios": {"font": "Arial", "header": "Arial", "size": 10}
}

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3145/3145765.png", width=80)
    st.title("Centro de Mando")
    
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("✅ Motor IA Activo")
    except:
        st.error("❌ Falta API Key en Secrets")
        st.stop()
        
    st.divider()
    
    selected_module = st.radio(
        "Selecciona Herramienta:",
        [
            "1. 💎 Auditor & Corrector IA",
            "2. 📏 Maquetador KDP PRO (Papel)",
            "3. 📲 Workbook Cleaner (Kindle)",
            "4. 🧼 Limpiador Rápido",
            "5. ⚡ Generador EPUB (eBook)"
        ]
    )
    
    st.divider()
    MODEL_NAME = 'models/gemini-flash-latest' 
    model = genai.GenerativeModel(MODEL_NAME)

# --- 4. FUNCIONES ---

def apply_hyphenation(text, lang='es'):
    """Inserta guiones suaves (\xad). Útil para EPUB, evitable en DOCX."""
    if not text: return ""
    dic = pyphen.Pyphen(lang=lang)
    words = text.split()
    new_words = []
    for word in words:
        if len(word) > 7: 
            inserted = dic.inserted(word, hyphen='\xad')
            new_words.append(inserted)
        else:
            new_words.append(word)
    return " ".join(new_words)

def nuclear_clean(text):
    if not text: return text
    return " ".join(text.split())

def clean_markdown(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) 
    text = re.sub(r'\*(.*?)\*', r'\1', text)      
    text = re.sub(r'__(.*?)__', r'\1', text)      
    text = re.sub(r'^#+\s*', '', text) 
    text = nuclear_clean(text)
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
    uploaded_file = st.file_uploader("Sube manuscrito (.docx)", type=["docx"], key="mod1")

    if uploaded_file:
        doc = Document(uploaded_file)
        tab1, tab2 = st.tabs(["📊 Auditoría", "🚀 Corrección Final"])
        
        with tab1:
            if st.button("🔍 Auditar"):
                audit_doc = Document()
                audit_doc.add_heading("Reporte de Errores", 0)
                p_bar = st.progress(0)
                for i, p in enumerate(doc.paragraphs):
                    if len(p.text) > 10:
                        res = call_api(f"AUDIT this text. Identify grammar errors or inconsistencies. If clean, output 'CLEAN'. Text: '{p.text[:300]}'")
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
                    if len(p_orig.text) > 5:
                        res = call_api(f"Rewrite to native English. Keep tone. NO Markdown. Text: '{p_orig.text}'")
                        clean_res = clean_markdown(res)
                        if "[ERROR" not in clean_res: p_dest.text = clean_res
                    p_bar.progress((i+1)/len(doc.paragraphs))
                bio = BytesIO(); new_doc.save(bio)
                st.download_button("⬇️ Descargar Corregido", bio.getvalue(), "Libro_Corregido.docx")

# ==============================================================================
# MÓDULO 2: MAQUETADOR KDP PRO (CORREGIDO Y MEJORADO)
# ==============================================================================
elif "Maquetador" in selected_module:
    st.header("📏 Maquetador KDP PRO 3.1")
    st.markdown("Ahora con **Detección Inteligente de Títulos** y limpieza visual.")

    col1, col2 = st.columns(2)
    with col1:
        size = st.selectbox("Tamaño:", ["6 x 9 pulgadas", "5 x 8 pulgadas", "8.5 x 11 pulgadas"])
        theme_choice = st.selectbox("🎨 Tema Visual:", list(THEMES.keys())) 
    with col2:
        margins = st.radio("Márgenes:", ["Espejo (Doble Cara)", "Normales"])

    st.markdown("---")
    
    col3, col4 = st.columns(2)
    with col3:
        fix_titles = st.checkbox("📎 Pegar Títulos (Smart Detect)", value=True, help="Detecta 'Chapter' aunque no tenga estilo.")
        pro_start = st.checkbox("✨ Inicio Capítulo Pro (Small Caps)", value=True)
    with col4:
        fix_spaces = st.checkbox("☢️ Limpieza Nuclear", value=True)
        justify_text = st.checkbox("📄 Justificar Texto (Limpio)", value=True, help="Justifica sin ensuciar con guiones ocultos.")

    uploaded_file = st.file_uploader("Sube manuscrito (.docx)", type=["docx"], key="mod2")

    if uploaded_file and st.button("🛠️ Procesar Libro"):
        doc = Document(uploaded_file)
        theme = THEMES[theme_choice] 
        
        # 1. PAGE SETUP
        if "6 x 9" in size: w, h = Inches(6), Inches(9)
        elif "5 x 8" in size: w, h = Inches(5), Inches(8)
        else: w, h = Inches(8.5), Inches(11)

        for section in doc.sections:
            section.page_width = w; section.page_height = h
            section.top_margin = Inches(0.75); section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.8); section.right_margin = Inches(0.6)
            if "Espejo" in margins: section.mirror_margins = True; section.gutter = Inches(0.15)

        # 2. APLICAR TEMA
        style = doc.styles['Normal']
        style.font.name = theme['font']
        style.font.size = Pt(theme['size'])
        
        # 3. BUCLE INTELIGENTE
        count_fixed = 0
        p_bar = st.progress(0)
        total_p = len(doc.paragraphs)
        previous_was_heading = False 

        for i, p in enumerate(doc.paragraphs):
            
            # A. LIMPIEZA
            if fix_spaces and len(p.text) > 0:
                clean = nuclear_clean(p.text)
                if clean != p.text:
                    p.text = clean
                    count_fixed += 1
            
            # B. DETECCIÓN INTELIGENTE DE TÍTULOS (LA SOLUCIÓN)
            # 1. ¿Es estilo Heading?
            is_style_heading = p.style.name.startswith('Heading')
            
            # 2. ¿Parece un título visualmente?
            # (Texto corto, mayúsculas, o empieza con palabra clave)
            text_clean = p.text.strip()
            is_visual_heading = False
            
            if 0 < len(text_clean) < 60:
                # Palabras clave (sin importar mayúsculas/minúsculas)
                if re.match(r'^(chapter|cap[íi]tulo|part|parte|pr[óo]logo|prologue|intro)\b', text_clean, re.IGNORECASE):
                    is_visual_heading = True
                # Números romanos solos (I, II, IV...)
                elif re.match(r'^[IVXLCDM]+\.?$', text_clean):
                    is_visual_heading = True
                # TODO MAYÚSCULAS (común en manuscritos viejos)
                elif text_clean.isupper() and len(text_clean) > 3:
                    is_visual_heading = True

            # LÓGICA DE DECISIÓN
            if is_style_heading or is_visual_heading:
                previous_was_heading = True
                if fix_titles: 
                    p.paragraph_format.keep_with_next = True
                    # Opcional: Podrías forzar negrita aquí si quieres
                    # for run in p.runs: run.bold = True
            
            else:
                # C. TEXTO DE CUERPO
                if len(p.text) > 2:
                    
                    # Justificación (SIN Hyphenation sucio)
                    if justify_text:
                        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                        # NOTA: Hemos quitado apply_hyphenation() para DOCX para que quede limpio.
                        # Word lo hará automáticamente si el usuario activa "Guiones".

                    # Estilo Inicio de Capítulo (Small Caps)
                    if pro_start and previous_was_heading:
                        words = p.text.split()
                        # Aseguramos que el párrafo tenga suficiente "carne"
                        if len(words) > 3:
                            # Tomamos las primeras 3-4 palabras
                            limit = min(4, len(words))
                            first_phrase = " ".join(words[:limit])
                            rest = " ".join(words[limit:])
                            
                            p.text = "" 
                            run = p.add_run(first_phrase + " ")
                            run.font.name = theme['font']
                            run.font.small_caps = True # Versalitas
                            run.bold = True
                            
                            p.add_run(rest)
                
                # Reseteamos la bandera inmediatamente después del primer párrafo
                previous_was_heading = False 

            if i % 10 == 0: p_bar.progress((i+1)/total_p)

        bio = BytesIO(); doc.save(bio)
        st.success(f"✅ Maquetación completada. Se usó detección visual de títulos.")
        st.download_button("⬇️ Descargar Libro KDP", bio.getvalue(), "Libro_KDP_Pro.docx")

# ==============================================================================
# MÓDULO 3: WORKBOOK CLEANER
# ==============================================================================
elif "Workbook" in selected_module:
    st.header("📲 Workbook Cleaner")
    cta_text = st.text_area("Texto CTA:", "🛑 (Ejercicio): Completa esto en tu Cuaderno.", height=80)
    uploaded_file = st.file_uploader("Sube manuscrito (.docx)", type=["docx"], key="mod3")

    if uploaded_file and st.button("🧹 Limpiar"):
        doc = Document(uploaded_file)
        for p in doc.paragraphs:
            if re.search(f"([_.\-]){{4,}}", p.text):
                p.text = cta_text # Reemplazo directo simple
        bio = BytesIO(); doc.save(bio)
        st.download_button("⬇️ Descargar eBook", bio.getvalue(), "Ebook_Ready.docx")

# ==============================================================================
# MÓDULO 4: LIMPIADOR NUCLEAR
# ==============================================================================
elif "Limpiador" in selected_module:
    st.header("☢️ Limpiador 'Nuclear'")
    uploaded_file = st.file_uploader("Sube docx", key="mod4")
    if uploaded_file and st.button("🧹 Limpiar"):
        doc = Document(uploaded_file)
        count = 0
        for p in doc.paragraphs:
            if p.text:
                clean = nuclear_clean(p.text)
                if clean != p.text: p.text = clean; count += 1
        st.success(f"✅ {count} párrafos limpiados.")
        bio = BytesIO(); doc.save(bio)
        st.download_button("⬇️ Descargar", bio.getvalue(), "Limpio.docx")

# ==============================================================================
# MÓDULO 5: GENERADOR EPUB
# ==============================================================================
elif "Generador EPUB" in selected_module:
    st.header("⚡ Generador EPUB")
    uploaded_file = st.file_uploader("Sube Manuscrito (.docx)", type=["docx"], key="mod5")
    
    if uploaded_file and st.button("Convertir"):
        st.info("Generando EPUB...")
        # (Código EPUB igual al anterior, usa mammoth y ebooklib)
        # Por brevedad en esta respuesta, asumo que mantienes el bloque del Módulo 5 anterior.
        # Si lo necesitas completo de nuevo, avísame.
