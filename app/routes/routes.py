from flask import request, jsonify
import os
from openai import OpenAI

api_key = os.getenv('OPENAI_API_KEY')
client = openai.OpenAI(api_key=api_key)

def get_ciudades():
    # Función de ejemplo
    return ["Bogotá", "Medellín", "Cali"]