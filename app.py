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
    if last_space != -1:
        paragraph.text = text[:last_space] + "\u00A0" + text[last_space+1:]

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
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) 
    text = re.sub(r'\*(.*?)\*', r'\1', text)      
    text = re.sub(r'__(.*?)__', r'\1', text)      
    text = re.sub(r'^#+\s*', '', text) 
    return nuclear_clean(text).strip()

def call_api(prompt, temp=0.7):
    for _ in range(3):
        try: return model.generate_content(prompt, generation_config={"temperature": temp}).text.strip()
        except: time.sleep(1)
    return "[ERROR API]"

# ==============================================================================
# MÓDULO 1: AUDITOR & CORRECTOR
# ==============================================================================
if "1." in selected_module:
    st.header("💎 Auditoría & Corrección IA")
    uploaded_file = st.file_uploader("Sube tu manuscrito", type=["docx"], key="mod1")
    if uploaded_file:
        doc = Document(uploaded_file)
        tab1, tab2 = st.tabs(["📊 Auditoría de Calidad", "🚀 Corrección de Estilo"])
        with tab1:
            if st.button("🔍 Iniciar Auditoría"):
                audit_doc = Document()
                audit_doc.add_heading("Reporte de Auditoría", 0)
                p_bar = st.progress(0)
                for i, p in enumerate(doc.paragraphs):
                    if len(p.text) > 15:
                        res = call_api(f"Analyze the following text for grammar or flow issues. Output 'CLEAN' if perfect, or describe the issue. Text: '{p.text[:400]}'")
                        if "CLEAN" not in res: audit_doc.add_paragraph(f"Párrafo {i+1}: {res}")
                    p_bar.progress((i+1)/len(doc.paragraphs))
                bio = BytesIO(); audit_doc.save(bio)
                st.download_button("⬇️ Descargar Reporte", bio.getvalue(), "Auditoria.docx")
        with tab2:
            if st.button("🚀 Re-escribir con IA"):
                new_doc = Document()
                p_bar = st.progress(0)
                for i, p in enumerate(doc.paragraphs):
                    if len(p.text) > 5:
                        res = call_api(f"Improve the flow and style of this text, keep original meaning: '{p.text}'")
                        new_doc.add_paragraph(clean_markdown(res))
                    else: new_doc.add_paragraph("")
                    p_bar.progress((i+1)/len(doc.paragraphs))
                bio = BytesIO(); new_doc.save(bio)
                st.download_button("⬇️ Descargar Corregido", bio.getvalue(), "Manuscrito_IA.docx")

# ==============================================================================
# MÓDULO 2: MAQUETADOR KDP PRO (PAPEL)
# ==============================================================================
elif "2." in selected_module
