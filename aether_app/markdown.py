import html
import re

import main as legacy


Gtk = legacy.Gtk
GLib = legacy.GLib
Gdk = legacy.Gdk


class EnhancedCodeBlock(Gtk.Box):
    """Scrollable code block with copy support and preserved whitespace."""

    def __init__(self, code, language=""):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
        )
        self.code = code
        self.add_css_class("code-block")

        header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6,
        )

        language_label = Gtk.Label(
            label=(language or "CODE").upper()
        )
        language_label.set_xalign(0)
        language_label.set_hexpand(True)
        language_label.add_css_class("code-language")
        header.append(language_label)

        copy_button = Gtk.Button(label="Kopyala")
        copy_button.add_css_class("flat")
        copy_button.connect("clicked", self.copy_code)
        header.append(copy_button)
        self.append(header)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.NEVER,
        )
        scroll.set_min_content_height(
            min(320, max(56, (code.count("\n") + 1) * 22))
        )

        text = Gtk.TextView()
        text.set_editable(False)
        text.set_cursor_visible(False)
        text.set_monospace(True)
        text.set_wrap_mode(Gtk.WrapMode.NONE)
        text.add_css_class("code-text")
        text.get_buffer().set_text(code, -1)

        scroll.set_child(text)
        self.append(scroll)

    def copy_code(self, button):
        display = Gdk.Display.get_default()
        if display is None:
            return

        display.get_clipboard().set(self.code)
        button.set_label("Kopyalandı")
        GLib.timeout_add(
            1500,
            self._reset_copy_button,
            button,
        )

    @staticmethod
    def _reset_copy_button(button):
        button.set_label("Kopyala")
        return False


class EnhancedMessageBubble(legacy.MessageBubble):
    """Message bubble with richer inline Markdown and copy actions."""

    def __init__(self, role, text=""):
        super().__init__(role, text)

        actions = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6,
        )
        actions.set_halign(Gtk.Align.END)
        actions.add_css_class("message-actions")

        copy_button = Gtk.Button(label="Kopyala")
        copy_button.add_css_class("flat")
        copy_button.set_tooltip_text("Mesajı panoya kopyala")
        copy_button.connect("clicked", self.copy_message)

        actions.append(copy_button)
        self.append(actions)

    def copy_message(self, button):
        display = Gdk.Display.get_default()
        if display is None:
            return

        display.get_clipboard().set(self.text or "")
        button.set_label("Kopyalandı")
        GLib.timeout_add(
            1500,
            self._reset_copy_label,
            button,
        )

    @staticmethod
    def _reset_copy_label(button):
        button.set_label("Kopyala")
        return False

    def render_markdown_text(self, text):
        for line in text.splitlines():
            stripped = line.strip()

            if not stripped:
                spacer = Gtk.Box()
                spacer.set_size_request(-1, 5)
                self.content_box.append(spacer)
                continue

            if stripped in {"---", "***", "___"}:
                self.content_box.append(Gtk.Separator())
                continue

            checkbox = re.match(
                r"^[-*]\s+\[([ xX])\]\s+(.*)$",
                stripped,
            )
            if checkbox:
                mark = (
                    "☑"
                    if checkbox.group(1).lower() == "x"
                    else "☐"
                )
                self.append_markdown_label(
                    f"{mark} {checkbox.group(2)}"
                )
                continue

            if stripped.startswith("### "):
                self.append_markdown_label(
                    stripped[4:],
                    "markdown-h3",
                )
                continue

            if stripped.startswith("## "):
                self.append_markdown_label(
                    stripped[3:],
                    "markdown-h2",
                )
                continue

            if stripped.startswith("# "):
                self.append_markdown_label(
                    stripped[2:],
                    "markdown-h1",
                )
                continue

            if stripped.startswith("- ") or stripped.startswith("* "):
                self.append_markdown_label(
                    "• " + stripped[2:]
                )
                continue

            numbered = re.match(
                r"^(\d+)\.\s+(.*)$",
                stripped,
            )
            if numbered:
                self.append_markdown_label(
                    f"{numbered.group(1)}. {numbered.group(2)}"
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

    def inline_markup(self, text):
        escaped = html.escape(text)

        escaped = re.sub(
            r"`([^`]+)`",
            r'<span font_family="monospace">\1</span>',
            escaped,
        )
        escaped = re.sub(
            r"\*\*(.+?)\*\*",
            r"<b>\1</b>",
            escaped,
        )
        escaped = re.sub(
            r"(?<!\*)\*([^*]+)\*(?!\*)",
            r"<i>\1</i>",
            escaped,
        )
        escaped = re.sub(
            r"~~(.+?)~~",
            r"<s>\1</s>",
            escaped,
        )
        escaped = re.sub(
            r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
            r'<a href="\2">\1</a>',
            escaped,
        )

        return escaped
