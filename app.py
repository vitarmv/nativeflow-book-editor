import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NativeFlow 2.0 Turbo", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #28a745; }
    .status-box { padding: 10px; border-radius: 5px; background-color: #f0f2f6; border-left: 5px solid #007bff; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURACIÓN API ---
with st.sidebar:
    st.header("⚙️ Configuración")
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        
        # MODELO: Usamos Gemini 2.0 Flash (Ideal para contextos largos)
        MODEL_NAME = 'gemini-2.0-flash' 
        model = genai.GenerativeModel(MODEL_NAME)
        st.success(f"✅ Motor: {MODEL_NAME}")
        
    except Exception as e:
        st.error(f"❌ Error API: {e}")
        st.stop()

    st.divider()
    
    st.subheader("🎨 Tono")
    tone_option = st.selectbox(
        "Estilo:", 
        ["Warm & Kid-Friendly", "Strict Grammar", "Storyteller"]
    )

    if tone_option == "Warm & Kid-Friendly":
        tone_prompt = "Tone: Warm, empathetic, simplifying complex words for kids."
        temp = 0.7
    elif tone_option == "Strict Grammar":
        tone_prompt = "Tone: Neutral. Keep author's voice, fix only grammar."
        temp = 0.3
    else:
        tone_prompt = "Tone: Vivid, magical, descriptive."
        temp = 0.8

# --- 3. FUNCIONES ROBUSTAS ---

def call_api_with_retry(prompt, temperature=0.7):
    """
    Intenta llamar a la API. Si da error 429, espera exponencialmente.
    """
    max_retries = 10 
    wait_time = 20  # Espera inicial más larga para asegurar que se limpie el cupo
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, generation_config={"temperature": temperature})
            return response.text.strip()
        except Exception as e:
            error_str = str(e)
            # Manejo de límites (429) o sobrecarga (503)
            if "429" in error_str or "quota" in error_str.lower() or "503" in error_str:
                st.toast(f"⏳ Límite alcanzado ({attempt+1}/{max_retries}). Pausando {wait_time}s...", icon="✋")
                time.sleep(wait_time)
                wait_time += 10 # Incremento lineal para no esperar eternamente
            elif "404" in error_str:
                return f"[ERROR CRÍTICO: Modelo no encontrado. Verifica el nombre en el sidebar.]"
            else:
                return f"[ERROR NO RECUPERABLE: {error_str}]"
    return "[ERROR: Google está saturado, intenta más tarde]"

def process_batch(text_batch, mode, tone_instr, temp):
    """
    Procesa bloques gigantes de texto.
    """
    if not text_batch.strip(): return ""

    if mode == "audit":
        prompt = f"""
        Analyze this text batch. It contains multiple paragraphs from a book.
        
        TASKS:
        1. Whirlwind Gender: Must be HE/HIM. Flag usages of 'she/her'.
        2. Corporate Jargon: Flag 'outsourcing'.
        3. Phrasing: Flag "The X of Y" (e.g. "The breathing of the balloon").
        
        OUTPUT:
        List issues found concisely. If the whole batch is fine, output "CLEAN".
        
        Text Batch:
        "{text_batch}"
        """
    else: # Rewrite mode
        prompt = f"""
        You are editing a children's book (US English).
        Rewrite the following text batch provided below.
        
        SPECS: {tone_instr}
        
        CRITICAL RULES:
        1. Whirlwind is ALWAYS Male (he/him).
        2. Replace 'outsourcing' with 'naming' or 'externalizing'.
        3. Fix "The X of Y" -> "X Y" (e.g. Balloon Breathing).
        4. Maintain the paragraphs structure.
        
        Text Batch to Rewrite:
        "{text_batch}"
        """
    
    return call_api_with_retry(prompt, temp)

# --- 4. INTERFAZ ---
st.title("🛡️ NativeFlow: Modo Lotes Gigantes")
st.info(f"Estrategia: Enviar bloques grandes para reducir llamadas a la API.")

uploaded_file = st.file_uploader("Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    # Filtramos párrafos vacíos
    all_paragraphs = [p.text for p in doc.paragraphs if len(p.text.strip()) > 2]
    total_paras = len(all_paragraphs)
    
    st.write(f"📖 Documento cargado: **{total_paras} párrafos detectados**.")
    
    tab1, tab2 = st.tabs(["📊 Auditoría", "🚀 Corrección"])

    # --- PESTAÑA 1: AUDITORÍA ---
    with tab1:
        if st.button("🔍 Auditar"):
            report_doc = Document()
            report_doc.add_heading('Reporte de Auditoría', 0)
            
            p_bar = st.progress(0)
            status = st.empty()
            
            # --- SUPER BATCHING ---
            # Aumentamos a 8,000 caracteres (aprox 3-4 páginas)
            # Gemini 2.0 maneja esto sin sudar.
            BATCH_SIZE = 8000 
            current_batch = ""
            
            for i, text in enumerate(all_paragraphs):
                current_batch += text + "\n\n"
                
                # Procesar si el lote es grande o es el final
                if len(current_batch) > BATCH_SIZE or i == total_paras - 1:
                    status.text(f"📡 Analizando bloque... ({int((i/total_paras)*100)}%)")
                    
                    result = process_batch(current_batch, "audit", "", 0)
                    
                    if result and "CLEAN" not in result and "ERROR" not in result:
                        report_doc.add_paragraph(f"--- REPORTE BLOQUE HASTA PÁRRAFO {i} ---")
                        report_doc.add_paragraph(result)
                    elif "ERROR" in result:
                        report_doc.add_paragraph(f"⚠️ {result}")
                    
                    current_batch = "" 
                    p_bar.progress((i+1)/total_paras)
                    
                    # PAUSA DE SEGURIDAD PROACTIVA
                    # Esperamos 5 segundos SIEMPRE, para no molestar a Google
                    time.sleep(5)
            
            status.success("✅ Auditoría Completada")
            bio = BytesIO()
            report_doc.save(bio)
            st.download_button("⬇️ Descargar Reporte", bio.getvalue(), "Reporte_Auditoria.docx")

    # --- PESTAÑA 2: CORRECCIÓN ---
    with tab2:
        if st.button("🚀 Crear Libro Final"):
            final_doc = Document()
            p_bar = st.progress(0)
            status = st.empty()
            
            # Mismo Batching Gigante
            BATCH_SIZE = 8000 
            current_batch = ""
            
            for i, text in enumerate(all_paragraphs):
                current_batch += text + "\n\n"
                
                if len(current_batch) > BATCH_SIZE or i == total_paras - 1:
                    status.text(f"✍️ Reescribiendo bloque... ({int((i/total_paras)*100)}%)")
                    
                    new_text_block = process_batch(current_batch, "rewrite", tone_prompt, temp)
                    
                    # Limpieza básica por si la IA añade markdown
                    new_text_block = new_text_block.replace("```", "")
                    
                    final_doc.add_paragraph(new_text_block)
                    final_doc.add_paragraph("-" * 20) # Separador visual entre bloques
                    
                    current_batch = ""
                    p_bar.progress((i+1)/total_paras)
                    
                    # PAUSA DE SEGURIDAD (Enfriamiento)
                    time.sleep(5)
            
            status.success("✅ ¡Libro Completado!")
            bio_f = BytesIO()
            final_doc.save(bio_f)
            st.download_button("⬇️ Descargar Libro", bio_f.getvalue(), "Libro_Final.docx")
