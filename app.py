import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NativeFlow 2.5", page_icon="📚", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    .success-box { padding: 10px; background-color: #d4edda; border-left: 5px solid #28a745; border-radius: 5px; }
    .error-box { padding: 10px; background-color: #f8d7da; border-left: 5px solid #dc3545; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 2. BARRA LATERAL: CONFIGURACIÓN ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    
    # CONEXIÓN API
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        
        # --- AQUÍ ESTÁ LA CORRECCIÓN CLAVE ---
        # Usamos el modelo exacto que tienes disponible
        MODEL_NAME = 'gemini-2.5-flash' 
        model = genai.GenerativeModel(MODEL_NAME)
        st.success(f"🚀 Motor Activo: {MODEL_NAME}")
        
    except Exception as e:
        st.error("❌ Error de API Key o Modelo")
        st.caption(f"Detalle: {e}")
        st.stop()

    st.divider()

    # SELECTOR DE TONO
    st.subheader("🎨 Tono de la Edición")
    tone_option = st.selectbox(
        "Objetivo:",
        options=[
            "Warm & Kid-Friendly (Tu Estilo)", 
            "Strict Grammar (Solo Corrección)", 
            "Storyteller (Más Creativo)"
        ]
    )

    # Configuración de instrucciones según el tono
    if tone_option == "Warm & Kid-Friendly (Tu Estilo)":
        tone_prompt = "Tone: Warm, validating, empathetic. Simplify complex words for kids (6-10 years). Use 'Balloon Breathing' style naming."
        temp = 0.7
    elif tone_option == "Strict Grammar (Solo Corrección)":
        tone_prompt = "Tone: Neutral. Keep author's exact voice. Only fix grammatical errors and awkward phrasing."
        temp = 0.3
    else:
        tone_prompt = "Tone: Vivid, magical, and engaging. Enhance descriptions."
        temp = 0.8

# --- 3. FUNCIONES DEL CEREBRO (GEMINI 2.5) ---

def audit_paragraph(text):
    """
    Modo Auditoría: Busca errores sin corregir.
    """
    if len(text.strip()) < 15: return None
    
    prompt = f"""
    You are a strict editor for a children's book.
    Analyze the text below.
    
    **CRITICAL RULES TO CHECK:**
    1. **Whirlwind:** Must be HE/HIM. Flag if 'she/her' is used.
    2. **Jargon:** Flag corporate words like 'outsourcing'.
    3. **Phrasing:** Flag clumsy "The X of Y" structures (e.g. "The breathing of the balloon").
    4. **Flow:** Flag unnatural/translated sentence structures.

    **OUTPUT:**
    - If issues found: Describe the issue briefly (e.g., "Used 'outsourcing', suggest 'naming'").
    - If clean: Output exactly "CLEAN".

    Text: "{text}"
    """
    try:
        response = model.generate_content(prompt)
        result = response.text.strip()
        return None if "CLEAN" in result else result
    except Exception as e:
        return f"Error API: {str(e)}"

def rewrite_paragraph(text, tone_instr, temperature):
    """
    Modo Corrección: Reescribe el texto.
    """
    if len(text.strip()) < 15: return text

    prompt = f"""
    You are an expert US English book editor.
    Rewrite the text below based on these specs:
    {tone_instr}

    **MANDATORY RULES:**
    1. **Character:** 'Whirlwind' is ALWAYS Male (he/him).
    2. **Vocabulary:** NO corporate jargon (use 'naming', not 'outsourcing').
    3. **Syntax:** Fix "The [noun] of [noun]" -> use "[Noun] [Noun]" (e.g., "Balloon Breathing").
    4. **Language:** Make it sound like a Native US speaker wrote it.

    **Output:** ONLY the rewritten text.

    Original: "{text}"
    """
    try:
        response = model.generate_content(prompt, generation_config={"temperature": temperature})
        return response.text.strip()
    except:
        return text

# --- 4. INTERFAZ PRINCIPAL ---
st.title("📚 NativeFlow con Gemini 2.5")
st.markdown(f"**Documento:** *Childhood Anxiety and Mindful Monsters* | **Motor:** `{MODEL_NAME}`")

uploaded_file = st.file_uploader("Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    total_paragraphs = len(doc.paragraphs)
    
    # PESTAÑAS
    tab1, tab2 = st.tabs(["📊 Paso 1: Auditoría (Reporte)", "🚀 Paso 2: Corrección (Libro Final)"])

    # --- PESTAÑA 1: AUDITORÍA ---
    with tab1:
        st.info("Genera un reporte de errores antes de cambiar nada.")
        if st.button("🔍 Iniciar Auditoría"):
            
            report_doc = Document()
            report_doc.add_heading('Reporte de Auditoría', 0)
            table = report_doc.add_table(rows=1, cols=2)
            table.style = 'Table Grid'
            hdr = table.rows[0].cells
            hdr[0].text = 'Original'
            hdr[1].text = 'Problema Detectado'
            
            prog_bar = st.progress(0)
            status = st.empty()
            issues = 0
            
            # Contenedor para ver el log en vivo
            log_container = st.container()

            for i, para in enumerate(doc.paragraphs):
                status.caption(f"Analizando {i+1}/{total_paragraphs}...")
                
                res = audit_paragraph(para.text)
                
                if res:
                    issues += 1
                    row = table.add_row().cells
                    row[0].text = para.text[:150]
                    row[1].text = res
                    
                    # Mostrar una muestra en pantalla cada tanto
                    if issues % 5 == 0:
                        with log_container:
                            st.markdown(f"<small>🔴 <b>Párrafo {i}:</b> {res}</small>", unsafe_allow_html=True)
                
                prog_bar.progress((i+1)/total_paragraphs)
                # Gemini 2.5 es rápido, pero ponemos una pausa mínima por seguridad
                time.sleep(0.05) 

            status.success(f"✅ Auditoría terminada. {issues} problemas encontrados.")
            
            bio = BytesIO()
            report_doc.save(bio)
            st.download_button("⬇️ Descargar Reporte (.docx)", bio.getvalue(), "Reporte_Auditoria.docx")

    # --- PESTAÑA 2: CORRECCIÓN ---
    with tab2:
        st.info(f"Reescribirá el libro usando el tono: **{tone_option}**")
        
        if st.button("🚀 Procesar Libro Completo"):
            final_doc = Document()
            p_bar = st.progress(0)
            st_msg = st.empty()
            
            for i, para in enumerate(doc.paragraphs):
                st_msg.caption(f"Reescribiendo {i+1}/{total_paragraphs}...")
                
                new_text = rewrite_paragraph(para.text, tone_prompt, temp)
                
                p = final_doc.add_paragraph(new_text)
                p.style = para.style
                
                p_bar.progress((i+1)/total_paragraphs)
                time.sleep(0.05)
            
            st_msg.success("✅ ¡Libro Completado!")
            
            bio_f = BytesIO()
            final_doc.save(bio_f)
            st.download_button(
                label="⬇️ Descargar Libro Corregido (.docx)", 
                data=bio_f.getvalue(), 
                file_name=f"NativeFlow_Final_{uploaded_file.name}",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
