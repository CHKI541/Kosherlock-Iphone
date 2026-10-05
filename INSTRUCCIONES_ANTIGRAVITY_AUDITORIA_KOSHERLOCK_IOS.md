# Instrucciones para Antigravity — auditoría y mejoras de KosherLock iOS

## Objetivo

Revisar y corregir KosherLock iOS para que sea seguro de configurar, claro para quien lo usa y resistente a los caminos de evasión que Apple realmente permite bloquear. No prometer que un perfil aislado puede inspeccionar todo el tráfico de todas las apps: documentar con precisión los límites de iOS.

## Antes de tocar código

1. Leer completo `KOSHERLOCK_IOS_CONTEXTO_PARA_IA.md`, en especial B.1 y B.2. No cambiar Bundle IDs, whitelist, restricciones ni afirmaciones sobre iPhone real sin respetar lo que esas secciones dejan pendiente.
2. Separar hechos comprobables leyendo el generador de perfil de lo que exige iPhone físico supervisado. No marcar como verificado en equipo real lo que no se haya probado allí.
3. Mantener intactos los Bundle IDs actuales hasta contrastarlos en iMazing → Apps de un iPhone real. Que el usuario agregue un ID personalizado no lo verifica automáticamente.
4. No presentar el resultado como “sin bugs” o “imposible de evadir” mientras no haya pruebas de dispositivo y una definición explícita del alcance del filtro.

## Hallazgos que requieren corrección o decisión

### P1 — Cada exportación crea un perfil distinto y puede acumular restricciones

En `src/profile_generator.py`, `PayloadIdentifier` del perfil raíz contiene un UUID aleatorio nuevo en cada llamada a `generate_mobileconfig()`. Apple usa `PayloadIdentifier` para decidir si una instalación reemplaza un perfil existente o agrega otro. Al regenerar, el perfil puede quedar duplicado; las restricciones antiguas pueden seguir aplicándose y una nueva lista más permisiva no necesariamente recuperará las apps ocultas.

**Hacer:** usar un identificador raíz estable del producto y una estrategia coherente para los identificadores de payload. Definir cómo se actualiza/reemplaza el perfil y cómo se retira una versión anterior, especialmente con `PayloadRemovalDisallowed` y `allowUIConfigurationProfileInstallation=false`.

**Aceptar solo después de probar:** instalar perfil A, exportar e instalar perfil B con cambios, confirmar en Ajustes que queda una única instalación del producto y que el conjunto de restricciones corresponde a B. Probar también la actualización desde el host de supervisión.

### P1 — El servidor QR entrega el perfil por HTTP a toda la red local

`src/server.py` escucha en `0.0.0.0:8089`, sin TLS, autenticación ni vencimiento. Cualquier equipo que alcance el puerto puede descargar el `.mobileconfig`; la respuesta incluye, entre otros datos, la contraseña de remoción si se configuró. El servidor permanece activo hasta cerrar la aplicación y la GUI no ofrece detenerlo. El perfil contiene datos legibles, no está firmado.

**Hacer:** eliminar el servidor como opción de instalación final o protegerlo con acceso de un solo uso, vencimiento breve, cierre visible/manual y exposición de red mínima. No entregar secretos de remoción en un endpoint adivinable. Si se conserva OTA, explicar claramente qué protege y qué no protege; no llamarlo instalación segura.

**Aceptar solo después de probar:** dispositivo no autorizado en la LAN no puede obtener el perfil; el enlace/token vence; el botón de detener cierra realmente el puerto; el cierre de la aplicación también lo cierra; errores de red dejan un mensaje útil. No usar la opción QR con perfiles de producción hasta cerrar este hallazgo.

### P1 — Claves de Web Content Filter obsoletas y coincidencia de dominios no validada

`src/profile_generator.py` emite `WhitelistedBookmarks` y `BlacklistedURLs`. La documentación actual de Apple las marca deprecated y ofrece `AllowListBookmarks` y `DenyListURLs` para el filtro `BuiltIn` (disponibles desde iOS/iPadOS 14.5). Apple limita `DenyListURLs` a 500 elementos. La lista negra genera hasta seis patrones por dominio, además de los enlaces de WhatsApp, pero no valida el total.

La documentación de Apple describe comparación por coincidencia de subcadena. Los prefijos actuales (`https://youtube.com`, `www`, `m`) no cubren de forma evidente todo subdominio (por ejemplo `video.youtube.com`) y pueden coincidir con dominios parecidos. La normalización acepta entradas que no son dominios limpios. El filtro de lista blanca también usa coincidencia de texto: no asumir que es un control por hostname con límites exactos.

**Hacer:** establecer una matriz explícita de versiones soportadas; emitir las claves actuales donde correspondan y conservar compatibilidad anterior solo cuando se haya verificado. Validar y limitar el número total de entradas a 500; normalizar/rechazar URL, puerto, ruta, espacios, IDN y valores malformados con mensajes accionables. Documentar los límites inevitables del matcher de Apple.

`AutoFilterEnabled=true` activa el filtrado automático de Apple además de la lista negra. Se asigna en modo “Bloquear Dominios Específicos” y también en “Sin Filtro Web” si queda activa la casilla de enlaces de WhatsApp; comprobar que el alcance real coincida con las etiquetas y explicarlo en la interfaz.

**Aceptar solo después de probar:** en los iOS objetivo, probar dominio raíz, `www`, `m`, subdominio arbitrario, HTTP/HTTPS, puerto, URL corta, redirección y dominio engañoso que contenga la cadena. Probar los cuatro modos de filtro. No afirmar cobertura de dominios hasta observarlo en dispositivo.

### P1 — Falta cerrar Private Relay y la instalación web en las restricciones

El “piso anti-evasión” no incluye `allowCloudPrivateRelay=false` (iOS 15+) ni `allowWebDistributionAppInstallation=false` (iOS 17.5+, regiones elegibles). `allowMarketplaceAppInstallation=false` sí se escribe cuando se activa el bloqueo de tiendas, pero la configuración debe cubrir por separado App Store, marketplaces alternativos y distribución web. `allowAppInstallation=false` puede cubrir parte de estos casos según versión, pero no usar eso como sustituto de una matriz de compatibilidad.

**Hacer:** contrastar cada clave, disponibilidad y efecto con Apple; agregar controles de cierre al modo estricto y exponer cualquier excepción de forma visible. Confirmar si Private Relay se bloquea con la clave y mostrar el estado resultante. No ocultar el hecho de que una app permitida puede implementar su propio DoH/DoT, proxy o conexión directa a IP: el DNS administrado por perfil no es un firewall de tráfico para apps nativas.

**Aceptar solo después de probar:** confirmar que el usuario no puede activar Private Relay, instalar un marketplace o hacer instalación web en una región/versión elegible; probar en Wi‑Fi y datos móviles. Probar una app permitida que use DNS propio o una conexión directa y documentar si el filtro la ve. Si se exige filtrar ese tráfico, recomendar una solución de filtrado de red/MDM adecuada en vez de atribuírselo al perfil actual.

### P1 — El modo estricto permite exportar con la whitelist vacía

`validate_before_export()` advierte que una lista vacía deja todas las apps visibles y permite continuar tras una confirmación. Para un usuario que intenta crear un teléfono kosher, una confirmación accidental produce un perfil que no aplica la lista blanca.

**Hacer:** bloquear la exportación vacía por defecto. Si se mantiene una excepción avanzada, separarla explícitamente del flujo estricto y hacer que la pantalla de resumen indique en rojo “todas las apps visibles”. Antes de guardar/servir, resumir apps incluidas, filtros, DNS, restricciones apagadas y método de instalación.

**Aceptar:** probar exportación vacía desde guardar y QR; el flujo seguro no debe generar ni servir un perfil permisivo por un clic accidental.

### P1 — “Confirmado” no significa realmente verificado

`is_confirmed()` considera confirmado cualquier elemento con `custom=True`; `add_app()` lo asigna automáticamente. El usuario puede escribir un ID equivocado y dejar de ver la advertencia sin haber mostrado evidencia de iMazing. Los IDs del catálogo y presets que sigan dudosos aparecen ya identificados como pendientes en B.1.

**Hacer:** distinguir “ingresado por el usuario” de “verificado en iPhone/iMazing”. No modificar IDs existentes ni marcarlos confirmados sin evidencia real. Mantener advertencia visible para personalizados hasta una acción de confirmación explícita con instrucciones y una última revisión antes de exportar; nunca inferir confirmación solo de `custom=True`.

**Aceptar:** verificar que un ID personalizado errado nunca recibe una etiqueta de verificado silenciosamente y que la interfaz explica que puede ocultar la app correcta o dejar permitido otro paquete.

**Caso prioritario ya documentado:** `tfilon.tfilon` está en los tres presets, mientras que el contexto dice que es el paquete Android y lo deja pendiente de confirmación. No asumir que el ID sirve en iOS; verificar en un iPhone con la app instalada y actualizar presets solo con esa evidencia.

### P1 — Firma e irremovibilidad se presentan como si estuvieran resueltas

El generador crea un plist XML sin firma. B.1 califica la firma como cosmética, pero la guía oficial de iMazing dice que para impedir de verdad quitar el perfil debe estar firmado e instalado en un dispositivo supervisado. La documentación general de Apple explica `PayloadRemovalDisallowed`, pero el comportamiento concreto de este flujo manual por cable debe confirmarse en iPhone.

**Hacer:** corregir la promesa de la GUI/contexto hasta verificarla; implementar firma verificable solo si el flujo puede manejar certificado/clave con seguridad. No guardar claves privadas sin protección ni afirmar que “por cable” por sí solo vuelve irremovible el perfil.

**Aceptar solo después de probar B.2:** comparar perfil sin firmar y firmado en dispositivo supervisado; probar eliminación desde Ajustes y desde el host. Registrar herramienta, versión de iOS, firma e identidad de supervisión.

### P1 — Falsa seguridad alrededor de reset y supervisión

`allowEraseContentAndSettings=false` bloquea el borrado desde Ajustes; no debe describirse como protección contra restauración DFU/Recovery o borrado remoto. `allowHostPairing=false` deja una excepción para el host de supervisión/identidad, no necesariamente una sola computadora física. El Bloqueo de Activación depende de Apple ID/Buscar y debe probarse; el perfil no lo fuerza por sí solo.

**Hacer:** revisar textos de GUI y guía para diferenciar host autorizado, identidad de supervisión, borrado desde Ajustes y restauración externa. Añadir pasos de respaldo y recuperación antes de activar restricciones difíciles de revertir. No afirmar que el DFU queda bloqueado.

**Aceptar solo después de probar:** ejecutar los puntos B.2 en un dispositivo de prueba y registrar cada resultado. Nunca experimentar DFU ni aplicar una política que pueda dejar al usuario sin recuperación en su teléfono principal.

### P2 — Guardado de perfil y datos de configuración

Las apps personalizadas se guardan, pero la selección y las restricciones vuelven a sus valores iniciales al reiniciar la app. En consecuencia, rehacer la configuración puede ser incómodo y es fácil exportar una configuración distinta de la última usada. Si `custom_apps.json` está mal formado o tiene tipos inesperados, `load_custom_apps()` puede fallar durante la construcción de la interfaz; `save_custom_apps()` imprime errores pero `add_app()` igual informa éxito.

**Hacer:** guardar/cargar la configuración de forma versionada y atómica; validar JSON por esquema, recuperar ante corrupción y mostrar errores en la GUI. Ofrecer guardar/duplicar/recuperar perfiles de configuración sin guardar contraseñas de remoción en texto claro. Mostrar fecha/configuración activa y un resumen final.

### P2 — Presets, etiquetas y opciones ocultas

Las descripciones de `PRESETS` no coinciden exactamente con sus IDs (Básico incluye Ajustes, Archivos, Tfilon y Mercado Pago; Trabajo & Finanzas no contiene las apps bancarias que sugiere el nombre). Aplicar preset cambia apps, pero no restricciones; la GUI no lo aclara. `get_profile_kwargs()` envía opciones de cámara y passcode que no tienen controles visibles; el estado de capturas no se envía. Los campos URL/dominio/NextDNS quedan visibles aunque no correspondan al modo elegido.

**Hacer:** alinear nombre, descripción e IDs; indicar “preset de apps” si eso es todo lo que cambia; exponer o eliminar opciones muertas; mostrar/ocultar y validar campos según selección. Explicar que allowlist permite/oculta apps ya instaladas; el programa no instala apps. Explicar que bloquear instalación también puede impedir actualizaciones manuales desde App Store.

### P2 — Declaración de compatibilidad desactualizada

README promete compatibilidad macOS, pero `open_export_dir()` usa `os.startfile`, disponible en Windows, y el script de compilación produce solo un `.exe`. README/contexto mencionan iOS 14–18+; la documentación actual de Apple ya marca claves usadas por el programa como deprecated y propone nuevas configuraciones con requisitos de versión/enrollment distintos.

**Hacer:** definir y probar plataformas de escritorio e iOS soportadas. Corregir o implementar la apertura multiplataforma. Publicar una matriz de claves por versión y método de inscripción; no migrar ciegamente a una declaración que requiere ADE/MDM si el producto promete instalación manual por iMazing.

## Alcance del filtro que debe quedar explícito

- Web Content Filter integrado no filtra el tráfico arbitrario de todas las apps nativas.
- DNS seguro administrado no controla apps que usen DoH/DoT propio, proxies o IP directa.
- Bloquear VPN nueva no elimina necesariamente configuraciones existentes; revisar el estado previo del teléfono antes de aplicar el perfil.
- `allowUIConfigurationProfileInstallation=false` bloquea instalaciones interactivas, pero el host de supervisión/MDM autorizado conserva capacidad administrativa.
- No hay prueba física en esta sesión. La pasada de autotest solo confirma checks automáticos escritos por el proyecto, no que iOS acepte las claves o aplique su semántica.

## Verificación requerida después de implementar

1. Ejecutar `python src/selftest.py` y exigir `0 fallas`; ampliar regresiones para identificador estable/reemplazo, whitelist vacía, límites de 500 entradas, entradas inválidas, carga JSON corrupta y exposición/cierre del servidor.
2. Si se modifica `src/`, ejecutar `powershell -ExecutionPolicy Bypass -File .\build.ps1` y confirmar que `KosherLock_iOS.exe` fue actualizado.
3. Probar el flujo completo en un iPhone supervisado de prueba según B.2, incluyendo los casos adicionales de Private Relay, distribución alternativa, actualización/reemplazo, dominio/subdominio y firma/eliminación. Registrar modelo, iOS, método de supervisión/instalación y resultado.
4. Actualizar Parte B del contexto solo con hechos resueltos. Lo que no se haya probado en dispositivo permanece como pendiente; agregar hallazgos y limitaciones nuevos.
5. Agregar a Parte C un resumen conciso de los cambios reales de esa sesión. Hacer un commit con un mensaje que explique el cambio y su motivo.

## Baseline de esta auditoría (2026-10-05)

- Revisados: `src/main.py`, `src/app_catalog.py`, `src/profile_generator.py`, `src/server.py`, `src/selftest.py`, README, `build.ps1` y el documento de contexto.
- `python src/selftest.py`: **270 verificaciones, 0 fallas**.
- No se modificó el código fuente y no se tuvo acceso a un iPhone real supervisado.
- El autotest comparte su catálogo esperado de claves con el generador; no valida contra un esquema vivo de Apple y no prueba comportamiento real de iOS.
- Hay una aserción vacía en `test_catalog()` (`... or True`) que siempre pasa; corregirla cuando se trabaje sobre tests para que valide una condición real.

## Fuentes oficiales consultadas

- [Apple — Restrictions](https://developer.apple.com/documentation/devicemanagement/restrictions)
- [Apple — WebContentFilter](https://developer.apple.com/documentation/devicemanagement/webcontentfilter)
- [Apple — DNS settings object](https://developer.apple.com/documentation/devicemanagement/networkdnssettingsdnssettingsobject)
- [Apple — Top-level profile keys](https://developer.apple.com/documentation/devicemanagement/toplevel)
- [Apple — Deployment restrictions for iPhone and iPad](https://support.apple.com/guide/deployment/dep0f7dd3d8/web)
- [iMazing — Managing configuration profiles](https://imazing.com/guides/how-to-manage-configuration-profiles)
- [iMazing — Pairing with supervised devices](https://imazing.com/guides/connect-your-device-to-imazing)
