import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time
import os
import re # Para limpieza de símbolos

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NativeFlow Completo", page_icon="💎", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #0d6efd; }
    .success-box { padding: 10px; background-color: #e6fffa; border-left: 5px solid #00bcd4; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURACIÓN API ---
with st.sidebar:
    st.header("🎛️ Centro de Mando")
    
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("✅ API Conectada")
    except Exception as e:
        st.error("❌ Falta API Key")
        st.stop()
    
    st.divider()

    # Usamos el comodín estable
    MODEL_NAME = 'models/gemini-flash-latest' 
    model = genai.GenerativeModel(MODEL_NAME)
    
    BATCH_SIZE = 5000 
    initial_wait = 2

    st.info("ℹ️ Sistema Todo en Uno")
    st.markdown("""
    * **Auditoría:** Detecta errores.
    * **Corrección:** Mantiene formato y limpia símbolos (**).
    """)

    st.divider()
    
    st.subheader("📝 Tono")
    tone_option = st.selectbox(
        "Estilo Literario:", 
        ["Warm & Kid-Friendly (Recomendado)", "Strict Grammar"]
    )

    if "Kid-Friendly" in tone_option:
        tone_prompt = "Tone: Warm, empathetic, validating. Simple vocabulary (Age 6-10)."
        temp = 0.7
    else:
        tone_prompt = "Tone: Neutral. Keep author's voice exact."
        temp = 0.3

# --- 3. FUNCIONES DE PROCESAMIENTO Y LIMPIEZA ---

def clean_markdown(text):
    """Elimina los símbolos de Markdown que ensucian el Word para Amazon KDP"""
    # 1. Eliminar negritas y cursivas (**texto**, *texto*)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) 
    text = re.sub(r'\*(.*?)\*', r'\1', text)     
    text = re.sub(r'__(.*?)__', r'\1', text)     
    
    # 2. Eliminar encabezados (### Título)
    text = re.sub(r'^#+\s*', '', text) 
    
    # 3. Eliminar viñetas de markdown si la IA las pone
    if text.strip().startswith("- "):
        text = text.strip()[2:] 
    
    return text.strip()

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
                wait_time += 1
            else:
                time.sleep(1)
    return f"[ERROR: {last_error}]"

def process_paragraph_text(text, mode, tone_instr, temp, wait_config):
    # Si es muy corto, lo ignoramos para no romper índices o pies de página
    if len(text.strip()) < 2: return text 

    if mode == "audit":
        prompt = f"""
        ACT AS A PROFESSIONAL EDITOR. Audit this text snippet.
        
        RULES: 
        1. Whirlwind Gender: Must be HE/HIM. Flag if 'she/her' appears.
        2. Corporate Jargon: Flag 'outsourcing'.
        3. Phrasing: Flag clumsy "The X of Y" structures.
        
        OUTPUT: List issues concisely. If perfect, output "CLEAN".
        Text: "{text}"
        """
    else: # Rewrite
        prompt = f"""
        You are a professional book editor.
        Rewrite this text to be native US English.
        
        STRICT FORMATTING RULES (CRITICAL):
        1. OUTPUT PLAIN TEXT ONLY. NO MARKDOWN.
        2. DO NOT use asterisks (**), hashes (##), or underscores (_).
        3. DO NOT use bullet points (-). Just the text.
        4. KEEP the sentence structure exactly as it is.
        5. Tone: {tone_instr}
        
        Text to rewrite: "{text}"
        """
    
    result = call_api(prompt, temp, wait_config)
    
    # Limpieza extra de seguridad solo en modo reescritura
    if mode == "rewrite":
        result = clean_markdown(result)
        
    return result

# --- 4. SISTEMA DE GUARDADO ---
def save_recovery_file(doc_obj, filename):
    try: doc_obj.save(filename)
    except: pass

def load_recovery_file(filename):
    with open(filename, "rb") as f: return BytesIO(f.read())

# --- 5. INTERFAZ ---
st.title("💎 NativeFlow: Sistema Completo")

# Recuperación de Desastres
if os.path.exists("temp_full_audit.docx"):
    st.warning("⚠️ Auditoría previa encontrada.")
    col1, col2 = st.columns([1,4])
    with col1:
        st.download_button("⬇️ Rescatar", load_recovery_file("temp_full_audit.docx"), "Audit_Rescatado.docx")
    with col2:
        if st.button("🗑️ Borrar", key="del_audit"): os.remove("temp_full_audit.docx"); st.rerun()

if os.path.exists("temp_full_rewrite.docx"):
    st.warning("⚠️ Libro corregido previo encontrado.")
    col1, col2 = st.columns([1,4])
    with col1:
        st.download_button("⬇️ Rescatar", load_recovery_file("temp_full_rewrite.docx"), "Libro_Rescatado.docx")
    with col2:
        if st.button("🗑️ Borrar", key="del_rew"): os.remove("temp_full_rewrite.docx"); st.rerun()

st.divider()

# Variables de Sesión para Botones
if "final_audit_doc" not in st.session_state: st.session_state.final_audit_doc = None
if "final_rewrite_doc" not in st.session_state: st.session_state.final_rewrite_doc = None

uploaded_file = st.file_uploader("Sube tu manuscrito ORIGINAL (.docx)", type=["docx"])

if uploaded_file:
    # 1. Cargamos el original
    original_doc = Document(uploaded_file)
    total_paras = len(original_doc.paragraphs)
    st.info(f"📖 Libro cargado: {total_paras} párrafos detectados.")

    # 2. Las Pestañas que pediste
    tab1, tab2 = st.tabs(["📊 Auditoría (Reporte)", "🚀 Corrección (KDP Ready)"])

    # --- LÓGICA DE PROCESO ---
    def run_process(mode):
        p_bar = st.progress(0)
        status = st.empty()
        
        # Preparar documento de salida
        if mode == "audit":
            # Para auditoría creamos un doc nuevo simple
            working_doc = Document()
            working_doc.add_heading("Reporte de Auditoría", 0)
            temp_filename = "temp_full_audit.docx"
            iterable = enumerate(original_doc.paragraphs)
        else:
            # Para corrección CLONAMOS el original para mantener formato
            uploaded_file.seek(0)
            working_doc = Document(uploaded_file)
            temp_filename = "temp_full_rewrite.docx"
            # Usamos zip para editar in-place
            iterable = zip(original_doc.paragraphs, working_doc.paragraphs)

        count = 0
        
        # Bucle principal
        for item in iterable:
            count += 1
            
            # Extraer texto según modo
            if mode == "audit":
                idx, p_orig = item
                text_orig = p_orig.text
            else:
                p_orig, p_dest = item
                text_orig = p_orig.text
            
            # Procesar solo si hay texto
            if len(text_orig.strip()) > 1:
                status.text(f"⚙️ Procesando párrafo {count}/{total_paras}...")
                
                result = process_paragraph_text(text_orig, mode, tone_prompt, temp, initial_wait)
                
                if mode == "audit":
                    # Si encontramos error, lo anotamos
                    if "CLEAN" not in result and "[ERROR" not in result:
                        working_doc.add_paragraph(f"--- Párrafo {count} ---")
                        working_doc.add_paragraph(f"Original: {text_orig[:40]}...")
                        working_doc.add_paragraph(result)
                else:
                    # Corrección: Reemplazo Quirúrgico + Limpieza
                    if "[ERROR" not in result:
                        p_dest.text = result # Aquí se pega el texto limpio sin asteriscos
            
            # Actualizar barra
            p_bar.progress(min(count / total_paras, 1.0))
            
            # Guardado parcial cada 10 párrafos
            if count % 10 == 0:
                save_recovery_file(working_doc, temp_filename)
            
            time.sleep(0.1) # Pausa mínima para velocidad

        status.success("✅ ¡Proceso completado!")
        st.balloons()
        
        bio = BytesIO()
        working_doc.save(bio)
        return bio

    # --- PESTAÑA 1: AUDITORÍA ---
    with tab1:
        st.write("Genera un reporte de errores (Género, frases raras, etc).")
        if st.button("📊 Comenzar Auditoría"):
            st.session_state.final_audit_doc = run_process("audit")
        
        if st.session_state.final_audit_doc:
            st.download_button("⬇️ Descargar Reporte", st.session_state.final_audit_doc.getvalue(), "Reporte_Auditoria.docx")

    # --- PESTAÑA 2: CORRECCIÓN ---
    with tab2:
        st.write("Genera el libro final: Formato original conservado, sin símbolos raros.")
        if st.button("🚀 Corregir Libro Final"):
            st.session_state.final_rewrite_doc = run_process("rewrite")
        
        if st.session_state.final_rewrite_doc:
            st.download_button("⬇️ Descargar Libro Listo (KDP)", st.session_state.final_rewrite_doc.getvalue(), "Libro_Final_KDP.docx")
