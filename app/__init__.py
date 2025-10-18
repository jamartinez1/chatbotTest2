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
    # Lista de saludos más precisa
    greetings = ['hola', 'buenos días', 'buenas tardes', 'buenas noches', 'saludos', 'hey', 'hi', 'hello', 'good morning', 'good afternoon', 'good evening']
    query_lower = query.lower().strip()

    # Solo considera saludo si la consulta es corta (menos de 10 palabras) y contiene un saludo
    words = query_lower.split()
    if len(words) > 10:
        return False

    # Verifica si la consulta es principalmente un saludo (no una pregunta)
    has_greeting = any(greeting in query_lower for greeting in greetings)
    has_question_words = any(word in query_lower for word in ['qué', 'que', 'cómo', 'como', 'cuándo', 'cuando', 'dónde', 'donde', 'por qué', 'porque', 'quién', 'quien'])

    # Si tiene palabras de pregunta, no es un saludo
    if has_question_words:
        return False

    return has_greeting

def search_releases(query, df):
    query_lower = query.lower()

    # Buscar en descripción y módulo
    relevant_rows = df[df['Descripcion'].str.contains(query, case=False, na=False) |
                        df['Modulo'].str.contains(query, case=False, na=False)]

    # Si no encuentra resultados, intentar búsqueda más amplia
    if relevant_rows.empty:
        # Buscar por palabras clave relacionadas
        keywords = query_lower.split()
        for keyword in keywords:
            if len(keyword) > 3:  # Solo palabras significativas
                temp_rows = df[df['Descripcion'].str.contains(keyword, case=False, na=False) |
                              df['Modulo'].str.contains(keyword, case=False, na=False)]
                if not temp_rows.empty:
                    relevant_rows = temp_rows
                    break

    if relevant_rows.empty:
        return "No encontré información específica sobre esa consulta en los lanzamientos de Relativity."

    # Ordenar por fecha más reciente y limitar resultados
    relevant_rows = relevant_rows.sort_values('Fecha Inicio', ascending=False)
    context = relevant_rows.head(15).to_string(index=False)
    return context

def generate_response(query, context):
    prompt = f"""
Eres un asistente experto en lanzamientos de Relativity. Tu tarea es responder preguntas específicas sobre lanzamientos, mejoras y funcionalidades basadas en la información proporcionada.

INFORMACIÓN DE LANZAMIENTOS DISPONIBLE:
{context}

PREGUNTA DEL USUARIO: {query}

INSTRUCCIONES:
1. Responde de manera específica y detallada basada únicamente en la información proporcionada arriba.
2. Si la información no cubre completamente la pregunta, menciona qué aspectos específicos no están disponibles en los datos actuales.
3. NO uses frases genéricas como "¡Hola! Soy un asistente experto..." a menos que sea realmente un saludo.
4. Si la pregunta requiere información adicional que no está en los datos, sugiere contactar al equipo de soporte, pero solo si es realmente necesario.
5. Mantén las respuestas concisas pero informativas.
6. Si no hay información relevante, di explícitamente qué buscaste y por qué no encontraste resultados.

Responde directamente a la pregunta del usuario.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=600,
            temperature=0.3  # Reducir temperatura para respuestas más consistentes
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

    # Agregar logging para depuración
    print(f"Pregunta recibida: '{question}'")

    if is_greeting(question):
        print("Detectado como saludo")
        answer = "¡Hola! Soy un asistente experto en lanzamientos de Relativity. ¿En qué puedo ayudarte hoy? Pregúntame sobre nuevas funcionalidades, mejoras o cualquier cosa relacionada con los lanzamientos."
        requires_contact = False
    else:
        print("Procesando pregunta sobre lanzamientos")
        df = load_csv_data()
        context = search_releases(question, df)
        print(f"Contexto encontrado: {len(context)} caracteres")

        answer = generate_response(question, context)
        print(f"Respuesta generada: '{answer[:100]}...'")

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