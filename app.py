import streamlit as st
from docx import Document
import google.generativeai as genai
from io import BytesIO
import time

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NativeFlow Debugger", page_icon="🛠️", layout="wide")

# --- BARRA LATERAL (SETUP) ---
# --- BARRA LATERAL (SETUP & DIAGNÓSTICO) ---
with st.sidebar:
    st.header("🔧 Configuración")
    
    # 1. CONEXIÓN API
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        st.success("✅ API Key detectada")
    except Exception as e:
        st.error(f"❌ Error de Config: {e}")
        st.stop()

    st.divider()

    # 2. ESCÁNER DE MODELOS (LA SOLUCIÓN AL 404)
    st.subheader("🔍 Diagnóstico de Modelos")
    st.info("Si tienes errores 404, usa este botón para ver los nombres reales disponibles para tu clave.")
    
    if st.button("Listar Mis Modelos"):
        try:
            st.write("Conectando con Google...")
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            
            if available_models:
                st.success("Modelos encontrados:")
                # Mostramos el código limpio para copiar
                st.code("\n".join(available_models))
                st.caption("☝️ Copia uno de estos nombres (ej. 'models/gemini-pro') y úsalo abajo.")
            else:
                st.error("No se encontraron modelos generativos.")
        except Exception as e:
            st.error(f"Error listando modelos: {e}")

    st.divider()

    # 3. SELECTOR MANUAL DE MODELO
    # Aquí pegas el nombre que encontraste arriba
    model_name_input = st.text_input("Nombre del Modelo a usar:", value="gemini-1.5-flash")
    
    # Configuramos el modelo con el nombre que tú digas
    try:
        # Nota: La API a veces requiere quitar 'models/' del principio, a veces no.
        # El SDK suele manejarlo, pero por si acaso limpiamos la entrada visualmente.
        clean_name = model_name_input.replace("models/", "") 
        model = genai.GenerativeModel(clean_name)
    except:
        st.warning("Nombre de modelo inválido.")

# --- FUNCIONES ---

def audit_paragraph_strict(text):
    """
    Compara el texto original con una versión ideal.
    Si son diferentes, reporta la mejora.
    """
    if len(text.strip()) < 15: return None

    prompt = f"""
    You are a ruthless editor for a children's book. 
    Your goal: Detect ANY phrasing that sounds like "Spanish translated to English" or lacks emotional warmth.

    Task:
    1. Read the text.
    2. Rewrite it to be PERFECT Native US English (Warm Tone).
    3. Compare your rewrite with the original.
    
    Output Format:
    - If the original was ALREADY PERFECT: Output exactly "NO_ISSUES".
    - If you changed ANYTHING (even a comma or a word for better flow): Output a short explanation of what was awkward (e.g. "Passive voice", "Unnatural phrasing", "Wrong gender").

    Original Text: "{text}"
    """
    
    try:
        # Quitamos el try/except silencioso para ver errores reales si ocurren
        response = model.generate_content(prompt)
        result = response.text.strip()
        
        if "NO_ISSUES" in result:
            return None
        return result
    except Exception as e:
        # Si falla la API, devolvemos el error como texto para verlo en el reporte
        return f"ERROR DE API: {str(e)}"

def rewrite_paragraph(text):
    if len(text.strip()) < 15: return text
    prompt = f"""
    Rewrite to sound Native US, warm tone. 
    Rules: Whirlwind=He/Him, No 'outsourcing'.
    Text: "{text}"
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return text

# --- INTERFAZ PRINCIPAL ---
st.title("🛠️ NativeFlow: Modo Auditoría Estricta")
st.markdown("""
Si el reporte salía en blanco, esta versión te dirá por qué.
- Usa un comparador estricto (si se puede mejorar, lo listará).
- Muestra errores de conexión si la API falla.
""")

uploaded_file = st.file_uploader("📂 Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    total_paragraphs = len(doc.paragraphs)
    
    tab1, tab2 = st.tabs(["📊 Auditoría (Diagnóstico)", "🚀 Corrección (Final)"])

    # --- PESTAÑA 1: AUDITORÍA ---
    with tab1:
        if st.button("🔍 Analizar Documento (Modo Estricto)"):
            
            # Preparar documento de reporte
            report_doc = Document()
            report_doc.add_heading('Reporte de Mejoras Detectadas', 0)
            table = report_doc.add_table(rows=1, cols=2)
            table.style = 'Table Grid'
            hdr = table.rows[0].cells
            hdr[0].text = 'Texto Original'
            hdr[1].text = 'Mejora Sugerida / Problema'
            
            prog_bar = st.progress(0)
            status = st.empty()
            issues_found = 0
            
            # Debug container (para ver qué está pasando en vivo)
            with st.expander("Ver Log en Vivo (Debug)", expanded=True):
                log_placeholder = st.empty()

            for i, para in enumerate(doc.paragraphs):
                status.caption(f"Analizando {i+1}/{total_paragraphs}...")
                
                # Análisis
                result = audit_paragraph_strict(para.text)
                
                # Si encontramos algo (o un error de API)
                if result:
                    issues_found += 1
                    row = table.add_row().cells
                    row[0].text = para.text[:200]
                    row[1].text = result
                    
                    # Mostrar en pantalla para que veas que SÍ está funcionando
                    log_placeholder.text(f"Detectado en párrafo {i}: {result[:50]}...")
                
                prog_bar.progress((i + 1) / total_paragraphs)
                time.sleep(0.1) 

            if issues_found == 0:
                st.warning("⚠️ El reporte sigue saliendo vacío. Revisa la consola de errores arriba.")
            else:
                status.success(f"✅ ¡Éxito! Se encontraron {issues_found} puntos de mejora.")
                
                bio = BytesIO()
                report_doc.save(bio)
                st.download_button(
                    "⬇️ Descargar Reporte Lleno (.docx)",
                    bio.getvalue(),
                    "Reporte_Estricto.docx"
                )

    # --- PESTAÑA 2: CORRECCIÓN ---
    with tab2:
        if st.button("🚀 Crear Libro Final"):
            final_doc = Document()
            p_bar = st.progress(0)
            st_text = st.empty()
            
            for i, para in enumerate(doc.paragraphs):
                st_text.caption(f"Procesando {i+1}/{total_paragraphs}")
                new_text = rewrite_paragraph(para.text)
                new_p = final_doc.add_paragraph(new_text)
                new_p.style = para.style
                p_bar.progress((i+1)/total_paragraphs)
            
            bio_f = BytesIO()
            final_doc.save(bio_f)
            st.download_button("⬇️ Descargar Final", bio_f.getvalue(), "Libro_Final.docx")
