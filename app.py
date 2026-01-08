import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time
import os  # <--- IMPORTANTE: Para guardar archivos físicos

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NativeFlow 2.0 Secure", page_icon="🔐", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #28a745; }
    .success-box { padding: 10px; background-color: #d4edda; border-left: 5px solid #28a745; }
    .recovery-box { padding: 15px; background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 5px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURACIÓN API ---
with st.sidebar:
    st.header("🔐 Panel Seguro")
    
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        
        # Usamos Gemini 2.0 Flash (Equilibrio perfecto)
        MODEL_NAME = 'gemini-2.0-flash' 
        model = genai.GenerativeModel(MODEL_NAME)
        st.success(f"✅ Motor: {MODEL_NAME}")
        
    except Exception as e:
        st.error("❌ Error de API Key.")
        st.stop()

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

# --- 3. FUNCIONES ---

def call_api_stable(prompt, temperature=0.7):
    max_retries = 8
    wait_time = 5
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, generation_config={"temperature": temperature})
            return response.text.strip()
        except Exception as e:
            error_str = str(e)
            if any(x in error_str for x in ["429", "503", "500", "quota", "overloaded"]):
                st.toast(f"⏳ Tráfico alto (Intento {attempt+1}). Esperando {wait_time}s...", icon="🛡️")
                time.sleep(wait_time)
                wait_time = min(wait_time * 1.5, 60)
            elif "404" in error_str:
                return f"[ERROR CRÍTICO: Modelo no encontrado]"
            else:
                time.sleep(5)
    return "[FALLO API]"

def process_batch(text_batch, mode, tone_instr, temp):
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
    return call_api_stable(prompt, temp)

# --- 4. SISTEMA DE RECUPERACIÓN (AUTO-SAVE) ---
def save_recovery_file(doc_obj, filename):
    """Guarda el archivo en el disco del servidor por si se refresca la página"""
    try:
        doc_obj.save(filename)
    except:
        pass

def load_recovery_file(filename):
    """Carga el archivo del disco"""
    with open(filename, "rb") as f:
        return BytesIO(f.read())

# --- 5. INTERFAZ ---
st.title("🔐 NativeFlow: Sistema con Auto-Recuperación")

# ZONA DE RECUPERACIÓN DE DESASTRES
# Verificamos si existen archivos huérfanos de una sesión anterior
if os.path.exists("temp_audit_recovery.docx"):
    st.markdown("""
    <div class="recovery-box">
        <h4>⚠️ ¡Archivo Recuperado!</h4>
        <p>Parece que tu última auditoría se completó pero se cerró la conexión. Aquí tienes el archivo:</p>
    </div>
    """, unsafe_allow_html=True)
    
    rec_data = load_recovery_file("temp_audit_recovery.docx")
    st.download_button("⬇️ Descargar Auditoría Recuperada", rec_data, "Reporte_Recuperado.docx")
    
    if st.button("🗑️ Borrar archivo temporal (Auditoría)"):
        os.remove("temp_audit_recovery.docx")
        st.rerun()

if os.path.exists("temp_rewrite_recovery.docx"):
    st.markdown("""
    <div class="recovery-box">
        <h4>⚠️ ¡Libro Corregido Recuperado!</h4>
        <p>Tu libro final está guardado en el servidor.</p>
    </div>
    """, unsafe_allow_html=True)
    
    rec_data = load_recovery_file("temp_rewrite_recovery.docx")
    st.download_button("⬇️ Descargar Libro Recuperado", rec_data, "Libro_Recuperado.docx")
    
    if st.button("🗑️ Borrar archivo temporal (Libro)"):
        os.remove("temp_rewrite_recovery.docx")
        st.rerun()

st.divider()

uploaded_file = st.file_uploader("Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    all_paragraphs = [p.text for p in doc.paragraphs if len(p.text.strip()) > 2]
    total_paras = len(all_paragraphs)
    
    st.info(f"📖 Libro cargado: {total_paras} párrafos.")

    tab1, tab2 = st.tabs(["📊 Auditoría", "🚀 Corrección"])

    def run_process_secure(mode):
        output_doc = Document()
        if mode == "audit": output_doc.add_heading('Reporte Auditoría', 0)
        
        p_bar = st.progress(0)
        status = st.empty()
        
        BATCH_SIZE = 10000 
        current_batch = ""
        
        total_chars = sum(len(p) for p in all_paragraphs)
        estimated_batches = (total_chars // BATCH_SIZE) + 2
        processed_batches = 0

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
                time.sleep(1)

        status.success(f"✅ ¡Finalizado!")
        st.balloons()
        
        # --- AQUÍ ESTÁ EL TRUCO: GUARDADO FÍSICO ---
        if mode == "audit":
            save_recovery_file(output_doc, "temp_audit_recovery.docx")
        else:
            save_recovery_file(output_doc, "temp_rewrite_recovery.docx")
            
        bio = BytesIO()
        output_doc.save(bio)
        return bio

    with tab1:
        if st.button("📊 Auditar Ahora"):
            data = run_process_secure("audit")
            # Si llegamos aquí sin que se corte, mostramos el botón normal
            st.download_button("⬇️ Descargar Reporte", data.getvalue(), "Reporte_Auditoria.docx")
            st.success("Nota: Si no ves este botón, recarga la página; aparecerá arriba como 'Recuperado'.")

    with tab2:
        if st.button("🚀 Corregir Libro"):
            data = run_process_secure("rewrite")
            st.download_button("⬇️ Descargar Libro", data.getvalue(), "Libro_Final.docx")
            st.success("Nota: Si no ves este botón, recarga la página; aparecerá arriba como 'Recuperado'.")
