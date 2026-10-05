"""
Autotest de KosherLock iOS. Ejecutar:  python selftest.py
No necesita iPhone: valida estructura del perfil, catálogo, servidor y GUI.
Sale con código 1 si algo falla.
"""
import itertools
import os
import plistlib
import re
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app_catalog
from app_catalog import AppCatalogManager, DEFAULT_CATALOG, PRESETS, is_confirmed
from profile_generator import (
    ESSENTIAL_APPS, KNOWN_RESTRICTION_KEYS, ProfileError, generate_mobileconfig,
)

FAILS = []
CHECKS = 0


def check(cond, msg):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(msg)
        print(f"  FALLA: {msg}")


def parse(data):
    return plistlib.loads(data)


def payload(profile, ptype):
    for p in profile["PayloadContent"]:
        if p["PayloadType"] == ptype:
            return p
    return None


def test_profile():
    print("[perfil]")
    ids = ["com.whatsapp.WhatsApp", "com.apple.camera"]
    snapshot = list(ids)
    prof = parse(generate_mobileconfig(allowed_bundle_ids=ids))
    check(ids == snapshot, "generate_mobileconfig mutó la lista del llamador")

    r = payload(prof, "com.apple.applicationaccess")
    check(r is not None, "falta payload de Restrictions")
    keys = {k for k in r if not k.startswith("Payload")}
    check(keys <= KNOWN_RESTRICTION_KEYS, f"claves no registradas: {keys - KNOWN_RESTRICTION_KEYS}")
    check("allowHostPairing" in r and r["allowHostPairing"] is False, "falta allowHostPairing=False")
    check("allowPairing" not in r, "quedó la clave inventada allowPairing")
    check("allowCloudPrivateRelay" in r and r["allowCloudPrivateRelay"] is False, "falta allowCloudPrivateRelay=False")
    check("allowWebDistributionAppInstallation" in r and r["allowWebDistributionAppInstallation"] is False, "falta allowWebDistributionAppInstallation=False")
    for e in ESSENTIAL_APPS:
        check(e in r["whitelistedAppBundleIDs"], f"falta app esencial {e}")
    check(r["whitelistedAppBundleIDs"] == r["allowListedAppBundleIDs"], "las dos listas blancas difieren")
    for k in ("allowUIConfigurationProfileInstallation", "allowVPNCreation",
              "allowEnterpriseAppTrust", "allowAppClips", "allowAppInstallation"):
        check(r.get(k) is False, f"piso anti-evasión: {k} debería ser False")

    # Identificadores estables
    p1 = parse(generate_mobileconfig())
    p2 = parse(generate_mobileconfig())
    check(p1["PayloadIdentifier"] == p2["PayloadIdentifier"] == "com.kosherlock.ios.profile",
          "PayloadIdentifier debe ser estable entre exportaciones para reemplazo limpio")

    # Sin lista blanca no debe escribirse ninguna lista (dejaría solo 2 apps)
    r0 = payload(parse(generate_mobileconfig(allowed_bundle_ids=[])), "com.apple.applicationaccess")
    check("whitelistedAppBundleIDs" not in r0, "lista vacía no debe escribir whitelistedAppBundleIDs")

    # Combinaciones web x DNS
    for web, dns in itertools.product(["block_all", "blacklist", "whitelist", "none"],
                                      ["cleanbrowsing", "cloudflare", "nextdns", "none"]):
        kw = dict(allowed_bundle_ids=ids, web_filter_mode=web, dns_filter_mode=dns,
                  allowed_urls=["example.com"], nextdns_id="abc123",
                  custom_blocked_domains=["youtube.com"])
        try:
            p = parse(generate_mobileconfig(**kw))
        except Exception as e:  # noqa
            check(False, f"{web}/{dns} lanzó {e!r}")
            continue
        check(p["PayloadType"] == "Configuration", f"{web}/{dns}: perfil raíz inválido")
        uuids = [p["PayloadUUID"]] + [x["PayloadUUID"] for x in p["PayloadContent"]]
        check(len(uuids) == len(set(uuids)), f"{web}/{dns}: UUIDs repetidos")
        for x in p["PayloadContent"]:
            check(all(k in x for k in ("PayloadType", "PayloadVersion", "PayloadIdentifier",
                                       "PayloadUUID")), f"{web}/{dns}: payload incompleto")
        w = payload(p, "com.apple.webcontent-filter")
        if web == "block_all":
            check(w and w["WhitelistedBookmarks"] and w["AllowListBookmarks"], "block_all sin marcador inerte")
            check("FilterBrowsers" not in w and "FilterSockets" not in w, "claves de Plugin en filtro BuiltIn")
        if web == "blacklist":
            check(w and any(u.startswith("https://youtube.com") for u in w["BlacklistedURLs"]),
                  "blacklist no contiene youtube.com")
            check("DenyListURLs" in w and "BlacklistedURLs" in w, "falta DenyListURLs o BlacklistedURLs")
            check(not any("*" in u for u in w["BlacklistedURLs"]), "comodines en BlacklistedURLs")
            check(w.get("AutoFilterEnabled") is True, "blacklist sin AutoFilterEnabled")
        if web == "whitelist":
            check(w["WhitelistedBookmarks"][0]["URL"] == "https://example.com", "whitelist no normalizó URL")
            check("AllowListBookmarks" in w, "whitelist sin AllowListBookmarks")
        d = payload(p, "com.apple.dnsSettings.managed")
        check((d is None) == (dns == "none"), f"{web}/{dns}: payload DNS incorrecto")
        if d is not None:
            check(d["DNSSettings"]["DNSProtocol"] == "HTTPS", "DNS no es HTTPS")
            check(d["DNSSettings"]["ServerURL"].startswith("https://"), "ServerURL sin https")

    # Errores esperados
    too_many_domains = [f"ejemplo-bloqueado-{i}.com" for i in range(100)]  # genera 600 URLs
    for kw, what in [
        (dict(dns_filter_mode="nextdns", nextdns_id="  "), "NextDNS sin ID"),
        (dict(web_filter_mode="whitelist", allowed_urls=[]), "whitelist sin URLs"),
        (dict(web_filter_mode="blacklist", custom_blocked_domains=[],
              block_whatsapp_status_channels=False), "blacklist vacía"),
        (dict(web_filter_mode="blacklist", custom_blocked_domains=too_many_domains), "límite 500 URLs excedido"),
        (dict(web_filter_mode="xyz"), "modo web desconocido"),
        (dict(dns_filter_mode="xyz"), "modo DNS desconocido"),
    ]:
        try:
            generate_mobileconfig(**kw)
            check(False, f"debió lanzar ProfileError: {what}")
        except ProfileError:
            check(True, what)

    # Remoción
    p = parse(generate_mobileconfig(non_removable=True, removal_passcode=""))
    check(p.get("PayloadRemovalDisallowed") is True and "RemovalPassword" not in p, "no-removible mal")
    p = parse(generate_mobileconfig(non_removable=True, removal_passcode="1234"))
    check(p.get("RemovalPassword") == "1234" and "PayloadRemovalDisallowed" not in p,
          "contraseña y no-removible no pueden coexistir")
    p = parse(generate_mobileconfig(non_removable=False, removal_passcode=""))
    check("RemovalPassword" not in p and "PayloadRemovalDisallowed" not in p, "removible mal")

    # Dominios con formatos raros
    p = parse(generate_mobileconfig(web_filter_mode="blacklist", block_whatsapp_status_channels=False,
                                    custom_blocked_domains=["https://www.Tiktok.com/foo", " x.com "]))
    deny = payload(p, "com.apple.webcontent-filter")["BlacklistedURLs"]
    check("https://tiktok.com" in deny and "https://x.com" in deny, "normalización de dominios")


def test_catalog():
    print("[catálogo]")
    ids = [a["id"] for a in DEFAULT_CATALOG]
    check(len(ids) == len(set(ids)), f"IDs duplicados: {[i for i in set(ids) if ids.count(i) > 1]}")
    rx = re.compile(r"^[A-Za-z0-9\-]+(\.[A-Za-z0-9\-_]+)+$")
    for i in ids:
        check(bool(rx.match(i)), f"Bundle ID con formato dudoso: {i}")
    for k, pr in PRESETS.items():
        for i in pr["allowed_ids"]:
            check(i in ids, f"preset {k} referencia ID que no está en el catálogo: {i}")
    for e in ESSENTIAL_APPS:
        check(e in ids, f"app esencial {e} no está en el catálogo")

    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "c.json")
        m = AppCatalogManager(data_file=f)
        n0 = len(m.apps)
        ok = m.add_app("com.test.banco", "Banco Test")
        check(ok is not False and len(m.apps) == n0 + 1, "add_app no agregó")
        bad = m.add_app("no es un id", "X")
        check(not bad if not isinstance(bad, tuple) else not bad[0], "aceptó ID inválido")
        dup = m.add_app("COM.TEST.BANCO", "Dup")
        check(not dup if not isinstance(dup, tuple) else not dup[0], "aceptó ID duplicado")
        m2 = AppCatalogManager(data_file=f)
        check(any(a["id"] == "com.test.banco" for a in m2.apps), "no persistió en disco")
        check(not is_confirmed(next(a for a in m2.apps if a["id"] == "com.test.banco")),
              "app personalizada sin ID en CONFIRMED_IDS no debe figurar confirmada")
        m2.remove_custom_app("com.test.banco")
        m3 = AppCatalogManager(data_file=f)
        check(not any(a["id"] == "com.test.banco" for a in m3.apps), "no se borró del disco")
        m3.remove_custom_app("com.apple.camera")
        check(any(a["id"] == "com.apple.camera" for a in m3.apps), "se borró una app del catálogo base")


def test_server():
    print("[servidor]")
    from server import ProfileServerManager
    data = generate_mobileconfig(allowed_bundle_ids=["com.apple.camera"])
    s = ProfileServerManager()
    ok, url = s.start(data, port=18089)
    check(ok, f"no arrancó: {url}")
    if ok:
        try:
            local = f"http://127.0.0.1:18089/{url.rsplit('/', 1)[-1]}"
            with urllib.request.urlopen(local, timeout=5) as resp:
                body = resp.read()
                ct = resp.headers.get("Content-Type", "")
                check(body == data, "bytes servidos distintos")
                check("application/x-apple-aspen-config" in ct, f"Content-Type={ct}")
                check(resp.headers.get("Content-Disposition") is None, "no debe haber Content-Disposition")
            with urllib.request.urlopen(local + "?x=1", timeout=5) as resp:
                check(resp.read() == data, "query string rompió la ruta")

            # Petición no autorizada sin token debe devolver 404
            unauth = "http://127.0.0.1:18089/kosher.mobileconfig"
            try:
                urllib.request.urlopen(unauth, timeout=5)
                check(False, "servidor aceptó petición sin token")
            except urllib.error.HTTPError as e:
                check(e.code == 404, f"código inesperado sin token: {e.code}")
            except Exception:
                pass

            img = s.generate_qr_image(size=200)
            check(img.size == (200, 200), "QR de tamaño incorrecto")
        finally:
            s.stop()
            check(not s.is_running, "servidor no se detuvo correctamente")


def test_gui():
    print("[GUI]")
    import main as m
    from tkinter import messagebox
    answers = []
    m.messagebox.askyesno = lambda *a, **k: (answers.append(a) or True)
    m.messagebox.showerror = lambda *a, **k: answers.append(("ERR",) + a)
    m.messagebox.showinfo = lambda *a, **k: None
    app = m.KosherLockApp()
    try:
        app.update()
        check(app.winfo_width() >= 980 and app.winfo_height() >= 680,
              f"ventana demasiado chica: {app.winfo_width()}x{app.winfo_height()}")
        for key in PRESETS:
            app.apply_preset(key)
            app.update()
            data = app.build_profile_bytes()
            check(data is not None, f"preset {key}: no generó perfil")
            if data:
                r = payload(parse(data), "com.apple.applicationaccess")
                chosen = set(PRESETS[key]["allowed_ids"])
                listed = set(r.get("whitelistedAppBundleIDs", []))
                check(chosen <= listed, f"preset {key}: faltan apps en el perfil")
        # Buscador y categorías
        app.search_var.set("zzzzzz")
        app.refresh_app_list()
        app.search_var.set("")
        for cat in app.catalog_mgr.get_categories():
            app.category_var.set(cat)
            app.refresh_app_list()
        app.category_var.set("Todas")
        app.refresh_app_list()
        app.select_all_visible()
        app.deselect_all()
        check(app.get_selected_bundle_ids() == [], "deselect_all no limpió")
        check(app.build_profile_bytes() is None, "lista blanca vacía debe bloquear la exportación")
        # Error de usuario: NextDNS sin ID debe mostrar error y devolver None
        app.apply_preset("basico")
        app.dns_filter_mode_var.set("nextdns")
        app.nextdns_id_var.set("")
        answers.clear()
        check(app.build_profile_bytes() is None, "NextDNS sin ID debió bloquear la exportación")
        app.dns_filter_mode_var.set("cleanbrowsing")
        app.update()
    finally:
        app.on_close() if hasattr(app, "on_close") else app.destroy()


if __name__ == "__main__":
    for t in (test_profile, test_catalog, test_server, test_gui):
        try:
            t()
        except Exception as e:  # noqa
            import traceback
            traceback.print_exc()
            FAILS.append(f"{t.__name__} explotó: {e!r}")
    print(f"\n{CHECKS} verificaciones, {len(FAILS)} fallas")
    for f in FAILS:
        print(" -", f)
    sys.exit(1 if FAILS else 0)
