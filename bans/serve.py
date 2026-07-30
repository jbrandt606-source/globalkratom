from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os, webbrowser

folder = Path(__file__).resolve().parent
os.chdir(folder)
url = 'http://127.0.0.1:8000/index.html'
print(f'Opening {url}')
webbrowser.open(url)
ThreadingHTTPServer(('127.0.0.1', 8000), SimpleHTTPRequestHandler).serve_forever()
