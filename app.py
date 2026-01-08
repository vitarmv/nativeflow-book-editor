import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NativeFlow 2.0 Stable", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #007bff; } /* Azul Estabilidad */
    .success-box { padding: 10px; background-color: #e3f2fd; border-left: 5px solid #007bff; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURACIÓN API ---
with st.sidebar:
    st.header("🛡️ Panel de Control")
    
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        
        # --- CAMBIO ESTRATÉGICO: GEMINI 2.0 FLASH ---
        # Es mucho más estable que el 2.5 y más listo que el 1.5.
        MODEL_NAME = 'gemini-2.0-flash' 
        model = genai.GenerativeModel(MODEL_NAME)
        st.success(f"✅ Motor: {MODEL_NAME}")
        st.caption("🚀 Modo: Estabilidad + Calidad")
        
    except Exception as e:
        st.error("❌ Error de API Key.")
        st.stop()

    st.divider()
    
    # SELECTOR DE TONO
    st.subheader("🎨 Estilo Literario")
    tone_option = st.selectbox(
        "Objetivo:", 
        ["Warm & Kid-Friendly (Recomendado)", "Strict Grammar", "Storyteller"]
    )

    if tone_option == "Warm & Kid-Friendly (Recomendado)":
        tone_prompt = "Tone: Warm, empathetic, validating. Use simple, sensory words for kids (6-10 years)."
        temp = 0.7
    elif tone_option == "Strict Grammar":
        tone_prompt = "Tone: Neutral. Keep author's voice exact. Only fix grammar errors."
        temp = 0.3
    else:
        tone_prompt = "Tone: Vivid, magical, descriptive, focusing on emotional imagery."
        temp = 0.8

# --- 3. FUNCIONES BLINDADAS ---

def call_api_stable(prompt, temperature=0.7):
    """
    Llama al modelo 2.0 con reintentos inteligentes.
    """
    max_retries = 8  # 8 Intentos de seguridad
    wait_time = 5    # Espera inicial
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, generation_config={"temperature": temperature})
            return response.text.strip()
            
        except Exception as e:
            error_str = str(e)
            # Filtramos errores de saturación típicos
            if any(x in error_str for x in ["429", "503", "500", "quota", "overloaded"]):
                st.toast(f"⏳ Tráfico en Google (Intento {attempt+1}). Esperando {wait_time}s...", icon="🛡️")
                time.sleep(wait_time)
                wait_time = min(wait_time * 1.5, 60) # Aumentamos tiempo progresivamente
            elif "404" in error_str:
                return f"[ERROR CRÍTICO: Modelo no encontrado. Revisa el nombre.]"
            else:
                time.sleep(5) # Pausa por error desconocido y reintenta
    
    return "[FALLO: Google no respondió tras múltiples intentos]"

def process_batch(text_batch, mode, tone_instr, temp):
    if not text_batch.strip(): return ""

    if mode == "audit":
        prompt = f"""
        ACT AS A PROFESSIONAL EDITOR. Audit this text section.
        
        STRICT CHECKS:
        1. Whirlwind Gender: Must be HE/HIM. Flag if 'she/her' appears.
        2. Corporate Jargon: Flag 'outsourcing'.
        3. Phrasing: Flag clumsy "The X of Y" structures.
        
        OUTPUT: List issues concisely. If perfect, output "CLEAN".
        Text: "{text_batch}"
        """
    else: # Rewrite
        prompt = f"""
        You are a professional children's book editor (US English).
        Rewrite this text section to be native, warm, and engaging.
        
        TONE SPECS: {tone_instr}
        
        CRITICAL RULES (DO NOT BREAK):
        1. **Character:** 'Whirlwind' is ALWAYS Male (he/him). Fix any 'she'.
        2. **Vocabulary:** NEVER use 'outsourcing'. Use 'naming', 'externalizing', or 'separating'.
        3. **Flow:** Fix "The [noun] of [noun]" -> "[Noun] [Noun]" (e.g. "Balloon Breathing").
        4. **Style:** Make it flow naturally like a story.
        
        Text Batch:
        "{text_batch}"
        """
    return call_api_stable(prompt, temp)

# --- 4. INTERFAZ ---
st.title("🛡️ NativeFlow: Edición Estable (2.0)")
st.markdown(f"**Motor:** `{MODEL_NAME}` | **Estado:** Optimizado para libros largos")

# INICIALIZAR MEMORIA (Para que el botón de descarga NO desaparezca)
if "audit_result" not in st.session_state:
    st.session_state.audit_result = None
if "rewrite_result" not in st.session_state:
    st.session_state.rewrite_result = None

uploaded_file = st.file_uploader("Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    all_paragraphs = [p.text for p in doc.paragraphs if len(p.text.strip()) > 2]
    total_paras = len(all_paragraphs)
    
    st.info(f"📖 Libro cargado: {total_paras} párrafos.")

    tab1, tab2 = st.tabs(["📊 Auditoría", "🚀 Corrección"])

    def run_process_stable(mode):
        output_doc = Document()
        if mode == "audit": output_doc.add_heading('Reporte Auditoría NativeFlow', 0)
        
        p_bar = st.progress(0)
        status = st.empty()
        
        # BATCH SIZE: 10,000 chars. El modelo 2.0 aguanta esto perfectamente.
        BATCH_SIZE = 10000 
        current_batch = ""
        
        total_chars = sum(len(p) for p in all_paragraphs)
        estimated_batches = (total_chars // BATCH_SIZE) + 2
        processed_batches = 0

        start_time = time.time()

        for i, text in enumerate(all_paragraphs):
            current_batch += text + "\n\n"
            
            if len(current_batch) > BATCH_SIZE or i == total_paras - 1:
                processed_batches += 1
                status.text(f"⚙️ Procesando Bloque {processed_batches}/{estimated_batches}...")
                
                result = process_batch(current_batch, mode, tone_prompt, temp)
                
                if mode == "audit":
                    if "CLEAN" not in result and "ERROR" not in result:
                        output_doc.add_paragraph(f"--- BLOQUE {processed_batches} ---")
                        output_doc.add_paragraph(result)
                else:
                    clean_text = result.replace("```", "").replace("markdown", "")
                    output_doc.add_paragraph(clean_text)
                    output_doc.add_paragraph("-" * 20)

                p_bar.progress(min(processed_batches / estimated_batches, 1.0))
                current_batch = ""
                
                # Pausa mínima para no saturar
                time.sleep(1)

        total_time = round((time.time() - start_time) / 60, 2)
        status.success(f"✅ ¡PROCESO FINALIZADO EN {total_time} MINUTOS!")
        st.balloons()
        
        bio = BytesIO()
        output_doc.save(bio)
        return bio

    # --- PESTAÑA 1: AUDITORÍA ---
    with tab1:
        if st.button("📊 Auditar Ahora"):
            with st.spinner("Analizando libro..."):
                st.session_state.audit_result = run_process_stable("audit")
        
        if st.session_state.audit_result is not None:
            st.divider()
            st.success("¡Reporte listo!")
            st.download_button(
                "⬇️ Descargar Reporte (.docx)",
                st.session_state.audit_result.getvalue(),
                "Reporte_Auditoria_2.0.docx"
            )

    # --- PESTAÑA 2: CORRECCIÓN ---
    with tab2:
        if st.button("🚀 Corregir Libro"):
            with st.spinner("Reescribiendo libro..."):
                st.session_state.rewrite_result = run_process_stable("rewrite")
        
        if st.session_state.rewrite_result is not None:
            st.divider()
            st.success("¡Libro completado!")
            st.download_button(
                "⬇️ Descargar Libro (.docx)",
                st.session_state.rewrite_result.getvalue(),
                "Libro_Final_2.0.docx"
            )
