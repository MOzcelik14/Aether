#!/usr/bin/env python3

import gi
import threading
import re
import time
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, Gdk

from ollama import OllamaClient
from database import Database
from config import Config


APP_ID = "com.murat.Aether"
DEFAULT_MODEL = "qwen3:8b"


AETHER_SYSTEM_PROMPT = (
    "Sen Aether'sın. "
    "Adın Aether'dır ve kullanıcıyla konuşan yapay zeka "
    "asistanısın. "
    "Kendinden bahsederken Aether adını kullan. "
    "Kullanıcı sana adını veya kimliğini sorarsa Aether olduğunu söyle. "
    "Teknik olarak hangi temel model kullanılıyor olursa olsun "
    "kullanıcıya karşı kimliğin Aether'dır. "
    "Kendini Qwen, Llama, Gemma, Phi veya başka bir temel model "
    "adıyla tanıtma. "
    "Yanıtlarını doğal, açık ve yardımcı şekilde ver."
)


RECOMMENDED_MODELS = [
    ("qwen3:8b", "Genel amaçlı • güçlü"),
    ("qwen3:4b", "Daha hafif • hızlı"),
    ("qwen3:1.7b", "Çok hafif • hızlı"),
    ("llama3.2:3b", "Genel amaçlı"),
    ("llama3.2:1b", "Hafif"),
    ("gemma3:4b", "Genel amaçlı"),
    ("gemma3:1b", "Hafif"),
    ("phi4-mini", "Kodlama • hafif"),
]


# ============================================================
# CODE BLOCK
# ============================================================

class CodeBlock(Gtk.Box):

    def __init__(self, code, language=""):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6
        )

        self.add_css_class("code-block")

        header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6
        )

        language_label = Gtk.Label(
            label=language or "CODE"
        )

        language_label.set_xalign(0)
        language_label.set_hexpand(True)
        language_label.add_css_class("code-language")

        header.append(language_label)

        copy_button = Gtk.Button(label="Kopyala")
        copy_button.add_css_class("flat")

        copy_button.connect(
            "clicked",
            self.copy_code,
            code
        )

        header.append(copy_button)
        self.append(header)

        code_label = Gtk.Label(label=code)

        code_label.set_xalign(0)
        code_label.set_wrap(True)
        code_label.set_selectable(True)
        code_label.set_hexpand(True)
        code_label.add_css_class("code-text")

        self.append(code_label)

    def copy_code(self, button, code):
        display = Gdk.Display.get_default()

        if display is None:
            return

        display.get_clipboard().set(code)

        button.set_label("Kopyalandı")

        GLib.timeout_add(
            1500,
            self.reset_copy_button,
            button
        )

    def reset_copy_button(self, button):
        button.set_label("Kopyala")
        return False


# ============================================================
# MESSAGE BUBBLE
# ============================================================

class MessageBubble(Gtk.Box):

    def __init__(self, role, text=""):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8
        )

        self.role = role
        self.text = text

        self.set_hexpand(True)

        if role == "user":
            self.add_css_class("user-message")
            title = "SEN"
        else:
            self.add_css_class("assistant-message")
            title = "AETHER"

        header = Gtk.Label(label=title)
        header.set_xalign(0)
        header.add_css_class("message-role")

        self.append(header)

        self.content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6
        )

        self.content_box.set_hexpand(True)
        self.append(self.content_box)

        self.render(text)

    def set_text(self, text):
        self.text = text
        self.render(text)

    def clear_content(self):
        while True:
            child = self.content_box.get_first_child()

            if child is None:
                break

            self.content_box.remove(child)

    def render(self, text):
        self.clear_content()

        if not text:
            label = Gtk.Label(label="...")
            label.set_xalign(0)
            self.content_box.append(label)
            return

        if self.role == "user":
            label = Gtk.Label(label=text)
            label.set_xalign(0)
            label.set_wrap(True)
            label.set_selectable(True)
            label.set_hexpand(True)

            self.content_box.append(label)
            return

        self.render_markdown(text)

    def render_markdown(self, text):
        pattern = r"```([^\n]*)\n?(.*?)```"

        parts = re.split(
            pattern,
            text,
            flags=re.DOTALL
        )

        index = 0

        while index < len(parts):
            normal_text = parts[index]

            if normal_text.strip():
                self.render_markdown_text(normal_text)

            if index + 2 < len(parts):
                language = parts[index + 1].strip()
                code = parts[index + 2].strip()

                self.content_box.append(
                    CodeBlock(code, language)
                )

            index += 3

    def render_markdown_text(self, text):
        for line in text.splitlines():
            stripped = line.strip()

            if not stripped:
                spacer = Gtk.Box()
                spacer.set_size_request(-1, 5)
                self.content_box.append(spacer)
                continue

            if stripped.startswith("### "):
                self.append_markdown_label(
                    stripped[4:],
                    "markdown-h3"
                )
                continue

            if stripped.startswith("## "):
                self.append_markdown_label(
                    stripped[3:],
                    "markdown-h2"
                )
                continue

            if stripped.startswith("# "):
                self.append_markdown_label(
                    stripped[2:],
                    "markdown-h1"
                )
                continue

            if stripped.startswith("- ") or stripped.startswith("* "):
                self.append_markdown_label(
                    "• " + stripped[2:]
                )
                continue

            numbered = re.match(
                r"^(\d+)\.\s+(.*)$",
                stripped
            )

            if numbered:
                self.append_markdown_label(
                    f"{numbered.group(1)}. "
                    f"{numbered.group(2)}"
                )
                continue

            if stripped.startswith("> "):
                label = self.create_markup_label(
                    "❯ " + stripped[2:]
                )

                label.add_css_class("markdown-quote")
                self.content_box.append(label)
                continue

            self.append_markdown_label(stripped)

    def append_markdown_label(self, text, css_class=None):
        label = self.create_markup_label(text)

        if css_class:
            label.add_css_class(css_class)

        self.content_box.append(label)

    def create_markup_label(self, text):
        label = Gtk.Label()

        label.set_xalign(0)
        label.set_wrap(True)
        label.set_selectable(True)
        label.set_hexpand(True)

        try:
            label.set_markup(
                self.inline_markup(text)
            )
        except Exception:
            label.set_text(text)

        return label

    def inline_markup(self, text):
        text = (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        text = re.sub(
            r"`([^`]+)`",
            (
                r'<span font_family="monospace" '
                r'foreground="#d99a4e">\1</span>'
            ),
            text
        )

        text = re.sub(
            r"\*\*(.+?)\*\*",
            r"<b>\1</b>",
            text
        )

        text = re.sub(
            r"(?<!\*)\*([^*]+)\*(?!\*)",
            r"<i>\1</i>",
            text
        )

        return text


# ============================================================
# SETTINGS
# ============================================================

class SettingsWindow(Adw.PreferencesWindow):

    def __init__(self, parent):
        super().__init__(
            transient_for=parent,
            modal=True,
            title="Ayarlar"
        )

        self.parent_window = parent

        self.set_default_size(650, 600)

        self.build_ui()

    def build_ui(self):

        model_page = Adw.PreferencesPage(
            title="Model",
            icon_name="system-run-symbolic"
        )

        self.add(model_page)

        model_group = Adw.PreferencesGroup(
            title="Model Ayarları",
            description="Yanıt üretimini yapılandır."
        )

        model_page.add(model_group)

        self.thinking_row = Adw.SwitchRow(
            title="Thinking",
            subtitle=(
                "Destekleyen modellerde düşünme "
                "modunu etkinleştir."
            )
        )

        self.thinking_row.set_active(
            self.parent_window.thinking
        )

        self.thinking_row.connect(
            "notify::active",
            self.on_thinking_changed
        )

        model_group.add(self.thinking_row)

        context_adjustment = Gtk.Adjustment.new(
            self.parent_window.context,
            1024,
            131072,
            1024,
            4096,
            0
        )

        self.context_row = Adw.SpinRow(
            title="Context",
            subtitle=(
                "Modelin kullanacağı maksimum "
                "bağlam uzunluğu."
            ),
            adjustment=context_adjustment
        )

        self.context_row.set_value(
            self.parent_window.context
        )

        self.context_row.connect(
            "notify::value",
            self.on_context_changed
        )

        model_group.add(self.context_row)

        temperature_adjustment = Gtk.Adjustment.new(
            self.parent_window.temperature,
            0.0,
            2.0,
            0.1,
            0.5,
            0
        )

        self.temperature_row = Adw.SpinRow(
            title="Temperature",
            subtitle="Yanıtların rastgelelik seviyesi.",
            adjustment=temperature_adjustment
        )

        self.temperature_row.set_digits(1)

        self.temperature_row.connect(
            "notify::value",
            self.on_temperature_changed
        )

        model_group.add(self.temperature_row)

        chat_page = Adw.PreferencesPage(
            title="Sohbet",
            icon_name="user-available-symbolic"
        )

        self.add(chat_page)

        chat_group = Adw.PreferencesGroup(
            title="Mesaj Girişi"
        )

        chat_page.add(chat_group)

        self.enter_row = Adw.SwitchRow(
            title="Enter ile gönder",
            subtitle="Kapalıysa Enter yeni satır ekler."
        )

        self.enter_row.set_active(
            self.parent_window.enter_to_send
        )

        self.enter_row.connect(
            "notify::active",
            self.on_enter_changed
        )

        chat_group.add(self.enter_row)

        connection_page = Adw.PreferencesPage(
            title="Bağlantı",
            icon_name="network-server-symbolic"
        )

        self.add(connection_page)

        connection_group = Adw.PreferencesGroup(
            title="Ollama",
            description="Ollama sunucusunun adresi."
        )

        connection_page.add(connection_group)

        self.url_row = Adw.EntryRow(
            title="Ollama adresi"
        )

        self.url_row.set_text(
            self.parent_window.client.base_url
        )

        connection_group.add(self.url_row)

        apply_button = Gtk.Button(
            label="Adresi Uygula"
        )

        apply_button.add_css_class(
            "suggested-action"
        )

        apply_button.connect(
            "clicked",
            self.apply_url
        )

        connection_group.add(apply_button)

        app_page = Adw.PreferencesPage(
            title="Uygulama",
            icon_name="applications-system-symbolic"
        )

        self.add(app_page)

        app_group = Adw.PreferencesGroup(
            title="Genel"
        )

        app_page.add(app_group)

        self.theme_row = Adw.ComboRow(
            title="Tema",
            subtitle="Uygulama görünümünü seç."
        )

        self.theme_row.set_model(
            Gtk.StringList.new([
                "Sistem",
                "Açık",
                "Koyu"
            ])
        )

        theme_index = {
            "system": 0,
            "light": 1,
            "dark": 2
        }.get(
            self.parent_window.theme,
            2
        )

        self.theme_row.set_selected(theme_index)

        self.theme_row.connect(
            "notify::selected",
            self.on_theme_changed
        )

        app_group.add(self.theme_row)

        about_page = Adw.PreferencesPage(
            title="Hakkında",
            icon_name="help-about-symbolic"
        )

        self.add(about_page)

        about_group = Adw.PreferencesGroup(
            title="Aether"
        )

        about_page.add(about_group)

        about_row = Adw.ActionRow(
            title="Aether",
            subtitle="Ollama için yerel masaüstü istemcisi"
        )

        about_group.add(about_row)

    def on_thinking_changed(self, row, param):
        value = row.get_active()
        self.parent_window.thinking = value
        self.parent_window.config.set("thinking", value)

    def on_context_changed(self, row, param):
        value = int(row.get_value())
        self.parent_window.context = value
        self.parent_window.config.set("context", value)

    def on_temperature_changed(self, row, param):
        value = row.get_value()
        self.parent_window.temperature = value
        self.parent_window.config.set("temperature", value)

    def on_enter_changed(self, row, param):
        value = row.get_active()
        self.parent_window.enter_to_send = value
        self.parent_window.config.set("enter_to_send", value)

    def on_theme_changed(self, row, param):

        selected = row.get_selected()

        if selected == 0:
            scheme = Adw.ColorScheme.DEFAULT
            theme = "system"
        elif selected == 1:
            scheme = Adw.ColorScheme.FORCE_LIGHT
            theme = "light"
        else:
            scheme = Adw.ColorScheme.FORCE_DARK
            theme = "dark"

        Adw.StyleManager.get_default().set_color_scheme(
            scheme
        )

        self.parent_window.theme = theme
        self.parent_window.config.set("theme", theme)

    def apply_url(self, button):

        url = self.url_row.get_text().strip()

        if not url:
            return

        url = url.rstrip("/")

        self.parent_window.client.base_url = url

        self.parent_window.config.set(
            "ollama_url",
            url
        )

        self.parent_window.check_ollama()


# ============================================================
# RENAME CHAT
# ============================================================

class RenameChatWindow(Gtk.Window):

    def __init__(self, parent, chat_id, current_title):

        super().__init__(
            transient_for=parent,
            modal=True,
            title="Sohbeti Yeniden Adlandır"
        )

        self.parent_window = parent
        self.chat_id = chat_id

        self.set_default_size(430, 180)

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12
        )

        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)

        self.set_child(box)

        label = Gtk.Label(label="Sohbet adı")
        label.set_xalign(0)
        box.append(label)

        self.entry = Gtk.Entry()

        self.entry.set_text(current_title)
        self.entry.set_hexpand(True)

        box.append(self.entry)

        buttons = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8
        )

        buttons.set_halign(Gtk.Align.END)

        cancel = Gtk.Button(label="İptal")

        cancel.connect(
            "clicked",
            lambda _button: self.close()
        )

        buttons.append(cancel)

        save = Gtk.Button(label="Kaydet")

        save.add_css_class("suggested-action")
        save.connect("clicked", self.save)

        buttons.append(save)

        box.append(buttons)

        self.entry.connect(
            "activate",
            self.save
        )

    def save(self, widget):

        title = self.entry.get_text().strip()

        if not title:
            return

        self.parent_window.database.update_chat_title(
            self.chat_id,
            title
        )

        self.parent_window.update_history_row(
            self.chat_id,
            title
        )

        if self.parent_window.current_chat_id == self.chat_id:
            self.parent_window.chat_title.set_text(title)

        self.close()


# ============================================================
# MODEL PULL WINDOW
# ============================================================

class ModelPullWindow(Gtk.Window):

    def __init__(self, parent):

        super().__init__(
            transient_for=parent,
            modal=True,
            title="Model İndir"
        )

        self.parent_window = parent
        self.running = False
        self.stop_event = threading.Event()
        self.recommended_rows = []

        self.set_default_size(620, 620)

        root = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12
        )

        root.set_margin_top(20)
        root.set_margin_bottom(20)
        root.set_margin_start(20)
        root.set_margin_end(20)

        self.set_child(root)

        title = Gtk.Label(label="Model İndir")
        title.set_xalign(0)
        title.add_css_class("heading")

        root.append(title)

        subtitle = Gtk.Label(
            label=(
                "Bir Ollama model etiketi gir veya "
                "önerilen modellerden birini seç."
            )
        )

        subtitle.set_xalign(0)
        subtitle.set_wrap(True)

        root.append(subtitle)

        self.search = Gtk.SearchEntry()

        self.search.set_placeholder_text(
            "Model ara veya model adı yaz..."
        )

        self.search.connect(
            "search-changed",
            self.filter_recommended
        )

        root.append(self.search)

        self.entry = Gtk.Entry()

        self.entry.set_placeholder_text(
            "örn. qwen3:8b"
        )

        self.entry.set_hexpand(True)

        root.append(self.entry)

        recommended_title = Gtk.Label(
            label="ÖNERİLEN MODELLER"
        )

        recommended_title.set_xalign(0)
        recommended_title.add_css_class("section-title")

        root.append(recommended_title)

        recommended_scroll = Gtk.ScrolledWindow()

        recommended_scroll.set_min_content_height(230)
        recommended_scroll.set_vexpand(True)

        root.append(recommended_scroll)

        self.recommended_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4
        )

        recommended_scroll.set_child(
            self.recommended_box
        )

        self.build_recommended_models()

        self.status = Gtk.Label(label="Hazır")

        self.status.set_xalign(0)
        self.status.set_wrap(True)

        root.append(self.status)

        self.progress = Gtk.ProgressBar()

        self.progress.set_show_text(True)
        self.progress.set_fraction(0.0)

        root.append(self.progress)

        buttons = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8
        )

        buttons.set_halign(Gtk.Align.END)

        self.cancel_button = Gtk.Button(label="Kapat")

        self.cancel_button.connect(
            "clicked",
            self.on_close
        )

        buttons.append(self.cancel_button)

        self.download_button = Gtk.Button(label="İndir")

        self.download_button.add_css_class(
            "suggested-action"
        )

        self.download_button.connect(
            "clicked",
            self.start_download
        )

        buttons.append(self.download_button)

        root.append(buttons)

        self.entry.connect(
            "activate",
            self.start_download
        )

        self.connect(
            "close-request",
            self.on_window_close
        )

    def build_recommended_models(self):

        self.recommended_rows.clear()

        while True:
            child = self.recommended_box.get_first_child()

            if child is None:
                break

            self.recommended_box.remove(child)

        for model_name, description in RECOMMENDED_MODELS:

            row = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL,
                spacing=8
            )

            row.add_css_class(
                "model-recommendation"
            )

            text_box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=2
            )

            text_box.set_hexpand(True)

            name = Gtk.Label(label=model_name)
            name.set_xalign(0)
            name.add_css_class("model-name")

            text_box.append(name)

            desc = Gtk.Label(label=description)

            desc.set_xalign(0)
            desc.add_css_class("dim-label")

            text_box.append(desc)

            row.append(text_box)

            select = Gtk.Button(label="Seç")
            select.add_css_class("flat")

            select.connect(
                "clicked",
                self.select_recommended,
                model_name
            )

            row.append(select)

            self.recommended_box.append(row)

            self.recommended_rows.append({
                "row": row,
                "name": model_name,
                "description": description
            })

    def select_recommended(self, button, model_name):

        self.entry.set_text(model_name)
        self.search.set_text(model_name)
        self.entry.grab_focus()

    def filter_recommended(self, entry):

        query = entry.get_text().strip().lower()

        for item in self.recommended_rows:

            visible = (
                not query
                or query in item["name"].lower()
                or query in item["description"].lower()
            )

            item["row"].set_visible(visible)

        if query:

            exact = next(
                (
                    item[0]
                    for item in RECOMMENDED_MODELS
                    if item[0].lower() == query
                ),
                None
            )

            if exact:
                self.entry.set_text(exact)

    def start_download(self, widget):

        if self.running:
            return

        model = self.entry.get_text().strip()

        if not model:

            self.status.set_text(
                "Bir model adı gir."
            )

            self.entry.grab_focus()
            return

        self.running = True
        self.stop_event.clear()

        self.entry.set_sensitive(False)
        self.search.set_sensitive(False)
        self.download_button.set_sensitive(False)

        self.cancel_button.set_label("İptal")

        self.progress.set_fraction(0.0)
        self.progress.set_text("0%")

        self.status.set_text(
            f"{model} indiriliyor..."
        )

        def worker():

            def callback(
                status,
                completed,
                total,
                done,
                data
            ):

                GLib.idle_add(
                    self.update_progress,
                    model,
                    status,
                    completed,
                    total,
                    done,
                    data
                )

            self.parent_window.client.pull_model(
                model,
                callback,
                self.stop_event
            )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def update_progress(
        self,
        model,
        status,
        completed,
        total,
        done,
        data
    ):

        if self.stop_event.is_set():

            self.running = False

            self.entry.set_sensitive(True)
            self.search.set_sensitive(True)
            self.download_button.set_sensitive(True)

            self.cancel_button.set_label("Kapat")

            self.status.set_text(
                "İndirme iptal edildi."
            )

            return False

        status_text = str(status or "")

        error_status = (
            status_text.lower().startswith("error")
            or "http " in status_text.lower()
            or "hata" in status_text.lower()
            or "bağlantı" in status_text.lower()
        )

        if total > 0:

            fraction = completed / total

            fraction = max(
                0.0,
                min(1.0, fraction)
            )

            self.progress.set_fraction(fraction)
            self.progress.set_text(
                f"{fraction * 100:.1f}%"
            )

        else:
            self.progress.pulse()

        if status_text:
            self.status.set_text(status_text)

        if done:

            self.running = False

            self.entry.set_sensitive(True)
            self.search.set_sensitive(True)
            self.download_button.set_sensitive(True)

            self.cancel_button.set_label("Kapat")

            if error_status:

                self.status.set_text(status_text)
                return False

            self.progress.set_fraction(1.0)
            self.progress.set_text("Tamamlandı")

            self.status.set_text(
                f"{model} başarıyla indirildi."
            )

            self.parent_window.refresh_models(None)

            self.parent_window.selected_model = model

            self.parent_window.config.set(
                "selected_model",
                model
            )

            return False

        return False

    def on_close(self, button):

        if self.running:

            self.stop_event.set()

            self.status.set_text(
                "İndirme durduruluyor..."
            )

            return

        self.close()

    def on_window_close(self, window):

        if self.running:

            self.stop_event.set()

            self.status.set_text(
                "İndirme durduruluyor..."
            )

            return True

        return False


# ============================================================
# MAIN WINDOW
# ============================================================

class LocalAIWindow(Adw.ApplicationWindow):

    def __init__(self, app):

        super().__init__(
            application=app
        )

        self.set_title("Aether")
        self.set_default_size(1150, 780)
        self.set_resizable(True)

        # ====================================================
        # CONFIG
        # ====================================================

        self.config = Config()

        self.thinking = bool(
            self.config.get("thinking")
        )

        self.context = int(
            self.config.get("context")
        )

        self.temperature = float(
            self.config.get("temperature")
        )

        self.enter_to_send = bool(
            self.config.get("enter_to_send")
        )

        self.theme = self.config.get("theme")

        self.selected_model = (
            self.config.get("selected_model")
            or DEFAULT_MODEL
        )

        ollama_url = self.config.get(
            "ollama_url"
        )

        self.client = OllamaClient(
            base_url=ollama_url
        )

        self.database = Database()

        self.messages = []
        self.current_chat_id = None

        self.generating = False
        self.stop_event = None
        self.generation_started = 0.0

        self.last_stats = {
            "elapsed": 0.0,
            "prompt_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "prompt_speed": 0.0,
            "generation_speed": 0.0
        }

        self.chat_rows = {}
        self.model_data = []

        self.settings_window = None
        self.rename_window = None
        self.pull_window = None

        self.search_text = ""

        self.apply_theme()
        self.load_css()
        self.build_ui()
        self.load_chat_history()
        self.check_ollama()

    # ========================================================
    # THEME
    # ========================================================

    def apply_theme(self):

        manager = Adw.StyleManager.get_default()

        if self.theme == "light":

            manager.set_color_scheme(
                Adw.ColorScheme.FORCE_LIGHT
            )

        elif self.theme == "dark":

            manager.set_color_scheme(
                Adw.ColorScheme.FORCE_DARK
            )

        else:

            manager.set_color_scheme(
                Adw.ColorScheme.DEFAULT
            )

    # ========================================================
    # CSS
    # ========================================================

    def load_css(self):

        css = Gtk.CssProvider()

        css_path = (
            Path(__file__).resolve().parent
            / "style.css"
        )

        try:

            css.load_from_path(
                str(css_path)
            )

        except Exception as error:

            print(
                f"CSS yüklenemedi: {error}"
            )

            return

        display = Gdk.Display.get_default()

        if display is None:
            return

        Gtk.StyleContext.add_provider_for_display(
            display,
            css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # ========================================================
    # UI
    # ========================================================

    def build_ui(self):

        # ====================================================
        # AETHER WINDOW STRUCTURE
        #
        # ÖNEMLİ:
        # Adw.ApplicationWindow'da set_titlebar() KULLANMIYORUZ.
        #
        # Doğru yapı:
        #
        # Adw.ApplicationWindow
        #   └── Adw.ToolbarView
        #        ├── Adw.HeaderBar
        #        └── content
        #
        # Libadwaita'nın önerdiği yapı budur.
        # ====================================================

        toolbar_view = Adw.ToolbarView()

        self.set_content(
            toolbar_view
        )

        # ====================================================
        # GERÇEK WINDOW HEADER BAR
        # ====================================================

        titlebar = Adw.HeaderBar()

        titlebar.set_show_start_title_buttons(True)
        titlebar.set_show_end_title_buttons(True)

        # Sistem pencere düğmelerinin yerleşimini açıkça belirle.
        #
        # GNOME:
        # minimize / maximize / close
        #
        # Cinnamon / diğer WM:
        # WM'nin desteklediği düğmeler gösterilir.
        #
        titlebar.set_decoration_layout(
            "icon:minimize,maximize,close"
        )

        title_widget = Gtk.Label(
            label="Aether"
        )

        title_widget.add_css_class(
            "window-title"
        )

        titlebar.set_title_widget(
            title_widget
        )

        toolbar_view.add_top_bar(
            titlebar
        )

        # ====================================================
        # MAIN BOX
        # ====================================================

        main_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL
        )

        main_box.set_hexpand(True)
        main_box.set_vexpand(True)

        toolbar_view.set_content(
            main_box
        )

        # ====================================================
        # SIDEBAR
        # ====================================================

        sidebar = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10
        )

        sidebar.set_size_request(
            270,
            -1
        )

        sidebar.set_margin_top(16)
        sidebar.set_margin_bottom(16)
        sidebar.set_margin_start(16)
        sidebar.set_margin_end(10)

        sidebar.add_css_class("sidebar")

        main_box.append(sidebar)

        title = Gtk.Label(
            label="AETHER"
        )

        title.set_xalign(0)
        title.add_css_class("app-title")

        sidebar.append(title)

        new_chat_button = Gtk.Button(
            label="+  Yeni Sohbet"
        )

        new_chat_button.add_css_class(
            "suggested-action"
        )

        new_chat_button.connect(
            "clicked",
            self.new_chat
        )

        sidebar.append(new_chat_button)

        sidebar.append(Gtk.Separator())

        history_title = Gtk.Label(
            label="SOHBETLER"
        )

        history_title.set_xalign(0)
        history_title.add_css_class("section-title")

        sidebar.append(history_title)

        self.search_entry = Gtk.SearchEntry()

        self.search_entry.set_placeholder_text(
            "Sohbetlerde ara..."
        )

        self.search_entry.connect(
            "search-changed",
            self.on_search_changed
        )

        sidebar.append(self.search_entry)

        history_scroll = Gtk.ScrolledWindow()

        history_scroll.set_vexpand(True)
        history_scroll.set_min_content_height(120)

        sidebar.append(history_scroll)

        self.history_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4
        )

        history_scroll.set_child(
            self.history_box
        )

        model_title = Gtk.Label(
            label="MODEL"
        )

        model_title.set_xalign(0)
        model_title.add_css_class("section-title")

        sidebar.append(model_title)

        model_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6
        )

        self.model_dropdown = (
            Gtk.DropDown.new_from_strings(
                [self.selected_model]
            )
        )

        self.model_dropdown.set_hexpand(True)

        self.model_dropdown.connect(
            "notify::selected-item",
            self.on_model_changed
        )

        model_row.append(
            self.model_dropdown
        )

        refresh_models = Gtk.Button(
            label="↻"
        )

        refresh_models.set_tooltip_text(
            "Modelleri yenile"
        )

        refresh_models.connect(
            "clicked",
            self.refresh_models
        )

        model_row.append(refresh_models)

        sidebar.append(model_row)

        self.model_info = Gtk.Label(
            label="Model bilgisi..."
        )

        self.model_info.set_xalign(0)
        self.model_info.set_wrap(True)

        self.model_info.add_css_class("dim-label")
        self.model_info.add_css_class("model-info")

        sidebar.append(self.model_info)

        download_button = Gtk.Button(
            label="＋  Model İndir"
        )

        download_button.connect(
            "clicked",
            self.open_model_pull
        )

        sidebar.append(download_button)

        bottom_spacer = Gtk.Box()
        bottom_spacer.set_vexpand(True)

        sidebar.append(bottom_spacer)

        settings_button = Gtk.Button(
            label="⚙  Ayarlar"
        )

        settings_button.connect(
            "clicked",
            self.open_settings
        )

        sidebar.append(settings_button)

        self.status_label = Gtk.Label(
            label="● Ollama kontrol ediliyor..."
        )

        self.status_label.set_xalign(0)
        self.status_label.add_css_class("dim-label")

        sidebar.append(self.status_label)

        # ====================================================
        # CHAT AREA
        # ====================================================

        chat_area = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL
        )

        chat_area.set_hexpand(True)
        chat_area.set_vexpand(True)

        main_box.append(chat_area)

        header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10
        )

        header.set_margin_top(16)
        header.set_margin_bottom(12)
        header.set_margin_start(20)
        header.set_margin_end(20)

        chat_area.append(header)

        self.chat_title = Gtk.Label(
            label="Yeni Sohbet"
        )

        self.chat_title.set_xalign(0)
        self.chat_title.set_hexpand(True)
        self.chat_title.add_css_class("chat-title")

        header.append(self.chat_title)

        self.stats_button = Gtk.Button(
            label="Hazır"
        )

        self.stats_button.add_css_class("flat")

        self.stats_button.set_tooltip_text(
            "Performans istatistiklerini göster"
        )

        self.stats_button.connect(
            "clicked",
            self.show_stats
        )

        header.append(self.stats_button)

        self.scroll = Gtk.ScrolledWindow()

        self.scroll.set_hexpand(True)
        self.scroll.set_vexpand(True)

        chat_area.append(self.scroll)

        self.messages_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10
        )

        self.messages_box.set_margin_top(16)
        self.messages_box.set_margin_bottom(16)
        self.messages_box.set_margin_start(30)
        self.messages_box.set_margin_end(30)

        self.scroll.set_child(
            self.messages_box
        )

        self.show_welcome()

        # ====================================================
        # INPUT
        # ====================================================

        input_area = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8
        )

        input_area.set_margin_top(10)
        input_area.set_margin_bottom(16)
        input_area.set_margin_start(20)
        input_area.set_margin_end(20)

        chat_area.append(input_area)

        self.entry_scroll = Gtk.ScrolledWindow()

        self.entry_scroll.set_hexpand(True)
        self.entry_scroll.set_min_content_height(44)
        self.entry_scroll.set_max_content_height(150)

        self.entry_scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC
        )

        input_area.append(self.entry_scroll)

        self.entry = Gtk.TextView()

        self.entry.set_wrap_mode(
            Gtk.WrapMode.WORD_CHAR
        )

        self.entry.set_hexpand(True)

        self.entry.set_top_margin(10)
        self.entry.set_bottom_margin(10)
        self.entry.set_left_margin(12)
        self.entry.set_right_margin(12)

        self.entry.add_css_class("chat-input")

        self.entry_scroll.set_child(
            self.entry
        )

        key_controller = Gtk.EventControllerKey()

        key_controller.connect(
            "key-pressed",
            self.on_input_key_pressed
        )

        self.entry.add_controller(
            key_controller
        )

        self.send_button = Gtk.Button(
            label="➤"
        )

        self.send_button.set_tooltip_text(
            "Gönder"
        )

        self.send_button.add_css_class(
            "suggested-action"
        )

        self.send_button.connect(
            "clicked",
            self.send_message
        )

        input_area.append(self.send_button)

        self.stop_button = Gtk.Button(
            label="■"
        )

        self.stop_button.set_tooltip_text(
            "Üretimi durdur"
        )

        self.stop_button.set_sensitive(False)

        self.stop_button.connect(
            "clicked",
            self.stop_generation
        )

        input_area.append(self.stop_button)

    # ========================================================
    # SETTINGS
    # ========================================================

    def open_settings(self, button):

        if self.settings_window is not None:

            if self.settings_window.get_visible():

                self.settings_window.present()
                return

        self.settings_window = SettingsWindow(self)

        self.settings_window.connect(
            "close-request",
            self.on_settings_closed
        )

        self.settings_window.present()

    def on_settings_closed(self, window):

        self.settings_window = None

        return False

    # ========================================================
    # MODEL PULL
    # ========================================================

    def open_model_pull(self, button):

        if self.generating:
            return

        if self.pull_window is not None:

            if self.pull_window.get_visible():

                self.pull_window.present()
                return

        self.pull_window = ModelPullWindow(self)

        self.pull_window.connect(
            "close-request",
            self.on_pull_closed
        )

        self.pull_window.present()

    def on_pull_closed(self, window):

        self.pull_window = None

        return False

    # ========================================================
    # INPUT
    # ========================================================

    def on_input_key_pressed(
        self,
        controller,
        keyval,
        keycode,
        state
    ):

        shift_pressed = bool(
            state & Gdk.ModifierType.SHIFT_MASK
        )

        if (
            keyval == Gdk.KEY_Return
            and shift_pressed
        ):
            return False

        if (
            keyval == Gdk.KEY_Return
            and self.enter_to_send
        ):

            if not self.generating:
                self.send_message(self.entry)

            return True

        return False

    def get_input_text(self):

        buffer = self.entry.get_buffer()

        start = buffer.get_start_iter()
        end = buffer.get_end_iter()

        return buffer.get_text(
            start,
            end,
            False
        )

    def clear_input(self):

        self.entry.get_buffer().set_text(
            "",
            0
        )

    # ========================================================
    # SEARCH
    # ========================================================

    def on_search_changed(self, entry):

        self.search_text = (
            entry.get_text()
            .strip()
            .lower()
        )

        self.filter_history()

    def filter_history(self):

        for data in self.chat_rows.values():

            title = data["title"]

            visible = (
                not self.search_text
                or self.search_text in title.lower()
            )

            data["row"].set_visible(visible)

    # ========================================================
    # MODELS
    # ========================================================

    def get_model(self):

        item = (
            self.model_dropdown
            .get_selected_item()
        )

        if item:
            return item.get_string()

        return (
            self.selected_model
            or DEFAULT_MODEL
        )

    def refresh_models(self, button):

        if self.generating:
            return

        self.status_label.set_text(
            "● Modeller yenileniyor..."
        )

        def worker():

            try:

                models = self.client.get_models()

                GLib.idle_add(
                    self.update_models,
                    models
                )

            except Exception as error:

                GLib.idle_add(
                    self.ollama_error,
                    str(error)
                )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def update_models(self, models):

        self.model_data = models

        names = [
            model.get("name", "")
            for model in models
            if model.get("name")
        ]

        if not names:
            names = [
                self.selected_model
                or DEFAULT_MODEL
            ]

        if self.selected_model in names:

            preferred = names.index(
                self.selected_model
            )

        elif DEFAULT_MODEL in names:

            preferred = names.index(
                DEFAULT_MODEL
            )

        else:

            preferred = 0

        self.model_dropdown.set_model(
            Gtk.StringList.new(names)
        )

        self.model_dropdown.set_selected(
            preferred
        )

        self.selected_model = names[preferred]

        self.config.set(
            "selected_model",
            self.selected_model
        )

        self.status_label.set_text(
            f"● Ollama bağlı • {len(models)} model"
        )

        self.update_model_info()

        return False

    def on_model_changed(self, dropdown, param):

        model = self.get_model()

        self.selected_model = model

        self.config.set(
            "selected_model",
            model
        )

        self.update_model_info()

    def update_model_info(self):

        model_name = self.get_model()

        model = None

        for item in self.model_data:

            if item.get("name") == model_name:

                model = item
                break

        if model is None:

            self.model_info.set_text(model_name)
            return

        size = model.get("size", 0)

        if size:

            size_text = (
                f"{size / (1024 ** 3):.2f} GB"
            )

        else:

            size_text = "Bilinmiyor"

        details = model.get("details", {})

        info = model_name

        parameter_size = details.get(
            "parameter_size",
            ""
        )

        quantization = details.get(
            "quantization_level",
            ""
        )

        family = details.get(
            "family",
            ""
        )

        if parameter_size:
            info += f"\nParametre: {parameter_size}"

        if quantization:
            info += f"\nQuantization: {quantization}"

        if family:
            info += f"\nAile: {family}"

        info += f"\nBoyut: {size_text}"

        self.model_info.set_text(info)

    # ========================================================
    # STATS
    # ========================================================

    def show_stats(self, button):

        stats = self.last_stats

        dialog = Gtk.Window(
            transient_for=self,
            modal=True,
            title="Performans"
        )

        dialog.set_default_size(420, 300)

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12
        )

        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)

        dialog.set_child(box)

        title = Gtk.Label(label="PERFORMANS")

        title.set_xalign(0)
        title.add_css_class("section-title")

        box.append(title)

        rows = [
            ("Model", self.get_model()),
            ("Süre", f"{stats['elapsed']:.2f} saniye"),
            ("Prompt token", str(stats["prompt_tokens"])),
            ("Çıktı token", str(stats["output_tokens"])),
            ("Toplam token", str(stats["total_tokens"])),
            ("Prompt hızı", f"{stats['prompt_speed']:.1f} tok/s"),
            ("Üretim hızı", f"{stats['generation_speed']:.1f} tok/s")
        ]

        for name, value in rows:

            row = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL,
                spacing=10
            )

            label = Gtk.Label(label=name)

            label.set_xalign(0)
            label.set_hexpand(True)

            value_label = Gtk.Label(label=value)
            value_label.set_xalign(1)

            row.append(label)
            row.append(value_label)

            box.append(row)

        close_button = Gtk.Button(label="Kapat")

        close_button.connect(
            "clicked",
            lambda _button: dialog.close()
        )

        box.append(close_button)

        dialog.present()

    def update_stats(self, data):

        elapsed = (
            time.monotonic()
            - self.generation_started
        )

        prompt_tokens = int(
            data.get(
                "prompt_eval_count",
                0
            ) or 0
        )

        output_tokens = int(
            data.get(
                "eval_count",
                0
            ) or 0
        )

        prompt_duration = int(
            data.get(
                "prompt_eval_duration",
                0
            ) or 0
        )

        eval_duration = int(
            data.get(
                "eval_duration",
                0
            ) or 0
        )

        if prompt_duration > 0:

            prompt_speed = (
                prompt_tokens
                /
                (
                    prompt_duration
                    /
                    1_000_000_000
                )
            )

        else:

            prompt_speed = 0.0

        if eval_duration > 0:

            generation_speed = (
                output_tokens
                /
                (
                    eval_duration
                    /
                    1_000_000_000
                )
            )

        else:

            generation_speed = 0.0

        total_tokens = (
            prompt_tokens
            + output_tokens
        )

        self.last_stats = {
            "elapsed": elapsed,
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "prompt_speed": prompt_speed,
            "generation_speed": generation_speed
        }

        self.stats_button.set_label(
            f"{output_tokens} tok • "
            f"{generation_speed:.1f} tok/s • "
            f"{elapsed:.1f}s"
        )

    # ========================================================
    # WELCOME
    # ========================================================

    def show_welcome(self):

        while True:

            child = self.messages_box.get_first_child()

            if child is None:
                break

            self.messages_box.remove(child)

        welcome = Gtk.Label(
            label=(
                "Aether'a hoş geldin.\n\n"
                "Yerel modellerle sohbet etmeye "
                "hazırsın."
            )
        )

        welcome.set_wrap(True)
        welcome.set_xalign(0)
        welcome.add_css_class("welcome")

        self.messages_box.append(welcome)

    # ========================================================
    # OLLAMA
    # ========================================================

    def check_ollama(self):

        def worker():

            try:

                models = self.client.get_models()

                GLib.idle_add(
                    self.update_models,
                    models
                )

            except Exception as error:

                GLib.idle_add(
                    self.ollama_error,
                    str(error)
                )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def ollama_error(self, error):

        self.status_label.set_text(
            "● Ollama bağlantı hatası"
        )

        self.stats_button.set_label(
            "Ollama çalışmıyor"
        )

        print(
            f"Ollama hatası: {error}"
        )

        return False

    # ========================================================
    # CHAT HISTORY
    # ========================================================

    def load_chat_history(self):

        chats = self.database.get_chats()

        for chat_id, title in chats:

            self.add_history_item(
                chat_id,
                title
            )

    def add_history_item(self, chat_id, title):

        row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=3
        )

        row.add_css_class("history-row")

        select_button = Gtk.Button(
            label=title
        )

        select_button.set_hexpand(True)
        select_button.set_halign(Gtk.Align.FILL)

        select_button.connect(
            "clicked",
            self.load_chat,
            chat_id
        )

        row.append(select_button)

        rename_button = Gtk.Button(
            label="✎"
        )

        rename_button.set_tooltip_text(
            "Yeniden adlandır"
        )

        rename_button.add_css_class("flat")

        rename_button.connect(
            "clicked",
            self.rename_chat,
            chat_id
        )

        row.append(rename_button)

        delete_button = Gtk.Button(
            label="×"
        )

        delete_button.set_tooltip_text(
            "Sohbeti sil"
        )

        delete_button.add_css_class("flat")

        delete_button.connect(
            "clicked",
            self.delete_chat,
            chat_id,
            row
        )

        row.append(delete_button)

        self.history_box.append(row)

        self.chat_rows[chat_id] = {
            "row": row,
            "button": select_button,
            "title": title
        }

        self.update_active_chat_style()

    def update_history_row(
        self,
        chat_id,
        title
    ):

        data = self.chat_rows.get(chat_id)

        if data is None:
            return

        data["title"] = title

        data["button"].set_label(title)

        self.filter_history()

    def update_active_chat_style(self):

        for chat_id, data in self.chat_rows.items():

            if chat_id == self.current_chat_id:

                data["row"].add_css_class(
                    "active-chat"
                )

            else:

                data["row"].remove_css_class(
                    "active-chat"
                )

    def refresh_history(self):

        while True:

            child = self.history_box.get_first_child()

            if child is None:
                break

            self.history_box.remove(child)

        self.chat_rows.clear()

        self.load_chat_history()
        self.filter_history()

    # ========================================================
    # CHAT ACTIONS
    # ========================================================

    def rename_chat(self, button, chat_id):

        if self.generating:
            return

        data = self.chat_rows.get(chat_id)

        if data is None:
            return

        self.rename_window = RenameChatWindow(
            self,
            chat_id,
            data["title"]
        )

        self.rename_window.present()

    def load_chat(self, button, chat_id):

        if self.generating:
            return

        messages = self.database.get_messages(
            chat_id
        )

        self.current_chat_id = chat_id

        for cid, title in self.database.get_chats():

            if cid == chat_id:

                self.chat_title.set_text(title)
                break

        self.messages = []

        while True:

            child = self.messages_box.get_first_child()

            if child is None:
                break

            self.messages_box.remove(child)

        for role, content in messages:

            self.messages.append({
                "role": role,
                "content": content
            })

            self.add_message(
                role,
                content
            )

        self.update_active_chat_style()
        self.scroll_to_bottom()

    def delete_chat(
        self,
        button,
        chat_id,
        row
    ):

        if self.generating:
            return

        self.database.delete_chat(chat_id)

        self.history_box.remove(row)

        self.chat_rows.pop(
            chat_id,
            None
        )

        if self.current_chat_id == chat_id:

            self.current_chat_id = None
            self.messages.clear()

            self.chat_title.set_text(
                "Yeni Sohbet"
            )

            self.stats_button.set_label(
                "Hazır"
            )

            self.show_welcome()

        self.update_active_chat_style()

    # ========================================================
    # MESSAGES
    # ========================================================

    def add_message(self, role, text):

        bubble = MessageBubble(
            role,
            text
        )

        self.messages_box.append(bubble)

        return bubble

    # ========================================================
    # SEND
    # ========================================================

    def send_message(self, widget):

        if self.generating:
            return

        text = (
            self.get_input_text()
            .strip()
        )

        if not text:
            return

        self.clear_input()

        if self.current_chat_id is None:

            title = text[:45]

            if len(text) > 45:
                title += "..."

            self.current_chat_id = (
                self.database.create_chat(
                    title
                )
            )

            self.chat_title.set_text(title)

            self.refresh_history()
            self.update_active_chat_style()

        self.messages.append({
            "role": "user",
            "content": text
        })

        self.database.add_message(
            self.current_chat_id,
            "user",
            text
        )

        self.add_message(
            "user",
            text
        )

        assistant_bubble = self.add_message(
            "assistant",
            ""
        )

        assistant_state = {
            "text": ""
        }

        self.messages.append({
            "role": "assistant",
            "content": ""
        })

        self.generating = True
        self.stop_event = threading.Event()

        self.generation_started = time.monotonic()

        self.send_button.set_sensitive(False)
        self.stop_button.set_sensitive(True)
        self.entry.set_sensitive(False)

        self.stats_button.set_label(
            "Üretiliyor..."
        )

        model = self.get_model()
        context = self.context
        temperature = self.temperature
        thinking = self.thinking

        messages_for_model = [
            {
                "role": "system",
                "content": AETHER_SYSTEM_PROMPT
            }
        ]

        messages_for_model.extend(
            self.messages[:-1]
        )

        def callback(
            chunk,
            done,
            data
        ):

            GLib.idle_add(
                self.update_response,
                assistant_bubble,
                assistant_state,
                chunk,
                done,
                data
            )

        threading.Thread(
            target=self.client.chat,
            args=(
                model,
                messages_for_model,
                context,
                temperature,
                thinking,
                self.stop_event,
                callback
            ),
            daemon=True
        ).start()

    # ========================================================
    # RESPONSE
    # ========================================================

    def update_response(
        self,
        bubble,
        state,
        chunk,
        done,
        data
    ):

        if chunk:

            state["text"] += chunk

            bubble.set_text(
                state["text"]
            )

            if self.messages:

                self.messages[-1]["content"] = (
                    state["text"]
                )

        if done:

            self.update_stats(data)

            self.generating = False

            self.send_button.set_sensitive(True)
            self.stop_button.set_sensitive(False)
            self.entry.set_sensitive(True)

            self.entry.grab_focus()

            if state["text"]:

                self.database.add_message(
                    self.current_chat_id,
                    "assistant",
                    state["text"]
                )

        self.scroll_to_bottom()

        return False

    # ========================================================
    # STOP
    # ========================================================

    def stop_generation(self, button):

        if not self.generating:
            return

        if self.stop_event:
            self.stop_event.set()

        self.generating = False

        self.send_button.set_sensitive(True)
        self.stop_button.set_sensitive(False)
        self.entry.set_sensitive(True)

        elapsed = (
            time.monotonic()
            - self.generation_started
        )

        self.stats_button.set_label(
            f"Durduruldu • {elapsed:.1f}s"
        )

        self.entry.grab_focus()

    # ========================================================
    # NEW CHAT
    # ========================================================

    def new_chat(self, button):

        if self.generating:
            return

        self.current_chat_id = None

        self.messages.clear()

        self.chat_title.set_text(
            "Yeni Sohbet"
        )

        self.stats_button.set_label(
            "Hazır"
        )

        self.update_active_chat_style()

        self.show_welcome()

        self.clear_input()

        self.entry.set_sensitive(True)
        self.entry.grab_focus()

    # ========================================================
    # SCROLL
    # ========================================================

    def scroll_to_bottom(self):

        def scroll():

            adjustment = (
                self.scroll
                .get_vadjustment()
            )

            adjustment.set_value(
                max(
                    0,
                    adjustment.get_upper()
                    - adjustment.get_page_size()
                )
            )

            return False

        GLib.idle_add(scroll)


# ============================================================
# APPLICATION
# ============================================================

class LocalAIApplication(Adw.Application):

    def __init__(self):

        super().__init__(
            application_id=APP_ID,
            flags=0
        )

    def do_activate(self):

        window = self.props.active_window

        if window is None:

            window = LocalAIWindow(self)

        window.present()


# ============================================================
# MAIN
# ============================================================

def main():

    app = LocalAIApplication()

    return app.run(None)


if __name__ == "__main__":
    main()
