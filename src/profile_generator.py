"""
Generador de Perfiles de Configuración de Apple (.mobileconfig).

Todas las claves usadas acá fueron contrastadas con la documentación de Apple
Device Management (payload Restrictions / WebContentFilter / DNSSettings).
Casi todo requiere que el iPhone esté SUPERVISADO; en uno sin supervisar, iOS
ignora esas claves en silencio (no da error).

LÍMITES HONESTOS (leer antes de prometerle algo al usuario):
  * El filtro web integrado (FilterType=BuiltIn) actúa sobre navegación WebKit
    (Safari, vistas web embebidas). NO ve el tráfico nativo de apps como
    WhatsApp, por eso NO puede bloquear Estados/Canales dentro de la app.
  * PayloadRemovalDisallowed solo es confiable si el perfil se instala por
    cable desde la PC supervisora (iMazing / Apple Configurator) o por MDM.
    Un perfil bajado por QR/Safari puede ser removible por el usuario.
"""

import plistlib
import uuid

# Si el perfil queda con la lista blanca vacía, iOS muestra TODAS las apps.
# Estas dos siempre tienen que estar para no dejar el equipo inusable.
ESSENTIAL_APPS = ["com.apple.mobilephone", "com.apple.Preferences"]

# Identificadores estables de Apple (PayloadIdentifier)
# Apple utiliza el PayloadIdentifier para saber si una instalación debe REEMPLAZAR
# un perfil existente o duplicarlo. Deben ser fijos para evitar acumulación de restricciones.
PROFILE_IDENTIFIER = "com.kosherlock.ios.profile"
RESTRICTIONS_IDENTIFIER = "com.kosherlock.ios.profile.restrictions"
WEBFILTER_IDENTIFIER = "com.kosherlock.ios.profile.webfilter"
DNS_IDENTIFIER = "com.kosherlock.ios.profile.dns"

# Claves de Restrictions que escribe este generador. Lo usa el autotest para
# detectar claves inventadas: si agregás una acá, tiene que existir en Apple.
KNOWN_RESTRICTION_KEYS = {
    "whitelistedAppBundleIDs", "allowListedAppBundleIDs",
    "allowSafari", "allowAppInstallation", "allowUIConfigurationProfileInstallation",
    "allowMarketplaceAppInstallation", "allowWebDistributionAppInstallation",
    "allowAppRemoval", "allowInAppPurchases",
    "allowEraseContentAndSettings", "allowHostPairing", "allowAccountModification",
    "allowPasscodeModification", "allowAssistant", "allowAssistantWhileLocked",
    "allowAirDrop", "allowGameCenter", "allowMultiplayerGaming", "allowCamera",
    "allowScreenShot", "allowSharedStream", "allowDiagnosticSubmission",
    "forceLimitAdTracking", "allowUntrustedTLSPrompt",
    "allowSpotlightInternetResults", "allowVPNCreation", "allowEnterpriseAppTrust",
    "allowAppClips", "allowAutomaticAppDownloads", "allowCloudPrivateRelay",
}

# URLs de Canales/Estados de WhatsApp. SOLO afectan enlaces abiertos en una vista
# web (p. ej. tocar un link wa.me/channel); no bloquean la pestaña Novedades.
WHATSAPP_WEB_LINKS_BLACKLIST = [
    "https://whatsapp.com/channel", "https://www.whatsapp.com/channel",
    "https://whatsapp.com/newsletter", "https://www.whatsapp.com/newsletter",
    "https://wa.me/channel", "https://whatsapp.com/status",
]

DEFAULT_WEBVIEW_BLOCKED_DOMAINS = [
    "mercadolibre.com", "mercadolibre.com.ar", "ofertas.mercadopago.com",
    "promociones.mercadopago.com", "youtube.com", "youtu.be", "tiktok.com",
    "instagram.com", "facebook.com", "twitter.com", "x.com",
]

# Marcador inerte: el modo "Solo lista blanca" de Apple se activa cuando hay al
# menos un marcador permitido. Con la lista vacía el filtro NO se activaría y
# quedaría todo abierto, así que "bloquear todo" usa un destino que no existe.
INERT_BOOKMARK_URL = "https://kosherlock.invalid/"


class ProfileError(ValueError):
    """Configuración inconsistente que produciría un perfil engañoso."""


def _normalize_domain(raw):
    d = raw.strip().lower()
    for prefix in ("https://", "http://"):
        if d.startswith(prefix):
            d = d[len(prefix):]
    d = d.split("/")[0].split(":")[0].strip(".")
    if d.startswith("www."):
        d = d[4:]
    return d


def _domain_to_prefixes(domain):
    """Apple compara por prefijo de URL y no admite comodines."""
    out = []
    for host in (domain, "www." + domain, "m." + domain):
        out.append(f"https://{host}")
        out.append(f"http://{host}")
    return out


def _normalize_url(raw):
    u = raw.strip()
    if not u:
        return ""
    if not (u.startswith("http://") or u.startswith("https://")):
        u = "https://" + u
    return u


def generate_mobileconfig(
    profile_name="KosherLock MDM - Perfil Kosher",
    organization="KosherLock / LockSuite",
    allowed_bundle_ids=None,
    # Navegación
    block_safari=True,
    block_whatsapp_status_channels=True,
    web_filter_mode="block_all",  # block_all | blacklist | whitelist | none
    allowed_urls=None,
    custom_blocked_domains=None,
    dns_filter_mode="cleanbrowsing",  # cleanbrowsing | cloudflare | nextdns | none
    nextdns_id="",
    # Apps
    block_app_store=True,
    block_app_removal=False,
    block_in_app_purchases=True,
    # Anti-evasión y hardware
    block_erase=True,
    block_pairing=True,
    block_airdrop=True,
    block_account_modification=True,
    block_passcode_modification=False,
    block_siri=True,
    block_camera=False,
    block_screenshots=False,
    block_game_center=True,
    # Perfil
    non_removable=True,
    removal_passcode="",
):
    """Devuelve el .mobileconfig como bytes XML. Lanza ProfileError si es inconsistente."""
    if web_filter_mode not in ("block_all", "blacklist", "whitelist", "none"):
        raise ProfileError(f"Modo de filtro web desconocido: {web_filter_mode!r}")
    if dns_filter_mode not in ("cleanbrowsing", "cloudflare", "nextdns", "none"):
        raise ProfileError(f"Modo DNS desconocido: {dns_filter_mode!r}")
    if dns_filter_mode == "nextdns" and not nextdns_id.strip():
        raise ProfileError("Elegiste NextDNS pero no escribiste el ID de configuración.")

    # Copia: no mutar la lista del llamador.
    bundle_ids = list(allowed_bundle_ids or [])
    if bundle_ids:
        for essential in ESSENTIAL_APPS:
            if essential not in bundle_ids:
                bundle_ids.append(essential)

    top_uuid = str(uuid.uuid4()).upper()
    payloads = []

    # ------------------------------------------------------------------
    # 1) Restricciones
    # ------------------------------------------------------------------
    rid = str(uuid.uuid4()).upper()
    r = {
        "PayloadType": "com.apple.applicationaccess",
        "PayloadVersion": 1,
        "PayloadIdentifier": RESTRICTIONS_IDENTIFIER,
        "PayloadUUID": rid,
        "PayloadDisplayName": "Restricciones de Sistema Kosher",
        "PayloadDescription": "Lista blanca de apps y restricciones de sistema.",
    }

    if bundle_ids:
        lista = sorted(set(bundle_ids))
        # Apple marcó el nombre viejo como obsoleto pero ambos siguen vigentes;
        # se escriben los dos con la misma lista para cubrir todas las versiones de iOS.
        r["whitelistedAppBundleIDs"] = lista
        r["allowListedAppBundleIDs"] = lista

    if block_safari:
        r["allowSafari"] = False

    if block_app_store:
        r["allowAppInstallation"] = False
        r["allowMarketplaceAppInstallation"] = False
        r["allowWebDistributionAppInstallation"] = False  # iOS 17.5+ (UE): bloquea instalación desde sitios web
    if block_app_removal:
        r["allowAppRemoval"] = False
    if block_in_app_purchases:
        r["allowInAppPurchases"] = False

    if block_erase:
        r["allowEraseContentAndSettings"] = False
    if block_pairing:
        # Clave real de Apple. Con false, solo la PC supervisora puede emparejarse.
        r["allowHostPairing"] = False
    if block_account_modification:
        r["allowAccountModification"] = False
    if block_passcode_modification:
        r["allowPasscodeModification"] = False
    if block_siri:
        r["allowAssistant"] = False
        r["allowAssistantWhileLocked"] = False
    if block_airdrop:
        r["allowAirDrop"] = False
    if block_game_center:
        r["allowGameCenter"] = False
        r["allowMultiplayerGaming"] = False
    if block_camera:
        r["allowCamera"] = False
    if block_screenshots:
        r["allowScreenShot"] = False

    # Piso anti-evasión: siempre activo, sin interruptor (un interruptor apagado
    # por defecto solo protege a quien se acuerde de encenderlo).
    r["allowUIConfigurationProfileInstallation"] = False  # no instalar otro perfil/VPN
    r["allowVPNCreation"] = False                         # no crear VPN para saltar el filtro
    r["allowEnterpriseAppTrust"] = False                  # no confiar en apps empresariales
    r["allowAppClips"] = False                            # App Clips abren contenido web
    r["allowAutomaticAppDownloads"] = False
    r["allowSpotlightInternetResults"] = False            # Spotlight no busca en internet
    r["allowCloudPrivateRelay"] = False                   # iOS 15+: bloquea iCloud Private Relay para no evadir DNS
    r["allowSharedStream"] = False
    r["allowDiagnosticSubmission"] = False
    r["forceLimitAdTracking"] = True
    r["allowUntrustedTLSPrompt"] = False

    payloads.append(r)

    # ------------------------------------------------------------------
    # 2) Filtro de contenido web integrado (solo navegación WebKit)
    # ------------------------------------------------------------------
    wid = str(uuid.uuid4()).upper()
    web = {
        "PayloadType": "com.apple.webcontent-filter",
        "PayloadVersion": 1,
        "PayloadIdentifier": WEBFILTER_IDENTIFIER,
        "PayloadUUID": wid,
        "PayloadDisplayName": "Filtro Web Kosher",
        "PayloadDescription": "Filtro integrado de iOS para navegación web.",
        "FilterType": "BuiltIn",
    }

    web_needed = True
    if web_filter_mode == "block_all":
        bm = [{"URL": INERT_BOOKMARK_URL, "Title": "Bloqueado"}]
        web["AllowListBookmarks"] = bm
        web["WhitelistedBookmarks"] = bm
    elif web_filter_mode == "whitelist":
        urls = [_normalize_url(u) for u in (allowed_urls or [])]
        urls = [u for u in urls if u]
        if not urls:
            raise ProfileError(
                "Elegiste 'Solo lista blanca' pero no escribiste ninguna URL permitida."
            )
        bm = [{"URL": u, "Title": u} for u in urls]
        web["AllowListBookmarks"] = bm
        web["WhitelistedBookmarks"] = bm
    elif web_filter_mode == "blacklist":
        domains = custom_blocked_domains
        if domains is None:
            domains = DEFAULT_WEBVIEW_BLOCKED_DOMAINS
        deny = []
        for raw in domains:
            d = _normalize_domain(raw)
            if d:
                deny.extend(_domain_to_prefixes(d))
        if block_whatsapp_status_channels:
            deny.extend(WHATSAPP_WEB_LINKS_BLACKLIST)
        deny = list(dict.fromkeys(deny))  # sin duplicados, conserva el orden
        if not deny:
            raise ProfileError("Elegiste bloquear dominios pero la lista está vacía.")
        if len(deny) > 500:
            raise ProfileError(
                f"Apple limita el filtro de URLs a un máximo de 500 entradas (se generaron {len(deny)}). "
                "Reduce la cantidad de dominios bloqueados."
            )
        web["DenyListURLs"] = deny
        web["BlacklistedURLs"] = deny
        web["AutoFilterEnabled"] = True  # filtro de contenido adulto de Apple
    else:  # none
        if block_whatsapp_status_channels:
            deny = list(WHATSAPP_WEB_LINKS_BLACKLIST)
            web["DenyListURLs"] = deny
            web["BlacklistedURLs"] = deny
            web["AutoFilterEnabled"] = True
        else:
            web_needed = False

    if web_needed:
        payloads.append(web)

    # ------------------------------------------------------------------
    # 3) DNS cifrado
    # ------------------------------------------------------------------
    if dns_filter_mode != "none":
        did = str(uuid.uuid4()).upper()
        dns = {
            "PayloadType": "com.apple.dnsSettings.managed",
            "PayloadVersion": 1,
            "PayloadIdentifier": DNS_IDENTIFIER,
            "PayloadUUID": did,
            "PayloadDisplayName": "DNS Cifrado Kosher",
            "PayloadDescription": "Resolución DNS por un servidor con filtrado.",
        }
        if dns_filter_mode == "cleanbrowsing":
            dns["DNSSettings"] = {
                "DNSProtocol": "HTTPS",
                "ServerURL": "https://doh.cleanbrowsing.org/doh/family-filter/",
                "ServerAddresses": ["185.228.168.168", "185.228.169.168"],
            }
        elif dns_filter_mode == "cloudflare":
            dns["DNSSettings"] = {
                "DNSProtocol": "HTTPS",
                "ServerURL": "https://family.cloudflare-dns.com/dns-query",
                "ServerAddresses": ["1.1.1.3", "1.0.0.3"],
            }
        else:  # nextdns (el ID ya se validó arriba)
            dns["DNSSettings"] = {
                "DNSProtocol": "HTTPS",
                "ServerURL": f"https://dns.nextdns.io/{nextdns_id.strip()}",
            }
        payloads.append(dns)

    # ------------------------------------------------------------------
    # Perfil
    # ------------------------------------------------------------------
    profile = {
        "PayloadType": "Configuration",
        "PayloadVersion": 1,
        "PayloadIdentifier": PROFILE_IDENTIFIER,
        "PayloadUUID": top_uuid,
        "PayloadDisplayName": profile_name,
        "PayloadDescription": "Perfil Kosher generado por KosherLock iOS.",
        "PayloadOrganization": organization,
        "PayloadContent": payloads,
    }

    # Son alternativas: con contraseña de remoción el usuario PUEDE quitarlo si la
    # sabe; con "no removable" no puede quitarlo nadie desde el teléfono. Mezclarlos
    # deja un comportamiento ambiguo, así que la contraseña tiene prioridad.
    pwd = removal_passcode.strip()
    if pwd:
        profile["RemovalPassword"] = pwd
    elif non_removable:
        profile["PayloadRemovalDisallowed"] = True

    return plistlib.dumps(profile, fmt=plistlib.FMT_XML)


def save_mobileconfig_file(filepath, **kwargs):
    content = generate_mobileconfig(**kwargs)
    with open(filepath, "wb") as f:
        f.write(content)
    return filepath
