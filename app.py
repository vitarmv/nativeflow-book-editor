import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="NativeFlow: Editor de Libros",
    page_icon="📚",
    layout="centered"
)

st.title("📚 NativeFlow: Edición con IA")
st.markdown("""
Esta herramienta reescribe tu manuscrito para que suene como **inglés nativo (US)**, 
manteniendo el tono cálido y la consistencia de tus personajes.
""")

# --- 2. CONFIGURACIÓN DE LA API Y SELECCIÓN DE MODELO ---
try:
    # 2.1 Recuperar API Key de los secretos
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    
    # 2.2 Lógica de Selección de Modelo (Try/Except)
    try:
        # INTENTO PLAN A: Usar el modelo más potente/nuevo
        # Nota: Ajusta el nombre si usas una versión experimental (ej. 'gemini-2.0-flash-exp')
        model = genai.GenerativeModel('gemini-2.5-flash')
        st.success("🚀 Conectado exitosamente a Gemini 2.5 Flash")
        
    except Exception:
        # INTENTO PLAN B: Fallback al modelo estándar si el 2.5 falla
        # st.warning("⚠️ No se detectó Gemini 2.5. Cambiando automáticamente a Gemini 1.5 Flash.")
        model = genai.GenerativeModel('gemini-1.5-flash')

except FileNotFoundError:
    st.error("Error crítico: No se encontró el archivo .streamlit/secrets.toml")
    st.stop()
except KeyError:
    st.error("Error crítico: Falta la clave GOOGLE_API_KEY en los secretos.")
    st.stop()
except Exception as e:
    st.error(f"Error general de configuración: {e}")
    st.stop()

# --- 3. EL CEREBRO: FUNCIÓN DE REESCRITURA ---
def rewrite_paragraph(text):
    """
    Envía el texto a la IA con las reglas estrictas de tu libro.
    """
    # Si el párrafo es muy corto (ej. número de página), lo saltamos para ahorrar tiempo
    if len(text.strip()) < 15:
        return text

    # PROMPT DE INGENIERÍA ACTUALIZADO CON TUS REGLAS
    prompt = f"""
    You are a professional children's book editor (native US English speaker).
    Your task is to polish the following text to sound natural, warm, and empathetic for kids.

    *** CRITICAL RULES FOR THIS BOOK ***
    1. **Technique Titles (Natural Phrasing):** - Fix "The [noun] of [noun]" structures. They sound clinical or translated.
       - BAD: "The breathing of the balloon" -> GOOD: "Balloon Breathing".
       - BAD: "The breathing of the brave warrior" -> GOOD: "Brave Warrior Breath".
       
    2. **Vocabulary Fixes:** - NEVER use business terms like "outsourcing". Use "naming your feelings", "externalizing", or "separating".
       - Use kid-friendly language that connects emotionally.

    3. **Sentence Structure (Syntax):**
       - Fix Spanish sentence structures (long, passive sentences).
       - Example: Change "That means that in a classroom..." to "This means that inside a classroom...".
       - Make sentences flow naturally for a native US reader.

    4. **Character Consistency:** - The monster 'Whirlwind' (Torbellino) is ALWAYS **Male (he/him)**. Fix any 'she/her' references to him immediately.
       - 'Little Cloud' is acceptable, keep consistency.

    5. **Tone:** Warm, validating, empowering. Not clinical.

    **Output:** Return ONLY the rewritten text. Do not add quotes, intros, or explanations.

    Original Text to Rewrite:
    "{text}"
    """

    try:
        # Generar respuesta
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        # Si falla la API en un párrafo, devolvemos el original para no romper el libro
        print(f"Error procesando párrafo: {e}")
        return text

# --- 4. INTERFAZ DE USUARIO (FRONTEND) ---
uploaded_file = st.file_uploader("📂 Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file:
    st.info(f"Archivo cargado: {uploaded_file.name}")
    
    # Botón para iniciar
    if st.button("✨ Iniciar Magia (Procesar Libro)"):
        
        # Cargar documento
        doc = Document(uploaded_file)
        new_doc = Document() # Documento vacío para resultados
        
        total_paragraphs = len(doc.paragraphs)
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Contenedor para ver cambios en vivo
        st.write("---")
        st.subheader("🔍 Vista Previa en Tiempo Real")
        col1, col2 = st.columns(2)
        with col1: st.markdown("**Original**")
        with col2: st.markdown("**Corregido (IA)**")
        
        preview_container = st.container()

        # BUCLE PRINCIPAL (Iterar por cada párrafo)
        for i, para in enumerate(doc.paragraphs):
            original_text = para.text
            
            # Actualizar mensaje de estado
            status_text.caption(f"Procesando párrafo {i+1} de {total_paragraphs}...")
            
            # Llamar a la IA
            new_text = rewrite_paragraph(original_text)
            
            # Guardar en el nuevo documento
            # (Intentamos mantener el estilo si es un título, etc.)
            new_para = new_doc.add_paragraph(new_text)
            new_para.style = para.style 
            
            # Mostrar muestra cada 10 párrafos para que veas progreso real
            if i % 10 == 0 and len(original_text) > 40:
                with preview_container:
                    c1, c2 = st.columns(2)
                    c1.info(original_text[:150] + "...")
                    c2.success(new_text[:150] + "...")
            
            # Actualizar barra
            progress_bar.progress((i + 1) / total_paragraphs)
            
            # Pausa técnica para respetar límites de velocidad de la API (Rate Limits)
            time.sleep(0.2) 

        status_text.success("✅ ¡Libro completado! Ya puedes descargarlo.")
        progress_bar.progress(100)
        
        # PREPARAR DESCARGA
        bio = BytesIO()
        new_doc.save(bio)
        
        st.download_button(
            label="⬇️ Descargar Manuscrito Corregido (.docx)",
            data=bio.getvalue(),
            file_name=f"NativeFlow_{uploaded_file.name}",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
