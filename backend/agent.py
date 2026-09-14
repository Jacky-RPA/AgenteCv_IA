import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
from pypdf import PdfReader
from tavily import TavilyClient

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview"),
    temperature=0.1,
    google_api_key=os.getenv("GEMINI_API_KEY"),
    max_tokens=3500,
    timeout=60,
    max_retries=2,
)

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


@tool
def buscar_web(query: str) -> str:
    """Busca información actual en internet para investigar una empresa, noticias o hechos recientes."""
    results = tavily_client.search(query, max_results=1)
    return str(results)[:1000]


tools = [buscar_web]
checkpointer = InMemorySaver()
agent = create_react_agent(llm, tools, checkpointer=checkpointer)


def extraer_texto_pdf(archivo) -> str:
    lector = PdfReader(archivo)
    return "\n".join(pagina.extract_text() or "" for pagina in lector.pages)


def _texto_mensaje(mensaje) -> str:
    contenido = getattr(mensaje, "content", "")
    if isinstance(contenido, str):
        return contenido.strip()
    if isinstance(contenido, list):
        partes = []
        for bloque in contenido:
            if isinstance(bloque, str):
                partes.append(bloque)
            elif isinstance(bloque, dict) and bloque.get("text"):
                partes.append(str(bloque["text"]))
        return "\n".join(partes).strip()
    return ""


def crear_prompt_analisis(oferta: str, cv_texto: str) -> str:
    return f"""Eres un analista de talento humano y reclutamiento. Tu trabajo es comparar una vacante con el CV del candidato.

INSTRUCCIONES IMPORTANTES:

VACANTE / PUESTO:
{oferta}

CV DEL CANDIDATO:
{cv_texto}

Entrega un informe profesional de selección, detallado, ordenado y fácil de leer. No hagas un resumen superficial. Analiza requisito por requisito y explica la evidencia. Usa exactamente estos títulos Markdown, cada uno en una línea independiente:

## 1. Veredicto ejecutivo
Indica si conviene postularse, el nivel general de ajuste y la razón principal. Explica también cuál es la principal condición o riesgo para avanzar.

## 2. Porcentaje aproximado de adecuación
Indica un porcentaje estimado y explica cómo se calculó considerando requisitos obligatorios, requisitos deseables, experiencia, herramientas, formación y evidencias. No presentes el porcentaje como una verdad matemática.

## 3. Requisitos de la vacante frente al CV
Antes de la matriz, presenta una breve síntesis de lo que realmente busca el puesto. Usa una tabla Markdown de cumplimiento y analiza cada requisito por separado:

 Presenta una tabla Markdown con este formato:
 | Requisito evaluado | Estado | Evidencia encontrada en el CV | Brecha o impacto |
 |---|---|---|---|
 | Requisito concreto | Cumple / Cumple parcialmente / No se evidencia | Explicación clara | Qué significa para la candidatura |

 Incluye una fila independiente por cada requisito de experiencia, formación, herramienta, idioma, responsabilidad o competencia. No agrupes requisitos distintos en una sola fila. Después de la tabla, explica en párrafos sencillos los hallazgos más importantes.

## 4. Fortalezas más importantes
Presenta las fortalezas en orden de valor para la vacante. Para cada una explica la evidencia concreta, su relación con el puesto y el beneficio que podría aportar.

## 5. Brechas y riesgos
Separa claramente: requisitos que no aparecen, requisitos que aparecen de forma insuficiente, diferencias entre el cargo actual y el cargo objetivo, y dudas que un reclutador podría validar. Explica el impacto de cada brecha y no confundas "no se evidencia" con "no cumple".

## 6. Recomendaciones concretas
Incluye acciones priorizadas y prácticas en tres grupos: mejoras del CV, preparación de entrevista y estrategia de postulación. Cada acción debe indicar qué hacer y por qué mejora la candidatura.

## 7. Resumen de la empresa y del rol
Explica el tipo de empresa, el objetivo del rol, sus responsabilidades principales y el contexto solo si esos datos aparecen en la vacante o se pueden confirmar. No inventes información.

## 8. Conclusión final
Resume qué tan adecuado es el perfil, qué debe corregirse antes de postularse y cuál sería la recomendación final.

    Reglas para el análisis:
    - No confundas una habilidad deseable con un requisito obligatorio.
    - No asumas experiencia solo porque una herramienta aparece relacionada con otra.
    - Diferencia siempre entre "no cumple" y "no se evidencia en el CV".
    - No inventes porcentajes, empresas, años, certificaciones ni responsabilidades.
    - Usa ejemplos concretos del CV y de la vacante, pero no copies párrafos largos.
    - Escribe en español claro, con párrafos cortos y listas legibles.
    - Mantén un tono profesional de consultoría de selección, directo y respetuoso.
    - Explica cada conclusión con evidencia; no uses frases genéricas sin justificarla.
    - No comiences con "### Informe del análisis" ni repitas el título del informe.
    - No mezcles una tabla con otra ni uses tablas con más de cuatro columnas.
    """


def crear_prompt_pregunta(pregunta: str, oferta: str, cv_texto: str) -> str:
    return f"""Eres un asistente experto en selección de personal.

La persona está evaluando una vacante y un CV. Debes responder la pregunta usando ambas fuentes como base de evidencia.

PREGUNTA DEL USUARIO:
{pregunta}

INFORMACIÓN DE LA VACANTE:
{oferta}

INFORMACIÓN DEL CV:
{cv_texto}

Reglas obligatorias:
- Consulta siempre la vacante y el CV antes de responder.
- Responde en español claro y fácil de entender para cualquier persona.
- Si la pregunta puede responderse con ambas fuentes, explica la comparación entre lo que pide la vacante y lo que aporta el CV.
- Si una respuesta necesita información que no aparece en ninguna de las dos fuentes, dilo claramente y no inventes.
- Si la pregunta pide recomendación, explica por qué y en qué punto el candidato cumple o no cumple el puesto.
- No seas técnico ni ambiguo; usa un lenguaje simple.
"""


def analizar_oferta(oferta: str, cv_texto: str, thread_id: str = "analisis-1") -> str:
    prompt = crear_prompt_analisis(oferta, cv_texto)
    config = {"configurable": {"thread_id": thread_id}}
    response = agent.invoke({"messages": [("user", prompt)]}, config)
    return _texto_mensaje(response["messages"][-1])


def responder_pregunta(pregunta: str, oferta: str, cv_texto: str, thread_id: str = "preguntas-1") -> str:
    prompt = crear_prompt_pregunta(pregunta, oferta, cv_texto)
    config = {"configurable": {"thread_id": thread_id}}
    response = agent.invoke({"messages": [("user", prompt)]}, config)
    return _texto_mensaje(response["messages"][-1])


def run_cli() -> None:
    config = {"configurable": {"thread_id": "conversacion-1"}}
    print("Chat con el agente. Escribe 'salir' para terminar.\n")
    while True:
        pregunta = input("Tu: ")
        if pregunta.lower() == "salir":
            break
        response = agent.invoke({"messages": [("user", pregunta)]}, config)
        respuesta = response["messages"][-1].content
        print(f"Agente: {respuesta}\n")
