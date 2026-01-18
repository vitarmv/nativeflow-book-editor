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
    """Inserta campo de número de página."""
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
    """
    Activa el motor de silabeo nativo de Word en el XML del documento.
    Esto permite que Word corte las palabras automáticamente para justificar mejor.
    """
    settings = doc.settings.element
    hyphenation_zone = OxmlElement('w:autoHyphenation')
    create_attribute(hyphenation_zone, 'w:val', 'true')
    settings.append(hyphenation_zone)

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
# MÓDULO 2: MAQUETADOR KDP PRO (V4.1 - JUSTIFICACIÓN PERFECTA)
# ==============================================================================
elif "Maquetador" in selected_module:
    st.header("📏 Maquetador KDP PRO 4.1")
    
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
        start_style = st.selectbox("Estilo de Inicio:", ["Letra Capital (Big Letter)", "Frase Versalitas (Small Caps)"])
        
    with col4:
        fix_spaces = st.checkbox("☢️ Limpieza Nuclear", value=True)
        justify_text = st.checkbox("📄 Justificar + Silabeo (Hyphenation)", value=True, help="Activa el corte de palabras de Word para evitar ríos blancos.")
        add_numbers = st.checkbox("🔢 Agregar Números de Página", value=True)

    uploaded_file = st.file_uploader("Sube manuscrito (.docx)", type=["docx"], key="mod2")

    if uploaded_file and st.button("🛠️ Procesar Libro"):
        doc = Document(uploaded_file)
        theme = THEMES[theme_choice] 
        
        # --- ACTIVAR SILABEO NATIVO DE WORD ---
        if justify_text:
            try:
                enable_native_hyphenation(doc)
            except:
                st.warning("No se pudo activar el silabeo automático en el XML.")
        # --------------------------------------
        
        # 1. PAGE SETUP
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

        # 2. CONFIGURACIÓN DE ESTILOS
        style = doc.styles['Normal']
        style.font.name = theme['font']
        style.font.size = Pt(theme['size'])
        style.paragraph_format.line_spacing = 1.25 
        style.paragraph_format.space_after = Pt(0) 
        
        # Estilos de Título
        for h in ['Heading 1', 'Heading 2']:
            try:
                h_style = doc.styles[h]
                h_style.font.name = theme['header']
                h_style.font.color.rgb = RGBColor(0, 0, 0)
                h_style.paragraph_format.space_before = Pt(0) 
                h_style.paragraph_format.space_after = Pt(30) 
                h_style.alignment = WD_ALIGN_PARAGRAPH.CENTER 
                h_style.paragraph_format.page_break_before = True
                h_style.paragraph_format.keep_with_next = True
            except: pass

        total_p = len(doc.paragraphs)
        p_bar = st.progress(0)
        previous_was_heading = False 

        for i, p in enumerate(doc.paragraphs):
            
            if fix_spaces and len(p.text) > 0:
                clean = nuclear_clean(p.text)
                if clean != p.text: p.text = clean
            
            text_clean = p.text.strip()
            
            # A. SALTAR VACÍOS
            if len(text_clean) < 2:
                continue 

            # B. DETECTAR TÍTULO
            is_style_heading = p.style.name.startswith('Heading')
            is_visual_heading = False
            
            if len(text_clean) < 60:
                if re.match(r'^(chapter|cap[íi]tulo|part|parte|pr[óo]logo|prologue|intro)\b', text_clean, re.IGNORECASE):
                    is_visual_heading = True
                elif re.match(r'^[IVXLCDM]+\.?$', text_clean):
                    is_visual_heading = True
                elif text_clean.isupper() and len(text_clean) > 3:
                    is_visual_heading = True

            if is_style_heading or is_visual_heading:
                previous_was_heading = True
                p.style = doc.styles['Heading 1']
                p.text = "\n" + text_clean.upper() 
                
                if fix_titles: 
                    p.paragraph_format.keep_with_next = True
                    p.paragraph_format.page_break_before = True
            
            # C. CUERPO DE TEXTO
            else:
                if justify_text: p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                
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
                else:
                    previous_was_heading = False

            if i % 10 == 0: p_bar.progress((i+1)/total_p)

        bio = BytesIO(); doc.save(bio)
        st.success(f"✅ Libro Maquetado: {theme_choice} (Silabeo Activado)")
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
# MÓDULO 5: EPUB
# ==============================================================================
elif "Generador EPUB" in selected_module:
    st.header("⚡ Generador EPUB")
    uploaded_file = st.file_uploader("Sube Manuscrito", key="mod5")
    if uploaded_file and st.button("Convertir"):
        book = epub.EpubBook()
        book.set_identifier(str(uuid.uuid4()))
        book.set_title("Mi Libro")
        book.set_language("es")
        
        result = mammoth.convert_to_html(uploaded_file)
        soup = BeautifulSoup(result.value, 'html.parser')
        
        chapters = []
        headers = soup.find_all(['h1'])
        
        if not headers:
            c = epub.EpubHtml(title="Inicio", file_name="chap_1.xhtml")
            c.content = result.value
            book.add_item(c); chapters.append(c)
        else:
            current_content = ""; current_title = "Inicio"; count = 0
            for elem in soup.body.children:
                if elem.name == 'h1':
                    if current_content:
                        count += 1
                        c = epub.EpubHtml(title=current_title, file_name=f"chap_{count}.xhtml")
                        c.content = f"<h1>{current_title}</h1>{current_content}"
                        book.add_item(c); chapters.append(c)
                    current_title = elem.get_text(); current_content = ""
                else: current_content += str(elem)
            if current_content:
                count += 1
                c = epub.EpubHtml(title=current_title, file_name=f"chap_{count}.xhtml")
                c.content = f"<h1>{current_title}</h1>{current_content}"
                book.add_item(c); chapters.append(c)

        book.toc = tuple(chapters)
        book.add_item(epub.EpubNcx()); book.add_item(epub.EpubNav())
        book.spine = ['nav'] + chapters
        
        bio = BytesIO(); epub.write_epub(bio, book, {})
        st.success("✅ EPUB Creado.")
        st.download_button("⬇️ Descargar EPUB", bio.getvalue(), "Libro.epub")
