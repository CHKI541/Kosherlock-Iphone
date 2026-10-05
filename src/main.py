"""
KosherLock iOS — Gestor y Creador de Perfiles Kosher para iPhone
Herramienta de escritorio moderna y visual para configurar iPhones Kosher
mediante listas blancas de apps y perfiles de restricción oficial de Apple (.mobileconfig).
"""

import os
import sys

# Asegurar resolución de módulos internos independientemente del directorio de trabajo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

# Módulos internos
from app_catalog import AppCatalogManager, PRESETS, is_confirmed
from profile_generator import generate_mobileconfig, ProfileError
from server import ProfileServerManager, get_local_ip

# Configuración visual
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class KosherLockApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("KosherLock iOS — Gestor de iPhones Kosher")
        self.geometry("1060x780")
        self.minsize(980, 680)

        # Gestores
        self.catalog_mgr = AppCatalogManager()
        self.server_mgr = ProfileServerManager()

        # Variables de estado: Apps seleccionadas (bundle_id -> BooleanVar)
        self.app_vars = {}
        for app in self.catalog_mgr.apps:
            self.app_vars[app["id"]] = tk.BooleanVar(value=app.get("default", False))

        # Variables de Restricciones
        self.block_safari_var = tk.BooleanVar(value=True)
        self.block_wa_status_var = tk.BooleanVar(value=True)
        self.block_app_store_var = tk.BooleanVar(value=True)
        self.block_app_removal_var = tk.BooleanVar(value=False)
        self.block_in_app_purchases_var = tk.BooleanVar(value=True)

        self.block_erase_var = tk.BooleanVar(value=True)
        self.block_pairing_var = tk.BooleanVar(value=True)
        self.block_airdrop_var = tk.BooleanVar(value=True)
        self.block_game_center_var = tk.BooleanVar(value=True)
        self.block_accounts_var = tk.BooleanVar(value=True)
        self.block_passcode_var = tk.BooleanVar(value=False)
        self.block_siri_var = tk.BooleanVar(value=True)
        self.block_camera_var = tk.BooleanVar(value=False)

        self.web_filter_mode_var = tk.StringVar(value="block_all")
        self.custom_blocked_domains_var = tk.StringVar(value="mercadolibre.com, ofertas.mercadopago.com, youtube.com, tiktok.com, instagram.com")
        self.allowed_urls_var = tk.StringVar(value="")
        self.dns_filter_mode_var = tk.StringVar(value="cleanbrowsing")
        self.nextdns_id_var = tk.StringVar(value="")
        self.removal_passcode_var = tk.StringVar(value="")
        self.non_removable_var = tk.BooleanVar(value=True)

        self.search_var = tk.StringVar(value="")
        self.category_var = tk.StringVar(value="Todas")

        # Construir interfaz gráfica
        self.setup_ui()

        # Protocolo de cierre
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        # -------------------------------------------------------------
        # CABECERA PRINCIPAL
        # -------------------------------------------------------------
        header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#0F172A", height=75)
        header_frame.pack(fill="x", side="top")

        title_label = ctk.CTkLabel(
            header_frame,
            text="🍎 KosherLock iOS",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#38BDF8"
        )
        title_label.pack(side="left", padx=(20, 10), pady=12)

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Configurador de iPhones Kosher (Modo Supervisado & Lista Blanca)",
            font=ctk.CTkFont(size=13),
            text_color="#94A3B8"
        )
        subtitle_label.pack(side="left", pady=12)

        # Botón de Presets Rápidos en la cabecera
        preset_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        preset_frame.pack(side="right", padx=20, pady=12)

        btn_preset_basic = ctk.CTkButton(
            preset_frame,
            text="⚡ Preset Básico",
            width=120,
            height=32,
            fg_color="#1E293B",
            hover_color="#334155",
            command=lambda: self.apply_preset("basico")
        )
        btn_preset_basic.pack(side="left", padx=4)

        btn_preset_strict = ctk.CTkButton(
            preset_frame,
            text="🔒 Ultra Estricto",
            width=120,
            height=32,
            fg_color="#1E293B",
            hover_color="#334155",
            command=lambda: self.apply_preset("estricto")
        )
        btn_preset_strict.pack(side="left", padx=4)

        btn_preset_work = ctk.CTkButton(
            preset_frame,
            text="💼 Trabajo & Banco",
            width=130,
            height=32,
            fg_color="#1E293B",
            hover_color="#334155",
            command=lambda: self.apply_preset("trabajo")
        )
        btn_preset_work.pack(side="left", padx=4)

        # -------------------------------------------------------------
        # PESTAÑAS PRINCIPALES
        # -------------------------------------------------------------
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=15)

        self.tab_apps = self.tabview.add("📱 1. Aplicaciones Permitidas")
        self.tab_rules = self.tabview.add("🛡️ 2. Restricciones & Políticas")
        self.tab_export = self.tabview.add("🚀 3. Aplicar al iPhone")
        self.tab_guide = self.tabview.add("📖 4. Guía de Supervisión")

        self.build_apps_tab()
        self.build_rules_tab()
        self.build_export_tab()
        self.build_guide_tab()

        # -------------------------------------------------------------
        # BARRA DE ESTADO INFERIOR
        # -------------------------------------------------------------
        self.status_bar = ctk.CTkLabel(
            self,
            text="Listo. Selecciona tus apps y genera el perfil .mobileconfig.",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8",
            anchor="w",
            padx=20,
            height=28
        )
        self.status_bar.pack(fill="x", side="bottom")

    # =========================================================================
    # TAB 1: SELECCIÓN DE APLICACIONES
    # =========================================================================
    def build_apps_tab(self):
        # Barra superior de filtros y búsqueda
        filter_bar = ctk.CTkFrame(self.tab_apps, fg_color="transparent")
        filter_bar.pack(fill="x", padx=10, pady=(10, 8))

        lbl_search = ctk.CTkLabel(filter_bar, text="Buscar:", font=ctk.CTkFont(weight="bold"))
        lbl_search.pack(side="left", padx=(0, 6))

        self.entry_search = ctk.CTkEntry(
            filter_bar,
            placeholder_text="Nombre de app o bundle ID (ej. Waze, Galicia, WhatsApp)...",
            textvariable=self.search_var,
            width=320
        )
        self.entry_search.pack(side="left", padx=(0, 15))
        self.entry_search.bind("<KeyRelease>", lambda e: self.refresh_app_list())

        lbl_cat = ctk.CTkLabel(filter_bar, text="Categoría:", font=ctk.CTkFont(weight="bold"))
        lbl_cat.pack(side="left", padx=(0, 6))

        self.combo_cat = ctk.CTkComboBox(
            filter_bar,
            values=self.catalog_mgr.get_categories(),
            variable=self.category_var,
            command=lambda v: self.refresh_app_list(),
            width=180
        )
        self.combo_cat.pack(side="left", padx=(0, 15))

        btn_add_custom = ctk.CTkButton(
            filter_bar,
            text="+ Agregar Otra App",
            fg_color="#0284C7",
            hover_color="#0369A1",
            width=150,
            command=self.open_add_app_dialog
        )
        btn_add_custom.pack(side="right")

        # Barra de acciones rápidas sobre la lista
        quick_bar = ctk.CTkFrame(self.tab_apps, fg_color="transparent")
        quick_bar.pack(fill="x", padx=10, pady=(0, 8))

        self.lbl_selected_count = ctk.CTkLabel(
            quick_bar,
            text="Apps permitidas: 0 seleccionadas",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38BDF8"
        )
        self.lbl_selected_count.pack(side="left")

        btn_select_all = ctk.CTkButton(
            quick_bar,
            text="Seleccionar Todo",
            width=110,
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            command=self.select_all_visible
        )
        btn_select_all.pack(side="right", padx=(4, 0))

        btn_deselect_all = ctk.CTkButton(
            quick_bar,
            text="Deseleccionar Todo",
            width=125,
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            command=self.deselect_all
        )
        btn_deselect_all.pack(side="right", padx=4)

        # Contenedor con scroll para las apps
        self.scroll_apps = ctk.CTkScrollableFrame(self.tab_apps, corner_radius=8, fg_color="#1E293B")
        self.scroll_apps.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        self.refresh_app_list()

    def refresh_app_list(self):
        # Limpiar contenedor de apps
        for widget in self.scroll_apps.winfo_children():
            widget.destroy()

        cat = self.category_var.get()
        search = self.search_var.get()
        filtered = self.catalog_mgr.filter_apps(cat, search)

        if not filtered:
            empty_lbl = ctk.CTkLabel(
                self.scroll_apps,
                text="No se encontraron apps con ese criterio de búsqueda.",
                text_color="#94A3B8",
                pady=30
            )
            empty_lbl.pack()
            self.update_count_label()
            return

        for app in filtered:
            app_id = app["id"]
            if app_id not in self.app_vars:
                self.app_vars[app_id] = tk.BooleanVar(value=app.get("default", False))

            row = ctk.CTkFrame(self.scroll_apps, fg_color="#0F172A", corner_radius=6, height=54)
            row.pack(fill="x", padx=6, pady=3)
            row.pack_propagate(False)

            # Checkbox
            chk = ctk.CTkCheckBox(
                row,
                text="",
                variable=self.app_vars[app_id],
                width=24,
                command=self.update_count_label
            )
            chk.pack(side="left", padx=(12, 8))

            # Información de la App
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, pady=6)

            title_row = ctk.CTkFrame(info_frame, fg_color="transparent")
            title_row.pack(fill="x")

            name_lbl = ctk.CTkLabel(
                title_row,
                text=app["name"],
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#F8FAFC"
            )
            name_lbl.pack(side="left")

            badge = ctk.CTkLabel(
                title_row,
                text=f" {app['category']} ",
                font=ctk.CTkFont(size=11),
                fg_color="#334155",
                corner_radius=4,
                text_color="#CBD5E1"
            )
            badge.pack(side="left", padx=10)

            if not is_confirmed(app):
                ctk.CTkLabel(
                    title_row,
                    text=" ⚠ ID sin confirmar ",
                    font=ctk.CTkFont(size=11),
                    fg_color="#92400E",
                    corner_radius=4,
                    text_color="#FDE68A"
                ).pack(side="left")

            desc_text = f"{app.get('description', '')}  •  Bundle ID: {app_id}"
            desc_lbl = ctk.CTkLabel(
                info_frame,
                text=desc_text,
                font=ctk.CTkFont(size=11),
                text_color="#94A3B8",
                anchor="w"
            )
            desc_lbl.pack(fill="x")

            # Botón eliminar si es personalizada
            if app.get("custom"):
                btn_del = ctk.CTkButton(
                    row,
                    text="✕",
                    width=28,
                    height=28,
                    fg_color="#EF4444",
                    hover_color="#DC2626",
                    command=lambda bid=app_id: self.delete_custom_app(bid)
                )
                btn_del.pack(side="right", padx=10)

        self.update_count_label()

    def update_count_label(self):
        count = sum(1 for v in self.app_vars.values() if v.get())
        total = len(self.catalog_mgr.apps)
        self.lbl_selected_count.configure(text=f"Apps permitidas: {count} seleccionadas de {total}")

    def select_all_visible(self):
        cat = self.category_var.get()
        search = self.search_var.get()
        for app in self.catalog_mgr.filter_apps(cat, search):
            self.app_vars[app["id"]].set(True)
        self.update_count_label()

    def deselect_all(self):
        for v in self.app_vars.values():
            v.set(False)
        self.update_count_label()

    def apply_preset(self, preset_key):
        if preset_key not in PRESETS:
            return
        preset = PRESETS[preset_key]
        allowed = set(preset["allowed_ids"])

        for app_id, var in self.app_vars.items():
            var.set(app_id in allowed)

        self.update_count_label()
        messagebox.showinfo(
            "Preset Aplicado",
            f"Se aplicó el preset: {preset['name']}\n\n{preset['desc']}"
        )

    def open_add_app_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Agregar App Personalizada")
        dialog.geometry("480x330")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        lbl_head = ctk.CTkLabel(
            dialog,
            text="Agregar Aplicación por Bundle ID",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        lbl_head.pack(pady=(16, 10))

        lbl_n = ctk.CTkLabel(dialog, text="Nombre de la App (ej. Banco Provincia):")
        lbl_n.pack(anchor="w", padx=25)
        entry_name = ctk.CTkEntry(dialog, width=430)
        entry_name.pack(padx=25, pady=(2, 10))

        lbl_i = ctk.CTkLabel(dialog, text="Bundle ID de iOS (ej. com.bancoprovincia.app):")
        lbl_i.pack(anchor="w", padx=25)
        entry_id = ctk.CTkEntry(dialog, width=430)
        entry_id.pack(padx=25, pady=(2, 10))

        lbl_d = ctk.CTkLabel(dialog, text="Descripción (opcional):")
        lbl_d.pack(anchor="w", padx=25)
        entry_desc = ctk.CTkEntry(dialog, width=430)
        entry_desc.pack(padx=25, pady=(2, 16))

        def on_save():
            name = entry_name.get()
            bid = entry_id.get()
            desc = entry_desc.get()
            ok, msg = self.catalog_mgr.add_app(bid, name, "Personalizadas", desc)
            if ok:
                self.app_vars[bid] = tk.BooleanVar(value=True)
                self.combo_cat.configure(values=self.catalog_mgr.get_categories())
                self.refresh_app_list()
                dialog.destroy()
            else:
                messagebox.showerror("Error", msg, parent=dialog)

        btn_save = ctk.CTkButton(dialog, text="Guardar y Permitir", fg_color="#10B981", hover_color="#059669", command=on_save)
        btn_save.pack(pady=5)

    def delete_custom_app(self, bundle_id):
        if messagebox.askyesno("Eliminar App", f"¿Eliminar '{bundle_id}' del catálogo?"):
            self.catalog_mgr.remove_custom_app(bundle_id)
            if bundle_id in self.app_vars:
                del self.app_vars[bundle_id]
            self.refresh_app_list()

    # =========================================================================
    # TAB 2: POLÍTICAS Y RESTRICCIONES
    # =========================================================================
    def build_rules_tab(self):
        scroll_rules = ctk.CTkScrollableFrame(self.tab_rules, corner_radius=8, fg_color="transparent")
        scroll_rules.pack(fill="both", expand=True, padx=10, pady=10)

        # CARD 1: NAVEGACIÓN Y WEB
        card_web = ctk.CTkFrame(scroll_rules, fg_color="#1E293B", corner_radius=8)
        card_web.pack(fill="x", pady=6, padx=6)

        ctk.CTkLabel(
            card_web,
            text="🌐 Navegación & Acceso a Internet",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#38BDF8"
        ).pack(anchor="w", padx=16, pady=(12, 6))

        ctk.CTkSwitch(
            card_web,
            text="Bloquear Safari y Web Clips (Elimina el navegador nativo de Apple)",
            variable=self.block_safari_var,
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=20, pady=5)

        ctk.CTkLabel(
            card_web,
            text="Filtro de Contenido Web en WebViews (Dentro de apps permitidas):",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=20, pady=(10, 4))

        seg_web = ctk.CTkSegmentedButton(
            card_web,
            values=["Bloqueo Total WebViews", "Bloquear Dominios Específicos", "Solo Lista Blanca", "Sin Filtro Web"],
            command=self.on_web_filter_change
        )
        seg_web.set("Bloqueo Total WebViews")
        seg_web.pack(anchor="w", padx=20, pady=(0, 8))

        lbl_custom_domains = ctk.CTkLabel(
            card_web,
            text="Dominios no kosher a bloquear en WebViews (ej: Mercado Libre, Ofertas, YouTube):",
            font=ctk.CTkFont(size=12)
        )
        lbl_custom_domains.pack(anchor="w", padx=20, pady=(4, 2))

        entry_custom_domains = ctk.CTkEntry(
            card_web,
            textvariable=self.custom_blocked_domains_var,
            width=580,
            placeholder_text="mercadolibre.com, ofertas.mercadopago.com, youtube.com, tiktok.com, instagram.com"
        )
        entry_custom_domains.pack(anchor="w", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            card_web,
            text="Filtro DNS Cifrado Kosher a nivel de Sistema (DoH):",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=20, pady=(6, 4))

        seg_dns = ctk.CTkSegmentedButton(
            card_web,
            values=["CleanBrowsing Family (Recomendado)", "Cloudflare 1.1.1.3", "NextDNS", "Ninguno"],
            command=self.on_dns_filter_change
        )
        seg_dns.set("CleanBrowsing Family (Recomendado)")
        seg_dns.pack(anchor="w", padx=20, pady=(0, 8))

        ctk.CTkLabel(
            card_web,
            text="ID de NextDNS (solo si elegiste NextDNS, ej: abc123):",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=20, pady=(4, 2))
        ctk.CTkEntry(card_web, textvariable=self.nextdns_id_var, width=260).pack(
            anchor="w", padx=20, pady=(0, 8))

        ctk.CTkLabel(
            card_web,
            text="Sitios permitidos (solo si elegiste 'Solo Lista Blanca'; separados por coma):",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=20, pady=(4, 2))
        ctk.CTkEntry(
            card_web, textvariable=self.allowed_urls_var, width=580,
            placeholder_text="ejemplo.com, banco.com.ar"
        ).pack(anchor="w", padx=20, pady=(0, 12))

        # CARD 1.5: WHATSAPP KOSHER (ESTADOS Y CANALES)
        card_wa = ctk.CTkFrame(scroll_rules, fg_color="#1E293B", corner_radius=8)
        card_wa.pack(fill="x", pady=6, padx=6)

        ctk.CTkLabel(
            card_wa,
            text="💬 WhatsApp: enlaces a Canales y Estados",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#38BDF8"
        ).pack(anchor="w", padx=16, pady=(12, 4))

        ctk.CTkSwitch(
            card_wa,
            text="Bloquear ENLACES a Canales/Estados de WhatsApp en vistas web",
            variable=self.block_wa_status_var,
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=20, pady=5)

        ctk.CTkLabel(
            card_wa,
            text="⚠ Un perfil de iOS NO puede bloquear la pestaña Novedades (Estados y Canales) dentro de la\n"
                 "app de WhatsApp: esa app no usa el motor web que Apple filtra. Esto solo bloquea los\n"
                 "ENLACES a canales (wa.me/channel, whatsapp.com/channel) si se abren en una vista web.\n"
                 "Para anular Novedades de verdad hace falta un filtro comercial con inspección SSL\n"
                 "(MB Smart, Netspark, Meshimer) o no permitir WhatsApp.",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8",
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 12))

        # CARD 2: APP STORE E INSTALACIONES
        card_store = ctk.CTkFrame(scroll_rules, fg_color="#1E293B", corner_radius=8)
        card_store.pack(fill="x", pady=6, padx=6)

        ctk.CTkLabel(
            card_store,
            text="🛑 App Store & Gestión de Aplicaciones",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#38BDF8"
        ).pack(anchor="w", padx=16, pady=(12, 6))

        ctk.CTkSwitch(
            card_store,
            text="Bloquear App Store e Instalaciones nuevas (Oculta el App Store)",
            variable=self.block_app_store_var,
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=20, pady=5)

        ctk.CTkSwitch(
            card_store,
            text="Bloquear Desinstalación de Apps autorizadas (Impide borrar íconos)",
            variable=self.block_app_removal_var,
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=20, pady=5)

        ctk.CTkSwitch(
            card_store,
            text="Bloquear compras y suscripciones dentro de las aplicaciones",
            variable=self.block_in_app_purchases_var,
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=20, pady=(5, 12))

        # CARD 3: ANTI-EVASIÓN Y SEGURIDAD HARDWARE
        card_sec = ctk.CTkFrame(scroll_rules, fg_color="#1E293B", corner_radius=8)
        card_sec.pack(fill="x", pady=6, padx=6)

        ctk.CTkLabel(
            card_sec,
            text="🔒 Anti-Evasión & Bloqueo de Hardware",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#38BDF8"
        ).pack(anchor="w", padx=16, pady=(12, 6))

        ctk.CTkSwitch(
            card_sec,
            text="Bloquear Restablecimiento de Fábrica (Deshabilita 'Borrar contenido' en Ajustes)",
            variable=self.block_erase_var,
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=20, pady=5)

        ctk.CTkSwitch(
            card_sec,
            text="Bloquear Emparejamiento USB (solo la PC que lo supervisó podrá conectarse)",
            variable=self.block_pairing_var,
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=20, pady=5)

        ctk.CTkSwitch(
            card_sec,
            text="Bloquear AirDrop (Impide transferir fotos o enlaces por proximidad)",
            variable=self.block_airdrop_var,
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=20, pady=5)

        ctk.CTkSwitch(
            card_sec,
            text="Bloquear Game Center y juegos multijugador",
            variable=self.block_game_center_var,
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=20, pady=5)

        ctk.CTkSwitch(
            card_sec,
            text="Bloquear Modificación de Cuentas (No permite agregar ni borrar iCloud / correos)",
            variable=self.block_accounts_var,
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=20, pady=5)

        ctk.CTkSwitch(
            card_sec,
            text="Bloquear Siri y Dictado por voz (Evita navegación web indirecta mediante voz)",
            variable=self.block_siri_var,
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=20, pady=5)

        ctk.CTkSwitch(
            card_sec,
            text="Hacer Perfil NO Removible (se ignora si definís una contraseña abajo)",
            variable=self.non_removable_var,
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=20, pady=(5, 12))

        # CARD 4: CONTRASEÑA DE ADMINISTRADOR (OPCIONAL)
        card_pwd = ctk.CTkFrame(scroll_rules, fg_color="#1E293B", corner_radius=8)
        card_pwd.pack(fill="x", pady=6, padx=6)

        ctk.CTkLabel(
            card_pwd,
            text="🔑 Contraseña de Administrador (Opcional)",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#38BDF8"
        ).pack(anchor="w", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            card_pwd,
            text="Si la definís, el perfil se podrá quitar desde Ajustes SOLO con esta clave (y 'No Removible' se ignora).",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        ).pack(anchor="w", padx=16, pady=(0, 6))

        entry_pwd = ctk.CTkEntry(
            card_pwd,
            textvariable=self.removal_passcode_var,
            placeholder_text="Dejar vacío para bloqueo absoluto o escribir contraseña...",
            show="*",
            width=360
        )
        entry_pwd.pack(anchor="w", padx=16, pady=(0, 14))

    def on_web_filter_change(self, val):
        mapping = {
            "Bloqueo Total WebViews": "block_all",
            "Bloquear Dominios Específicos": "blacklist",
            "Solo Lista Blanca": "whitelist",
            "Sin Filtro Web": "none"
        }
        self.web_filter_mode_var.set(mapping.get(val, "block_all"))

    def on_dns_filter_change(self, val):
        mapping = {
            "CleanBrowsing Family (Recomendado)": "cleanbrowsing",
            "Cloudflare 1.1.1.3": "cloudflare",
            "NextDNS": "nextdns",
            "Ninguno": "none"
        }
        self.dns_filter_mode_var.set(mapping.get(val, "cleanbrowsing"))

    # =========================================================================
    # TAB 3: GENERAR Y APLICAR AL IPHONE
    # =========================================================================
    def build_export_tab(self):
        container = ctk.CTkFrame(self.tab_export, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=15)

        # PANEL IZQUIERDO: EXPORTAR ARCHIVO
        card_file = ctk.CTkFrame(container, fg_color="#1E293B", corner_radius=10)
        card_file.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=5)

        ctk.CTkLabel(
            card_file,
            text="💾 Opción 1: Guardar Perfil (.mobileconfig)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38BDF8"
        ).pack(anchor="w", padx=20, pady=(20, 8))

        ctk.CTkLabel(
            card_file,
            text="Genera el archivo estándar de Apple para cargarlo\npor USB con iMazing o Apple Configurator.\n\n"
                 "✓ Método recomendado: instalado desde la PC supervisora,\n  el perfil queda protegido contra borrado.\n"
                 "✓ Solo instala las apps marcadas en la pantalla.\n"
                 "✓ Funciona con el iPhone en Modo Supervisado.",
            font=ctk.CTkFont(size=13),
            text_color="#CBD5E1",
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 20))

        btn_save = ctk.CTkButton(
            card_file,
            text="💾 Guardar Archivo .mobileconfig...",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            fg_color="#0284C7",
            hover_color="#0369A1",
            command=self.save_profile_file
        )
        btn_save.pack(fill="x", padx=20, pady=10)

        btn_open_folder = ctk.CTkButton(
            card_file,
            text="📂 Abrir Carpeta de Guardado",
            height=34,
            fg_color="#334155",
            hover_color="#475569",
            command=self.open_export_dir
        )
        btn_open_folder.pack(fill="x", padx=20, pady=(5, 20))

        # PANEL DERECHO: SERVIDOR QR OTA
        card_qr = ctk.CTkFrame(container, fg_color="#1E293B", corner_radius=10)
        card_qr.pack(side="right", fill="both", expand=True, padx=(10, 0), pady=5)

        ctk.CTkLabel(
            card_qr,
            text="📲 Opción 2: Instalación por Código QR",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38BDF8"
        ).pack(anchor="w", padx=20, pady=(20, 8))

        ctk.CTkLabel(
            card_qr,
            text="Instala el perfil en el aire (OTA) sin cables:\n"
                 "1. Conecta el iPhone a la misma Wi-Fi que esta PC.\n"
                 "2. Escanea el código con la Cámara del iPhone.\n"
                 "3. Ve a Ajustes → Perfil descargado → Instalar.\n"
                 "⚠ Método menos seguro: un perfil bajado así podría poder quitarse.\n"
                 "   Usalo para probar; para dejarlo definitivo, instalá por cable.\n"
                 "   (Si el firewall de Windows pregunta, permití el acceso en red privada.)",
            font=ctk.CTkFont(size=12),
            text_color="#CBD5E1",
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 10))

        btn_qr = ctk.CTkButton(
            card_qr,
            text="📡 Generar Código QR de Instalación",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=38,
            fg_color="#10B981",
            hover_color="#059669",
            command=self.start_qr_server
        )
        btn_qr.pack(fill="x", padx=20, pady=(0, 12))

        # Contenedor para mostrar la imagen del QR
        self.qr_display_frame = ctk.CTkFrame(card_qr, fg_color="#0F172A", corner_radius=8, height=220)
        self.qr_display_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.qr_display_frame.pack_propagate(False)

        self.qr_image_label = ctk.CTkLabel(
            self.qr_display_frame,
            text="Presiona el botón para generar el QR",
            text_color="#64748B"
        )
        self.qr_image_label.pack(expand=True)

    def get_selected_bundle_ids(self):
        return [app_id for app_id, var in self.app_vars.items() if var.get()]

    def get_profile_kwargs(self):
        return {
            "profile_name": "KosherLock MDM - Perfil Kosher",
            "organization": "KosherLock / LockSuite",
            "allowed_bundle_ids": self.get_selected_bundle_ids(),
            "block_safari": self.block_safari_var.get(),
            "block_app_store": self.block_app_store_var.get(),
            "block_app_removal": self.block_app_removal_var.get(),
            "block_erase": self.block_erase_var.get(),
            "block_pairing": self.block_pairing_var.get(),
            "block_airdrop": self.block_airdrop_var.get(),
            "block_game_center": self.block_game_center_var.get(),
            "block_account_modification": self.block_accounts_var.get(),
            "block_passcode_modification": self.block_passcode_var.get(),
            "block_siri": self.block_siri_var.get(),
            "block_camera": self.block_camera_var.get(),
            "block_in_app_purchases": self.block_in_app_purchases_var.get(),
            "block_whatsapp_status_channels": self.block_wa_status_var.get(),
            "web_filter_mode": self.web_filter_mode_var.get(),
            "allowed_urls": [u.strip() for u in self.allowed_urls_var.get().split(",") if u.strip()],
            "custom_blocked_domains": [d.strip() for d in self.custom_blocked_domains_var.get().split(",") if d.strip()],
            "dns_filter_mode": self.dns_filter_mode_var.get(),
            "nextdns_id": self.nextdns_id_var.get(),
            "removal_passcode": self.removal_passcode_var.get(),
            "non_removable": self.non_removable_var.get()
        }

    def validate_before_export(self):
        """True si se puede seguir. Avisa de todo lo que dejaría el iPhone mal armado."""
        selected = [
            a for a in self.catalog_mgr.apps
            if a["id"] in self.app_vars and self.app_vars[a["id"]].get()
        ]
        if not selected:
            if not messagebox.askyesno(
                "Lista blanca vacía",
                "No tildaste ninguna app.\n\n"
                "Sin lista blanca el iPhone seguirá mostrando TODAS sus apps "
                "(solo se aplicarían los bloqueos de sistema).\n\n¿Continuar igual?"
            ):
                return False

        dudosas = [a for a in selected if not is_confirmed(a)]
        if dudosas:
            lista = "\n".join(f"  • {a['name']}  ({a['id']})" for a in dudosas[:12])
            if len(dudosas) > 12:
                lista += f"\n  … y {len(dudosas) - 12} más"
            if not messagebox.askyesno(
                "Bundle IDs sin confirmar",
                "Estas apps están tildadas pero su Bundle ID no está confirmado:\n\n"
                f"{lista}\n\n"
                "Si el ID está mal, esa app quedará OCULTA en el iPhone aunque esté "
                "instalada.\nConfirmá cada ID en iMazing → Apps (muestra el Bundle ID de "
                "cada app instalada) y agregala con '+ Agregar Otra App'.\n\n"
                "¿Generar el perfil igual?"
            ):
                return False
        return True

    def build_profile_bytes(self):
        """Valida y genera el perfil. Devuelve bytes o None (ya avisó al usuario)."""
        if not self.validate_before_export():
            return None
        try:
            return generate_mobileconfig(**self.get_profile_kwargs())
        except ProfileError as e:
            messagebox.showerror("Revisá la configuración", str(e))
            return None
        except Exception as e:
            messagebox.showerror("Error inesperado", f"No se pudo generar el perfil:\n{e}")
            return None

    def save_profile_file(self):
        data = self.build_profile_bytes()
        if data is None:
            return

        path = filedialog.asksaveasfilename(
            title="Guardar Perfil Kosher para iPhone",
            defaultextension=".mobileconfig",
            filetypes=[("Perfil de Configuración de Apple", "*.mobileconfig"), ("Todos los archivos", "*.*")],
            initialfile="KosherLock_iPhone.mobileconfig"
        )
        if not path:
            return

        try:
            with open(path, "wb") as f:
                f.write(data)
        except OSError as e:
            messagebox.showerror("Error al Guardar", f"No se pudo guardar el archivo:\n{e}")
            return

        self.last_saved_dir = os.path.dirname(path)
        self.status_bar.configure(text=f"Perfil guardado en: {path}")
        messagebox.showinfo(
            "Perfil creado",
            f"Se guardó en:\n\n{path}\n\n"
            "ANTES de instalarlo, mirá la pestaña '4. Guía': respaldá la identidad de "
            "supervisión de iMazing. Con el emparejamiento USB bloqueado, solo esa PC "
            "podrá volver a conectarse al iPhone."
        )

    def open_export_dir(self):
        export_dir = getattr(self, "last_saved_dir", os.getcwd())
        if os.path.isdir(export_dir):
            os.startfile(export_dir)

    def start_qr_server(self):
        data = self.build_profile_bytes()
        if data is None:
            return
        try:
            ok, url = self.server_mgr.start(data)
            if not ok:
                messagebox.showerror(
                    "Error de red",
                    f"No se pudo iniciar el servidor local:\n{url}\n\n"
                    "Puede ser que el puerto 8089 esté ocupado o que el firewall lo bloquee."
                )
                return

            pil_img = self.server_mgr.generate_qr_image(size=200)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(200, 200))
            self.qr_image_label.configure(image=ctk_img, text="")
            self.qr_image_label.image = ctk_img  # evita que Tk descarte la imagen
            self.status_bar.configure(text=f"Servidor activo en: {url} | Escaneá el código con el iPhone.")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error generando el código QR:\n{e}")

    # =========================================================================
    # TAB 4: GUÍA DE SUPERVISIÓN
    # =========================================================================
    def build_guide_tab(self):
        scroll_guide = ctk.CTkScrollableFrame(self.tab_guide, corner_radius=8, fg_color="transparent")
        scroll_guide.pack(fill="both", expand=True, padx=10, pady=10)

        header = ctk.CTkLabel(
            scroll_guide,
            text="📘 Guía: cómo preparar un iPhone Kosher (leer completa antes de empezar)",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#38BDF8"
        )
        header.pack(anchor="w", padx=10, pady=(10, 15))

        steps = [
            (
                "1. Qué hace este programa y qué NO hace",
                "Genera un perfil de Apple (.mobileconfig) que, en un iPhone SUPERVISADO, deja visibles "
                "solo las apps tildadas, oculta Safari y el App Store, bloquea el borrado de fábrica, "
                "la conexión USB con otras PCs, AirDrop, Siri y la creación de VPN.\n"
                "NO puede: quitar la pestaña Novedades (Estados/Canales) dentro de WhatsApp, ni filtrar el "
                "contenido de apps que abren sus propias pantallas web. Un iPhone no supervisado ignora "
                "casi todo este perfil sin avisar."
            ),
            (
                "2. Supervisar el iPhone (una sola vez) con iMazing",
                "a) Desactivá 'Buscar mi iPhone' y conectá el iPhone por USB.\n"
                "b) En iMazing elegí la opción de supervisar / preparar el dispositivo. Verificá en "
                "imazing.com qué licencia incluye esa función.\n"
                "c) El iPhone se borra por completo. Es normal y obligatorio: Apple no permite supervisar "
                "sin borrar.\n"
                "d) ⚠ CRÍTICO: exportá y guardá la identidad de supervisión (en iMazing, en la configuración "
                "de supervisión). Con el emparejamiento USB bloqueado, SOLO esa identidad permite volver a "
                "conectar el iPhone a una PC. Si la perdés no podrás cambiarle el perfil nunca más."
            ),
            (
                "3. Instalar las apps y confirmar sus Bundle IDs",
                "Instalá desde el App Store las apps que vas a permitir. Después, en iMazing → Apps, copiá el "
                "Bundle ID de las que aparezcan con '⚠ ID sin confirmar' en este programa y agregalas con "
                "'+ Agregar Otra App'. Un ID equivocado deja esa app oculta."
            ),
            (
                "4. Aplicar el perfil POR CABLE (recomendado)",
                "a) Pestaña 3 → 'Guardar Archivo .mobileconfig'.\n"
                "b) En iMazing, con el iPhone conectado, instalá el perfil (Perfiles → Instalar).\n"
                "El código QR sirve para probar rápido, pero un perfil instalado así puede no ser "
                "irremovible, y una vez oculto Safari no se puede volver a usar para actualizarlo."
            ),
            (
                "5. PROBAR en el iPhone antes de entregarlo",
                "☐ Safari y App Store no aparecen.\n"
                "☐ Ajustes → General → Transferir o restablecer: no se puede borrar.\n"
                "☐ Ajustes → General → VPN y gestión: el perfil no tiene botón de eliminar.\n"
                "☐ Conectarlo a otra PC: no debe pedir 'Confiar' ni mostrarse.\n"
                "☐ Cada app permitida abre. Si falta alguna, revisá su Bundle ID.\n"
                "☐ Tocar un enlace dentro de WhatsApp: no debe abrir un navegador."
            ),
            (
                "6. Evitar el formateo por Modo DFU",
                "Orden correcto: primero supervisar, después iniciar sesión con un iCloud de administración y "
                "activar 'Buscar mi iPhone', y recién entonces aplicar el perfil (que bloquea cambiar "
                "cuentas). Así, un formateo forzado por DFU deja el iPhone con Bloqueo de Activación pidiendo "
                "tu clave. Probalo con un iPhone de descarte antes de confiar en esto."
            ),
        ]

        for title, text in steps:
            card = ctk.CTkFrame(scroll_guide, fg_color="#1E293B", corner_radius=8)
            card.pack(fill="x", pady=6, padx=6)

            ctk.CTkLabel(
                card,
                text=title,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#F8FAFC"
            ).pack(anchor="w", padx=16, pady=(12, 4))

            ctk.CTkLabel(
                card,
                text=text,
                font=ctk.CTkFont(size=12),
                text_color="#CBD5E1",
                justify="left"
            ).pack(anchor="w", padx=16, pady=(0, 12))

    def on_close(self):
        self.server_mgr.stop()
        self.destroy()


def main():
    app = KosherLockApp()
    app.mainloop()


if __name__ == "__main__":
    main()
