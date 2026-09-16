import main as legacy
from version import __version__


Gtk = legacy.Gtk
Adw = legacy.Adw
GLib = legacy.GLib


class EnhancedSettingsWindow(legacy.SettingsWindow):
    """Advanced generation controls and a custom system prompt."""

    def build_ui(self):
        super().build_ui()

        advanced_page = Adw.PreferencesPage(
            title="Gelişmiş",
            icon_name="preferences-other-symbolic",
        )
        self.add(advanced_page)

        generation_group = Adw.PreferencesGroup(
            title="Üretim",
            description="Ollama'nın gelişmiş üretim seçenekleri.",
        )
        advanced_page.add(generation_group)

        self._add_float_row(
            generation_group,
            "Top P",
            "Nucleus sampling eşiği.",
            "top_p",
            0.0,
            1.0,
            0.05,
            2,
        )
        self._add_int_row(
            generation_group,
            "Top K",
            "Her adımda değerlendirilecek aday token sayısı.",
            "top_k",
            0,
            200,
            1,
        )
        self._add_float_row(
            generation_group,
            "Repeat penalty",
            "Tekrarları azaltmak için uygulanan ceza.",
            "repeat_penalty",
            0.0,
            2.0,
            0.05,
            2,
        )
        self._add_int_row(
            generation_group,
            "Maksimum çıktı token",
            "-1 seçeneği Ollama varsayılanını kullanır.",
            "num_predict",
            -1,
            32768,
            1,
        )

        prompt_group = Adw.PreferencesGroup(
            title="System Prompt",
            description=(
                "Boş bırakırsan Aether'ın varsayılan "
                "kimlik prompt'u kullanılır."
            ),
        )
        advanced_page.add(prompt_group)

        prompt_scroll = Gtk.ScrolledWindow()
        prompt_scroll.set_min_content_height(150)
        prompt_scroll.set_max_content_height(260)

        self.prompt_view = Gtk.TextView()
        self.prompt_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.prompt_view.get_buffer().set_text(
            self.parent_window.config.get("system_prompt") or "",
            -1,
        )
        prompt_scroll.set_child(self.prompt_view)
        prompt_group.add(prompt_scroll)

        save_prompt = Gtk.Button(
            label="System Prompt'u Kaydet"
        )
        save_prompt.add_css_class("suggested-action")
        save_prompt.connect(
            "clicked",
            self.save_system_prompt,
        )
        prompt_group.add(save_prompt)

        info_group = Adw.PreferencesGroup(title="Sürüm")
        advanced_page.add(info_group)
        info_group.add(
            Adw.ActionRow(
                title=f"Aether {__version__}",
                subtitle="Foundation Update",
            )
        )

    def _add_float_row(
        self,
        group,
        title,
        subtitle,
        key,
        minimum,
        maximum,
        step,
        digits,
    ):
        adjustment = Gtk.Adjustment.new(
            float(self.parent_window.config.get(key)),
            minimum,
            maximum,
            step,
            step * 5,
            0,
        )
        row = Adw.SpinRow(
            title=title,
            subtitle=subtitle,
            adjustment=adjustment,
        )
        row.set_digits(digits)
        row.connect(
            "notify::value",
            self._on_advanced_float_changed,
            key,
        )
        group.add(row)

    def _add_int_row(
        self,
        group,
        title,
        subtitle,
        key,
        minimum,
        maximum,
        step,
    ):
        adjustment = Gtk.Adjustment.new(
            int(self.parent_window.config.get(key)),
            minimum,
            maximum,
            step,
            step * 10,
            0,
        )
        row = Adw.SpinRow(
            title=title,
            subtitle=subtitle,
            adjustment=adjustment,
        )
        row.set_digits(0)
        row.connect(
            "notify::value",
            self._on_advanced_int_changed,
            key,
        )
        group.add(row)

    def _on_advanced_float_changed(
        self,
        row,
        param,
        key,
    ):
        self.parent_window.config.set(
            key,
            float(row.get_value()),
        )
        self.parent_window.refresh_runtime_settings()

    def _on_advanced_int_changed(
        self,
        row,
        param,
        key,
    ):
        self.parent_window.config.set(
            key,
            int(row.get_value()),
        )
        self.parent_window.refresh_runtime_settings()

    def save_system_prompt(self, button):
        buffer = self.prompt_view.get_buffer()
        text = buffer.get_text(
            buffer.get_start_iter(),
            buffer.get_end_iter(),
            False,
        ).strip()

        self.parent_window.config.set(
            "system_prompt",
            text,
        )
        self.parent_window.refresh_runtime_settings()

        button.set_label("Kaydedildi")
        GLib.timeout_add(
            1500,
            self._reset_prompt_button,
            button,
        )

    @staticmethod
    def _reset_prompt_button(button):
        button.set_label("System Prompt'u Kaydet")
        return False
