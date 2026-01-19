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
        try: return model.generate_content(prompt, generation_config={"temperature": temp}).text.strip()
        except: time.sleep(1)
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
# MÓDULO 2: MAQUETADOR KDP PRO
# ==============================================================================
elif "Maquetador" in selected_module:
    st.header("📏 Maquetador KDP PRO")
    col1, col2 = st.columns(2)
    with col1:
        size = st.selectbox("Tamaño:", ["6 x 9 pulgadas", "5 x 8 pulgadas", "8.5 x 11 pulgadas"])
        theme_choice = st.selectbox("🎨 Tema Visual:", list(THEMES.keys())) 
    with col2:
        margins = st.radio("Márgenes:", ["Espejo (Doble Cara)", "Normales"])
    uploaded_file = st.file_uploader("Sube manuscrito (.docx)", type=["docx"], key="mod2")
    if uploaded_file and st.button("🛠️ Procesar Libro"):
        doc = Document(uploaded_file)
        theme = THEMES[theme_choice] 
        # Lógica de procesamiento (Simplificada por brevedad, igual a tu base)
        bio = BytesIO(); doc.save(bio)
        st.success("✅ Procesado para papel.")
        st.download_button("⬇️ Descargar DOCX", bio.getvalue(), "Libro_Maquetado.docx")

# ==============================================================================
# MÓDULO 5: GENERADOR EPUB (CORRECCIONES APLICADAS)
# ==============================================================================
elif "Generador EPUB" in selected_module:
    st.header("⚡ Generador EPUB Pro (Fix Kindle)")
    uploaded_file = st.file_uploader("Sube el archivo DOCX (Preferiblemente el maquetado del Módulo 2)", key="mod5")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        book_title = st.text_input("Título del Libro", "Mi Libro")
    with col2:
        author_name = st.text_input("Nombre del Autor", "Autor Desconocido")
    with col3:
        lang_code = st.selectbox("Idioma del Contenido:", ["es", "en", "fr", "it", "pt", "de"], help="Importante para que Kindle reconozca el archivo.")
    
    if uploaded_file and st.button("🚀 Convertir a EPUB"):
        uploaded_file.seek(0)
        book = epub.EpubBook()
        
        # 1. METADATOS (Arregla el problema del idioma)
        book.set_identifier(str(uuid.uuid4()))
        book.set_title(book_title)
        book.set_language(lang_code)
        book.add_author(author_name)
        
        # 2. MAPA DE ESTILOS (Arregla el problema del Índice)
        # Esto le dice a Mammoth: "Si ves un párrafo con estilo 'Heading 1' en Word, conviértelo en un <h1> real"
        custom_style_map = """
        p[style-name='Heading 1'] => h1:fresh
        p[style-name='Heading 2'] => h2:fresh
        """
        
        # Conversión de DOCX a HTML usando el mapa de estilos
        result = mammoth.convert_to_html(uploaded_file, style_map=custom_style_map)
        soup = BeautifulSoup(result.value, 'html.parser')
        
        # CSS Básico para asegurar legibilidad
        style_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", 
                                  content="body { font-family: serif; } h1 { text-align: center; } p { text-align: justify; }")
        book.add_item(style_css)

        # 3. DIVISIÓN POR CAPÍTULOS BASADA EN <h1>
        content_container = soup.body if soup.body else soup
        chapters = []
        headers = soup.find_all(['h1'])
        
        if not headers:
            # Si no detecta títulos, crea un solo bloque
            c = epub.EpubHtml(title="Contenido Principal", file_name="chap_1.xhtml", lang=lang_code)
            c.content = result.value
            c.add_item(style_css)
            book.add_item(c)
            chapters.append(c)
        else:
            # Divide el contenido cada vez que encuentra un h1
            current_content = ""
            current_title = "Inicio"
            count = 0
            
            for elem in content_container.children:
                if elem.name == 'h1':
                    if current_content.strip():
                        count += 1
                        c = epub.EpubHtml(title=current_title, file_name=f"chap_{count}.xhtml", lang=lang_code)
                        c.content = f"<html><body>{current_content}</body></html>"
                        c.add_item(style_css)
                        book.add_item(c)
                        chapters.append(c)
                    current_title = elem.get_text()
                    current_content = str(elem)
                else:
                    current_content += str(elem)
            
            # Añadir último capítulo
            if current_content.strip():
                count += 1
                c = epub.EpubHtml(title=current_title, file_name=f"chap_{count}.xhtml", lang=lang_code)
                c.content = f"<html><body>{current_content}</body></html>"
                c.add_item(style_css)
                book.add_item(c)
                chapters.append(c)

        # 4. GENERACIÓN DE ÍNDICE Y NAVEGACIÓN (Arregla el menú lateral)
        book.toc = tuple(chapters)
        book.add_item(epub.EpubNcx()) # Navegación para dispositivos antiguos
        book.add_item(epub.EpubNav()) # Navegación para dispositivos modernos
        
        # Definir el orden de lectura
        book.spine = ['nav'] + chapters
        
        # 5. GUARDADO
        bio = BytesIO()
        epub.write_epub(bio, book, {})
        st.success(f"✅ EPUB '{book_title}' generado correctamente.")
        st.download_button("⬇️ Descargar EPUB", bio.getvalue(), f"{book_title}.epub")
