import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Scanner de Modelos", page_icon="🕵️")
st.title("🕵️ Escáner de Modelos Disponibles")

# 1. Conexión
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    st.success("✅ Llave API aceptada")
except:
    st.error("❌ Falta la API Key en secrets")
    st.stop()

# 2. Botón de Escaneo
if st.button("🔍 Ver qué modelos tengo disponibles"):
    try:
        st.info("Consultando a los servidores de Google...")
        
        # Obtenemos la lista cruda
        all_models = list(genai.list_models())
        
        # Filtramos los que sirven para generar texto (generateContent)
        chat_models = []
        for m in all_models:
            if 'generateContent' in m.supported_generation_methods:
                chat_models.append(m.name)
        
        if not chat_models:
            st.warning("No se encontraron modelos de chat. ¿Tu API Key tiene permisos?")
        else:
            st.success(f"¡Conectado! Tienes acceso a {len(chat_models)} modelos.")
            st.write("### Copia uno de estos nombres EXACTOS:")
            
            # Mostramos la lista limpia para copiar
            st.code("\n".join(chat_models), language="text")
            
            # Verificación específica de Flash
            st.divider()
            if any("flash" in m for m in chat_models):
                st.balloons()
                st.markdown("✅ **¡BUENAS NOTICIAS!** El modelo Flash SÍ está en la lista.")
            else:
                st.error("⚠️ El modelo Flash NO aparece en tu lista. Debes usar 'models/gemini-pro'.")

    except Exception as e:
        st.error(f"Error fatal de conexión: {str(e)}")
        st.write("Pista: Si el error es 404 o Auth, revisa tu API Key.")
