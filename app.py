import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NativeFlow Pro", page_icon="✍️", layout="wide")

# CSS para mejorar la comparación visual
st.markdown("""
<style>
    .original-text { color: #856404; background-color: #fff3cd; padding: 10px; border-radius: 5px; border-left: 5px solid #ffeeba; }
    .edited-text { color: #155724; background-color: #d4edda; padding: 10px; border-radius: 5px; border-left: 5px solid #c3e6cb; }
    .stProgress > div > div > div > div { background-color: #4CAF50; }
</style>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR: CONFIGURACIÓN Y TONOS ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    
    # API Key Handling
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("✅ API Conectada")
    except:
        st.error("❌ Falta API Key en secrets")
        st.stop()

    st.divider()
    
    # SELECCIÓN DE TONO
    st.subheader("🎨 Estilo de Edición")
    tone_option = st.selectbox(
        "Elige el objetivo del texto:",
        options=["Warm & Kid-Friendly (Recomendado)", "Grammar Polish Only (Conservador)", "Magical Storyteller (Creativo)"],
        index=0
    )
    
    # Definir instrucciones según la opción
    if tone_option == "Warm & Kid-Friendly (Recomendado)":
        tone_instruction = "Tone: Warm, validating, empathetic. Simplify complex words for kids (6-10 years old)."
        temp_setting = 0.7 # Creatividad balanceada
    elif tone_option == "Grammar Polish Only (Conservador)":
        tone_instruction = "Tone: Neutral. KEEP the author's original style/voice strictly. Only fix grammar, syntax errors, and unnatural phrasing."
        temp_setting = 0.3 # Baja creatividad, alta fidelidad
    else: # Magical
        tone_instruction = "Tone: Whimsical, magical, and vivid. Use descriptive verbs and sensory language to make the story come alive."
        temp_setting = 0.9 # Alta creatividad

    st.info(f"Modo seleccionado: **{tone_option}**")

# --- 3. LÓGICA DE IA ---
def rewrite_paragraph_pro(text, tone_instr, temp):
    if len(text.strip()) < 15: return text

    # Modelo con fallback
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
    except:
        model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    You are an expert US English book editor.
    
    **TASK:** Rewrite the text below according to these specifications:
    {tone_instr}

    **MANDATORY RULES (Always active):**
    1. **Consistency:** Character 'Whirlwind' is ALWAYS Male (he/him).
    2. **Anti-Jargon:** Replace 'outsourcing' with 'naming' or 'externalizing'.
    3. **Syntax:** Fix Spanish sentence structures to sound Native US.
    4. **Output:** Return ONLY the rewritten text.

    **Original Text:**
    "{text}"
    """
    
    try:
        response = model.generate_content(prompt, generation_config={"temperature": temp})
        return response.text.strip()
    except Exception:
        return text

# --- 4. INTERFAZ PRINCIPAL ---
st.title("✍️ NativeFlow Pro: Edición Inteligente")
st.markdown("Analiza, corrige y adapta el tono de tu manuscrito en tiempo real.")

uploaded_file = st.file_uploader("Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file:
    if st.button("🚀 INICIAR EDICIÓN"):
        doc = Document(uploaded_file)
        new_doc = Document()
        
        # Contenedores para el reporte
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Crear pestañas para organizar la vista
        tab1, tab2 = st.tabs(["👁️ Vista en Vivo (Live)", "📄 Documento Final"])
        
        with tab1:
            st.write("### 🔍 Comparativa Antes vs. Después")
            # Un contenedor que se irá llenando (o scrollable)
            history_container = st.container()

        total_paragraphs = len(doc.paragraphs)
        
        # --- BUCLE DE PROCESAMIENTO ---
        for i, para in enumerate(doc.paragraphs):
            original = para.text
            
            status_text.caption(f"Editando párrafo {i+1} de {total_paragraphs}...")
            
            # Procesar
            edited = rewrite_paragraph_pro(original, tone_instruction, temp_setting)
            
            # Guardar
            new_para = new_doc.add_paragraph(edited)
            new_para.style = para.style
            
            # --- MOSTRAR CAMBIOS EN VIVO ---
            # Solo mostramos si hubo cambios significativos y el texto no es vacío
            if len(original) > 40:
                with history_container:
                    # Usamos columnas y HTML personalizado para que se vea bonito
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f'<div class="original-text"><b>Original:</b><br>{original}</div>', unsafe_allow_html=True)
                    with c2:
                        # Si quedó igual, mostramos aviso, si cambió, mostramos el nuevo
                        if original.strip() == edited.strip():
                            st.markdown(f'<div class="edited-text" style="background-color:#f8f9fa; border-color:#ccc;"><i>Sin cambios necesarios</i></div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="edited-text"><b>✨ NativeFlow:</b><br>{edited}</div>', unsafe_allow_html=True)
                    st.write("---") # Separador
            
            progress_bar.progress((i + 1) / total_paragraphs)
            time.sleep(0.1) # Pequeña pausa para no saturar UI

        status_text.success("✅ ¡Edición Completada!")
        
        # --- DESCARGA ---
        bio = BytesIO()
        new_doc.save(bio)
        
        with tab2:
            st.success("Tu documento está listo.")
            st.download_button(
                label="⬇️ Descargar DOCX Corregido",
                data=bio.getvalue(),
                file_name=f"NativeFlow_{tone_option.split()[0]}_{uploaded_file.name}",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
