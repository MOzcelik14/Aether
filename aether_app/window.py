import threading
from pathlib import Path

import main as legacy


Gtk = legacy.Gtk
Adw = legacy.Adw
GLib = legacy.GLib
Gdk = legacy.Gdk
BASE_SYSTEM_PROMPT = legacy.AETHER_SYSTEM_PROMPT


class EnhancedLocalAIWindow(legacy.LocalAIWindow):
    """Aether 1.1 window behaviour layered over the 1.0 UI core."""

    def __init__(self, app):
        self._partial_response_saved = False
        super().__init__(app)
        self._install_chat_options_wrapper()
        self.refresh_runtime_settings()
        self.connect(
            "close-request",
            self._on_close_request,
        )

    def _install_chat_options_wrapper(self):
        original_chat = self.client.chat

        def chat_with_defaults(
            model,
            messages,
            context=8192,
            temperature=0.6,
            thinking=False,
            stop_event=None,
            callback=None,
            options=None,
        ):
            merged_options = dict(
                getattr(
                    self.client,
                    "default_options",
                    {},
                )
            )
            if options:
                merged_options.update(options)

            return original_chat(
                model,
                messages,
                context,
                temperature,
                thinking,
                stop_event,
                callback,
                merged_options,
            )

        self.client.chat = chat_with_defaults

    def refresh_runtime_settings(self):
        options = {
            "top_p": float(self.config.get("top_p")),
            "top_k": int(self.config.get("top_k")),
            "repeat_penalty": float(
                self.config.get("repeat_penalty")
            ),
        }

        num_predict = int(
            self.config.get("num_predict")
        )
        if num_predict >= 0:
            options["num_predict"] = num_predict

        self.client.default_options = options

        custom_prompt = (
            self.config.get("system_prompt") or ""
        ).strip()

        legacy.AETHER_SYSTEM_PROMPT = (
            custom_prompt or BASE_SYSTEM_PROMPT
        )

    def build_ui(self):
        super().build_ui()

        model_row = self.model_dropdown.get_parent()
        if model_row is not None:
            delete_model = Gtk.Button(label="−")
            delete_model.set_tooltip_text(
                "Seçili modeli sil"
            )
            delete_model.connect(
                "clicked",
                self.confirm_delete_model,
            )
            model_row.append(delete_model)

        chat_header = self.chat_title.get_parent()
        if chat_header is not None:
            export_button = Gtk.Button(
                label="Dışa aktar"
            )
            export_button.add_css_class("flat")
            export_button.set_tooltip_text(
                "Sohbeti Markdown olarak dışa aktar"
            )
            export_button.connect(
                "clicked",
                self.export_current_chat,
            )
            chat_header.append(export_button)

            self.regenerate_button = Gtk.Button(
                label="Yeniden üret"
            )
            self.regenerate_button.add_css_class("flat")
            self.regenerate_button.set_tooltip_text(
                "Son Aether yanıtını yeniden üret"
            )
            self.regenerate_button.connect(
                "clicked",
                self.regenerate_last_response,
            )
            chat_header.append(self.regenerate_button)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect(
            "key-pressed",
            self.on_global_key_pressed,
        )
        self.add_controller(key_controller)

    def on_global_key_pressed(
        self,
        controller,
        keyval,
        keycode,
        state,
    ):
        ctrl = bool(
            state & Gdk.ModifierType.CONTROL_MASK
        )

        if not ctrl:
            return False

        if keyval in (Gdk.KEY_n, Gdk.KEY_N):
            self.new_chat(None)
            return True

        if keyval == Gdk.KEY_comma:
            self.open_settings(None)
            return True

        if keyval in (Gdk.KEY_k, Gdk.KEY_K):
            self.model_dropdown.grab_focus()
            return True

        return False

    def filter_history(self):
        if not self.search_text:
            for data in self.chat_rows.values():
                data["row"].set_visible(True)
            return

        matching_ids = (
            self.database.search_chat_ids(
                self.search_text
            )
        )

        for chat_id, data in self.chat_rows.items():
            data["row"].set_visible(
                chat_id in matching_ids
            )

    def delete_chat(
        self,
        button,
        chat_id,
        row,
    ):
        if self.generating:
            return

        dialog = Adw.MessageDialog.new(
            self,
            "Sohbet silinsin mi?",
            (
                "Bu sohbet ve içindeki mesajlar "
                "kalıcı olarak silinecek."
            ),
        )
        dialog.add_response("cancel", "İptal")
        dialog.add_response("delete", "Sil")
        dialog.set_close_response("cancel")
        dialog.set_default_response("cancel")
        dialog.set_response_appearance(
            "delete",
            Adw.ResponseAppearance.DESTRUCTIVE,
        )
        dialog.connect(
            "response",
            self._on_delete_chat_response,
            chat_id,
            row,
        )
        dialog.present()

    def _on_delete_chat_response(
        self,
        dialog,
        response,
        chat_id,
        row,
    ):
        if response == "delete":
            super().delete_chat(
                None,
                chat_id,
                row,
            )

    def confirm_delete_model(self, button):
        if self.generating:
            return

        model = self.get_model()
        if not model:
            return

        dialog = Adw.MessageDialog.new(
            self,
            "Model silinsin mi?",
            (
                f"{model} yerel Ollama "
                "deposundan silinecek."
            ),
        )
        dialog.add_response("cancel", "İptal")
        dialog.add_response("delete", "Sil")
        dialog.set_close_response("cancel")
        dialog.set_default_response("cancel")
        dialog.set_response_appearance(
            "delete",
            Adw.ResponseAppearance.DESTRUCTIVE,
        )
        dialog.connect(
            "response",
            self._on_delete_model_response,
            model,
        )
        dialog.present()

    def _on_delete_model_response(
        self,
        dialog,
        response,
        model,
    ):
        if response != "delete":
            return

        self.status_label.set_text(
            f"● {model} siliniyor..."
        )

        def worker():
            try:
                self.client.delete_model(model)
                GLib.idle_add(
                    self._model_deleted,
                    model,
                )
            except Exception as error:
                GLib.idle_add(
                    self.ollama_error,
                    str(error),
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def _model_deleted(self, model):
        self.status_label.set_text(
            f"● {model} silindi"
        )
        self.refresh_models(None)
        return False

    def export_current_chat(self, button):
        if self.current_chat_id is None:
            return

        chooser = Gtk.FileChooserNative.new(
            "Sohbeti Dışa Aktar",
            self,
            Gtk.FileChooserAction.SAVE,
            "Kaydet",
            "İptal",
        )
        chooser.set_current_name("aether-chat.md")
        chooser.connect(
            "response",
            self._on_export_response,
        )
        chooser.show()

    def _on_export_response(
        self,
        chooser,
        response,
    ):
        if response != Gtk.ResponseType.ACCEPT:
            chooser.destroy()
            return

        file = chooser.get_file()
        path = file.get_path() if file else None
        chooser.destroy()

        if not path:
            return

        title = (
            self.chat_title.get_text()
            or "Aether Sohbeti"
        )
        lines = [f"# {title}", ""]

        for role, content in (
            self.database.get_messages(
                self.current_chat_id
            )
        ):
            lines.append(
                "## Sen"
                if role == "user"
                else "## Aether"
            )
            lines.append("")
            lines.append(content)
            lines.append("")

        try:
            Path(path).write_text(
                "\n".join(lines),
                encoding="utf-8",
            )
            self.status_label.set_text(
                "● Sohbet dışa aktarıldı"
            )
        except OSError as error:
            self.status_label.set_text(
                f"● Dışa aktarma hatası: {error}"
            )

    def send_message(self, widget):
        self._partial_response_saved = False
        super().send_message(widget)

    def update_response(
        self,
        bubble,
        state,
        chunk,
        done,
        data,
    ):
        if (
            self._partial_response_saved
            and not self.generating
        ):
            return False

        if chunk:
            state["text"] += chunk
            bubble.set_text(state["text"])

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

            if (
                state["text"]
                and not self._partial_response_saved
            ):
                self.database.add_message(
                    self.current_chat_id,
                    "assistant",
                    state["text"],
                )

            self._partial_response_saved = False

        self.scroll_to_bottom()
        return False

    def stop_generation(self, button):
        if not self.generating:
            return

        if self.stop_event:
            self.stop_event.set()

        partial = ""
        if (
            self.messages
            and self.messages[-1].get("role")
            == "assistant"
        ):
            partial = (
                self.messages[-1]
                .get("content", "")
                .strip()
            )

        if (
            partial
            and self.current_chat_id is not None
        ):
            self.database.add_message(
                self.current_chat_id,
                "assistant",
                partial,
            )
            self._partial_response_saved = True

        elif self.messages and (
            self.messages[-1].get("role")
            == "assistant"
        ):
            self.messages.pop()
            child = (
                self.messages_box.get_last_child()
            )
            if child is not None:
                self.messages_box.remove(child)

        super().stop_generation(button)

    def regenerate_last_response(self, button):
        if (
            self.generating
            or self.current_chat_id is None
        ):
            return

        if (
            not self.messages
            or self.messages[-1].get("role")
            != "assistant"
        ):
            return

        self.messages.pop()
        self.database.delete_last_message(
            self.current_chat_id,
            "assistant",
        )

        child = self.messages_box.get_last_child()
        if child is not None:
            self.messages_box.remove(child)

        assistant_bubble = self.add_message(
            "assistant",
            "",
        )
        assistant_state = {"text": ""}

        self.messages.append({
            "role": "assistant",
            "content": "",
        })

        self._partial_response_saved = False
        self.generating = True
        self.stop_event = threading.Event()
        self.generation_started = (
            legacy.time.monotonic()
        )

        self.send_button.set_sensitive(False)
        self.stop_button.set_sensitive(True)
        self.entry.set_sensitive(False)
        self.stats_button.set_label(
            "Üretiliyor..."
        )

        messages_for_model = [{
            "role": "system",
            "content": (
                legacy.AETHER_SYSTEM_PROMPT
            ),
        }]
        messages_for_model.extend(
            self.messages[:-1]
        )

        def callback(chunk, done, data):
            GLib.idle_add(
                self.update_response,
                assistant_bubble,
                assistant_state,
                chunk,
                done,
                data,
            )

        threading.Thread(
            target=self.client.chat,
            args=(
                self.get_model(),
                messages_for_model,
                self.context,
                self.temperature,
                self.thinking,
                self.stop_event,
                callback,
            ),
            daemon=True,
        ).start()

    def _on_close_request(self, window):
        if self.stop_event:
            self.stop_event.set()

        try:
            self.database.close()
        except Exception:
            pass

        return False
