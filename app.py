import streamlit as st
from docx import Document
from docx.shared import RGBColor
import google.generativeai as genai
from io import BytesIO
import time

# --- 1. CONFIGURACIÓN VISUAL Y PÁGINA ---
st.set_page_config(page_title="NativeFlow Master", page_icon="✍️", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    .report-box { padding: 10px; border-radius: 5px; background-color: #f0f2f6; border-left: 5px solid #4CAF50; }
</style>
""", unsafe_allow_html=True)

# --- 2. BARRA LATERAL: CONFIGURACIÓN GLOBAL ---
with st.sidebar:
    st.header("⚙️ Configuración Editorial")
    
    # A. GESTIÓN DE API KEY
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("✅ API Conectada")
    except Exception as e:
        st.error("❌ Error de API Key")
        st.stop()

    st.divider()

    # B. SELECTOR DE TONO (Define cómo escribirá la IA)
    st.subheader("🎨 Estilo & Tono")
    tone_option = st.selectbox(
        "Objetivo de la Corrección:",
        options=[
            "Warm & Kid-Friendly (Recomendado)", 
            "Grammar Polish Only (Conservador)", 
            "Magical Storyteller (Creativo)"
        ],
        index=0
    )

    # Definimos las instrucciones internas según la elección
    if tone_option == "Warm & Kid-Friendly (Recomendado)":
        tone_instruction = "Tone: Warm, validating, empathetic. Simplify complex words for kids (6-10 years old)."
        temp_setting = 0.7 
        st.info("ℹ️ Ideal para libros de autoayuda infantil. Suaviza el lenguaje.")

    elif tone_option == "Grammar Polish Only (Conservador)":
        tone_instruction = "Tone: Neutral. KEEP the author's original style strictly. Only fix grammar, syntax errors, and unnatural phrasing."
        temp_setting = 0.3
        st.info("ℹ️ Solo arregla errores. No cambia tu estilo de escritura.")

    else: # Magical
        tone_instruction = "Tone: Whimsical, magical, and vivid. Use descriptive verbs and sensory language."
        temp_setting = 0.9
        st.info("ℹ️ Ideal para cuentos de fantasía. Aumenta la creatividad.")

# --- 3. LÓGICA DE IA (Funciones del Cerebro) ---

def get_model():
    """Intenta obtener el mejor modelo disponible con fallback."""
    try:
        return genai.GenerativeModel('gemini-2.5-flash')
    except:
        return genai.GenerativeModel('gemini-1.5-flash')

def audit_paragraph(text):
    """
    MODO AUDITORÍA: Solo detecta problemas, no reescribe.
    """
    if len(text.strip()) < 20: return None
    
    model = get_model()
    prompt = f"""
    You are a strict book editor. Analyze the text below based on these rules:
    1. **Whirlwind Gender:** Must be HE/HIM. Detect if 'she/her' is used.
    2. **Phrasing:** Detect clumsy "The X of Y" structures (e.g., "The breathing of the balloon").
    3. **Jargon:** Detect corporate words like "outsourcing".
    4. **Syntax:** Detect overly complex/Spanish-like sentence structures.

    Output format:
    - If issues found: A short description of the error (e.g., "Found 'outsourcing', suggest 'naming'").
    - If CLEAN: Output exactly "CLEAN".

    Text: "{text}"
    """
    try:
        response = model.generate_content(prompt)
        result = response.text.strip()
        return None if "CLEAN" in result else result
    except:
        return None

def rewrite_paragraph(text, instructions, temp):
    """
    MODO CORRECCIÓN: Reescribe aplicando el tono seleccionado.
    """
    if len(text.strip()) < 15: return text

    model = get_model()
    prompt = f"""
    You are an expert US English book editor.
    
    **TASK:** Rewrite the text below according to these specifications:
    {instructions}

    **MANDATORY RULES (Overrides everything):**
    1. **Consistency:** Character 'Whirlwind' is ALWAYS Male (he/him).
    2. **Vocabulary:** Replace 'outsourcing' with 'naming' or 'externalizing'.
    3. **Phrasing:** Fix "The [noun] of [noun]" -> use "[Noun] [Noun]" (e.g., "Balloon Breathing").
    4. **Output:** Return ONLY the rewritten text.

    **Original Text:**
    "{text}"
    """
    try:
        response = model.generate_content(prompt, generation_config={"temperature": temp})
        return response.text.strip()
    except:
        return text

# --- 4. INTERFAZ PRINCIPAL ---
st.title("✍️ NativeFlow: Panel de Edición")
st.markdown("Sube tu manuscrito y elige si quieres **Auditar** (ver errores) o **Corregir** (aplicar cambios).")

uploaded_file = st.file_uploader("📂 Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file:
    # Cargar documento en memoria una sola vez
    doc = Document(uploaded_file)
    total_paragraphs = len(doc.paragraphs)
    
    # PESTAÑAS DE NAVEGACIÓN
    tab_audit, tab_fix = st.tabs(["📊 Paso 1: Auditoría (Reporte)", "🚀 Paso 2: Corrección Final (Libro)"])

    # --- PESTAÑA 1: AUDITORÍA ---
    with tab_audit:
        st.header("Generar Reporte de Diagnóstico")
        st.markdown(f"""
        Esta herramienta analizará tu libro buscando:
        - Inconsistencias de género (Whirlwind).
        - Vocabulario corporativo (Outsourcing).
        - Fraseo no nativo.
        **No modificará tu libro**, solo creará un reporte en Word.
        """)
        
        if st.button("🔍 Iniciar Auditoría"):
            report_doc = Document()
            report_doc.add_heading('Reporte de Auditoría NativeFlow', 0)
            
            # Crear tabla
            table = report_doc.add_table(rows=1, cols=2)
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'Párrafo Original'
            hdr_cells[1].text = 'Problema Detectado'
            
            prog_bar = st.progress(0)
            status = st.empty()
            issues_count = 0
            
            for i, para in enumerate(doc.paragraphs):
                status.caption(f"Analizando párrafo {i+1}/{total_paragraphs}...")
                
                issue = audit_paragraph(para.text)
                
                if issue:
                    issues_count += 1
                    row_cells = table.add_row().cells
                    # Cortamos texto muy largo para que la tabla no sea gigante
                    row_cells[0].text = para.text[:200] + ("..." if len(para.text)>200 else "")
                    row_cells[1].text = issue
                
                prog_bar.progress((i + 1) / total_paragraphs)
                time.sleep(0.05) # Pequeña pausa para API

            status.success(f"✅ Auditoría terminada. Se encontraron {issues_count} problemas potenciales.")
            
            # Descargar Reporte
            bio_audit = BytesIO()
            report_doc.save(bio_audit)
            st.download_button(
                label="⬇️ Descargar Reporte (.docx)",
                data=bio_audit.getvalue(),
                file_name="Reporte_Auditoria.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    # --- PESTAÑA 2: CORRECCIÓN FINAL ---
    with tab_fix:
        st.header("Generar Manuscrito Final")
        st.markdown(f"""
        **Configuración Actual:**
        - **Tono:** {tone_option}
        - **Intensidad:** {temp_setting}
        
        Este proceso reescribirá todo el libro aplicando las correcciones.
        """)
        
        if st.button("🚀 Procesar Libro Completo"):
            final_doc = Document()
            prog_bar_fix = st.progress(0)
            status_fix = st.empty()
            
            for i, para in enumerate(doc.paragraphs):
                status_fix.caption(f"Reescribiendo párrafo {i+1}/{total_paragraphs}...")
                
                # Usamos la función de reescritura con el tono seleccionado en el Sidebar
                new_text = rewrite_paragraph(para.text, tone_instruction, temp_setting)
                
                new_para = final_doc.add_paragraph(new_text)
                new_para.style = para.style
                
                prog_bar_fix.progress((i + 1) / total_paragraphs)
                time.sleep(0.1) # Pausa técnica

            status_fix.success("✅ ¡Libro Completado!")
            
            # Descargar Libro Final
            bio_final = BytesIO()
            final_doc.save(bio_final)
            st.download_button(
                label="⬇️ Descargar Libro Corregido (.docx)",
                data=bio_final.getvalue(),
                file_name=f"NativeFlow_Final_{uploaded_file.name}",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
