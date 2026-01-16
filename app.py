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

# --- LIBRERÍAS NUEVAS PARA FUNCIONES PRO ---
import pyphen  # Para silabeo
import mammoth # Para conversión limpia a HTML
from bs4 import BeautifulSoup # Para estructurar el EPUB
from ebooklib import epub # Para armar el archivo .epub

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

# --- 2. DICCIONARIO DE TEMAS (MAQUETADOR PRO) ---
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
        # CONEXIÓN SEGURA A ST.SECRETS
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("✅ Motor IA Activo")
    except:
        st.error("❌ Falta API Key en Secrets")
        st.stop()
        
    st.divider()
    
    # --- MENÚ DE SELECCIÓN (5 MÓDULOS) ---
    selected_module = st.radio(
        "Selecciona Herramienta:",
        [
            "1. 💎 Auditor & Corrector IA",
            "2. 📏 Maquetador KDP PRO (Papel)",
            "3. 📲 Workbook Cleaner (Kindle)",
            "4. 🧼 Limpiador Rápido",
            "5. ⚡ Generador EPUB (eBook)"  # <--- NUEVO MÓDULO
        ]
    )
    
    st.divider()
    MODEL_NAME = 'models/gemini-flash-latest' 
    model = genai.GenerativeModel(MODEL_NAME)

# --- 4. FUNCIONES DE LÓGICA ---

def apply_hyphenation(text, lang='es'):
    """Inserta guiones suaves (\xad) para justificación perfecta."""
    if not text: return ""
    dic = pyphen.Pyphen(lang=lang)
    words = text.split()
    new_words = []
    for word in words:
        if len(word) > 6: 
            inserted = dic.inserted(word, hyphen='\xad')
            new_words.append(inserted)
        else:
            new_words.append(word)
    return " ".join(new_words)

def nuclear_clean(text):
    """Elimina tabs, espacios dobles y basura web."""
    if not text: return text
    return " ".join(text.split())

def clean_markdown(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) 
    text = re.sub(r'\*(.*?)\*', r'\1', text)      
    text = re.sub(r'__(.*?)__', r'\1', text)      
    text = re.sub(r'^#+\s*', '', text) 
    if text.strip().startswith("- "): text = text.strip()[2:] 
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
# MÓDULO 2: MAQUETADOR KDP PRO (FUSIONADO)
# ==============================================================================
elif "Maquetador" in selected_module:
    st.header("📏 Maquetador KDP PRO 2.0")
    st.markdown("Motor de diseño editorial con Temas, Silabeo y Estilos Pro.")

    # --- CONTROLES VISUALES ---
    col1, col2 = st.columns(2)
    with col1:
        size = st.selectbox("Tamaño:", ["6 x 9 pulgadas (Estándar)", "5 x 8 pulgadas", "8.5 x 11 pulgadas"])
        theme_choice = st.selectbox("🎨 Tema Visual:", list(THEMES.keys())) 
    with col2:
        margins = st.radio("Márgenes:", ["Normales", "Espejo (Doble Cara)"])

    st.markdown("---")
    st.subheader("⚙️ Ingeniería de Texto")
    
    col3, col4 = st.columns(2)
    with col3:
        fix_orphans = st.checkbox("🛡️ Proteger líneas huérfanas", value=True)
        fix_titles = st.checkbox("📎 Pegar Títulos (Keep with Next)", value=True)
        pro_start = st.checkbox("✨ Inicio Capítulo Pro (Small Caps)", value=True, help="Estilo elegante al iniciar capítulo.")
    with col4:
        fix_spaces = st.checkbox("☢️ Limpieza Nuclear", value=True)
        justify_text = st.checkbox("📄 Justificar + Silabeo (Hyphenation)", value=True, help="Evita ríos blancos.")

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
            section.left_margin = Inches(0.75); section.right_margin = Inches(0.6)
            if "Espejo" in margins: section.mirror_margins = True; section.gutter = Inches(0.13)

        # 2. APLICAR TEMA
        style = doc.styles['Normal']
        style.font.name = theme['font']
        style.font.size = Pt(theme['size'])
        
        for h in ['Heading 1', 'Heading 2']:
            try:
                h_style = doc.styles[h]
                h_style.font.name = theme['header']
                h_style.font.color.rgb = RGBColor(0, 0, 0) 
            except: pass

        # 3. PROCESAMIENTO
        count_fixed = 0
        p_bar = st.progress(0)
        total_p = len(doc.paragraphs)
        previous_was_heading = False 

        for i, p in enumerate(doc.paragraphs):
            
            # Limpieza
            if fix_spaces and len(p.text) > 0:
                clean = nuclear_clean(p.text)
                if clean != p.text:
                    p.text = clean
                    count_fixed += 1
            
            # Detección Títulos
            if p.style.name.startswith('Heading'):
                previous_was_heading = True
                if fix_titles: p.paragraph_format.keep_with_next = True
            
            else:
                # Texto Cuerpo
                if len(p.text) > 2:
                    # Justificación + Hyphenation
                    if justify_text:
                        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                        if len(p.text) > 60: p.text = apply_hyphenation(p.text)

                    # Estilo Inicio de Capítulo (Small Caps)
                    if pro_start and previous_was_heading:
                        words = p.text.split()
                        if len(words) > 4:
                            first_phrase = " ".join(words[:4])
                            rest = " ".join(words[4:])
                            p.text = "" 
                            run = p.add_run(first_phrase + " ")
                            run.font.name = theme['font']
                            run.font.small_caps = True  # <--- MAGIA AQUÍ
                            run.bold = True
                            p.add_run(rest)
                
                previous_was_heading = False 

            if fix_orphans: p.paragraph_format.widow_control = True 
            p_bar.progress((i+1)/total_p)

        bio = BytesIO(); doc.save(bio)
        st.success(f"✅ Maquetación completada: {theme_choice}")
        st.download_button("⬇️ Descargar Libro KDP", bio.getvalue(), "Libro_KDP_Pro.docx")

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
        p_bar = st.progress(0)
        for i, p in enumerate(doc.paragraphs):
            if re.search(f"([_.\-]){{{threshold},}}", p.text):
                prompt = f"Identify question. Remove lines. Add CTA: '{cta_text}'. Input: '{p.text}'"
                new_text = call_api(prompt)
                if new_text != p.text: p.text = new_text
            p_bar.progress((i+1)/len(doc.paragraphs))
        bio = BytesIO(); doc.save(bio)
        st.download_button("⬇️ Descargar eBook", bio.getvalue(), "Ebook_Ready.docx")

# ==============================================================================
# MÓDULO 4: LIMPIADOR NUCLEAR
# ==============================================================================
elif "Limpiador" in selected_module:
    st.header("☢️ Limpiador 'Nuclear' de Formato")
    uploaded_file = st.file_uploader("Sube docx", type=["docx"], key="mod4")
    if uploaded_file and st.button("🧹 Limpiar"):
        doc = Document(uploaded_file)
        count = 0
        for p in doc.paragraphs:
            if p.text:
                new_text = nuclear_clean(p.text)
                if new_text != p.text: p.text = new_text; count += 1
        st.success(f"✅ {count} arreglos realizados.")
        bio = BytesIO(); doc.save(bio)
        st.download_button("⬇️ Descargar Limpio", bio.getvalue(), "Limpio_Nuclear.docx")

# ==============================================================================
# MÓDULO 5: GENERADOR EPUB (FUSIONADO)
# ==============================================================================
elif "Generador EPUB" in selected_module:
    st.header("⚡ Generador de EPUB Nativo")
    st.markdown("Convierte DOCX a EPUB con Tabla de Contenidos automática.")
    
    col1, col2 = st.columns(2)
    with col1:
        book_title = st.text_input("Título del Libro", "Mi Novela")
        author_name = st.text_input("Autor", "Indie Author")
    with col2:
        lang_code = st.selectbox("Idioma", ["es", "en"])
        cover_file = st.file_uploader("Portada (JPG) - Opcional", type=["jpg", "jpeg"])

    uploaded_file = st.file_uploader("Sube tu Manuscrito (.docx)", type=["docx"], key="mod5")

    if uploaded_file and st.button("📲 Convertir a EPUB"):
        
        # 1. Configuración del Libro
        book = epub.EpubBook()
        book.set_identifier(str(uuid.uuid4()))
        book.set_title(book_title)
        book.set_language(lang_code)
        book.add_author(author_name)
        
        if cover_file:
            book.set_cover("cover.jpg", cover_file.read())
            
        # 2. Conversión DOCX -> HTML (Mammoth)
        result = mammoth.convert_to_html(uploaded_file)
        html_content = result.value
        
        # 3. Parsing de Capítulos (BeautifulSoup)
        soup = BeautifulSoup(html_content, 'html.parser')
        chapters = []
        
        # Detectamos Títulos (h1, h2...)
        headers = soup.find_all(['h1'])
        
        if not headers:
            st.warning("⚠️ No se detectaron Títulos H1. Se creará un solo capítulo.")
            c1 = epub.EpubHtml(title="Inicio", file_name="chap_01.xhtml", lang=lang_code)
            c1.content = html_content
            book.add_item(c1)
            chapters.append(c1)
        else:
            # Algoritmo de corte de capítulos
            current_content = ""
            current_title = "Front Matter"
            count = 0
            
            for element in soup.body.children:
                elem_str = str(element)
                if element.name == 'h1':
                    if current_content.strip():
                        count += 1
                        c = epub.EpubHtml(title=current_title, file_name=f"chap_{count}.xhtml", lang=lang_code)
                        c.content = f"<h1>{current_title}</h1>{current_content}" if count > 0 else current_content
                        # Añadir CSS básico
                        c.add_item(epub.EpubItem(uid="style", file_name="style.css", media_type="text/css", content="body{font-family:serif} h1{text-align:center}"))
                        book.add_item(c)
                        chapters.append(c)
                    
                    current_title = element.get_text()
                    current_content = ""
                else:
                    current_content += elem_str
            
            # Último capítulo
            if current_content.strip():
                count += 1
                c = epub.EpubHtml(title=current_title, file_name=f"chap_{count}.xhtml", lang=lang_code)
                c.content = f"<h1>{current_title}</h1>{current_content}"
                book.add_item(c)
                chapters.append(c)

        # 4. Empaquetado final
        book.toc = tuple(chapters)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav'] + chapters

        bio = BytesIO()
        epub.write_epub(bio, book, {})
        
        st.success(f"✅ EPUB Creado con {len(chapters)} capítulos.")
        st.download_button("⬇️ Descargar EPUB", bio.getvalue(), f"{book_title}.epub")
