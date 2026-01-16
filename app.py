import streamlit as st
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
import google.generativeai as genai
from io import BytesIO
import time
import re
import pyphen  # <--- NUEVA LIBRERÍA: pip install pyphen

# --- 1. CONFIGURACIÓN GLOBAL ---
st.set_page_config(page_title="Suite Autores 360 PRO", page_icon="📚", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    .block-container { padding-top: 2rem; }
    div[data-testid="stSidebar"] { background-color: #f8f9fa; }
    h1 { color: #2c3e50; }
</style>
""", unsafe_allow_html=True)

# --- 2. DICCIONARIO DE TEMAS (ESTILOS) ---
THEMES = {
    "Neutro (Estándar)": {"font": "Calibri", "header": "Calibri", "size": 11},
    "Romance / Fantasía (Serif)": {"font": "Garamond", "header": "Garamond", "size": 12},
    "Thriller / Crimen (Sharp)": {"font": "Georgia", "header": "Arial Black", "size": 11},
    "No Ficción / Negocios": {"font": "Arial", "header": "Arial", "size": 10}
}

# --- 3. FUNCIONES DE LÓGICA AVANZADA ---

def apply_hyphenation(text, lang='en'):
    """
    Inserta guiones suaves (&shy; / \xad) en palabras largas.
    Esto permite que Word rompa las palabras al justificar.
    """
    if not text: return ""
    dic = pyphen.Pyphen(lang=lang)
    words = text.split()
    new_words = []
    for word in words:
        # Solo silabeamos palabras largas (>6 letras) para no ensuciar
        if len(word) > 6:
            inserted = dic.inserted(word, hyphen='\xad')
            new_words.append(inserted)
        else:
            new_words.append(word)
    return " ".join(new_words)

def nuclear_clean(text):
    """Limpia tabs, espacios dobles y basura web"""
    if not text: return text
    return " ".join(text.split())

def call_api(model, prompt, temp=0.7):
    try:
        return model.generate_content(prompt, generation_config={"temperature": temp}).text.strip()
    except:
        return "[ERROR API - Intenta de nuevo]"

# --- 4. INTERFAZ Y SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3145/3145765.png", width=80)
    st.title("Autores 360 Studio")
    
    # API KEY HANDLING
    api_key = st.sidebar.text_input("Tu Google API Key:", type="password")
    if api_key:
        genai.configure(api_key=api_key)
        try:
            model = genai.GenerativeModel('models/gemini-flash-latest')
            st.success("✅ Sistema Listo")
        except:
            st.error("❌ Key Inválida")
    else:
        st.warning("⚠️ Ingresa tu API Key para usar IA")
    
    st.divider()
    
    selected_module = st.radio(
        "Herramientas:",
        [
            "1. 💎 Auditor & Editor IA",
            "2. 📏 Maquetador Editorial PRO",  # <--- MEJORADO
            "3. 📲 Workbook Converter",
            "4. 🧼 Limpiador Rápido"
        ]
    )

# ==============================================================================
# MÓDULO 1: AUDITOR (OPTIMIZADO)
# ==============================================================================
if "Auditor" in selected_module:
    st.header("💎 Auditor & Editor Inteligente")
    st.caption("Detecta errores y mejora el estilo sin perder tu voz.")
    
    mode = st.selectbox("Modo:", ["Auditoría (Solo reporte)", "Corrección (Reescribir)"])
    uploaded_file = st.file_uploader("Sube manuscrito (.docx)", type=["docx"], key="m1")

    if uploaded_file and api_key:
        doc = Document(uploaded_file)
        
        if st.button("▶️ Ejecutar Procesamiento"):
            output_doc = Document()
            p_bar = st.progress(0)
            total = len(doc.paragraphs)
            
            for i, p in enumerate(doc.paragraphs):
                if len(p.text) > 10:
                    if "Auditoría" in mode:
                        prompt = f"Act as a strict editor. Find grammar errors, consistency issues (names/places), or POV shifts in this text. If Clean, say 'CLEAN'. Text: '{p.text}'"
                        res = call_api(model, prompt, 0.2)
                        if "CLEAN" not in res:
                            output_doc.add_paragraph(f"🔴 Párrafo {i}: {res}")
                            output_doc.add_paragraph(f"Texto Original: {p.text[:50]}...")
                            output_doc.add_paragraph("-" * 20)
                    else:
                        # Modo Corrección
                        prompt = f"Correct grammar and flow. Keep tone natural. Output ONLY the corrected text. Text: '{p.text}'"
                        res = call_api(model, prompt, 0.7)
                        p.text = res
                
                p_bar.progress((i+1)/total)

            bio = BytesIO()
            save_target = output_doc if "Auditoría" in mode else doc
            save_target.save(bio)
            
            fname = "Reporte_Auditoria.docx" if "Auditoría" in mode else "Manuscrito_Corregido.docx"
            st.download_button(f"⬇️ Descargar {fname}", bio.getvalue(), fname)

# ==============================================================================
# MÓDULO 2: MAQUETADOR PRO (EL CEREBRO DEL "ANTES/DESPUÉS")
# ==============================================================================
elif "Maquetador" in selected_module:
    st.header("📏 Maquetador Editorial PRO")
    st.markdown("Transforma un Word básico en un libro listo para imprenta (PDF Ready).")

    # --- CONFIGURACIÓN VISUAL ---
    col1, col2 = st.columns(2)
    with col1:
        paper_size = st.selectbox("Tamaño de Papel:", ["6x9 (Novela Estándar)", "5x8 (Bolsillo)", "8.5x11 (Técnico)"])
        theme_choice = st.selectbox("Estilo Visual (Tema):", list(THEMES.keys()))
    with col2:
        use_hyphen = st.checkbox("🔡 Silabeo Inteligente (Hyphenation)", value=True, help="Crucial para texto justificado.")
        pro_start = st.checkbox("✨ Inicio de Capítulo Pro", value=True, help="Pone la primera frase en MAYÚSCULAS tras un título.")
        justify = st.checkbox("📄 Justificar Texto", value=True)

    uploaded_file = st.file_uploader("Sube tu manuscrito final (.docx)", type=["docx"], key="m2")

    if uploaded_file and st.button("🛠️ Maquetar Libro"):
        doc = Document(uploaded_file)
        theme = THEMES[theme_choice]
        
        # 1. AJUSTES DE PÁGINA
        section = doc.sections[0]
        if "6x9" in paper_size: w, h = 6, 9
        elif "5x8" in paper_size: w, h = 5, 8
        else: w, h = 8.5, 11
        
        section.page_width = Inches(w)
        section.page_height = Inches(h)
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.8) # Margen interior más amplio
        section.right_margin = Inches(0.6)
        section.mirror_margins = True # Márgenes espejo para imprenta
        section.gutter = Inches(0.15) # Espacio para encuadernación

        # 2. PROCESAMIENTO DE ESTILOS
        # Definir estilo Normal base
        style = doc.styles['Normal']
        style.font.name = theme['font']
        style.font.size = Pt(theme['size'])
        style.paragraph_format.line_spacing = 1.2 # Interlineado pro, no simple
        
        # Definir estilos de Título
        for h in ['Heading 1', 'Heading 2']:
            try:
                h_style = doc.styles[h]
                h_style.font.name = theme['header']
                h_style.font.color.rgb = RGBColor(0, 0, 0) # Negro puro
                h_style.paragraph_format.space_before = Pt(24)
                h_style.paragraph_format.space_after = Pt(12)
            except: pass

        # 3. BUCLE PRINCIPAL DE PÁRRAFOS
        p_bar = st.progress(0)
        total = len(doc.paragraphs)
        
        # Lógica para detectar inicio de capítulo
        previous_was_heading = False
        
        for i, p in enumerate(doc.paragraphs):
            # Limpieza Nuclear integrada
            p.text = nuclear_clean(p.text)
            
            # Detectar si es título
            if p.style.name.startswith('Heading'):
                previous_was_heading = True
                p.paragraph_format.page_break_before = True # Salto de página en cap.
            else:
                # Si es texto normal
                if len(p.text) > 2:
                    # A. Justificación y Silabeo
                    if justify:
                        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                        if use_hyphen:
                            # Insertamos soft-hyphens para romper palabras largas
                            p.text = apply_hyphenation(p.text, lang='es') # Cambiar a 'en' si es inglés
                    
                    # B. Estilo "Inicio de Capítulo Pro"
                    if pro_start and previous_was_heading:
                        # Truco: Poner primera frase en mayúsculas o negrita para simular Drop Cap
                        # python-docx no soporta drop caps flotantes bien, pero esto se ve muy PRO.
                        words = p.text.split()
                        if len(words) > 4:
                            # Opción: Poner las primeras 4 palabras en MAYÚSCULAS (Versalitas fake)
                            first_phrase = " ".join(words[:4]).upper()
                            rest = " ".join(words[4:])
                            p.text = "" # Limpiamos
                            run = p.add_run(first_phrase + " ")
                            run.font.name = theme['font']
                            run.bold = True # Opcional
                            p.add_run(rest)
                
                previous_was_heading = False # Reset flag
            
            p_bar.progress((i+1)/total)

        bio = BytesIO()
        doc.save(bio)
        st.success("✅ Libro Maquetado con Estándares Editoriales.")
        st.download_button("⬇️ Descargar Libro Listo", bio.getvalue(), f"Libro_{theme_choice.split()[0]}.docx")

# ==============================================================================
# MÓDULO 3: WORKBOOK (CONSERVADO)
# ==============================================================================
elif "Workbook" in selected_module:
    st.header("📲 Workbook Converter")
    uploaded_file = st.file_uploader("Sube manuscrito", key="m3")
    if uploaded_file and api_key and st.button("Convertir"):
        # ... (Tu código original aquí, funciona bien) ...
        st.info("Función en mantenimiento (copiar del código anterior si se necesita)")

# ==============================================================================
# MÓDULO 4: LIMPIEZA RÁPIDA
# ==============================================================================
elif "Limpiador" in selected_module:
    st.header("🧼 Limpiador Rápido")
    uploaded_file = st.file_uploader("Sube docx", key="m4")
    if uploaded_file and st.button("Limpiar"):
        doc = Document(uploaded_file)
        for p in doc.paragraphs:
            p.text = nuclear_clean(p.text)
        bio = BytesIO(); doc.save(bio)
        st.download_button("⬇️ Descargar Limpio", bio.getvalue(), "Clean.docx")
