# Proyecto IA

## Estructura
- backend/
- frontend/
- .venv/
- .env
- .env.example
- requirements.txt

## Variables de entorno
1. Copiar `.env.example` como `.env`.
2. Completar localmente `GEMINI_API_KEY` y `TAVILY_API_KEY`.
3. Mantener `.env` fuera de Git. Está excluido mediante `.gitignore`.

Las claves API nunca deben subirse al repositorio ni compartirse en capturas, mensajes o logs. Si una clave se expone, revocarla y generar una nueva.

## Ejecutar
1. Activar entorno: .\.venv\Scripts\Activate.ps1
2. Ejecutar app: .\.venv\Scripts\python.exe -m streamlit run frontend\web_app.py --server.address 127.0.0.1 --server.port 8501
