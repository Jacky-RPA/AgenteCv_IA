import streamlit as st

from backend.agent import (
    analizar_oferta,
    extraer_texto_pdf,
    responder_pregunta,
)
from backend.cv_optimizer import crear_word_cv_optimizado

st.title("Analizador de vacantes y CV")

st.caption("Compara una vacante con el CV del candidato, responde preguntas y genera un CV optimizado para el puesto.")

oferta = st.text_area("Pega aquí la vacante o descripción del puesto", height=220)
cv_archivo = st.file_uploader("Sube tu CV en PDF", type="pdf")
cv_texto_manual = st.text_area("O pega aquí el texto del CV", height=180)

if "thread_id" not in st.session_state:
    st.session_state.thread_id = "analisis-1"
if "cv_texto_actual" not in st.session_state:
    st.session_state.cv_texto_actual = ""
if "resultado_analisis" not in st.session_state:
    st.session_state.resultado_analisis = ""
if "respuestas" not in st.session_state:
    st.session_state.respuestas = []
if "word_optimizado" not in st.session_state:
    st.session_state.word_optimizado = None

if st.button("Analizar vacante vs CV"):
    if not oferta:
        st.warning("Primero pega la vacante o descripción del puesto.")
    elif not cv_archivo and not cv_texto_manual.strip():
        st.warning("Debes subir un CV en PDF o pegar el texto del CV.")
    else:
        cv_texto = extraer_texto_pdf(cv_archivo) if cv_archivo is not None else cv_texto_manual.strip()
        cv_texto = cv_texto[:8000]
        st.session_state.cv_texto_actual = cv_texto

        with st.spinner("Analizando la vacante frente al CV..."):
            resultado = analizar_oferta(oferta, cv_texto, thread_id=st.session_state.thread_id)

        st.session_state.resultado_analisis = resultado
        st.success("Análisis completado.")

if st.session_state.resultado_analisis:
    st.markdown("---")
    st.markdown("## Informe profesional de compatibilidad")
    st.markdown(st.session_state.resultado_analisis)

    st.markdown("---")
    st.subheader("Optimización del CV para esta vacante")
    if st.button("Generar Word optimizado"):
        try:
            with st.spinner("Preparando el CV optimizado..."):
                word_buffer = crear_word_cv_optimizado(
                    st.session_state.cv_texto_actual,
                    oferta,
                    st.session_state.resultado_analisis,
                )
            st.session_state.word_optimizado = word_buffer.getvalue()
            if not st.session_state.word_optimizado:
                st.error("No se pudo generar el documento. El contenido recibido del modelo estaba vacío.")
            else:
                st.success("Word generado correctamente. Ya puedes descargarlo.")
        except Exception as error:
            st.session_state.word_optimizado = None
            st.error(f"No se pudo generar el Word: {error}")

    if st.session_state.word_optimizado:
        st.download_button(
            label="Descargar CV optimizado (.docx)",
            data=st.session_state.word_optimizado,
            file_name="cv_optimizado_para_vacante.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    st.markdown("Este documento reescribe tu CV para alinearlo mejor con la vacante y destacar las fortalezas que más encajan con el puesto.")

st.markdown("---")
pregunta = st.text_input("Haz una pregunta sobre la vacante y el CV?")
if st.button("Preguntar") and pregunta:
    if not oferta:
        st.warning("Antes debes ingresar la vacante.")
    elif not st.session_state.cv_texto_actual:
        st.warning("Primero analiza un CV para poder responder preguntas basadas en ambas fuentes.")
    else:
        with st.spinner("Consultando la vacante y el CV para responder..."):
            respuesta = responder_pregunta(
                pregunta,
                oferta,
                st.session_state.cv_texto_actual,
                thread_id=f"preguntas-{st.session_state.thread_id}",
            )
        st.session_state.respuestas.append((pregunta, respuesta))
        st.rerun()

if st.session_state.respuestas:
    st.markdown("---")
    for pregunta_texto, respuesta_texto in st.session_state.respuestas:
        st.markdown(f"### Pregunta: {pregunta_texto}")
        st.markdown(respuesta_texto)

