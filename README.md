# KosherLock iOS — Gestor de iPhones Kosher

Herramienta de escritorio moderna y visual para Windows (y compatible con macOS) diseñada para configurar iPhones (especialmente iPhone 12 y modelos con iOS 14 a iOS 18+) en dispositivos Kosher estrictamente controlados mediante listas blancas de apps y perfiles de configuración oficial de Apple (`.mobileconfig`).

---

## Características Principales

* **Lista Blanca Estricta de Apps (`whitelistedAppBundleIDs`)**: Únicamente las aplicaciones autorizadas aparecen en la pantalla de inicio del iPhone.
* **Bloqueo de Instalaciones y Tiendas (`allowAppInstallation = false`)**: Deshabilita el App Store, TestFlight y tiendas alternativas en iOS de la UE.
* **Bloqueo Total de Safari (`allowSafari = false`)**: Desaparece del sistema operativo.
* **Filtro de WebViews en Apps Nativas (`com.apple.webcontent-filter`)**: Bloqueo total de navegación, lista blanca estricta de URLs o lista negra de dominios (redes sociales, MercadoLibre, etc.).
* **Filtro DNS Cifrado DoH (`com.apple.dnsSettings.managed`)**: Soporta CleanBrowsing Family, Cloudflare 1.1.1.3 o NextDNS personalizado.
* **Protección Anti-Evasión de Sistema**:
  * Bloqueo de borrado de fábrica (`allowEraseContentAndSettings = false`).
  * Bloqueo de emparejamiento USB con PCs desconocidas (`allowHostPairing = false`).
  * Perfil inamovible (`PayloadRemovalDisallowed = true` o contraseña de administración).
  * Bloqueo de instalación de perfiles UI, creación de VPNs y apps empresariales.
* **Instalación Flexible**:
  * **Por Cable (Recomendada / Inviolable)**: Exportación de `.mobileconfig` para instalar mediante iMazing o Apple Configurator.
  * **Inalámbrica (OTA)**: Servidor HTTP local con código QR para escaneo directo con la cámara.

---

## Cómo Ejecutar

### Opción 1: Ejecutable Portable (Sin instalar Python)
Hacer doble clic en `KosherLock_iOS.exe` o ejecutar `Iniciar_KosherLock_iOS.bat`.

### Opción 2: Desde el Código Fuente
1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Iniciar la aplicación:
   ```bash
   python src/main.py
   ```

---

## Compilación del Ejecutable

Para compilar `KosherLock_iOS.exe` con PyInstaller en Windows:
```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

---

## Documentación Técnica y Contexto para IA

Consultar el archivo [`KOSHERLOCK_IOS_CONTEXTO_PARA_IA.md`](KOSHERLOCK_IOS_CONTEXTO_PARA_IA.md) para conocer la arquitectura interna, restricciones detalladas de Apple, limitaciones honestas de la plataforma y la guía paso a paso para supervisar un iPhone.
