import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NativeFlow Robust", page_icon="🛡️", layout="wide")

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
        # Usamos 1.5 Flash porque tiene límites más generosos que el 2.5 experimental
        MODEL_NAME = 'gemini-1.5-flash' 
        model = genai.GenerativeModel(MODEL_NAME)
        st.success(f"✅ Conectado a {MODEL_NAME} (Modo Estable)")
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

# --- 3. FUNCIONES ROBUSTAS (BACKOFF & BATCHING) ---

def call_api_with_retry(prompt, temperature=0.7):
    """
    Intenta llamar a la API. Si da error 429 (Límite), espera y reintenta.
    """
    max_retries = 5
    wait_time = 10 # Segundos iniciales
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, generation_config={"temperature": temperature})
            return response.text.strip()
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                st.toast(f"⏳ Límite alcanzado. Esperando {wait_time}s para reintentar...", icon="⚠️")
                time.sleep(wait_time)
                wait_time *= 2 # Espera exponencial (10s, 20s, 40s...)
            else:
                return f"[ERROR NO RECUPERABLE: {error_str}]"
    return "[ERROR: Demasiados reintentos]"

def process_batch(text_batch, mode, tone_instr, temp):
    """
    Procesa un bloque grande de texto (varios párrafos juntos).
    """
    if not text_batch.strip(): return ""

    if mode == "audit":
        prompt = f"""
        Analyze this text batch for:
        1. Whirlwind = HE/HIM (Flag 'she').
        2. Corporate jargon ('outsourcing').
        3. Clumsy phrasing ("The X of Y").
        
        OUTPUT FORMAT:
        List specific issues found per paragraph snippet. If clean, say "CLEAN".
        
        Text: "{text_batch}"
        """
    else: # Rewrite mode
        prompt = f"""
        Rewrite this text batch to be Native US English.
        Specs: {tone_instr}
        
        RULES:
        1. Whirlwind is ALWAYS Male (he/him).
        2. Replace 'outsourcing' with 'naming'.
        3. Fix "The X of Y" -> "X Y" (e.g. Balloon Breathing).
        4. Maintain roughly the same paragraph structure.
        
        Text: "{text_batch}"
        """
    
    return call_api_with_retry(prompt, temp)

# --- 4. INTERFAZ ---
st.title("🛡️ NativeFlow: Procesamiento por Lotes")
st.info("Esta versión agrupa párrafos para evitar el error 429 y procesar libros largos.")

uploaded_file = st.file_uploader("Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    # Convertimos iterador a lista para saber total real
    all_paragraphs = [p.text for p in doc.paragraphs if len(p.text.strip()) > 5]
    total_paras = len(all_paragraphs)
    
    tab1, tab2 = st.tabs(["📊 Auditoría (Lotes)", "🚀 Corrección (Lotes)"])

    # --- PESTAÑA 1: AUDITORÍA ---
    with tab1:
        if st.button("🔍 Auditar por Lotes"):
            report_doc = Document()
            report_doc.add_heading('Reporte de Auditoría (Lotes)', 0)
            
            p_bar = st.progress(0)
            status = st.empty()
            
            # LÓGICA DE LOTES (BATCHING)
            BATCH_SIZE = 1500 # Caracteres por llamada (aprox 1 página)
            current_batch = ""
            
            for i, text in enumerate(all_paragraphs):
                status.caption(f"Acumulando texto... ({i}/{total_paras})")
                current_batch += text + "\n\n"
                
                # Si el lote está lleno o es el último párrafo
                if len(current_batch) > BATCH_SIZE or i == total_paras - 1:
                    status.text(f"📡 Enviando lote a la IA ({i}/{total_paras})...")
                    
                    # Llamada con reintento automático
                    result = process_batch(current_batch, "audit", "", 0)
                    
                    if result and "CLEAN" not in result:
                        report_doc.add_paragraph(f"--- LOTE HASTA PÁRRAFO {i} ---")
                        report_doc.add_paragraph(result)
                    
                    current_batch = "" # Limpiar lote
                    p_bar.progress((i+1)/total_paras)
            
            status.success("✅ Auditoría Completada")
            bio = BytesIO()
            report_doc.save(bio)
            st.download_button("⬇️ Descargar Reporte", bio.getvalue(), "Reporte_Lotes.docx")

    # --- PESTAÑA 2: CORRECCIÓN ---
    with tab2:
        if st.button("🚀 Crear Libro Final (Lotes)"):
            final_doc = Document()
            p_bar = st.progress(0)
            status = st.empty()
            
            # LÓGICA DE LOTES PARA REESCRITURA
            BATCH_SIZE = 1800 # Un poco más grande para aprovechar contexto
            current_batch = ""
            
            for i, text in enumerate(all_paragraphs):
                current_batch += text + "\n\n"
                
                if len(current_batch) > BATCH_SIZE or i == total_paras - 1:
                    status.text(f"✍️ Reescribiendo página aprox {int(i/10)}...")
                    
                    # Llamada con reintento
                    new_text_block = process_batch(current_batch, "rewrite", tone_prompt, temp)
                    
                    # Añadir el bloque reescrito al documento final
                    final_doc.add_paragraph(new_text_block)
                    final_doc.add_paragraph("-" * 10) # Separador visual opcional
                    
                    current_batch = ""
                    p_bar.progress((i+1)/total_paras)
            
            status.success("✅ ¡Libro Completado!")
            bio_f = BytesIO()
            final_doc.save(bio_f)
            st.download_button("⬇️ Descargar Libro", bio_f.getvalue(), "Libro_Final_Lotes.docx")
