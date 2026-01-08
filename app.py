import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time
import os

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NativeFlow Flexible", page_icon="🎛️", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #6c757d; }
    .success-box { padding: 10px; background-color: #d4edda; border-left: 5px solid #28a745; }
    .recovery-box { padding: 15px; background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 5px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURACIÓN API Y MOTOR ---
with st.sidebar:
    st.header("🎛️ Centro de Control")
    
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("✅ API Conectada")
    except Exception as e:
        st.error("❌ Error de API Key.")
        st.stop()
    
    st.divider()

    # --- SELECTOR DE MOTOR (TU IDEA) ---
    st.subheader("🏎️ Selector de Motor")
    model_choice = st.radio(
        "Prioridad actual:",
        ["Velocidad (1.5 Flash)", "Calidad (2.0 Flash)"],
        help="Usa 1.5 en horas pico. Usa 2.0 para máxima inteligencia cuando esté tranquilo."
    )

    if "Velocidad" in model_choice:
        MODEL_NAME = 'gemini-1.5-flash'
        BATCH_SIZE = 12000 # Lotes grandes para volar
        initial_wait = 1   # Espera mínima si falla
        st.info(f"🚀 Modo Turbo activado.\nMotor: {MODEL_NAME}")
    else:
        MODEL_NAME = 'gemini-2.0-flash'
        BATCH_SIZE = 7000  # Lotes medianos para no saturar
        initial_wait = 3   # Espera prudente
        st.info(f"💎 Modo Calidad activado.\nMotor: {MODEL_NAME}")

    # Inicializamos el modelo seleccionado
    model = genai.GenerativeModel(MODEL_NAME)

    st.divider()
    
    st.subheader("🎨 Estilo")
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
        tone_prompt = "Tone: Vivid, magical, descriptive."
        temp = 0.8

# --- 3. FUNCIONES INTELIGENTES ---

def call_api(prompt, temperature=0.7, wait_start=2):
    """
    Llama a la API con estrategia adaptativa según el modelo elegido.
    """
    max_retries = 6
    wait_time = wait_start
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, generation_config={"temperature": temperature})
            return response.text.strip()
            
        except Exception as e:
            error_str = str(e)
            
            # Si es un error de límite o servidor
            if any(x in error_str for x in ["429", "503", "500", "quota", "overloaded"]):
                # Solo mostramos toast si es el modelo 2.0 (el 1.5 suele recuperar rápido)
                if "2.0" in MODEL_NAME:
                    st.toast(f"⏳ Tráfico alto. Reintentando en {wait_time}s...", icon="🐢")
                
                time.sleep(wait_time)
                # Incremento suave, no tan agresivo como antes
                wait_time += 2 
            
            elif "404" in error_str:
                return f"[ERROR: Modelo no encontrado]"
            else:
                time.sleep(1) # Error desconocido, pausa breve
                
    return "[FALLO: Google no respondió tras varios intentos]"

def process_batch(text_batch, mode, tone_instr, temp, wait_config):
    if not text_batch.strip(): return ""

    if mode == "audit":
        prompt = f"""
        ACT AS A PROFESSIONAL EDITOR. Audit this text section.
        STRICT CHECKS:
        1. Whirlwind Gender: Must be HE/HIM. Flag 'she/her'.
        2. Corporate Jargon: Flag 'outsourcing'.
        3. Phrasing: Flag clumsy "The X of Y".
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
st.title("🎛️ NativeFlow Flexible")

# RECUPERACIÓN DE DESASTRES
if os.path.exists("temp_audit_rec.docx"):
    st.warning("⚠️ Se encontró una auditoría interrumpida.")
    col1, col2 = st.columns([1,4])
    with col1:
        st.download_button("⬇️ Rescatar Archivo", load_recovery_file("temp_audit_rec.docx"), "Audit_Rescatado.docx")
    with col2:
        if st.button("🗑️ Descartar y empezar de cero"):
            os.remove("temp_audit_rec.docx")
            st.rerun()

st.markdown(f"**Motor Actual:** `{MODEL_NAME}` | **Tamaño de Lote:** `{BATCH_SIZE}` chars")

uploaded_file = st.file_uploader("Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    all_paragraphs = [p.text for p in doc.paragraphs if len(p.text.strip()) > 2]
    total_paras = len(all_paragraphs)
    
    st.info(f"📖 Libro cargado: {total_paras} párrafos.")

    tab1, tab2 = st.tabs(["📊 Auditoría", "🚀 Corrección"])

    def run_process(mode):
        output_doc = Document()
        if mode == "audit": output_doc.add_heading('Reporte Auditoría', 0)
        
        p_bar = st.progress(0)
        status = st.empty()
        
        current_batch = ""
        total_chars = sum(len(p) for p in all_paragraphs)
        estimated_batches = (total_chars // BATCH_SIZE) + 2
        processed_batches = 0

        for i, text in enumerate(all_paragraphs):
            current_batch += text + "\n\n"
            
            if len(current_batch) > BATCH_SIZE or i == total_paras - 1:
                processed_batches += 1
                status.text(f"⚙️ Procesando Bloque {processed_batches}/{estimated_batches}...")
                
                # Ejecutamos con el tiempo de espera configurado en el selector
                result = process_batch(current_batch, mode, tone_prompt, temp, initial_wait)
                
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
                
                # Si es modo rápido, casi no hay pausa. Si es calidad, pausa pequeña.
                if "1.5" in MODEL_NAME:
                    time.sleep(0.1) # Autopista
                else:
                    time.sleep(1)   # Precaución

        status.success(f"✅ ¡Finalizado!")
        st.balloons()
        
        # Guardado físico
        filename = "temp_audit_rec.docx" if mode == "audit" else "temp_rewrite_rec.docx"
        save_recovery_file(output_doc, filename)
            
        bio = BytesIO()
        output_doc.save(bio)
        return bio

    with tab1:
        if st.button("📊 Auditar Ahora"):
            data = run_process("audit")
            st.download_button("⬇️ Descargar Reporte", data.getvalue(), "Reporte_Auditoria.docx")

    with tab2:
        if st.button("🚀 Corregir Libro"):
            data = run_process("rewrite")
            st.download_button("⬇️ Descargar Libro", data.getvalue(), "Libro_Final.docx")
