"""
Simula um provedor de IA com problema, para o gateway reagir.

Nota AI Gateways → "Resiliência - timeout, retry e fallback"

Escuta em http://127.0.0.1:4010 e demora 15 segundos para responder
(como um provedor sobrecarregado). Com o timeout do gateway menor que isso,
a tentativa principal falha e o fallback entra em ação.

Rode em um terminal separado e deixe aberto:  python provedor_simulado.py
"""

import time
from http.server import BaseHTTPRequestHandler, HTTPServer

DEMORA_SEGUNDOS = 15


class ProvedorLento(BaseHTTPRequestHandler):
    def do_POST(self):
        print(f"📥 Requisição recebida em {self.path}. Demorando {DEMORA_SEGUNDOS}s...", flush=True)
        time.sleep(DEMORA_SEGUNDOS)
        self.send_response(503)
        self.end_headers()

    def do_GET(self):
        self.send_response(404)
        self.end_headers()

    def log_message(self, *args):
        pass  # silencia o log padrão


print("🐢 Provedor lento em http://127.0.0.1:4010 (Ctrl+C para parar)", flush=True)
HTTPServer(("127.0.0.1", 4010), ProvedorLento).serve_forever()
