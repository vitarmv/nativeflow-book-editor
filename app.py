import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NativeFlow Crucero", page_icon="🚢", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #17a2b8; }
    .success-box { padding: 10px; background-color: #d4edda; border-left: 5px solid #28a745; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURACIÓN API ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # GESTIÓN DE CLAVES
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        
        # Usamos Gemini 2.0 Flash por su gran memoria (Context Window)
        MODEL_NAME = 'gemini-2.0-flash' 
        model = genai.GenerativeModel(MODEL_NAME)
        st.success(f"✅ Motor Activo: {MODEL_NAME}")
        
    except Exception as e:
        st.error("❌ Error de API Key. Revisa tus secrets.")
        st.stop()

    st.divider()
    
    # SELECTOR DE TONO
    st.subheader("🎨 Estilo de Edición")
    tone_option = st.selectbox(
        "Objetivo:", 
        ["Warm & Kid-Friendly (Tu Estilo)", "Strict Grammar (Solo Corrección)", "Storyteller (Creativo)"]
    )

    # Definición de Prompts según selección
    if tone_option == "Warm & Kid-Friendly (Tu Estilo)":
        tone_prompt = "Tone: Warm, empathetic, simplifying complex words for kids (6-10 years)."
        temp = 0.7
    elif tone_option == "Strict Grammar (Solo Corrección)":
        tone_prompt = "Tone: Neutral. Keep author's voice exactly. Only fix grammar."
        temp = 0.3
    else:
        tone_prompt = "Tone: Vivid, magical, descriptive and sensory."
        temp = 0.8

# --- 3. FUNCIONES DE PROCESAMIENTO ROBUSTO ---

def call_api_safe(prompt, temperature=0.7):
    """
    Realiza la llamada a la API con sistema de reintentos inteligente.
    """
    max_retries = 5
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, generation_config={"temperature": temperature})
            return response.text.strip()
            
        except Exception as e:
            error_str = str(e)
            # Si Google nos bloquea (429), esperamos 60 segundos y reintentamos
            if "429" in error_str or "quota" in error_str.lower():
                wait_time = 60
                st.toast(f"🛑 Tráfico alto en Google. Esperando {wait_time}s para enfriar...", icon="❄️")
                time.sleep(wait_time)
            elif "404" in error_str:
                return f"[ERROR CRÍTICO: El modelo {MODEL_NAME} no está disponible en tu cuenta]"
            else:
                return f"[ERROR DESCONOCIDO: {error_str}]"
    
    return "[FALLO: Google no respondió tras múltiples intentos]"

def process_mega_batch(text_batch, mode, tone_instr, temp):
    """
    Procesa bloques gigantes (15,000 caracteres) para minimizar llamadas.
    """
    if not text_batch.strip(): return ""

    if mode == "audit":
        prompt = f"""
        Analyze this book section (approx 5-7 pages).
        Identify strictly:
        1. Whirlwind Gender: Must be HE/HIM. Flag 'she/her'.
        2. Jargon: Flag 'outsourcing'.
        3. Phrasing: Flag "The X of Y" (e.g. "The breathing of the balloon").
        
        OUTPUT: List specific issues found concisely. If clean, output "CLEAN".
        Text: "{text_batch}"
        """
    else: # Rewrite
        prompt = f"""
        You are editing a children's book (US English).
        Rewrite the following text batch (approx 5-7 pages).
        
        SPECS: {tone_instr}
        
        CRITICAL RULES:
        1. Whirlwind is ALWAYS Male (he/him).
        2. No 'outsourcing' -> use 'naming' or 'externalizing'.
        3. Fix "The X of Y" -> "X Y" (e.g. Balloon Breathing).
        4. Maintain the paragraph structure.
        
        Text Batch:
        "{text_batch}"
        """
    
    return call_api_safe(prompt, temp)

# --- 4. INTERFAZ PRINCIPAL ---
st.title("🚢 NativeFlow: Modo Crucero")
st.markdown("Procesamiento estable por lotes grandes para evitar bloqueos.")

uploaded_file = st.file_uploader("Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    # Extraemos solo párrafos con contenido real
    all_paragraphs = [p.text for p in doc.paragraphs if len(p.text.strip()) > 2]
    total_paras = len(all_paragraphs)
    
    st.info(f"📖 Libro cargado: **{total_paras} párrafos detectados**.")
    
    tab1, tab2 = st.tabs(["📊 Auditoría (Reporte)", "🚀 Corrección (Libro Final)"])

    # Función Maestra de Ejecución
    def run_process(mode):
        output_doc = Document()
        if mode == "audit": output_doc.add_heading('Reporte Auditoría NativeFlow', 0)
        
        p_bar = st.progress(0)
        status = st.empty()
        
        # --- MEGA BATCHING (La clave del éxito) ---
        # 15,000 chars = ~6 páginas. Pocas llamadas = Pocos bloqueos.
        BATCH_SIZE = 15000 
        current_batch = ""
        
        # Cálculo para barra de progreso
        total_chars = sum(len(p) for p in all_paragraphs)
        estimated_batches = (total_chars // BATCH_SIZE) + 2
        processed_batches = 0

        start_time = time.time()

        for i, text in enumerate(all_paragraphs):
            current_batch += text + "\n\n"
            
            # Procesar cuando el lote esté lleno o sea el final
            if len(current_batch) > BATCH_SIZE or i == total_paras - 1:
                processed_batches += 1
                status.text(f"⚙️ Procesando Lote {processed_batches}/{estimated_batches} (Esto toma unos 20s)...")
                
                # LLAMADA A LA IA
                result = process_mega_batch(current_batch, mode, tone_prompt, temp)
                
                # GUARDADO DE RESULTADOS
                if mode == "audit":
                    if "CLEAN" not in result and "ERROR" not in result:
                        output_doc.add_paragraph(f"--- REPORTE LOTE {processed_batches} ---")
                        output_doc.add_paragraph(result)
                else:
                    # Limpiamos posibles bloques de código Markdown
                    clean_text = result.replace("```", "").replace("markdown", "")
                    output_doc.add_paragraph(clean_text)
                    output_doc.add_paragraph("-" * 20) # Separador visual

                # ACTUALIZAR UI
                progress_val = min(processed_batches / estimated_batches, 1.0)
                p_bar.progress(progress_val)
                
                current_batch = "" 
                
                # --- PAUSA PREVENTIVA (CRITICAL) ---
                # Esperamos 10s después de cada éxito para mantenernos bajo el radar.
                if i < total_paras - 1:
                    status.caption(f"☕ Enfriando motores (10s)... Lote {processed_batches} completado.")
                    time.sleep(10)

        total_time = round((time.time() - start_time) / 60, 1)
        status.success(f"✅ ¡Proceso completado en {total_time} minutos!")
        
        bio = BytesIO()
        output_doc.save(bio)
        return bio

    # --- PESTAÑA 1 ---
    with tab1:
        if st.button("🔍 Iniciar Auditoría"):
            file_data = run_process("audit")
            st.download_button("⬇️ Descargar Reporte (.docx)", file_data.getvalue(), "Reporte_Auditoria.docx")

    # --- PESTAÑA 2 ---
    with tab2:
        if st.button("🚀 Iniciar Corrección"):
            file_data = run_process("rewrite")
            st.download_button("⬇️ Descargar Libro Final (.docx)", file_data.getvalue(), "Libro_Corregido.docx")
