import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time
import os
import re # Importamos expresiones regulares para limpieza profunda

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NativeFlow: Edición Limpia", page_icon="🧼", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #20c997; }
    .success-box { padding: 10px; background-color: #e6fffa; border-left: 5px solid #20c997; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURACIÓN API ---
with st.sidebar:
    st.header("🧼 Limpieza y Edición")
    
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("✅ API Conectada")
    except Exception as e:
        st.error("❌ Falta API Key")
        st.stop()
    
    st.divider()

    # Usamos el modelo Latest para estabilidad
    MODEL_NAME = 'models/gemini-flash-latest' 
    model = genai.GenerativeModel(MODEL_NAME)
    
    # Ajustes para texto limpio
    BATCH_SIZE = 5000 
    initial_wait = 2

    st.info("ℹ️ Modo: Texto Plano (KDP Ready)")
    st.caption("Elimina símbolos raros (**, ##) y respeta los párrafos originales.")

    st.divider()
    
    st.subheader("📝 Tono")
    tone_option = st.selectbox(
        "Estilo:", 
        ["Warm & Kid-Friendly (Recomendado)", "Strict Grammar"]
    )

    if "Kid-Friendly" in tone_option:
        tone_prompt = "Tone: Warm, empathetic, validating. Simple vocabulary (Age 6-10)."
        temp = 0.7
    else:
        tone_prompt = "Tone: Neutral. Keep author's voice exact."
        temp = 0.3

# --- 3. FUNCIONES DE LIMPIEZA ---

def clean_markdown(text):
    """Elimina los símbolos de Markdown que ensucian el Word"""
    # 1. Eliminar negritas y cursivas de markdown (**texto**, *texto*)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) # Quita **
    text = re.sub(r'\*(.*?)\*', r'\1', text)     # Quita *
    text = re.sub(r'__(.*?)__', r'\1', text)     # Quita __
    
    # 2. Eliminar encabezados de markdown (### Título)
    text = re.sub(r'^#+\s*', '', text) 
    
    # 3. Eliminar viñetas de markdown si la IA las pone (el Word ya tiene su viñeta)
    if text.strip().startswith("- "):
        text = text.strip()[2:] 
    
    return text.strip()

def call_api(prompt, temperature=0.7, wait_start=2):
    max_retries = 5 
    wait_time = wait_start
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, generation_config={"temperature": temperature})
            return response.text.strip()
        except Exception as e:
            time.sleep(wait_time)
            wait_time += 1
    return "[ERROR API]"

def process_paragraph_text(text, mode, tone_instr, temp, wait_config):
    # Si es texto muy corto o solo números/símbolos, lo dejamos igual para no romper índices
    if len(text.strip()) < 2: return text 

    if mode == "audit":
        prompt = f"""
        AUDIT this text. RULES: Whirlwind=HE. No 'outsourcing'.
        Text: "{text}"
        """
    else: # Rewrite
        # EL SECRETO: Instrucciones estrictas de NO MARKDOWN
        prompt = f"""
        You are a professional book editor.
        Rewrite this text to be native US English.
        
        STRICT FORMATTING RULES (CRITICAL):
        1. OUTPUT PLAIN TEXT ONLY. NO MARKDOWN.
        2. DO NOT use asterisks (**), hashes (##), or underscores (_).
        3. DO NOT use bullet points or list dashes (-). Just the text.
        4. KEEP the sentence structure exactly as it is (do not merge sentences).
        5. Tone: {tone_instr}
        
        Text to rewrite: "{text}"
        """
    
    result = call_api(prompt, temp, wait_config)
    
    # Doble seguridad: Limpiamos con Python por si la IA desobedece
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
st.title("🧼 NativeFlow: Limpieza para KDP")

# Recuperación
if os.path.exists("temp_clean_rewrite.docx"):
    st.warning("⚠️ Hay un trabajo previo guardado.")
    col1, col2 = st.columns([1,4])
    with col1:
        st.download_button("⬇️ Descargar", load_recovery_file("temp_clean_rewrite.docx"), "Libro_Rescatado.docx")
    with col2:
        if st.button("🗑️ Borrar y empezar de cero"):
            os.remove("temp_clean_rewrite.docx")
            st.rerun()

st.divider()

if "final_clean_doc" not in st.session_state: st.session_state.final_clean_doc = None

uploaded_file = st.file_uploader("Sube tu manuscrito ORIGINAL (.docx)", type=["docx"])

if uploaded_file:
    # Cargamos original y preparamos copia
    original_doc = Document(uploaded_file)
    uploaded_file.seek(0)
    output_doc = Document(uploaded_file) 
    
    all_paragraphs = original_doc.paragraphs
    total_paras = len(all_paragraphs)
    
    st.info(f"📖 Libro cargado: {total_paras} párrafos. Se eliminarán símbolos extraños.")

    if st.button("🚀 Corregir y Limpiar Formato"):
        p_bar = st.progress(0)
        status = st.empty()
        
        temp_filename = "temp_clean_rewrite.docx"
        
        # Iteramos párrafo a párrafo
        # Usamos zip para escribir en el destino manteniendo estilos
        iterable = zip(original_doc.paragraphs, output_doc.paragraphs)
        
        count = 0
        for p_orig, p_dest in iterable:
            count += 1
            text_orig = p_orig.text
            
            # Solo procesamos si hay contenido real
            if len(text_orig.strip()) > 1:
                status.text(f"🧼 Puliendo párrafo {count}/{total_paras}...")
                
                # Obtenemos texto limpio
                new_text = process_paragraph_text(text_orig, "rewrite", tone_prompt, temp, initial_wait)
                
                if "[ERROR" not in new_text:
                    # REEMPLAZO QUIRÚRGICO:
                    # Mantiene el estilo del párrafo (Heading 1, Normal, Bullet, etc.)
                    # Pero cambia el contenido por el texto limpio (sin **)
                    p_dest.text = new_text 
            
            # Barra de progreso
            p_bar.progress(min(count / total_paras, 1.0))
            
            # Guardado intermedio cada 10 párrafos
            if count % 10 == 0:
                save_recovery_file(output_doc, temp_filename)
                
            # Pausa mínima
            time.sleep(0.2)

        status.success("✅ ¡Libro listo para Amazon KDP!")
        st.balloons()
        
        # Guardamos en sesión
        bio = BytesIO()
        output_doc.save(bio)
        st.session_state.final_clean_doc = bio

    # Botón de descarga final
    if st.session_state.final_clean_doc:
         st.download_button(
             "⬇️ Descargar Libro Limpio (.docx)", 
             st.session_state.final_clean_doc.getvalue(), 
             "Libro_KDP_Ready.docx"
         )
