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

def create_element(name): return OxmlElement(name)
def create_attribute(element, name, value): element.set(ns.qn(name), value)

def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    page_run = paragraph.add_run()
    t1 = create_element('w:fldChar'); create_attribute(t1, 'w:fldCharType', 'begin'); page_run._r.append(t1)
    t2 = create_element('w:instrText'); create_attribute(t2, 'xml:space', 'preserve'); t2.text = "PAGE"; page_run._r.append(t2)
    t3 = create_element('w:fldChar'); create_attribute(t3, 'w:fldCharType', 'end'); page_run._r.append(t3)

def enable_native_hyphenation(doc):
    settings = doc.settings.element
    hyphenation_zone = OxmlElement('w:autoHyphenation')
    create_attribute(hyphenation_zone, 'w:val', 'true')
    settings.append(hyphenation_zone)

def prevent_runts_in_paragraph(paragraph):
    text = paragraph.text.strip()
    if not text or len(text) < 20: return 
    last_space = text.rfind(' ')
    if last_space != -1: paragraph.text = text[:last_space] + "\u00A0" + text[last_space+1:]

def delete_paragraph(paragraph):
    p = paragraph._element
    p.getparent().remove(p)
    p._p = p._element = None

def stitch_paragraphs(doc):
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
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text); text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text); text = re.sub(r'^#+\s*', '', text)
    return nuclear_clean(text).strip()

def call_api(prompt, temp=0.7):
    for _ in range(3):
        try: return model.generate_content(prompt, generation_config={"temperature": temp}).text.strip()
        except: time.sleep(1)
    return "[ERROR API]"

# ==============================================================================
# MÓDULOS 1, 3, 4
# ==============================================================================
if "1." in selected_module:
    st.header("💎 Corrector"); uploaded_file = st.file_uploader("Docx", key="m1")
elif "3." in selected_module:
    st.header("📲 Workbook"); uploaded_file = st.file_uploader("Docx", key="m3")
elif "4." in selected_module:
    st.header("🧼 Limpiador"); uploaded_file = st.file_uploader("Docx", key="m4")

# ==============================================================================
# MÓDULO 2: MAQUETADOR KDP PRO (BASE ESTABLE V5.1)
# ==============================================================================
elif "2." in selected_module:
    st.header("📏 Maquetador KDP PRO 5.1 (Estable)")
    
    col1, col2 = st.columns(2)
    with col1:
        size = st.selectbox("Tamaño:", ["6 x 9 pulgadas", "5 x 8 pulgadas", "8.5 x 11 pulgadas"])
        theme_choice = st.selectbox("🎨 Tema Visual:", list(THEMES.keys())) 
    with col2:
        margins = st.radio("Márgenes:", ["Espejo (Doble Cara)", "Normales"])

    st.markdown("---")
    col3, col4 = st.columns(2)
    with col3:
        fix_titles = st.checkbox("📎 Detectar Títulos", value=True)
        pro_start = st.checkbox("✨ Activar Inicio de Capítulo", value=True)
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
        
        if reconstruct: stitch_paragraphs(doc)
        if justify_text: 
            try: enable_native_hyphenation(doc)
            except: pass
        
        if "6 x 9" in size: w, h = Inches(6), Inches(9)
        elif "5 x 8" in size: w, h = Inches(5), Inches(8)
        else: w, h = Inches(8.5), Inches(11)

        for section in doc.sections:
            section.page_width = w; section.page_height = h
            section.top_margin = Inches(0.75); section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.8); section.right_margin = Inches(0.6)
            if "Espejo" in margins: section.mirror_margins = True; section.gutter = Inches(0.15)
            if add_numbers:
                p_footer = section.footer.paragraphs[0]; p_footer.text = "" 
                add_page_number(p_footer)
                p_footer.style.font.name = theme['font']; p_footer.style.font.size = Pt(10)

        style = doc.styles['Normal']
        style.font.name = theme['font']; style.font.size = Pt(theme['size'])
        style.paragraph_format.line_spacing = 1.25; style.paragraph_format.space_after = Pt(0)
        style.paragraph_format.widow_control = True 
        if justify_text: style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        for h in ['Heading 1', 'Heading 2']:
            try:
                h_style = doc.styles[h]
                h_style.font.name = theme['header']; h_style.font.color.rgb = RGBColor(0,0,0)
                h_style.paragraph_format.space_before = Pt(0) 
                h_style.paragraph_format.space_after = Pt(30) 
                h_style.alignment = WD_ALIGN_PARAGRAPH.CENTER 
                h_style.paragraph_format.page_break_before = True
            except: pass

        total_p = len(doc.paragraphs)
        p_bar = st.progress(0)
        previous_was_heading = False 
        
        for i, p in enumerate(doc.paragraphs):
            text_clean = p.text.strip()
            if len(text_clean) < 2: continue 

            is_heading = False
            if p.style.name.startswith('Heading'): is_heading = True
            elif len(text_clean) < 60 and (re.match(r'^(chapter|cap[íi]tulo)\b', text_clean, re.I) or text_clean.isupper()): is_heading = True

            if is_heading:
                previous_was_heading = True
                p.style = doc.styles['Heading 1']
                p.text = "\n" + text_clean.upper() 
                if fix_titles: p.paragraph_format.keep_with_next = True
            else:
                if fix_runts and len(text_clean) > 50: prevent_runts_in_paragraph(p)
                if justify_text: p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                
                if pro_start and previous_was_heading:
                    if "Big Letter" in start_style and len(text_clean) > 1:
                        # MANTENEMOS LOGICA SIMPLE: BIG LETTER EN DOCX
                        char = text_clean[0]; rest = text_clean[1:]
                        p.text = ""; run = p.add_run(char)
                        run.font.name = theme['header']; run.font.size = Pt(theme['size']+5); run.bold = True
                        p.add_run(rest).font.name = theme['font']
                    elif "Small Caps" in start_style:
                        p.text = text_clean
                        p.runs[0].font.small_caps = True
                    previous_was_heading = False
                else: previous_was_heading = False
            
            if i % 10 == 0: p_bar.progress((i+1)/total_p)

        bio = BytesIO(); doc.save(bio)
        st.success(f"✅ Libro Maquetado: {theme_choice}")
        st.download_button("⬇️ Descargar Libro KDP", bio.getvalue(), "Libro_KDP_Pro.docx")

# ==============================================================================
# MÓDULO 5: GENERADOR EPUB (V5.9 - FIX ESPACIADO)
# ==============================================================================
elif "5." in selected_module:
    st.header("⚡ Generador EPUB 5.9")
    uploaded_file = st.file_uploader("Sube DOCX procesado", key="mod5")
    
    col1, col2, col3 = st.columns(3)
    with col1: book_title = st.text_input("Título", "Mi Libro")
    with col2: author_name = st.text_input("Autor", "Autor")
    # 1. SOLUCIÓN ERROR IDIOMA: Selector de idioma
    with col3: lang = st.selectbox("Idioma", ["en", "es"], help="Selecciona 'en' para libros en inglés")

    if uploaded_file and st.button("Convertir"):
        # Limpieza de trucos Word (Enter \n)
        doc_temp = Document(uploaded_file)
        for p in doc_temp.paragraphs:
            if p.style.name.startswith('Heading'):
                p.text = p.text.replace('\n', '').strip()
        
        buffer_limpio = BytesIO()
        doc_temp.save(buffer_limpio)
        buffer_limpio.seek(0)

        book = epub.EpubBook()
        book.set_identifier(str(uuid.uuid4()))
        book.set_title(book_title)
        book.set_language(lang) 
        book.add_author(author_name)
        
        # 2. SOLUCIÓN ÍNDICE: Mapa de estilos
        style_map = "p[style-name='Heading 1'] => h1:fresh"
        
        result = mammoth.convert_to_html(buffer_limpio, style_map=style_map)
        soup = BeautifulSoup(result.value, 'html.parser')
        
        # 3. SOLUCIÓN ESPACIADO FEO (El secreto está en line-height: 0.8em para la letra)
        css_style = """
        <style>
            h1 { margin-top: 3em !important; text-align: center; page-break-before: always; color: black; }
            p { text-align: justify; text-indent: 1em; margin-bottom: 0em; line-height: 1.5em; }
            
            /* CSS LETRA CAPITAL COMPACTA */
            h1 + p::first-letter {
                float: left;
                font-size: 3.5em;
                font-weight: bold;
                line-height: 0.8em; /* ESTA ES LA CLAVE: Hace que la letra no empuje la línea */
                padding-right: 0.1em;
                padding-top: 0.1em;
                color: black;
            }
        </style>
        """

        content = soup.body if soup.body else soup
        chapters = []
        headers = soup.find_all('h1') 
        
        if not headers:
            c = epub.EpubHtml(title="Inicio", file_name="chap_1.xhtml")
            c.content = css_style + str(content)
            book.add_item(c); chapters.append(c)
        else:
            curr_html = ""; curr_title = "Inicio"; count = 0
            for elem in content.children:
                if elem.name == 'h1':
                    if curr_html.strip():
                        count += 1
                        c = epub.EpubHtml(title=curr_title, file_name=f"c_{count}.xhtml")
                        c.content = css_style + f"<h1>{curr_title}</h1>{curr_html}" if count > 1 else css_style + curr_html
                        book.add_item(c); chapters.append(c)
                    curr_title = elem.get_text()
                    curr_html = ""
                else: curr_html += str(elem)
            
            if curr_html.strip():
                count += 1
                c = epub.EpubHtml(title=curr_title, file_name=f"c_{count}.xhtml")
                c.content = css_style + f"<h1>{curr_title}</h1>{curr_html}"
                book.add_item(c); chapters.append(c)

        book.toc = tuple(chapters)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav'] + chapters
        
        bio = BytesIO(); epub.write_epub(bio, book, {})
        st.success("✅ EPUB Listo (Índice OK + Idioma OK + Espaciado Compacto).")
        st.download_button("⬇️ Descargar EPUB", bio.getvalue(), f"{book_title}.epub")
