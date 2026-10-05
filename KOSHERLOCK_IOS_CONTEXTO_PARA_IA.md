# KosherLock iOS — Contexto para IA y Documentación Técnica (archivo único)

Documento de referencia de **KosherLock iOS**: qué hace, cómo está armado, qué NO puede hacer y qué está verificado y qué no. Complemento de `LOCKSUITE_CONTEXTO_PARA_IA.md` (Android).

**Estructura:** Parte A = estable (cómo funciona) · Parte B = pendiente / no verificado · Parte C = bitácora de sesiones.

> [!IMPORTANT]
> **Estado de verificación:** el programa pasa un autotest automático (`selftest.py`, ~270 chequeos: estructura del perfil, claves, catálogo, servidor y GUI). **Nunca se probó contra un iPhone real.** La validez de las claves se contrastó con la documentación de Apple, pero el comportamiento en el equipo hay que confirmarlo con la lista de la sección B.2.

---

# PARTE A — ESTABLE

## A.1 Qué es

Programa de escritorio para **Windows** (`KosherLock_iOS.exe`, portable, sin instalar Python) con interfaz oscura en `CustomTkinter`. El usuario tilda las apps permitidas, elige restricciones y exporta un perfil `.mobileconfig` que se aplica a un **iPhone SUPERVISADO**.

**Por qué no es una app como LockSuite:** en iOS ninguna app de terceros tiene privilegios de sistema (no existe Device Owner, ni AccessibilityService, ni se pueden ocultar apps ajenas). La única vía oficial es **Modo Supervisado + perfil de configuración / MDM**, que es lo que usan TAG, Meshimer, Netspark y MB Smart.

**Dos etapas:**
1. **Supervisión** (una sola vez; **borra el iPhone**). Se hace con iMazing o Apple Configurator. KosherLock NO hace la supervisión.
2. **Perfil** (cuantas veces haga falta): lo genera KosherLock y se instala por cable desde la misma PC supervisora.

## A.2 Arquitectura

```
PC Windows
 ├─ main.py             GUI: 4 pestañas (1 Apps · 2 Restricciones · 3 Aplicar · 4 Guía)
 │    ├─ validate_before_export()  → avisa: lista vacía, Bundle IDs sin confirmar
 │    └─ build_profile_bytes()     → valida + genera (captura ProfileError)
 ├─ app_catalog.py      Catálogo (40 apps), presets, IDs confirmados, persistencia
 ├─ profile_generator.py  Construye el .mobileconfig (plistlib XML)
 └─ server.py           HTTP local :8089 + QR (instalación por Safari, método débil)
        │
        ▼  .mobileconfig  (cable: iMazing / Apple Configurator  ← recomendado)
iPhone supervisado
   Payload 1  com.apple.applicationaccess      Restricciones + lista blanca de apps
   Payload 2  com.apple.webcontent-filter      Filtro web integrado (BuiltIn, solo WebKit)
   Payload 3  com.apple.dnsSettings.managed    DNS cifrado (DoH) con filtro
```

## A.3 Mapa de archivos

| Archivo | Responsabilidad |
|---|---|
| `KosherLock_iOS.exe` (raíz) | Ejecutable portable compilado (PyInstaller `--onefile --windowed`). |
| `Iniciar_KosherLock_iOS.bat` (raíz) | Lanzador rápido por lotes (abre el .exe o ejecuta Python). |
| `build.ps1` (raíz) | Script de PowerShell para compilar el ejecutable con PyInstaller. |
| `requirements.txt` (raíz) | Dependencias requeridas (`customtkinter`, `pillow`, `qrcode`, `pyinstaller`). |
| `src/main.py` | GUI moderna (CustomTkinter), validaciones previas a exportar, guía paso a paso. |
| `src/app_catalog.py` | `DEFAULT_CATALOG`, `PRESETS`, `CONFIRMED_IDS`, `is_confirmed()`, `AppCatalogManager`, `data_dir()`. |
| `src/profile_generator.py` | `generate_mobileconfig()`, `ProfileError`, `KNOWN_RESTRICTION_KEYS`. |
| `src/server.py` | `ProfileServerManager` (HTTP local + código QR para instalación OTA), `get_local_ip()`. |
| `src/selftest.py` | Autotest integral sin dispositivo. `python src/selftest.py` → exit 0 si todo OK. |

**Persistencia:** las apps personalizadas se guardan en `%APPDATA%\KosherLockIOS\custom_apps.json` (escritura atómica). Sobreviven a cerrar el programa y a recompilar el `.exe`. Solo las apps `custom` se pueden borrar.

## A.4 Qué hace el perfil (todo requiere supervisión)

### Lista blanca de apps
- `whitelistedAppBundleIDs` + `allowListedAppBundleIDs` (misma lista; Apple marcó el nombre viejo como obsoleto pero ambos siguen vigentes). Las apps no listadas quedan ocultas.
- **Siempre** se agregan `com.apple.mobilephone` y `com.apple.Preferences` (si no, el equipo queda inusable).
- Si no se tilda ninguna app, **no se escribe la lista** (iOS mostraría todas) y el programa avisa.
- Presets: Básico (14), Estricto (11), Trabajo (17).

### Bloqueo de instalaciones y navegador
- `allowAppInstallation=false` (App Store desaparece), `allowMarketplaceAppInstallation=false`, `allowInAppPurchases=false`, opcional `allowAppRemoval=false`.
- `allowSafari=false`. Otros navegadores no existen si no están en la lista blanca ni se pueden instalar.

### Piso anti-evasión (siempre activo, sin interruptor)
`allowUIConfigurationProfileInstallation=false` (no instalar otro perfil/VPN) · `allowVPNCreation=false` · `allowEnterpriseAppTrust=false` · `allowAppClips=false` · `allowAutomaticAppDownloads=false` · `allowSpotlightInternetResults=false` · `allowSharedStream=false` · `allowDiagnosticSubmission=false` · `forceLimitAdTracking=true` · `allowUntrustedTLSPrompt=false`.

### Anti-reset / anti-PC (con interruptor, activos por defecto)
`allowEraseContentAndSettings=false` · **`allowHostPairing=false`** (clave real de Apple; solo la PC supervisora puede emparejarse) · `allowAccountModification=false` · `allowAirDrop=false` · `allowAssistant/WhileLocked=false` · `allowGameCenter/MultiplayerGaming=false` · opcionales: `allowPasscodeModification`, `allowCamera`, `allowScreenShot`.

### Filtro web (solo navegación WebKit: Safari y WebViews embebidos)
`FilterType=BuiltIn`. Modos:
| Modo | Implementación |
|---|---|
| Bloquear todo | `WhitelistedBookmarks` con 1 marcador inerte `https://kosherlock.invalid/` (con lista vacía el filtro no se activa). |
| Lista negra | `BlacklistedURLs` por prefijos (https/http × dominio, `www.`, `m.`) + `AutoFilterEnabled=true`. Apple no admite comodines. |
| Solo lista blanca | `WhitelistedBookmarks` con las URLs escritas (obligatorio ≥ 1). |
| Ninguno | Sin payload web (salvo enlaces de WhatsApp si la casilla está tildada). |

### DNS cifrado (DoH)
CleanBrowsing Family · Cloudflare `1.1.1.3` Family · NextDNS (requiere ID, si falta → `ProfileError`).

### Perfil
`PayloadRemovalDisallowed=true` **o** `RemovalPassword`; son excluyentes y **la contraseña gana**.

## A.5 Límites honestos (leer antes de prometer algo)

1. **Estados y Canales de WhatsApp NO se pueden bloquear con un perfil.** WhatsApp no usa WebKit (el filtro web no ve su tráfico) y su infraestructura no se puede separar por DNS. La casilla de la GUI solo bloquea **enlaces** a canales abiertos en vistas web. Lo que sí lo logra: un filtro comercial con inspección SSL (MB Smart, Netspark, Meshimer) o directamente no permitir WhatsApp. La pestaña "Novedades" no se puede quitar de la app oficial. *(Una versión anterior de este documento afirmaba un "bloqueo CDN"; era falso.)*
2. **El filtro web integrado no ve apps nativas** (bancos, WhatsApp, etc.). Los WebViews dentro de apps permitidas dependen de que la app use WebKit.
3. **Bundle IDs no confirmados:** 17 de 40 del catálogo se escribieron de memoria. Un ID incorrecto **oculta** la app. El programa marca "⚠ ID sin confirmar" y avisa al exportar. Confirmar en iMazing → Apps. Dudosos en presets: Tfilon (`tfilon.tfilon` es el paquete de Android), Mercado Pago, Luach.
4. **QR / instalación por Safari es el método débil:** `PayloadRemovalDisallowed` solo es confiable instalando por cable desde la PC supervisora o por MDM. Además, con `allowUIConfigurationProfileInstallation=false` un perfil posterior no se puede instalar por la interfaz.
5. **Riesgo de quedar bloqueado:** con `allowHostPairing=false` solo la **identidad de supervisión** de la PC original puede reconectar. Si se pierde (PC formateada sin respaldo), el perfil no se puede cambiar. **Respaldar la identidad de supervisión de iMazing** antes de aplicar.
6. **DFU / modo recuperación:** restaurar por cable borra el equipo y puede salirse del perfil. La defensa es **Bloqueo de Activación** (Apple ID del administrador en el iPhone). Comportamiento exacto con un equipo supervisado: **no verificado**.
7. Sin supervisión, iOS ignora estas claves en silencio (no da error).

## A.6 Flujo operativo (iPhone 12)

1. Respaldar el iPhone si tiene datos. **Supervisar con iMazing** (borra el equipo). Respaldar la identidad de supervisión.
2. Instalar desde el App Store las apps que se van a permitir (después no se podrá).
3. Abrir `KosherLock_iOS.exe` → tildar apps → pestaña Restricciones → Guardar `.mobileconfig`.
4. Instalar el perfil **por cable** (iMazing → Perfiles → Instalar) desde la misma PC.
5. Pasar la lista de prueba (B.2).

---

# PARTE B — PENDIENTE / NO VERIFICADO

## B.1 Pendiente
- Confirmar los Bundle IDs dudosos con un iPhone real (iMazing → Apps).
- La API de iTunes Search devolvió una página de filtro de red en el entorno de desarrollo: no se implementó la búsqueda automática de Bundle IDs.
- Firma del perfil (hoy sin firmar: iOS muestra "No firmado"). Cosmético, no afecta la función.
- Instalador (`.msi`) y firma de código del `.exe` (Windows SmartScreen puede advertir al abrirlo).

## B.2 Lista de prueba en un iPhone real (idealmente uno de prueba primero)
1. ¿Solo aparecen las apps permitidas? ¿Settings y Teléfono siguen?
2. ¿App Store, Safari y otros navegadores no existen?
3. Ajustes → General → Transferir/Restablecer: ¿"Borrar contenido" está bloqueado?
4. Ajustes → VPN y administración: ¿el perfil no tiene botón de eliminar?
5. ¿Intentar instalar otro perfil o VPN falla?
6. Conectar a una PC distinta con iTunes/3uTools: ¿rechaza el emparejamiento?
7. Abrir un link a `youtube.com` dentro de una app permitida (modo lista negra): ¿se bloquea?
8. DNS: abrir un sitio de prueba de filtrado de CleanBrowsing.
9. WhatsApp: confirmar que Novedades **sigue funcionando** (límite A.5.1).
10. Probar el DFU **solo en un equipo de prueba** y anotar el resultado.

---

# PARTE C — BITÁCORA

## Sesión de creación
- Se investigó la factibilidad: iOS no permite un equivalente a LockSuite; la vía es Supervisión + perfil.
- Se construyó la GUI de 4 pestañas, el catálogo, el generador y el servidor QR.

## Sesión de auditoría (bugs reales encontrados y corregidos)
| Bug | Corrección |
|---|---|
| `allowPairing` no existe en Apple y no hacía nada | → `allowHostPairing` |
| `FilterBrowsers`/`FilterSockets` y comodines `*` en un filtro BuiltIn (solo valen en filtros Plugin) | Eliminados; solo claves válidas de BuiltIn |
| "Bloquear todo" con lista vacía no activaba el filtro | Marcador inerte `kosherlock.invalid` |
| Lista negra sin `AutoFilterEnabled` y con comodines | Prefijos explícitos + `AutoFilterEnabled` |
| `RemovalPassword` + `PayloadRemovalDisallowed` a la vez (ambiguo) | Excluyentes, gana la contraseña |
| Faltaba bloqueo de VPN, perfiles adicionales, apps empresariales, App Clips, Spotlight web | Piso anti-evasión siempre activo |
| El generador mutaba la lista de apps del llamador | Copia local |
| Apps personalizadas se guardaban dentro de la carpeta temporal del `.exe` y se perdían | `%APPDATA%\KosherLockIOS\custom_apps.json` |
| Bundle IDs erróneos (`VoiceMemos`, Teams, Mercado Pago) | Corregidos |
| Sin validación de Bundle ID ni de configuraciones inconsistentes (NextDNS sin ID, lista blanca sin URLs, lista negra vacía) | `ProfileError` + avisos en la GUI |
| `geometry("1060, 780")` mal formado, Tk lo ignoraba | `"1060x780"` |
| Servidor: `Content-Disposition` rompía la instalación OTA, query string, errores en consola | Corregido |
| Textos que prometían "100% blindado" y bloqueo CDN de WhatsApp | Reescritos con los límites reales |

Resultado del autotest tras las correcciones: **270 verificaciones, 0 fallas.**
