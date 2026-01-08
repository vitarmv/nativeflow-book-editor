import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time
import os

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NativeFlow PRO", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #0d6efd; }
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

    # --- SELECTOR DE MOTOR (Basado en TU lista confirmada) ---
    st.subheader("🏎️ Elige tu Motor")
    
    model_option = st.radio(
        "¿Qué priorizamos?",
        ["Velocidad (Auditoría)", "Calidad (Edición Final)"],
        help="Velocidad usa 2.0 Flash. Calidad usa 2.5 Flash."
    )

    if "Velocidad" in model_option:
        # Usamos el nombre EXACTO de tu lista para evitar error 404
        MODEL_NAME = 'models/gemini-2.0-flash' 
        BATCH_SIZE = 12000 # Lotes grandes para ir rápido
        initial_wait = 1   # Espera mínima
        st.info(f"⚡ Motor Activo: 2.0 Flash\nIdeal para auditar rápido.")
    else:
        # Usamos el nombre EXACTO de tu lista
        MODEL_NAME = 'models/gemini-2.5-flash'
        BATCH_SIZE = 7000  # Lotes medianos para calidad
        initial_wait = 3   # Espera prudente
        st.info(f"💎 Motor Activo: 2.5 Flash\nIdeal para reescribir bonito.")

    # Inicializamos el modelo
    model = genai.GenerativeModel(MODEL_NAME)

    st.divider()
    
    st.subheader("🎨 Estilo")
    tone_option = st.selectbox(
        "Tono de Edición:", 
        ["Warm & Kid-Friendly (Recomendado)", "Strict Grammar", "Storyteller"]
    )

    if "Kid-Friendly" in tone_option:
        tone_prompt = "Tone: Warm, empathetic, validating. Use simple, sensory words for kids (6-10 years)."
        temp = 0.7
    elif "Strict" in tone_option:
        tone_prompt = "Tone: Neutral. Keep author's voice exact. Only fix grammar errors."
        temp = 0.3
    else:
        tone_prompt = "Tone: Vivid, magical, descriptive."
        temp = 0.8

# --- 3. FUNCIONES ROBUSTAS ---

def call_api(prompt, temperature=0.7, wait_start=2):
    max_retries = 8
    wait_time = wait_start
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, generation_config={"temperature": temperature})
            return response.text.strip()
            
        except Exception as e:
            error_str = str(e)
            
            # Gestión de tráfico (Errores 429, 503)
            if any(x in error_str for x in ["429", "503", "500", "quota", "overloaded"]):
                st.toast(f"🚦 Tráfico en la ruta. Reintentando en {wait_time}s...", icon="⏳")
                time.sleep(wait_time)
                wait_time += 2 # Incremento suave
            
            # Error 404 real (no debería pasar con nombres correctos)
            elif "404" in error_str:
                return f"[ERROR FATAL: El modelo {MODEL_NAME} no responde. Cambia el selector.]"
            else:
                time.sleep(1) 
                
    return "[FALLO: Google no respondió tras múltiples intentos]"

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

# --- 4. SISTEMA DE RECUPERACIÓN (AUTO-SAVE EN DISCO) ---
def save_recovery_file(doc_obj, filename):
    try: doc_obj.save(filename)
    except: pass

def load_recovery_file(filename):
    with open(filename, "rb") as f: return BytesIO(f.read())

# --- 5. INTERFAZ ---
st.title("🚀 NativeFlow: Sistema Pro")

# --- ZONA DE RESCATE ---
if os.path.exists("temp_audit_rec.docx"):
    st.markdown("""<div class="recovery-box"><h4>⚠️ Auditoría Interrumpida Detectada</h4></div>""", unsafe_allow_html=True)
    col1, col2 = st.columns([1,4])
    with col1:
        st.download_button("⬇️ Rescatar Archivo", load_recovery_file("temp_audit_rec.docx"), "Audit_Rescatado.docx")
    with col2:
        if st.button("🗑️ Borrar y empezar nuevo"):
            os.remove("temp_audit_rec.docx")
            st.rerun()

if os.path.exists("temp_rewrite_rec.docx"):
    st.markdown("""<div class="recovery-box"><h4>⚠️ Corrección Interrumpida Detectada</h4></div>""", unsafe_allow_html=True)
    col1, col2 = st.columns([1,4])
    with col1:
        st.download_button("⬇️ Rescatar Libro", load_recovery_file("temp_rewrite_rec.docx"), "Libro_Rescatado.docx")
    with col2:
        if st.button("🗑️ Borrar y empezar nuevo"):
            os.remove("temp_rewrite_rec.docx")
            st.rerun()

st.divider()

uploaded_file = st.file_uploader("Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    all_paragraphs = [p.text for p in doc.paragraphs if len(p.text.strip()) > 2]
    total_paras = len(all_paragraphs)
    
    st.info(f"📖 Libro cargado: {total_paras} párrafos detectados.")

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
        
        # Archivo temporal para ir guardando
        temp_filename = "temp_audit_rec.docx" if mode == "audit" else "temp_rewrite_rec.docx"

        for i, text in enumerate(all_paragraphs):
            current_batch += text + "\n\n"
            
            if len(current_batch) > BATCH_SIZE or i == total_paras - 1:
                processed_batches += 1
                status.text(f"⚙️ Procesando Bloque {processed_batches}/{estimated_batches}...")
                
                result = process_batch(current_batch, mode, tone_prompt, temp, initial_wait)
                
                if mode == "audit":
                    if "CLEAN" not in result and "ERROR" not in result:
                        output_doc.add_paragraph(f"--- BLOQUE {processed_batches} ---")
                        output_doc.add_paragraph(result)
                else:
                    clean_text = result.replace("```", "").replace("markdown", "")
                    output_doc.add_paragraph(clean_text)
                    output_doc.add_paragraph("-" * 20)

                # ACTUALIZAMOS BARRA
                p_bar.progress(min(processed_batches / estimated_batches, 1.0))
                current_batch = ""
                
                # PAUSA ESTRATÉGICA
                if "2.0" in MODEL_NAME:
                    time.sleep(0.1) # El 2.0 es rápido, casi sin pausa
                else:
                    time.sleep(1)   # El 2.5 necesita respirar
        
        # FINALIZACIÓN
        status.success(f"✅ ¡Finalizado!")
        st.balloons()
        
        # Guardado final en disco por seguridad
        save_recovery_file(output_doc, temp_filename)
            
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
