# Chatbot Relativity FAQ

Chatbot web que responde preguntas sobre lanzamientos de Relativity usando OpenAI y datos CSV.

## Instalación

1. Instala dependencias: `pip install -r requirements.txt`
2. Copia `.env.example` a `.env` y configura variables.
3. Configura Google Apps Script con `google_script.js`.
4. Ejecuta: `python run_production.py`

## Uso

- Desarrollo: `python app.py` (puerto 5000)
- Producción: `python run_production.py` (puerto 8000)

## Estructura

- `app.py`: Backend Flask
- `templates/index.html`: Interfaz
- `static/`: CSS y JS
- `google_script.js`: Para Google Apps Script
- `requirements.txt`: Dependencias
- `run_production.py`: Servidor producción

## Seguridad

- No subir `.env` a git.
- Usar HTTPS en producción.