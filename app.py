import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="NativeFlow Turbo", page_icon="⚡", layout="centered")
st.title("⚡ NativeFlow: Edición Turbo (Chunking)")
st.markdown("Procesa libros largos agrupando párrafos para mayor velocidad.")

# --- 2. API Y MODELO ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    # Intentamos usar el modelo rápido
    model = genai.GenerativeModel('gemini-1.5-flash') 
except Exception as e:
    st.error(f"Error de configuración: {e}")
    st.stop()

# --- 3. FUNCIÓN DE REESCRITURA (BLOQUES GRANDES) ---
def rewrite_chunk(text_chunk):
    """Procesa un bloque grande de texto (varios párrafos juntos)."""
    if len(text_chunk.strip()) < 10: return text_chunk

    prompt = f"""
    You are a professional children's book editor (US English).
    Rewrite the text below to be native, warm, and grammatically perfect.

    *** CRITICAL RULES ***
    1. **Character Consistency:** 'Whirlwind' is ALWAYS Male (he/him).
    2. **Vocabulary:** No corporate jargon (e.g., no 'outsourcing'). Use 'Balloon Breathing' not 'The breathing of the balloon'.
    3. **Format:** Keep the exact same number of paragraphs if possible.
    4. **Output:** Return ONLY the rewritten text.

    Text to rewrite:
    {text_chunk}
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return text_chunk

# --- 4. INTERFAZ ---
uploaded_file = st.file_uploader("📂 Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file and st.button("🚀 Iniciar Procesamiento Rápido"):
    doc = Document(uploaded_file)
    new_doc = Document()
    
    # Variables para el Chunking
    current_chunk = ""
    CHUNK_SIZE = 1500  # Caracteres aprox por llamada (aprox media página)
    
    total_paragraphs = len(doc.paragraphs)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # BUCLE DE PROCESAMIENTO
    for i, para in enumerate(doc.paragraphs):
        text = para.text
        
        # Si el párrafo está vacío, lo saltamos o lo agregamos directo si quieres conservar espacios
        if not text.strip():
            continue

        # Acumulamos texto
        current_chunk += text + "\n\n"
        
        # Si el bloque ya es grande o es el último párrafo, enviamos a procesar
        if len(current_chunk) > CHUNK_SIZE or i == total_paragraphs - 1:
            status_text.caption(f"Procesando bloque hasta el párrafo {i+1}...")
            
            # Llamada a la IA
            rewritten_block = rewrite_chunk(current_chunk)
            
            # La IA devuelve un bloque de texto. Lo añadimos al documento nuevo.
            # Nota: Al usar chunking, perdemos el mapeo exacto 1 a 1 de estilos (negritas/cursivas)
            # pero ganamos velocidad masiva.
            new_doc.add_paragraph(rewritten_block)
            
            # Limpiamos el chunk para empezar el siguiente
            current_chunk = ""
            
            # Actualizar barra
            progress_bar.progress((i + 1) / total_paragraphs)
            
            # Pausa mínima
            time.sleep(0.5)

    status_text.success("✅ ¡Libro completado!")
    
    bio = BytesIO()
    new_doc.save(bio)
    
    st.download_button(
        label="⬇️ Descargar Libro (.docx)",
        data=bio.getvalue(),
        file_name=f"NativeFlow_Turbo_{uploaded_file.name}",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
