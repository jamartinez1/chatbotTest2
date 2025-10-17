from flask import Flask, request, jsonify, render_template, session
import pandas as pd
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

# Configurar la aplicación para usar la carpeta templates y static desde la raíz
app.template_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
app.static_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
GOOGLE_SCRIPT_URL = os.getenv('GOOGLE_SCRIPT_URL')
CSV_FILE = os.getenv('CSV_FILE', 'RelativityOne Release Notes - RelativityOne.csv')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')

def load_csv_data():
    df = pd.read_csv(CSV_FILE, encoding='utf-8')
    df.columns = ['Fecha Inicio', 'Fecha Fin', 'Tipo', 'Modulo', 'Descripcion']
    df['Fecha Inicio'] = df['Fecha Inicio'].astype(str)
    df['Fecha Fin'] = df['Fecha Fin'].astype(str)
    return df

def is_greeting(query):
    greetings = ['hola', 'buenos días', 'buenas tardes', 'buenas noches', 'saludos', 'hey', 'hi']
    query_lower = query.lower().strip()
    return any(greeting in query_lower for greeting in greetings)

def search_releases(query, df):
    relevant_rows = df[df['Descripcion'].str.contains(query, case=False, na=False) |
                        df['Modulo'].str.contains(query, case=False, na=False)]
    if relevant_rows.empty:
        return "No encontré información específica sobre esa consulta en los lanzamientos de Relativity."
    context = relevant_rows.head(10).to_string(index=False)
    return context

def generate_response(query, context):
    prompt = f"""
Eres un asistente experto en lanzamientos de Relativity. Responde preguntas basadas en la información proporcionada sobre los lanzamientos.

Información de lanzamientos:
{context}

Pregunta del usuario: {query}

Responde de manera clara, concisa y útil. Si no hay información suficiente o la pregunta es demasiado compleja para responder con los datos disponibles, solicita los datos de contacto del usuario (nombre, correo electrónico y organización) para brindar soporte adicional. Incluye en tu respuesta una indicación clara de que necesitas estos datos para continuar.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error al generar respuesta: {str(e)}"

def log_to_google_sheets(question, answer, name=None, email=None, organization=None):
    timestamp = datetime.now().isoformat()
    data = {
        'timestamp': timestamp,
        'question': question,
        'answer': answer
    }
    if name:
        data['name'] = name
    if email:
        data['email'] = email
    if organization:
        data['organization'] = organization
    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=data, timeout=30)
        if response.status_code != 200:
            return False
        response_data = response.json()
        return response_data.get('status') == 'success'
    except Exception:
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question', '')
    if not question:
        return jsonify({'error': 'Pregunta vacía'}), 400

    if is_greeting(question):
        answer = "¡Hola! Soy un asistente experto en lanzamientos de Relativity. ¿En qué puedo ayudarte hoy? Pregúntame sobre nuevas funcionalidades, mejoras o cualquier cosa relacionada con los lanzamientos."
        requires_contact = False
    else:
        df = load_csv_data()
        context = search_releases(question, df)
        answer = generate_response(question, context)
        requires_contact = 'email' in answer.lower() or 'contacto' in answer.lower() or 'soporte adicional' in answer.lower() or 'nombre' in answer.lower() or 'organización' in answer.lower()

        if requires_contact:
            session['waiting_for_contact'] = True
            session['last_question'] = question
            session['last_answer'] = answer

    log_to_google_sheets(question, answer)
    return jsonify({'answer': answer, 'requires_contact': requires_contact})

@app.route('/contact', methods=['POST'])
def contact():
    data = request.json
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    organization = data.get('organization', '').strip()

    missing_fields = []
    if not name:
        missing_fields.append('nombre')
    if not email:
        missing_fields.append('correo electrónico')
    if not organization:
        missing_fields.append('organización')

    if missing_fields:
        error_msg = f"Por favor proporciona tu {' y '.join(missing_fields)}."
        return jsonify({'success': False, 'error': error_msg}), 400

    last_question = session.get('last_question', 'Contacto solicitado')
    last_answer = session.get('last_answer', 'Usuario proporcionó datos para soporte adicional')

    logging_success = log_to_google_sheets(last_question, last_answer, name, email, organization)

    session.pop('waiting_for_contact', None)
    session.pop('last_question', None)
    session.pop('last_answer', None)

    if logging_success:
        return jsonify({'success': True})
    else:
        return jsonify({
            'success': False,
            'error': 'Error al guardar los datos en Google Sheets. Verifica la configuración del script de Google Apps Script.'
        })

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))