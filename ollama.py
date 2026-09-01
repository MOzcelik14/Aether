import json
import urllib.request
import urllib.error


class OllamaError(Exception):
    """Ollama bağlantısı veya API hatası."""
    pass


class OllamaClient:

    def __init__(self, base_url="http://127.0.0.1:11434"):
        self.base_url = base_url.rstrip("/")

    # ==================================================
    # HTTP
    # ==================================================

    def _request(
        self,
        endpoint,
        method="GET",
        payload=None,
        timeout=30
    ):
        url = f"{self.base_url}{endpoint}"

        data = None

        headers = {
            "Accept": "application/json"
        }

        if payload is not None:
            data = json.dumps(
                payload
            ).encode("utf-8")

            headers["Content-Type"] = (
                "application/json"
            )

        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=timeout
            ) as response:

                return json.load(response)

        except urllib.error.HTTPError as exc:

            try:
                body = exc.read().decode(
                    "utf-8",
                    errors="replace"
                )
            except Exception:
                body = ""

            raise OllamaError(
                f"HTTP {exc.code}: {body}"
            ) from exc

        except urllib.error.URLError as exc:

            raise OllamaError(
                f"Ollama'ya bağlanılamadı: {exc.reason}"
            ) from exc

        except Exception as exc:

            raise OllamaError(
                str(exc)
            ) from exc

    # ==================================================
    # CONNECTION
    # ==================================================

    def is_available(self):

        try:
            self._request(
                "/api/version",
                timeout=3
            )
            return True

        except OllamaError:
            return False

    def get_version(self):

        data = self._request(
            "/api/version",
            timeout=3
        )

        return data.get(
            "version",
            "Bilinmiyor"
        )

    # ==================================================
    # MODELS
    # ==================================================

    def get_models(self):

        data = self._request(
            "/api/tags",
            timeout=5
        )

        return data.get(
            "models",
            []
        )

    def get_model_names(self):

        return [
            model.get("name", "")
            for model in self.get_models()
            if model.get("name")
        ]

    def get_model(self, model_name):

        for model in self.get_models():

            if model.get("name") == model_name:
                return model

        return None

    def delete_model(self, model_name):

        self._request(
            "/api/delete",
            method="DELETE",
            payload={
                "model": model_name
            },
            timeout=30
        )

    # ==================================================
    # PULL MODEL
    # ==================================================

    def pull_model(
        self,
        model_name,
        callback=None,
        stop_event=None
    ):
        """
        Ollama modelini indirir.

        callback:
            callback(status, completed, total, done, data)

        Örnek:
            status = "pulling manifest"
            completed = 500000000
            total = 1000000000
            done = False
        """

        payload = {
            "model": model_name,
            "stream": True
        }

        request = urllib.request.Request(
            f"{self.base_url}/api/pull",
            data=json.dumps(
                payload
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/x-ndjson"
            },
            method="POST"
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=3600
            ) as response:

                for raw_line in response:

                    if (
                        stop_event is not None
                        and stop_event.is_set()
                    ):
                        return

                    if not raw_line.strip():
                        continue

                    data = json.loads(
                        raw_line.decode(
                            "utf-8"
                        )
                    )

                    status = data.get(
                        "status",
                        ""
                    )

                    completed = int(
                        data.get(
                            "completed",
                            0
                        ) or 0
                    )

                    total = int(
                        data.get(
                            "total",
                            0
                        ) or 0
                    )

                    done = bool(
                        data.get(
                            "done",
                            status == "success"
                        )
                    )

                    if callback:

                        callback(
                            status,
                            completed,
                            total,
                            done,
                            data
                        )

        except urllib.error.HTTPError as exc:

            try:
                body = exc.read().decode(
                    "utf-8",
                    errors="replace"
                )
            except Exception:
                body = ""

            if callback:

                callback(
                    f"HTTP {exc.code}: {body}",
                    0,
                    0,
                    True,
                    {}
                )

        except urllib.error.URLError as exc:

            if callback:

                callback(
                    f"Ollama bağlantı hatası: {exc.reason}",
                    0,
                    0,
                    True,
                    {}
                )

        except Exception as exc:

            if callback:

                callback(
                    f"Hata: {exc}",
                    0,
                    0,
                    True,
                    {}
                )

    # ==================================================
    # CHAT
    # ==================================================

    def chat(
        self,
        model,
        messages,
        context=8192,
        temperature=0.6,
        thinking=False,
        stop_event=None,
        callback=None,
        options=None
    ):
        """
        Streaming chat.

        callback(chunk, done, data)
        """

        model_options = {
            "num_ctx": int(context),
            "temperature": float(temperature)
        }

        if options:
            model_options.update(options)

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "think": bool(thinking),
            "options": model_options
        }

        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(
                payload
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/x-ndjson"
            },
            method="POST"
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=600
            ) as response:

                for raw_line in response:

                    if (
                        stop_event is not None
                        and stop_event.is_set()
                    ):
                        return

                    if not raw_line.strip():
                        continue

                    data = json.loads(
                        raw_line.decode(
                            "utf-8"
                        )
                    )

                    message = data.get(
                        "message",
                        {}
                    )

                    content = message.get(
                        "content",
                        ""
                    )

                    if callback:

                        callback(
                            content,
                            data.get(
                                "done",
                                False
                            ),
                            data
                        )

        except urllib.error.HTTPError as exc:

            try:
                body = exc.read().decode(
                    "utf-8",
                    errors="replace"
                )
            except Exception:
                body = ""

            if callback:

                callback(
                    f"[Ollama HTTP {exc.code}] {body}",
                    True,
                    {}
                )

        except urllib.error.URLError as exc:

            if callback:

                callback(
                    f"[Ollama bağlantı hatası] {exc.reason}",
                    True,
                    {}
                )

        except Exception as exc:

            if callback:

                callback(
                    f"[Hata] {exc}",
                    True,
                    {}
                )
