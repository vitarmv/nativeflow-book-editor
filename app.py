import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time
import os

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NativeFlow 3.0 Final", page_icon="💎", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #28a745; }
    .success-box { padding: 10px; background-color: #d1e7dd; border-left: 5px solid #198754; }
    .recovery-box { padding: 15px; background-color: #fff3cd; border: 1px solid #ffecb5; border-radius: 5px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURACIÓN API Y SELECTOR ---
with st.sidebar:
    st.header("🎛️ Centro de Mando")
    
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("✅ Conexión Establecida")
    except Exception as e:
        st.error("❌ Falta API Key")
        st.stop()
    
    st.divider()

    # --- SELECTOR DE MOTOR ---
    st.subheader("🏎️ Motor de IA")
    
    model_option = st.radio(
        "Estrategia:",
        ["Estabilidad Total (Recomendado)", "Inteligencia 2.0 (Experimental)"],
        help="Estabilidad usa el modelo más robusto disponible. Inteligencia usa el nuevo 2.0."
    )

    if "Estabilidad" in model_option:
        # El comodín que nunca falla
        MODEL_NAME = 'models/gemini-flash-latest' 
        BATCH_SIZE = 8000 
        initial_wait = 2   
        st.info(f"🛡️ Modo Seguro Activo")
    else:
        # El modelo nuevo (puede saturarse en horas pico)
        MODEL_NAME = 'models/gemini-2.0-flash'
        BATCH_SIZE = 12000 
        initial_wait = 1   
        st.warning(f"⚡ Modo Velocidad 2.0")

    model = genai.GenerativeModel(MODEL_NAME)

    st.divider()
    
    st.subheader("🎨 Estilo de Edición")
    tone_option = st.selectbox(
        "Tono:", 
        ["Warm & Kid-Friendly (Recomendado)", "Strict Grammar"]
    )

    if "Kid-Friendly" in tone_option:
        tone_prompt = "Tone: Warm, empathetic, validating. Use simple, sensory words for kids (6-10 years)."
        temp = 0.7
    else:
        tone_prompt = "Tone: Neutral. Keep author's voice exact. Only fix grammar."
        temp = 0.3

# --- 3. FUNCIONES ROBUSTAS ---

def call_api(prompt, temperature=0.7, wait_start=2):
    max_retries = 5 
    wait_time = wait_start
    last_error = ""
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, generation_config={"temperature": temperature})
            return response.text.strip()
            
        except Exception as e:
            last_error = str(e)
            # Si es saturación, esperamos
            if any(x in last_error for x in ["429", "503", "500", "overloaded", "quota"]):
                time.sleep(wait_time)
                wait_time += 2 
            else:
                time.sleep(1)
                
    return f"[ERROR TÉCNICO: {last_error}]"

def process_batch(text_batch, mode, tone_instr, temp, wait_config):
    if not text_batch.strip(): return ""

    if mode == "audit":
        prompt = f"""
        ACT AS A PROFESSIONAL EDITOR. Audit this text section.
        STRICT CHECKS:
        1. Whirlwind Gender: Must be HE/HIM. Flag 'she/her'.
        2. Corporate Jargon: Flag 'outsourcing'.
        3. Phrasing: Flag clumsy "The X of Y" structures.
        OUTPUT: List issues concisely. If perfect, output "CLEAN".
        Text: "{text_batch}"
        """
    else: # Rewrite
        prompt = f"""
        You are a professional children's book editor (US English).
        Rewrite this text section.
        TONE SPECS: {tone_instr}
        CRITICAL RULES:
        1. 'Whirlwind' is ALWAYS Male (he/him).
        2. NO 'outsourcing'.
        3. Fix "The X of Y" -> "X Y".
        Text Batch: "{text_batch}"
        """
    return call_api(prompt, temp, wait_config)

# --- 4. SISTEMA DE RECUPERACIÓN (AUTO-SAVE) ---
def save_recovery_file(doc_obj, filename):
    try: doc_obj.save(filename)
    except: pass

def load_recovery_file(filename):
    with open(filename, "rb") as f: return BytesIO(f.read())

# --- 5. INTERFAZ ---
st.title("💎 NativeFlow: Edición 3.0")

# A) ZONA DE RESCATE (Detecta archivos huérfanos)
if os.path.exists("temp_audit_safe.docx"):
    st.markdown("""<div class="recovery-box"><h4>⚠️ Auditoría Rescatada Disponible</h4></div>""", unsafe_allow_html=True)
    col1, col2 = st.columns([1,4])
    with col1:
        st.download_button("⬇️ Descargar", load_recovery_file("temp_audit_safe.docx"), "Audit_Rescatado.docx")
    with col2:
        if st.button("🗑️ Borrar y empezar de cero", key="del_audit"):
            os.remove("temp_audit_safe.docx")
            st.rerun()

if os.path.exists("temp_rewrite_safe.docx"):
    st.markdown("""<div class="recovery-box"><h4>⚠️ Libro Corregido Rescatado Disponible</h4></div>""", unsafe_allow_html=True)
    col1, col2 = st.columns([1,4])
    with col1:
        st.download_button("⬇️ Descargar", load_recovery_file("temp_rewrite_safe.docx"), "Libro_Rescatado.docx")
    with col2:
        if st.button("🗑️ Borrar y empezar de cero", key="del_rewrite"):
            os.remove("temp_rewrite_safe.docx")
            st.rerun()

st.divider()

# B) MEMORIA DE SESIÓN (Para botones fijos)
if "audit_done" not in st.session_state: st.session_state.audit_done = None
if "rewrite_done" not in st.session_state: st.session_state.rewrite_done = None

uploaded_file = st.file_uploader("Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    all_paragraphs = [p.text for p in doc.paragraphs if len(p.text.strip()) > 2]
    total_paras = len(all_paragraphs)
    
    st.info(f"📖 Libro cargado: {total_paras} párrafos detectados.")

    tab1, tab2 = st.tabs(["📊 Auditoría", "🚀 Corrección"])

    # FUNCIÓN MAESTRA CON GUARDADO PROGRESIVO
    def run_process_wrapper(mode):
        output_doc = Document()
        if mode == "audit": output_doc.add_heading('Reporte Auditoría Final', 0)
        
        p_bar = st.progress(0)
        status = st.empty()
        
        current_batch = ""
        total_chars = sum(len(p) for p in all_paragraphs)
        estimated_batches = (total_chars // BATCH_SIZE) + 2
        processed_batches = 0
        
        # Archivo temporal para guardar PASO A PASO
        temp_file = "temp_audit_safe.docx" if mode == "audit" else "temp_rewrite_safe.docx"
        
        for i, text in enumerate(all_paragraphs):
            current_batch += text + "\n\n"
            
            if len(current_batch) > BATCH_SIZE or i == total_paras - 1:
                processed_batches += 1
                status.text(f"⚙️ Procesando Bloque {processed_batches}/{estimated_batches}...")
                
                result = process_batch(current_batch, mode, tone_prompt, temp, initial_wait)
                
                # Escribir en documento
                if mode == "audit":
                    output_doc.add_paragraph(f"--- BLOQUE {processed_batches} ---")
                    if "ERROR TÉCNICO" in result: st.error(result)
                    output_doc.add_paragraph(result)
                else:
                    clean_text = result.replace("```", "").replace("markdown", "")
                    output_doc.add_paragraph(clean_text)
                    output_doc.add_paragraph("-" * 20)

                # --- GUARDADO PROGRESIVO (Aquí está la magia) ---
                # Guardamos en disco AHORA MISMO, para no perder nada si se corta
                save_recovery_file(output_doc, temp_file)
                # -----------------------------------------------

                p_bar.progress(min(processed_batches / estimated_batches, 1.0))
                current_batch = ""
                time.sleep(1) 
        
        status.success(f"✅ ¡Finalizado!")
        
        # Devolver objeto para descarga directa
        bio = BytesIO()
        output_doc.save(bio)
        return bio

    # --- PESTAÑA 1: AUDITORÍA ---
    with tab1:
        if st.button("📊 EJECUTAR AUDITORÍA"):
            st.session_state.audit_done = run_process_wrapper("audit")
        
        if st.session_state.audit_done:
            st.download_button("⬇️ Descargar Reporte Final", st.session_state.audit_done.getvalue(), "Reporte_Final.docx")

    # --- PESTAÑA 2: CORRECCIÓN ---
    with tab2:
        if st.button("🚀 CORREGIR LIBRO"):
            st.session_state.rewrite_done = run_process_wrapper("rewrite")
        
        if st.session_state.rewrite_done:
            st.balloons()
            st.success("¡Libro listo!")
            st.download_button("⬇️ Descargar Libro Final", st.session_state.rewrite_done.getvalue(), "Libro_Corregido.docx")
