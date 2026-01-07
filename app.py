import streamlit as st
from docx import Document
from docx.shared import RGBColor
import google.generativeai as genai
from io import BytesIO
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="NativeFlow Auditor", page_icon="🕵️", layout="wide")

st.title("🕵️ NativeFlow: Auditoría y Corrección")
st.markdown("""
Este sistema funciona en dos pasos para manejar documentos grandes sin saturar tu pantalla:
1.  **Auditoría:** Genera un reporte detallado de qué se va a cambiar.
2.  **Corrección:** Genera el manuscrito final limpio.
""")

# --- 2. API SETUP ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    # Intentamos usar el modelo 2.5 Flash por velocidad
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
    except:
        model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Error de API: {e}")
    st.stop()

# --- 3. FUNCIONES INTELIGENTES ---

def audit_paragraph(text):
    """
    No reescribe, solo detecta problemas según las reglas.
    Devuelve: String con el problema detectado o None si está limpio.
    """
    if len(text.strip()) < 20: return None

    prompt = f"""
    You are a strict book editor. Analyze the text below for specific issues based on these rules:
    1. **Whirlwind Gender:** Must be HE/HIM. Detect if 'she/her' is used.
    2. **Phrasing:** Detect clumsy "The X of Y" structures (e.g., "The breathing of the balloon").
    3. **Jargon:** Detect corporate words like "outsourcing".
    4. **Syntax:** Detect overly complex/Spanish-like sentence structures.

    If issues are found, strictly output a short description of the error and the fix (e.g., "Found 'outsourcing', suggest 'naming'").
    If NO issues are found, output exact word: "CLEAN".

    Text: "{text}"
    """
    try:
        response = model.generate_content(prompt)
        result = response.text.strip()
        if "CLEAN" in result:
            return None
        return result
    except:
        return None

def rewrite_paragraph_silent(text):
    """Reescritura directa para el archivo final."""
    if len(text.strip()) < 15: return text
    
    prompt = f"""
    Rewrite this text to be native US English, warm tone. 
    Rules: Whirlwind=Male, No 'outsourcing', No 'The X of Y' phrasing.
    Text: "{text}"
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return text

# --- 4. INTERFAZ POR PESTAÑAS ---
uploaded_file = st.file_uploader("📂 Sube tu manuscrito (.docx)", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    total_paragraphs = len(doc.paragraphs)
    
    # Creamos dos pestañas para separar las acciones
    tab_audit, tab_fix = st.tabs(["📊 Paso 1: Generar Reporte", "✨ Paso 2: Crear Libro Final"])

    # --- PESTAÑA 1: AUDITORÍA ---
    with tab_audit:
        st.header("Generar Reporte de Diagnóstico")
        st.info("Esto leerá el libro y creará un archivo Word listando solo los párrafos que necesitan cambios.")
        
        if st.button("🔍 Analizar Documento"):
            report_doc = Document()
            report_doc.add_heading('Reporte de Auditoría NativeFlow', 0)
            
            # Crear tabla en el Word
            table = report_doc.add_table(rows=1, cols=2)
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'Párrafo Original'
            hdr_cells[1].text = 'Problema Detectado / Sugerencia'
            
            prog_bar = st.progress(0)
            status = st.empty()
            issues_count = 0
            
            for i, para in enumerate(doc.paragraphs):
                status.text(f"Analizando párrafo {i+1}/{total_paragraphs}...")
                
                # Llamada a la IA (Modo Auditoría)
                issue = audit_paragraph(para.text)
                
                if issue:
                    issues_count += 1
                    row_cells = table.add_row().cells
                    row_cells[0].text = para.text[:200] + "..." # Resumen del original
                    row_cells[1].text = issue
                
                prog_bar.progress((i + 1) / total_paragraphs)
                # time.sleep(0.1) # Pausa opcional si la API se queja

            status.success(f"✅ Análisis completado. Se detectaron {issues_count} posibles mejoras.")
            
            # Botón de descarga del reporte
            bio_audit = BytesIO()
            report_doc.save(bio_audit)
            
            st.download_button(
                label="⬇️ Descargar Reporte de Auditoría (.docx)",
                data=bio_audit.getvalue(),
                file_name="Reporte_Cambios.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    # --- PESTAÑA 2: CORRECCIÓN FINAL ---
    with tab_fix:
        st.header("Generar Manuscrito Final")
        st.warning("Este proceso aplicará todas las correcciones de gramática y tono directamente.")
        
        if st.button("🚀 Procesar y Descargar Libro"):
            final_doc = Document()
            prog_bar_fix = st.progress(0)
            status_fix = st.empty()
            
            for i, para in enumerate(doc.paragraphs):
                status_fix.text(f"Corrigiendo párrafo {i+1}/{total_paragraphs}...")
                
                # Llamada a la IA (Modo Reescritura)
                new_text = rewrite_paragraph_silent(para.text)
                
                # Guardar manteniendo estilo (título, normal, etc)
                new_para = final_doc.add_paragraph(new_text)
                new_para.style = para.style
                
                prog_bar_fix.progress((i + 1) / total_paragraphs)
                # time.sleep(0.2) # Pausa técnica

            status_fix.success("✅ ¡Libro terminado!")
            
            bio_final = BytesIO()
            final_doc.save(bio_final)
            
            st.download_button(
                label="⬇️ Descargar Libro Corregido (.docx)",
                data=bio_final.getvalue(),
                file_name=f"NativeFlow_Final_{uploaded_file.name}",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
