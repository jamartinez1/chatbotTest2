import os
from waitress import serve
from wsgi import app

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8000'))

    print(f"Iniciando servidor en {host}:{port}")
    print("Presiona Ctrl+C para detener el servidor")

    serve(app, host=host, port=port, threads=4)