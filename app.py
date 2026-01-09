import streamlit as st
from docx import Document
from docx.shared import Inches, Mm
import google.generativeai as genai
from io import BytesIO
import time
import os
import re

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="KDP Flow: Maquetador IA", page_icon="📚", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #ff9900; } /* Naranja Amazon */
    .success-box { padding: 10px; background-color: #fff3cd; border-left: 5px solid #ff9900; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURACIÓN API ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Amazon_logo.svg/1024px-Amazon_logo.svg.png", width=100)
    st.header("KDP Flow 1.0")
    
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("✅ Motor IA Conectado")
    except Exception as e:
        st.error("❌ Falta API Key")
        st.stop()
    
    st.divider()

    # --- NUEVA SECCIÓN: MAQUETACIÓN FÍSICA ---
    st.subheader("📏 Formato de Papel (KDP)")
    
    paper_size = st.selectbox(
        "Tamaño de Libro:",
        ["Mismo que original (No tocar)", "6 x 9 pulgadas (Estándar Novela)", "5 x 8 pulgadas (Bolsillo)", "8.5 x 11 pulgadas (Cuento/Educativo)"]
    )
    
    margins_mode = st.radio(
        "Márgenes:",
        ["Estándar", "Espejo (Para impresión a doble cara)"]
    )

    st.divider()

    # --- MOTOR DE IA (INTOCABLE) ---
    st.subheader("🧠 Motor de Corrección")
    MODEL_NAME = 'models/gemini-flash-latest' 
    model = genai.GenerativeModel(MODEL_NAME)
    
    tone_option = st.selectbox(
        "Tono Literario:", 
        ["Warm & Kid-Friendly (Infantil)", "Strict Grammar (Neutro)"]
    )

    if "Kid-Friendly" in tone_option:
        tone_prompt = "Tone: Warm, empathetic, validating. Simple vocabulary (Age 6-10)."
        temp = 0.7
    else:
        tone_prompt = "Tone: Neutral. Keep author's voice exact."
        temp = 0.3

# --- 3. FUNCIONES DE LÓGICA ---

def apply_kdp_layout(doc, size_selection, margin_mode):
    """
    Esta función cambia físicamente el tamaño de la hoja en Word.
    NO toca el texto, solo el papel.
    """
    if "Mismo que original" in size_selection:
        return doc # No hacemos nada

    # Definir medidas según selección
    if "6 x 9" in size_selection:
        width, height = Inches(6), Inches(9)
    elif "5 x 8" in size_selection:
        width, height = Inches(5), Inches(8)
    elif "8.5 x 11" in size_selection:
        width, height = Inches(8.5), Inches(11)
    
    # Aplicar a TODAS las secciones del documento
    for section in doc.sections:
        section.page_width = width
        section.page_height = height
        
        # Márgenes seguros para KDP (0.5 pulgadas mínimo)
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75) 
        section.right_margin = Inches(0.6) # Un poco menos a la derecha
        
        # Márgenes Espejo (Mirror Margins) para libros impresos
        if margin_mode == "Espejo":
            section.mirror_margins = True
            section.gutter = Inches(0.13) # Espacio para el pegamento del lomo
            
    return doc

def clean_markdown(text):
    """Limpieza de símbolos para que Amazon no rechace el libro"""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) 
    text = re.sub(r'\*(.*?)\*', r'\1', text)     
    text = re.sub(r'__(.*?)__', r'\1', text)     
    text = re.sub(r'^#+\s*', '', text) 
    if text.strip().startswith("- "): text = text.strip()[2:] 
    return text.strip()

def call_api(prompt, temperature=0.7):
    # Reintentos simples
    for _ in range(3):
        try:
            return model.generate_content(prompt, generation_config={"temperature": temperature}).text.strip()
        except:
            time.sleep(1)
    return "[ERROR API]"

def process_paragraph_text(text, mode, tone_instr, temp):
    if len(text.strip()) < 2: return text 

    # --- AQUÍ ESTÁ EL PROMPT QUE GARANTIZA LA CORRECCIÓN NATIVA ---
    if mode == "audit":
        prompt = f"""
        ACT AS A PROFESSIONAL EDITOR. Audit this text.
        CHECKS: Whirlwind=HE. No 'outsourcing'. Native Phrasing.
        OUTPUT: List issues or "CLEAN".
        Text: "{text}"
        """
    else: 
        prompt = f"""
        You are a professional book editor.
        Rewrite this text to be native US English.
        
        RULES:
        1. OUTPUT PLAIN TEXT ONLY. NO MARKDOWN (No **, No ##).
        2. Grammar: Whirlwind = He/Him. No 'outsourcing'.
        3. Style: Native, fluid English. Tone: {tone_instr}
        4. KEEP original sentence structure intact.
        
        Text: "{text}"
        """
    
    result = call_api(prompt, temp)
    if mode == "rewrite": result = clean_markdown(result)
    return result

# --- 4. INTERFAZ PRINCIPAL ---
st.title("📚 KDP Flow: De Word a Amazon")
st.markdown("Tu asistente personal para publicar libros perfectos.")

# Recuperación
if os.path.exists("temp_kdp_book.docx"):
    st.warning("⚠️ Trabajo no guardado detectado.")
    with open("temp_kdp_book.docx", "rb") as f:
        st.download_button("⬇️ Rescatar Libro", f, "Libro_Rescatado.docx")

if "final_doc_bio" not in st.session_state: st.session_state.final_doc_bio = None

uploaded_file = st.file_uploader("Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file:
    original_doc = Document(uploaded_file)
    total_paras = len(original_doc.paragraphs)
    st.info(f"📖 Manuscrito cargado: {total_paras} párrafos.")

    tab1, tab2 = st.tabs(["🔍 Auditoría (Revisar)", "🚀 Generar Libro KDP (Publicar)"])

    with tab1:
        if st.button("🔍 Auditar Texto"):
            st.write("Analizando gramática y estilo...")
            audit_doc = Document()
            audit_doc.add_heading("Reporte de Auditoría", 0)
            
            progress = st.progress(0)
            for i, p in enumerate(original_doc.paragraphs):
                if len(p.text) > 5:
                    res = process_paragraph_text(p.text, "audit", tone_prompt, temp)
                    if "CLEAN" not in res and "[ERROR" not in res:
                        audit_doc.add_paragraph(f"Párrafo {i+1}: {res}")
                progress.progress((i+1)/total_paras)
            
            bio = BytesIO()
            audit_doc.save(bio)
            st.download_button("⬇️ Bajar Reporte", bio.getvalue(), "Reporte_Auditoria.docx")

    with tab2:
        st.write("Esto hará dos cosas a la vez:")
        st.markdown("1. **Corregir Inglés:** Gramática nativa, limpieza de género y tono.")
        st.markdown(f"2. **Maquetar:** Ajustará el papel a **{paper_size}** con márgenes **{margins_mode}**.")
        
        if st.button("🚀 CREAR LIBRO MAESTRO"):
            # 1. Clonar original
            uploaded_file.seek(0)
            working_doc = Document(uploaded_file)
            
            # 2. APLICAR FORMATO KDP (La Magia Nueva 🌟)
            working_doc = apply_kdp_layout(working_doc, paper_size, margins_mode)
            
            # 3. PROCESAR TEXTO (La Magia Antigua 🧠)
            progress = st.progress(0)
            status = st.empty()
            
            # Usamos zip para editar in-place
            for i, (p_orig, p_dest) in enumerate(zip(original_doc.paragraphs, working_doc.paragraphs)):
                if len(p_orig.text) > 1:
                    status.text(f"Editando y Maquetando pág {i+1}...")
                    new_text = process_paragraph_text(p_orig.text, "rewrite", tone_prompt, temp)
                    if "[ERROR" not in new_text:
                        p_dest.text = new_text
                
                # Guardado de seguridad
                if i % 10 == 0: working_doc.save("temp_kdp_book.docx")
                progress.progress((i+1)/total_paras)
            
            status.success("✅ ¡Libro Terminado y Maquetado!")
            st.balloons()
            
            final_bio = BytesIO()
            working_doc.save(final_bio)
            st.session_state.final_doc_bio = final_bio

        if st.session_state.final_doc_bio:
            st.download_button(
                "⬇️ Descargar Libro Listo para Amazon (.docx)",
                st.session_state.final_doc_bio.getvalue(),
                "Libro_KDP_Final.docx"
            )
