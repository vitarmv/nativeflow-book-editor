import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="NativeFlow DEBUG", page_icon="🐞", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #dc3545; } /* Rojo Debug */
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("🐞 Modo Diagnóstico")
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("API Key Detectada")
    except:
        st.error("Falta la API Key")
        st.stop()
        
    # FORZAMOS EL MODELO 1.5 PARA PROBAR VELOCIDAD
    MODEL_NAME = 'gemini-1.5-flash'
    model = genai.GenerativeModel(MODEL_NAME)
    st.info(f"Probando Motor: {MODEL_NAME}")

    tone_prompt = "Tone: Warm, empathetic, validating."

# --- FUNCION TRANSPARENTE (SIN FILTROS) ---
def call_api_debug(prompt):
    try:
        # Temperatura baja para ser precisos
        response = model.generate_content(prompt, generation_config={"temperature": 0.3})
        return response.text.strip()
    except Exception as e:
        # SI FALLA, DEVUELVE EL ERROR EXACTO
        return f"!!! ERROR DE SISTEMA: {str(e)} !!!"

def process_batch(text_batch, mode):
    if not text_batch.strip(): return "Texto vacío"

    if mode == "audit":
        prompt = f"""
        AUDIT THIS TEXT.
        Find: 1. Whirlwind Gender (Must be HE). 2. Jargon (Outsourcing).
        OUTPUT: List issues or "CLEAN".
        Text: "{text_batch}"
        """
    else:
        prompt = f"Rewrite this text: {text_batch}"
        
    return call_api_debug(prompt)

# --- INTERFAZ ---
st.title("🐞 NativeFlow: Buscador de Errores")
st.warning("Este modo mostrará los errores en crudo para saber por qué falla.")

uploaded_file = st.file_uploader("Sube el manuscrito", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    all_paragraphs = [p.text for p in doc.paragraphs if len(p.text.strip()) > 2]
    total_paras = len(all_paragraphs)
    
    st.write(f"📊 **Diagnóstico del archivo:** Se detectaron **{total_paras} párrafos** con texto.")
    
    if total_paras == 0:
        st.error("🚨 ¡ALERTA! El archivo parece vacío o el formato no se puede leer. ¿Es un PDF convertido? Prueba copiar y pegar el texto en un Word nuevo.")
        st.stop()

    if st.button("🐞 INICIAR AUDITORÍA DE PRUEBA"):
        output_doc = Document()
        output_doc.add_heading('Reporte DEBUG', 0)
        
        p_bar = st.progress(0)
        status_box = st.empty()
        
        BATCH_SIZE = 12000
        current_batch = ""
        processed_batches = 0
        total_chars = sum(len(p) for p in all_paragraphs)
        estimated_batches = (total_chars // BATCH_SIZE) + 2

        for i, text in enumerate(all_paragraphs):
            current_batch += text + "\n\n"
            
            if len(current_batch) > BATCH_SIZE or i == total_paras - 1:
                processed_batches += 1
                
                # Muestra en pantalla qué está pasando
                status_box.info(f"Analizando Lote {processed_batches}... (Tamaño: {len(current_batch)} chars)")
                
                # LLAMADA
                result = process_batch(current_batch, "audit")
                
                # ESCRIBIMOS EL RESULTADO SEA CUAL SEA (Incluso errores)
                output_doc.add_paragraph(f"--- LOTE {processed_batches} ---")
                output_doc.add_paragraph(result)
                
                # Muestra una vista previa del resultado en pantalla
                with st.expander(f"Resultado Lote {processed_batches} (Click para ver)"):
                    st.write(result)
                
                p_bar.progress(min(processed_batches / estimated_batches, 1.0))
                current_batch = ""
                time.sleep(0.5)

        st.success("Diagnóstico finalizado.")
        
        bio = BytesIO()
        output_doc.save(bio)
        st.download_button("⬇️ Descargar Reporte Diagnóstico", bio, "Reporte_DEBUG.docx")
