import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NativeFlow 2.5 TURBO", page_icon="💎", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #9c27b0; } /* Color Púrpura (Calidad) */
    .success-box { padding: 10px; background-color: #f3e5f5; border-left: 5px solid #9c27b0; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURACIÓN API (MODO CALIDAD DE PAGO) ---
with st.sidebar:
    st.header("💎 Panel Calidad Premium")
    
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        
        # --- EL CAMBIO CLAVE ---
        # Volvemos al modelo 2.5 porque tienes Billing activado.
        # Es más inteligente y respeta mejor el tono del libro.
        MODEL_NAME = 'gemini-2.5-flash' 
        model = genai.GenerativeModel(MODEL_NAME)
        st.success(f"✅ Cerebro Activo: {MODEL_NAME}")
        st.caption("🚀 Modo Pago: Máxima Calidad + Velocidad")
        
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

# --- 3. FUNCIONES INTELIGENTES ---

def call_api_smart(prompt, temperature=0.7):
    """
    Llama al modelo 2.5. Si hay un límite momentáneo, reintenta rápido.
    """
    max_retries = 5
    wait_time = 5 # Empezamos esperando 5 segundos si falla
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, generation_config={"temperature": temperature})
            return response.text.strip()
            
        except Exception as e:
            error_str = str(e)
            # Aunque pagues, a veces el 2.5 tiene picos de tráfico. Lo manejamos suavemente.
            if "429" in error_str or "quota" in error_str.lower():
                st.toast(f"💎 Calibrando calidad... Esperando {wait_time}s", icon="⏳")
                time.sleep(wait_time)
                wait_time += 5 # Aumentamos un poco si insiste
            elif "503" in error_str: # Servicio sobrecargado
                time.sleep(5)
            else:
                return f"[ERROR: {error_str}]"
    
    return "[FALLO: Google no pudo procesar este fragmento]"

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
        4. **Style:** Make it flow naturally like a story, not a manual.
        
        Text Batch:
        "{text_batch}"
        """
    return call_api_smart(prompt, temp)

# ... (El resto del código de arriba se queda igual) ...

# --- 4. INTERFAZ ---
st.title("💎 NativeFlow: Edición Premium (2.5)")
st.markdown("**Motor:** Gemini 2.5 Flash | **Estado:** Facturación Activada")

# INICIALIZAR MEMORIA (Para que el botón de descarga no desaparezca)
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

    tab1, tab2 = st.tabs(["📊 Auditoría de Calidad", "🚀 Corrección Premium"])

    def run_premium_process(mode):
        output_doc = Document()
        if mode == "audit": output_doc.add_heading('Reporte Auditoría Premium', 0)
        
        p_bar = st.progress(0)
        status = st.empty()
        
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
                status.text(f"✨ Procesando Sección {processed_batches}/{estimated_batches} con IA avanzada...")
                
                result = process_batch(current_batch, mode, tone_prompt, temp)
                
                if mode == "audit":
                    if "CLEAN" not in result and "ERROR" not in result:
                        output_doc.add_paragraph(f"--- SECCIÓN {processed_batches} ---")
                        output_doc.add_paragraph(result)
                else:
                    clean_text = result.replace("```", "").replace("markdown", "")
                    output_doc.add_paragraph(clean_text)
                    output_doc.add_paragraph("-" * 20)

                p_bar.progress(min(processed_batches / estimated_batches, 1.0))
                current_batch = ""
                
                time.sleep(1)

        total_time = round((time.time() - start_time) / 60, 2)
        status.success(f"✅ ¡EDICIÓN COMPLETADA EN {total_time} MINUTOS!")
        st.balloons()
        
        bio = BytesIO()
        output_doc.save(bio)
        return bio

    # --- PESTAÑA 1: AUDITORÍA CON MEMORIA ---
    with tab1:
        # Botón de acción
        if st.button("💎 Auditar Calidad"):
            with st.spinner("Auditando... (Por favor espera)"):
                # Guardamos el resultado en la memoria persistente
                st.session_state.audit_result = run_premium_process("audit")
        
        # Botón de descarga (Aparece y SE QUEDA ahí)
        if st.session_state.audit_result is not None:
            st.divider()
            st.success("¡El reporte está listo para descargar!")
            st.download_button(
                label="⬇️ Descargar Reporte (.docx)",
                data=st.session_state.audit_result.getvalue(),
                file_name="Reporte_Premium.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    # --- PESTAÑA 2: CORRECCIÓN CON MEMORIA ---
    with tab2:
        if st.button("💎 Corregir Libro"):
            with st.spinner("Reescribiendo... (Esto toma unos minutos)"):
                st.session_state.rewrite_result = run_premium_process("rewrite")
        
        if st.session_state.rewrite_result is not None:
            st.divider()
            st.success("¡El libro corregido está listo!")
            st.download_button(
                label="⬇️ Descargar Libro Editado (.docx)",
                data=st.session_state.rewrite_result.getvalue(),
                file_name="Libro_Premium.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
