import streamlit as st
from docx import Document
from docx.shared import Inches, Mm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement, ns 
import google.generativeai as genai
from io import BytesIO
import time
import os
import re
import uuid
import itertools
import copy 

# --- LIBRERÍAS PRO ---
import pyphen  
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

# --- 2. DICCIONARIO DE TEMAS ---
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

# --- 4. FUNCIONES AUXILIARES ---

def create_element(name):
    return OxmlElement(name)

def create_attribute(element, name, value):
    element.set(ns.qn(name), value)

def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    page_run = paragraph.add_run()
    t1 = create_element('w:fldChar')
    create_attribute(t1, 'w:fldCharType', 'begin')
    page_run._r.append(t1)
    t2 = create_element('w:instrText')
    create_attribute(t2, 'xml:space', 'preserve')
    t2.text = "PAGE"
    page_run._r.append(t2)
    t3 = create_element('w:fldChar')
    create_attribute(t3, 'w:fldCharType', 'end')
    page_run._r.append(t3)

def enable_native_hyphenation(doc):
    settings = doc.settings.element
    hyphenation_zone = OxmlElement('w:autoHyphenation')
    create_attribute(hyphenation_zone, 'w:val', 'true')
    settings.append(hyphenation_zone)

def prevent_runts_in_paragraph(paragraph):
    text = paragraph.text.strip()
    if not text or len(text) < 20: return 
    last_space = text.rfind(' ')
    if last_space != -1:
        paragraph.text = text[:last_space] + "\u00A0" + text[last_space+1:]

def delete_paragraph(paragraph):
    p = paragraph._element
    p.getparent().remove(p)
    p._p = p._element = None

def stitch_paragraphs(doc):
    # Lógica V5.0: Une párrafos rotos por saltos de línea incorrectos
    for i in range(len(doc.paragraphs) - 2, -1, -1):
        p_curr = doc.paragraphs[i]
        p_next = doc.paragraphs[i+1]
        text_curr = p_curr.text.strip()
        text_next = p_next.text.strip()
        if not text_curr or not text_next: continue
        if p_curr.style.name.startswith('Heading') or p_next.style.name.startswith('Heading'): continue
        if text_curr[-1] not in ['.', '!', '?', '"', '”', ':']:
            p_curr.text = text_curr + " " + text_next
            delete_paragraph(p_next)

def nuclear_clean(text):
    if not text: return text
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\v', ' ').replace('\f', ' ')
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
# MÓDULO 1: CORRECTOR (RESTAURADO COMPLETO)
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
                audit_doc.add_heading("Reporte", 0)
                p_bar = st.progress(0)
                for i, p in enumerate(doc.paragraphs):
                    if len(p.text) > 10:
                        res = call_api(f"AUDIT this text. Output 'CLEAN' or issues. Text: '{p.text[:300]}'")
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
                        res = call_api(f"Rewrite to native English. Text: '{p_orig.text}'")
                        clean_res = clean_markdown(res)
                        if "[ERROR" not in clean_res: p_dest.text = clean_res
                    p_bar.progress((i+1)/len(doc.paragraphs))
                bio = BytesIO(); new_doc.save(bio)
                st.download_button("⬇️ Descargar Corregido", bio.getvalue(), "Libro_Corregido.docx")

# ==============================================================================
# MÓDULO 2: MAQUETADOR KDP PRO (V5.6 - RESTAURADO)
# ==============================================================================
elif "Maquetador" in selected_module:
    st.header("📏 Maquetador KDP PRO 5.6")
    
    col1, col2 = st.columns(2)
    with col1:
        size = st.selectbox("Tamaño:", ["6 x 9 pulgadas", "5 x 8 pulgadas", "8.5 x 11 pulgadas"])
        theme_choice = st.selectbox("🎨 Tema Visual:", list(THEMES.keys())) 
    with col2:
        margins = st.radio("Márgenes:", ["Espejo (Doble Cara)", "Normales"])

    st.markdown("---")
    st.subheader("🛠️ Opciones de Estilo")
    
    col3, col4 = st.columns(2)
    with col3:
        fix_titles = st.checkbox("📎 Detectar Títulos", value=True)
        pro_start = st.checkbox("✨ Activar Inicio de Capítulo", value=True)
        # CORRECCIÓN DE ETIQUETAS PARA QUE COINCIDA CON LA LÓGICA
        start_style = st.selectbox("Estilo de Inicio:", ["Letra Capital (Big Letter)", "Frase Versalitas (Small Caps)"])
        
    with col4:
        reconstruct = st.checkbox("🔗 Unir párrafos rotos (Reconstructor)", value=True)
        justify_text = st.checkbox("📄 Justificar + Silabeo", value=True)
        add_numbers = st.checkbox("🔢 Agregar Números de Página", value=True)
        fix_runts = st.checkbox("🛡️ Evitar palabras sueltas (Runts)", value=True)

    uploaded_file = st.file_uploader("Sube manuscrito (.docx)", type=["docx"], key="mod2")

    if uploaded_file and st.button("🛠️ Procesar Libro"):
        doc = Document(uploaded_file)
        theme = THEMES[theme_choice] 
        
        # 1. RECONSTRUCCIÓN
        if reconstruct:
            with st.spinner("🔗 Reconstruyendo..."):
                stitch_paragraphs(doc)
        
        # 2. SILABEO
        if justify_text:
            try: enable_native_hyphenation(doc)
            except: pass
        
        # 3. PAGE SETUP
        if "6 x 9" in size: w, h = Inches(6), Inches(9)
        elif "5 x 8" in size: w, h = Inches(5), Inches(8)
        else: w, h = Inches(8.5), Inches(11)

        for section in doc.sections:
            section.page_width = w; section.page_height = h
            section.top_margin = Inches(0.75); section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.8); section.right_margin = Inches(0.6)
            if "Espejo" in margins: section.mirror_margins = True; section.gutter = Inches(0.15)
            if add_numbers:
                footer = section.footer
                p_footer = footer.paragraphs[0]
                p_footer.text = "" 
                add_page_number(p_footer)
                p_footer.style.font.name = theme['font']
                p_footer.style.font.size = Pt(10)

        # 4. ESTILOS
        style = doc.styles['Normal']
        style.font.name = theme['font']
        style.font.size = Pt(theme['size'])
        style.paragraph_format.line_spacing = 1.25 
        style.paragraph_format.space_after = Pt(0)
        style.paragraph_format.widow_control = True 
        if justify_text: style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        for h in ['Heading 1', 'Heading 2']:
            try:
                h_style = doc.styles[h]
                h_style.font.name = theme['header']
                h_style.font.color.rgb = RGBColor(0, 0, 0)
                # IMPORTANTE: Space Before en 0. Usamos el truco del Enter (\n) para consistencia.
                h_style.paragraph_format.space_before = Pt(0) 
                h_style.paragraph_format.space_after = Pt(30) 
                h_style.alignment = WD_ALIGN_PARAGRAPH.CENTER 
                h_style.paragraph_format.page_break_before = True
                h_style.paragraph_format.keep_with_next = True
            except: pass

        total_p = len(doc.paragraphs)
        p_bar = st.progress(0)
        previous_was_heading = False 
        
        first_paragraph_found = False

        for i, p in enumerate(doc.paragraphs):
            text_clean = p.text.strip()
            if len(text_clean) < 2: continue 

            is_style_heading = p.style.name.startswith('Heading')
            is_visual_heading = False
            if len(text_clean) < 60:
                if re.match(r'^(chapter|cap[íi]tulo|part|parte|pr[óo]logo|prologue|intro)\b', text_clean, re.IGNORECASE):
                    is_visual_heading = True
                elif re.match(r'^[IVXLCDM]+\.?$', text_clean): is_visual_heading = True
                elif text_clean.isupper() and len(text_clean) > 3: is_visual_heading = True

            if is_style_heading or is_visual_heading:
                previous_was_heading = True
                p.style = doc.styles['Heading 1']
                
                # ECUALIZACIÓN DE TÍTULOS
                if not first_paragraph_found:
                    p.text = text_clean.upper() 
                    first_paragraph_found = True
                    p.paragraph_format.page_break_before = False 
                else:
                    p.text = "\n" + text_clean.upper() 
                    if fix_titles: 
                        p.paragraph_format.page_break_before = True
                        p.paragraph_format.keep_with_next = True
            else:
                if not first_paragraph_found: first_paragraph_found = True 
                
                if fix_runts and len(text_clean) > 50: prevent_runts_in_paragraph(p)
                if justify_text: p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

                # --- LÓGICA DE INICIO DE CAPÍTULO CORREGIDA ---
                if pro_start and previous_was_heading:
                    if "Big Letter" in start_style and len(text_clean) > 1:
                        first_char = text_clean[0]; rest_text = text_clean[1:]
                        p.text = "" 
                        run_big = p.add_run(first_char)
                        run_big.font.name = theme['header'] 
                        run_big.font.size = Pt(theme['size'] + 5) 
                        run_big.bold = True
                        run_rest = p.add_run(rest_text)
                        run_rest.font.name = theme['font']
                        run_rest.font.size = Pt(theme['size'])
                    elif "Small Caps" in start_style and len(text_clean.split()) > 3:
                        words = text_clean.split(); limit = min(3, len(words)) 
                        first_phrase = " ".join(words[:limit]); rest = " ".join(words[limit:])
                        p.text = ""
                        run = p.add_run(first_phrase + " ")
                        run.font.name = theme['font']; run.font.small_caps = True; run.bold = True
                        run_rest = p.add_run(rest)
                        run_rest.font.name = theme['font']; run_rest.font.small_caps = False; run_rest.bold = False
                    previous_was_heading = False
                else: previous_was_heading = False

            if i % 10 == 0: p_bar.progress((i+1)/total_p)

        bio = BytesIO(); doc.save(bio)
        st.success(f"✅ Libro Maquetado: {theme_choice} (Ecualizado)")
        st.download_button("⬇️ Descargar Libro KDP", bio.getvalue(), "Libro_KDP_Pro.docx")

# ==============================================================================
# MÓDULO 3: WORKBOOK
# ==============================================================================
elif "Workbook" in selected_module:
    st.header("📲 Workbook Cleaner")
    cta_text = st.text_area("Texto CTA:", "🛑 (Ejercicio): Completa esto en tu Cuaderno.", height=80)
    uploaded_file = st.file_uploader("Sube manuscrito", key="mod3")
    if uploaded_file and st.button("Limpiar"):
        doc = Document(uploaded_file)
        for p in doc.paragraphs:
            if re.search(f"([_.\-]){{4,}}", p.text): p.text = cta_text 
        bio = BytesIO(); doc.save(bio)
        st.download_button("⬇️ Descargar", bio.getvalue(), "Ebook.docx")

# ==============================================================================
# MÓDULO 4: LIMPIADOR
# ==============================================================================
elif "Limpiador" in selected_module:
    st.header("☢️ Limpiador 'Nuclear'")
    uploaded_file = st.file_uploader("Sube docx", key="mod4")
    if uploaded_file and st.button("Limpiar"):
        doc = Document(uploaded_file)
        for p in doc.paragraphs:
            if p.text: p.text = nuclear_clean(p.text)
        bio = BytesIO(); doc.save(bio)
        st.download_button("⬇️ Descargar", bio.getvalue(), "Limpio.docx")

# ==============================================================================
#
