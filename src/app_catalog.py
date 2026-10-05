"""
Catálogo de aplicaciones para iOS (iPhone) con Bundle IDs oficiales.
Soporta categorías, presets predefinidos y adición de apps personalizadas.
"""

import json
import os
import re

DEFAULT_CATALOG = [
    # --- SISTEMA APPLE ESENCIALES ---
    {
        "id": "com.apple.mobilephone",
        "name": "Teléfono",
        "category": "Sistema",
        "description": "Llamadas de voz nativas",
        "default": True,
        "system": True
    },
    {
        "id": "com.apple.MobileSMS",
        "name": "Mensajes (SMS / iMessage)",
        "category": "Sistema",
        "description": "Mensajería SMS nativa",
        "default": True,
        "system": True
    },
    {
        "id": "com.apple.camera",
        "name": "Cámara",
        "category": "Sistema",
        "description": "Captura de fotos y videos",
        "default": True,
        "system": True
    },
    {
        "id": "com.apple.mobileslideshow",
        "name": "Fotos",
        "category": "Sistema",
        "description": "Galería de imágenes local",
        "default": True,
        "system": True
    },
    {
        "id": "com.apple.calculator",
        "name": "Calculadora",
        "category": "Sistema",
        "description": "Calculadora básica y científica",
        "default": True,
        "system": True
    },
    {
        "id": "com.apple.mobiletimer",
        "name": "Reloj / Alarmas",
        "category": "Sistema",
        "description": "Alarmas, temporizador y cronómetro",
        "default": True,
        "system": True
    },
    {
        "id": "com.apple.mobilenotes",
        "name": "Notas",
        "category": "Sistema",
        "description": "Bloc de notas de Apple",
        "default": True,
        "system": True
    },
    {
        "id": "com.apple.MobileAddressBook",
        "name": "Contactos",
        "category": "Sistema",
        "description": "Agenda de contactos",
        "default": True,
        "system": True
    },
    {
        "id": "com.apple.mobilecal",
        "name": "Calendario",
        "category": "Sistema",
        "description": "Calendario nativo de iOS",
        "default": True,
        "system": True
    },
    {
        "id": "com.apple.reminders",
        "name": "Recordatorios",
        "category": "Sistema",
        "description": "Listas de tareas y recordatorios",
        "default": True,
        "system": True
    },
    {
        "id": "com.apple.DocumentsApp",
        "name": "Archivos",
        "category": "Sistema",
        "description": "Gestor de archivos y descargas locales",
        "default": True,
        "system": True
    },
    {
        "id": "com.apple.Preferences",
        "name": "Ajustes",
        "category": "Sistema",
        "description": "Configuración del iPhone (Requerido)",
        "default": True,
        "system": True
    },
    {
        "id": "com.apple.weather",
        "name": "Clima",
        "category": "Sistema",
        "description": "Pronóstico meteorológico",
        "default": False,
        "system": True
    },
    {
        "id": "com.apple.VoiceMemos",
        "name": "Notas de voz",
        "category": "Sistema",
        "description": "Grabador de audio",
        "default": True,
        "system": True
    },

    # --- KOSHER & RELIGIÓN ---
    {
        "id": "tfilon.tfilon",
        "name": "Tfilon (Sidur)",
        "category": "Kosher / Religión",
        "description": "Rezos, sidur y tefilot",
        "default": True,
        "system": False
    },
    {
        "id": "com.rustybrick.jewishcalendar",
        "name": "Luach / Jewish Calendar",
        "category": "Kosher / Religión",
        "description": "Zmanim y calendario hebreo",
        "default": True,
        "system": False
    },
    {
        "id": "org.chabad.zmanim",
        "name": "Chabad Zmanim",
        "category": "Kosher / Religión",
        "description": "Horarios halájicos de Chabad",
        "default": False,
        "system": False
    },
    {
        "id": "com.rustybrick.smartsiddur",
        "name": "Smart Siddur",
        "category": "Kosher / Religión",
        "description": "Sidur dinámico por ubicación y fecha",
        "default": False,
        "system": False
    },
    {
        "id": "org.sefaria.Sefaria",
        "name": "Sefaria",
        "category": "Kosher / Religión",
        "description": "Biblioteca de textos sagrados y Tanaj",
        "default": False,
        "system": False
    },
    {
        "id": "org.torahanytime.torahanytime",
        "name": "TorahAnytime",
        "category": "Kosher / Religión",
        "description": "Clases de Torá en audio",
        "default": False,
        "system": False
    },
    {
        "id": "com.calj.calj",
        "name": "CalJ (Calendrier Juif)",
        "category": "Kosher / Religión",
        "description": "Zmanim y conversor de fechas hebreas",
        "default": False,
        "system": False
    },

    # --- COMUNICACIÓN & TRABAJO ---
    {
        "id": "net.whatsapp.WhatsApp",
        "name": "WhatsApp Messenger",
        "category": "Comunicación",
        "description": "Mensajería y llamadas cifradas",
        "default": True,
        "system": False
    },
    {
        "id": "net.whatsapp.WhatsAppSMB",
        "name": "WhatsApp Business",
        "category": "Comunicación",
        "description": "WhatsApp para cuentas comerciales",
        "default": False,
        "system": False
    },
    {
        "id": "us.zoom.videomeetings",
        "name": "Zoom Workplace",
        "category": "Comunicación",
        "description": "Reuniones de video y trabajo",
        "default": False,
        "system": False
    },
    {
        "id": "com.microsoft.skype.teams",
        "name": "Microsoft Teams",
        "category": "Comunicación",
        "description": "Comunicación corporativa",
        "default": False,
        "system": False
    },
    {
        "id": "com.google.Gmail",
        "name": "Gmail",
        "category": "Comunicación",
        "description": "Cliente de correo de Google",
        "default": False,
        "system": False
    },
    {
        "id": "com.apple.mobilemail",
        "name": "Mail (Apple)",
        "category": "Comunicación",
        "description": "Cliente de correo nativo",
        "default": False,
        "system": True
    },

    # --- NAVEGACIÓN & TRANSPORTE ---
    {
        "id": "com.waze.iphone",
        "name": "Waze GPS & Tráfico",
        "category": "Transporte / Mapas",
        "description": "Navegación GPS comunitaria",
        "default": True,
        "system": False
    },
    {
        "id": "com.google.Maps",
        "name": "Google Maps",
        "category": "Transporte / Mapas",
        "description": "Mapas y navegación de Google",
        "default": False,
        "system": False
    },
    {
        "id": "com.apple.Maps",
        "name": "Apple Maps",
        "category": "Transporte / Mapas",
        "description": "Mapas nativos de iOS",
        "default": False,
        "system": True
    },
    {
        "id": "com.ubercab.UberClient",
        "name": "Uber",
        "category": "Transporte / Mapas",
        "description": "Servicio de transporte y viajes",
        "default": False,
        "system": False
    },
    {
        "id": "com.cabify.passenger",
        "name": "Cabify",
        "category": "Transporte / Mapas",
        "description": "Transporte y viajes en taxi/auto",
        "default": False,
        "system": False
    },
    {
        "id": "com.tranzmate",
        "name": "Moovit",
        "category": "Transporte / Mapas",
        "description": "Horarios de transporte público y colectivos",
        "default": False,
        "system": False
    },

    # --- BANCOS & FINANZAS ---
    {
        "id": "com.mercadopago.wallet",
        "name": "Mercado Pago",
        "category": "Finanzas",
        "description": "Billetera virtual y pagos QR",
        "default": True,
        "system": False
    },
    {
        "id": "ar.com.santanderrio.mbanking",
        "name": "Santander Argentina",
        "category": "Finanzas",
        "description": "Home banking Banco Santander",
        "default": False,
        "system": False
    },
    {
        "id": "ar.com.bancogalicia.bancogalicia",
        "name": "Banco Galicia",
        "category": "Finanzas",
        "description": "Home banking Banco Galicia",
        "default": False,
        "system": False
    },
    {
        "id": "com.bbva.ar.mbanking",
        "name": "BBVA Argentina",
        "category": "Finanzas",
        "description": "Home banking BBVA",
        "default": False,
        "system": False
    },
    {
        "id": "com.uala.app",
        "name": "Ualá",
        "category": "Finanzas",
        "description": "Billetera digital y tarjeta",
        "default": False,
        "system": False
    },
    {
        "id": "com.brubank",
        "name": "Brubank",
        "category": "Finanzas",
        "description": "Banco digital",
        "default": False,
        "system": False
    },
    {
        "id": "ar.gob.anses.miapp",
        "name": "mi ANSES",
        "category": "Finanzas",
        "description": "Consultas y prestaciones sociales",
        "default": False,
        "system": False
    },
]

PRESETS = {
    "basico": {
        "name": "Básico Kosher (Recomendado)",
        "desc": "Solo llamadas, SMS, Cámara, Fotos, Calculadora, Notas, Reloj, Contactos, Waze y WhatsApp.",
        "allowed_ids": [
            "com.apple.mobilephone",
            "com.apple.MobileSMS",
            "com.apple.camera",
            "com.apple.mobileslideshow",
            "com.apple.calculator",
            "com.apple.mobiletimer",
            "com.apple.mobilenotes",
            "com.apple.MobileAddressBook",
            "com.apple.Preferences",
            "com.apple.DocumentsApp",
            "net.whatsapp.WhatsApp",
            "com.waze.iphone",
            "tfilon.tfilon",
            "com.mercadopago.wallet"
        ]
    },
    "estricto": {
        "name": "Ultra Estricto (Sin WhatsApp ni Redes)",
        "desc": "Solo llamadas, SMS, Utilidades nativas, Sidur y GPS. Cero mensajerías con estados/canales.",
        "allowed_ids": [
            "com.apple.mobilephone",
            "com.apple.MobileSMS",
            "com.apple.camera",
            "com.apple.calculator",
            "com.apple.mobiletimer",
            "com.apple.MobileAddressBook",
            "com.apple.Preferences",
            "com.apple.DocumentsApp",
            "com.waze.iphone",
            "tfilon.tfilon",
            "com.rustybrick.jewishcalendar"
        ]
    },
    "trabajo": {
        "name": "Trabajo & Finanzas",
        "desc": "Básico Kosher + Apps Bancarias, Correo y Transporte.",
        "allowed_ids": [
            "com.apple.mobilephone",
            "com.apple.MobileSMS",
            "com.apple.camera",
            "com.apple.mobileslideshow",
            "com.apple.calculator",
            "com.apple.mobiletimer",
            "com.apple.mobilenotes",
            "com.apple.MobileAddressBook",
            "com.apple.Preferences",
            "com.apple.DocumentsApp",
            "com.apple.mobilecal",
            "net.whatsapp.WhatsApp",
            "com.waze.iphone",
            "com.mercadopago.wallet",
            "com.google.Gmail",
            "com.ubercab.UberClient",
            "tfilon.tfilon"
        ]
    }
}


# Bundle IDs que conozco con alta confianza (apps de Apple según su lista oficial de
# identificadores, y apps muy conocidas). Todo lo demás está SIN CONFIRMAR: si el ID
# está mal, la app queda OCULTA en el iPhone aunque esté tildada. El programa avisa
# antes de exportar. Para confirmar un ID: iMazing -> Apps muestra el Bundle ID de
# cada app instalada.
CONFIRMED_IDS = {
    "com.apple.mobilephone", "com.apple.MobileSMS", "com.apple.camera",
    "com.apple.mobileslideshow", "com.apple.calculator", "com.apple.mobiletimer",
    "com.apple.mobilenotes", "com.apple.MobileAddressBook", "com.apple.mobilecal",
    "com.apple.reminders", "com.apple.DocumentsApp", "com.apple.Preferences",
    "com.apple.weather", "com.apple.VoiceMemos", "com.apple.mobilemail",
    "com.apple.Maps",
    "net.whatsapp.WhatsApp", "net.whatsapp.WhatsAppSMB", "com.waze.iphone",
    "com.google.Gmail", "com.google.Maps", "com.ubercab.UberClient",
    "us.zoom.videomeetings",
}


def is_confirmed(app):
    """Una app solo está confirmada si su Bundle ID fue contrastado contra la App Store de Apple."""
    return bool(app and app.get("id") in CONFIRMED_IDS)


def data_dir():
    """Carpeta persistente del usuario. NUNCA junto al código: dentro del .exe
    (PyInstaller --onefile) esa carpeta es temporal y se borra al cerrar."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "KosherLockIOS")
    os.makedirs(path, exist_ok=True)
    return path


class AppCatalogManager:
    def __init__(self, data_file=None):
        self.data_file = data_file or os.path.join(data_dir(), "custom_apps.json")
        self.apps = [dict(a) for a in DEFAULT_CATALOG]
        self.load_custom_apps()

    def load_custom_apps(self):
        if not os.path.isfile(self.data_file):
            return
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                custom = json.load(f)
            if not isinstance(custom, list):
                print("El archivo custom_apps.json no contiene una lista válida.")
                return
        except (OSError, ValueError) as e:
            print(f"Error cargando apps personalizadas: {e}")
            return
        existing = {a["id"].lower() for a in self.apps}
        for item in custom:
            if not isinstance(item, dict) or not item.get("id") or not item.get("name"):
                continue
            if item["id"].lower() in existing:
                continue
            item["custom"] = True
            item["system"] = False
            item.setdefault("category", "Personalizadas")
            item.setdefault("description", "")
            item.setdefault("default", True)
            self.apps.append(item)
            existing.add(item["id"].lower())

    def save_custom_apps(self):
        custom = [a for a in self.apps if a.get("custom")]
        tmp = self.data_file + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(custom, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.data_file)  # escritura atómica: no deja el JSON a medias
            return True
        except OSError as e:
            print(f"Error guardando apps personalizadas: {e}")
            return False

    def add_app(self, bundle_id, name, category="Personalizadas", description=""):
        bundle_id = bundle_id.strip()
        name = name.strip()
        if not bundle_id or not name:
            return False, "Bundle ID y Nombre son obligatorios."
        # Un Bundle ID válido: segmentos con letras/números/guion/punto, sin espacios.
        if not re.fullmatch(r"[A-Za-z0-9\-]+(\.[A-Za-z0-9\-_]+)+", bundle_id):
            return False, ("El Bundle ID no es válido. Tiene la forma 'com.empresa.app' "
                           "(sin espacios). Copialo desde iMazing -> Apps.")
        for a in self.apps:
            if a["id"].lower() == bundle_id.lower():
                return False, f"La app con ID '{bundle_id}' ya existe ({a['name']})."
        self.apps.append({
            "id": bundle_id, "name": name, "category": category,
            "description": description or f"App personalizada ({bundle_id})",
            "default": True, "system": False, "custom": True,
        })
        self.save_custom_apps()
        return True, "App agregada exitosamente."

    def remove_custom_app(self, bundle_id):
        for i, a in enumerate(self.apps):
            if a["id"].lower() == bundle_id.lower() and a.get("custom"):
                del self.apps[i]
                self.save_custom_apps()
                return True
        return False

    def get_categories(self):
        return ["Todas"] + sorted({a["category"] for a in self.apps})

    def filter_apps(self, category="Todas", search_text=""):
        res = []
        q = search_text.strip().lower()
        for a in self.apps:
            if category != "Todas" and a["category"] != category:
                continue
            if q and (q not in a["name"].lower() and q not in a["id"].lower()
                      and q not in a.get("description", "").lower()):
                continue
            res.append(a)
        return res
