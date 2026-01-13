import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import re
import time

# --- FUNCIONES ---

def contains_fillable_lines(text, min_chars=3):
    """
    Detecta si el párrafo tiene líneas para escribir.
    Soporta:
    - Guiones bajos: ______
    - Guiones medios: ------
    - Puntos suspensivos: ......
    """
    # Explicación del Regex:
    # [_.\-]: Busca cualquier carácter que sea guion bajo, punto o guion medio.
    # {min_chars,}: Que aparezca 'min_chars' veces o más seguido.
    pattern = f"([_.\-]){{{min_chars},}}"
    return bool(re.search(pattern, text))

def transform_interactive_text(text, cta_message):
    """Usa IA para reemplazar las líneas por el mensaje de descarga"""
    
    # Usamos el modelo rápido
    model = genai.GenerativeModel('models/gemini-flash-latest')
    
    # --- PROMPT ACTUALIZADO ---
    prompt = f"""
    ACT AS A PROFESSIONAL EDITOR CONVERTING A WORKBOOK TO KDP EBOOK.
    
    TASK: Analyze the provided text. It contains "fill-in-the-blank" lines intended for a physical book.
    These lines might look like underscores (______), dashes (------), or dots (......).
    
    INSTRUCTIONS:
    1. Identify the question or prompt asking the user to write.
    2. DETECT AND REMOVE the physical lines (any sequence of _, -, or .).
    3. INSERT the following Call-To-Action (CTA) in a natural way immediately after the question:
       "{cta_message}"
    4. Keep the tone friendly. Do NOT summarize. Keep the original question intact, just swap the lines for the CTA.
    
    INPUT TEXT: "{text}"
    
    OUTPUT (Text only):
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return text 

# --- INTERFAZ ---
st.title("📲 Limpiador de Líneas (Workbook a eBook)")
st.markdown("Reemplaza líneas de escritura (`____` o `----`) por enlaces de descarga.")

# Configuración en barra lateral
with st.sidebar:
    st.header("⚙️ Configuración")
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("✅ API Conectada")
    except:
        st.error("❌ Falta API Key")

    cta_text = st.text_area(
        "Texto de Reemplazo (Call to Action):", 
        "🛑 **(Ejercicio Interactivo)**: Para completar esto, usa tu Cuaderno de Actividades (Pág X). Descárgalo aquí: [TuEnlace]",
        height=100
    )
    
    # Sensibilidad
    threshold = st.slider("Largo mínimo de la línea para detectarla", 3, 15, 4, 
                          help="Si hay 4 o más guiones seguidos, se considera una línea.")

uploaded_file = st.file_uploader("Sube tu Workbook (.docx)", type=["docx"])

if uploaded_file and st.button("🚀 Limpiar Líneas"):
    doc = Document(uploaded_file)
    original_paras = doc.paragraphs
    total = len(original_paras)
    
    p_bar = st.progress(0)
    status = st.empty()
    
    changes_count = 0
    
    for i, p in enumerate(original_paras):
        text_orig = p.text
        
        # 1. Detección (Ahora soporta ---- y ____)
        if contains_fillable_lines(text_orig, threshold):
            status.text(f"🧹 Limpiando líneas en párrafo {i+1}...")
            
            # 2. Reemplazo IA
            new_text = transform_interactive_text(text_orig, cta_text)
            
            if new_text != text_orig:
                p.text = new_text
                changes_count += 1
                time.sleep(0.5) # Pausa anti-saturación
        
        if i % 10 == 0: p_bar.progress((i + 1) / total)

    p_bar.progress(1.0)
    status.success(f"✅ ¡Listo! Se eliminaron {changes_count} bloques de líneas.")
    
    # Descarga
    bio = BytesIO()
    doc.save(bio)
    
    st.download_button(
        label="⬇️ Descargar Ebook Limpio",
        data=bio.getvalue(),
        file_name="Libro_Sin_Lineas.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
