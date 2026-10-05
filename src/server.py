"""
Servidor HTTP local y generador de Código QR para instalación OTA (sin cables) de perfiles iOS.
Permite escanear un código QR con la cámara del iPhone y descargar el perfil directamente.
"""

import http.server
import socket
import socketserver
import threading
import io
import uuid
import qrcode
from PIL import Image


def get_local_ip():
    """Detecta la IP local de la computadora en la red LAN / Wi-Fi"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No envía tráfico real, solo resuelve la interfaz primaria
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
    finally:
        s.close()
    return ip


class ProfileHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    profile_bytes = b""
    expected_token = ""

    def do_GET(self):
        clean_path = self.path.split("?")[0].strip("/")
        expected = f"{self.expected_token}.mobileconfig" if self.expected_token else ""
        if expected and clean_path == expected:
            self.send_response(200)
            # Content-type oficial de Apple para perfiles de configuración
            self.send_header("Content-Type", "application/x-apple-aspen-config; charset=utf-8")
            self.send_header("Content-Length", str(len(self.profile_bytes)))
            self.end_headers()
            self.wfile.write(self.profile_bytes)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"No encontrado o enlace no autorizado.")

    def log_message(self, format, *args):
        # Silenciar logs para no saturar la consola
        pass


class ProfileServerManager:
    def __init__(self):
        self.server = None
        self.thread = None
        self.is_running = False
        self.current_url = ""
        self.token = ""
        self.port = 8089

    def start(self, profile_bytes, port=8089):
        self.stop()
        self.port = port
        token = uuid.uuid4().hex[:12]
        self.token = token
        ProfileHTTPRequestHandler.profile_bytes = profile_bytes
        ProfileHTTPRequestHandler.expected_token = token

        local_ip = get_local_ip()
        self.current_url = f"http://{local_ip}:{self.port}/{token}.mobileconfig"

        try:
            # Permitir reuso rápido de socket
            class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
                allow_reuse_address = True
                daemon_threads = True

                def handle_error(self, request, client_address):
                    # Un iPhone que corta la descarga a mitad no debe imprimir nada
                    # (en el .exe sin consola no hay dónde imprimir y fallaría).
                    pass

            self.server = ThreadedTCPServer(("0.0.0.0", self.port), ProfileHTTPRequestHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            self.is_running = True
            return True, self.current_url
        except Exception as e:
            self.is_running = False
            return False, str(e)

    def stop(self):
        ProfileHTTPRequestHandler.profile_bytes = b""
        ProfileHTTPRequestHandler.expected_token = ""
        self.token = ""
        self.current_url = ""
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
            self.server = None
            self.thread = None
        self.is_running = False

    def generate_qr_image(self, url=None, size=300):
        target_url = url or self.current_url
        if not target_url:
            return None

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(target_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1E293B", back_color="#FFFFFF").convert("RGB")
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        return img
