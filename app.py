import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time
import os
import copy

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NativeFlow: Formato Preservado", page_icon="🎨", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #6610f2; }
    .success-box { padding: 10px; background-color: #e2e3e5; border-left: 5px solid #6610f2; }
    .recovery-box { padding: 15px; background-color: #fff3cd; border: 1px solid #ffecb5; border-radius: 5px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURACIÓN API ---
with st.sidebar:
    st.header("🎨 Centro de Diseño")
    
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("✅ API Conectada")
    except Exception as e:
        st.error("❌ Falta API Key")
        st.stop()
    
    st.divider()

    # --- SELECTOR DE MOTOR ---
    st.subheader("🏎️ Motor")
    # Usamos el comodín para asegurar estabilidad
    MODEL_NAME = 'models/gemini-flash-latest' 
    model = genai.GenerativeModel(MODEL_NAME)
    
    BATCH_SIZE = 5000 # Lotes más pequeños para ser precisos con el formato
    initial_wait = 2

    st.info("ℹ️ Modo: Preservación de Estilo Original")
    st.caption("Este modo edita sobre tu archivo original para mantener imágenes y diseño.")

    st.divider()
    
    st.subheader("📝 Instrucciones")
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

# --- 3. FUNCIONES ---

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
            if any(x in last_error for x in ["429", "503", "500", "overloaded"]):
                time.sleep(wait_time)
                wait_time += 2 
            else:
                time.sleep(1)
    return f"[ERROR: {last_error}]"

def process_paragraph_text(text, mode, tone_instr, temp, wait_config):
    if len(text.strip()) < 3: return text # Si es muy corto (un número, un espacio), no lo tocamos.

    if mode == "audit":
        prompt = f"""
        AUDIT this text snippet. 
        RULES: HE/HIM for Whirlwind. NO 'outsourcing'.
        OUTPUT: List issues or "CLEAN".
        Text: "{text}"
        """
    else: # Rewrite
        prompt = f"""
        You are a children's book editor. Rewrite this text to be native US English.
        
        CRITICAL FORMATTING RULES:
        1. PRESERVE ALL EMOJIS exactly as they are.
        2. DO NOT add new lines. Return exactly one paragraph.
        3. KEEP the tone: {tone_instr}
        4. RULES: Whirlwind = Male (he). No 'outsourcing'.
        
        Text to rewrite: "{text}"
        """
    
    result = call_api(prompt, temp, wait_config)
    
    # Limpieza básica de Markdown si la IA agrega negritas con asteriscos
    clean_text = result.replace("**", "").replace("##", "").strip()
    return clean_text

# --- 4. RECUPERACIÓN ---
def save_recovery_file(doc_obj, filename):
    try: doc_obj.save(filename)
    except: pass

def load_recovery_file(filename):
    with open(filename, "rb") as f: return BytesIO(f.read())

# --- 5. INTERFAZ ---
st.title("🎨 NativeFlow: Edición 'Quirúrgica'")
st.markdown("Este modo modifica el texto **dentro** de tu archivo original para conservar imágenes y diseño.")

# Recuperación
if os.path.exists("temp_preserve_audit.docx"):
    st.warning("⚠️ Auditoría interrumpida encontrada.")
    st.download_button("⬇️ Rescatar", load_recovery_file("temp_preserve_audit.docx"), "Audit_Rescatado.docx")
    if st.button("🗑️ Borrar temp audit"): os.remove("temp_preserve_audit.docx"); st.rerun()

if os.path.exists("temp_preserve_rewrite.docx"):
    st.warning("⚠️ Libro corregido interrumpido encontrado.")
    st.download_button("⬇️ Rescatar", load_recovery_file("temp_preserve_rewrite.docx"), "Libro_Rescatado.docx")
    if st.button("🗑️ Borrar temp libro"): os.remove("temp_preserve_rewrite.docx"); st.rerun()

st.divider()

# MEMORIA
if "final_doc" not in st.session_state: st.session_state.final_doc = None

uploaded_file = st.file_uploader("Sube tu manuscrito ORIGINAL (.docx)", type=["docx"])

if uploaded_file:
    # 1. Cargamos el original para leer
    original_doc = Document(uploaded_file)
    
    # 2. Creamos una COPIA exacta en memoria para escribir
    # Esto asegura que márgenes, estilos y headers se mantengan
    uploaded_file.seek(0)
    output_doc = Document(uploaded_file) 
    
    all_paragraphs = original_doc.paragraphs
    total_paras = len(all_paragraphs)
    
    st.info(f"📖 Documento cargado. Se procesarán {total_paras} bloques de texto conservando el diseño.")

    tab1, tab2 = st.tabs(["📊 Auditoría (Solo Texto)", "🚀 Corrección (Mantiene Formato)"])

    def run_preservation_process(mode):
        # Si es auditoría, creamos doc nuevo (no importa el formato del reporte)
        # Si es corrección, usamos output_doc (el clon)
        
        working_doc = output_doc if mode == "rewrite" else Document()
        if mode == "audit": working_doc.add_heading("Reporte de Auditoría", 0)
        
        p_bar = st.progress(0)
        status = st.empty()
        
        # Archivo temporal
        temp_filename = "temp_preserve_audit.docx" if mode == "audit" else "temp_preserve_rewrite.docx"
        
        # Iteramos sobre el ORIGINAL y escribimos en el WORKING_DOC
        # Usamos zip para asegurar que estamos en la misma línea
        if mode == "rewrite":
            iterable = zip(original_doc.paragraphs, working_doc.paragraphs)
            count_max = len(original_doc.paragraphs)
        else:
            iterable = enumerate(original_doc.paragraphs) # En audit solo leemos
            count_max = len(original_doc.paragraphs)

        processed_count = 0

        for item in iterable:
            processed_count += 1
            
            # Lógica diferente según el modo
            if mode == "rewrite":
                p_orig, p_dest = item
                text_to_process = p_orig.text
            else:
                idx, p_orig = item
                text_to_process = p_orig.text

            # SOLO PROCESAMOS SI HAY TEXTO (Ignoramos saltos de línea vacíos para no romper diseño)
            if len(text_to_process.strip()) > 2:
                status.text(f"🖊️ Editando párrafo {processed_count}/{count_max}...")
                
                result = process_paragraph_text(text_to_process, mode, tone_prompt, temp, initial_wait)
                
                if mode == "rewrite":
                    # AQUÍ ESTÁ LA MAGIA: Reemplazamos el texto dentro del párrafo existente
                    # Esto conserva la alineación y el estilo del párrafo (Normal, Heading, etc)
                    if "[ERROR" not in result:
                        p_dest.text = result 
                else:
                    # Auditoría (Reporte aparte)
                    if "CLEAN" not in result and "[ERROR" not in result:
                        working_doc.add_paragraph(f"--- Párrafo {processed_count} ---")
                        working_doc.add_paragraph(f"Original: {text_to_process[:50]}...")
                        working_doc.add_paragraph(result)
                
                # Pausa pequeña para no saturar
                time.sleep(0.5)
            
            # Actualizamos barra
            p_bar.progress(min(processed_count / count_max, 1.0))
            
            # Guardado progresivo cada 5 párrafos para no hacer lento el disco
            if processed_count % 5 == 0:
                save_recovery_file(working_doc, temp_filename)

        status.success("✅ ¡Proceso Terminado!")
        
        bio = BytesIO()
        working_doc.save(bio)
        return bio

    # --- BOTONES ---
    with tab1:
        if st.button("📊 Auditar"):
            st.session_state.final_doc = run_preservation_process("audit")
            
        if st.session_state.final_doc and st.session_state.final_doc.getbuffer().nbytes > 0: # Check simple
             st.download_button("⬇️ Descargar Reporte", st.session_state.final_doc.getvalue(), "Reporte.docx")

    with tab2:
        if st.button("🚀 Corregir y Mantener Diseño"):
            result_bio = run_preservation_process("rewrite")
            st.session_state.final_doc = result_bio # Guardar en sesión
        
        # Botón siempre visible si hay resultado en sesión
        if st.session_state.final_doc: 
             st.download_button("⬇️ Descargar Libro Final", st.session_state.final_doc.getvalue(), "Libro_Diseño_Preservado.docx")
