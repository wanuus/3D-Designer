from __future__ import annotations
import base64, json, re
import httpx
from .base import AIProvider, ProviderInfo, ProviderUnavailable

PROMPT = """You are analysing a photograph of an interior room for a 3D interior-design tool.
Reply with ONLY one JSON object, no prose, in this shape:
{"room_type": string|null, "style": string|null, "wall_color": string|null,
 "flooring": {"material": string|null, "color": string|null}|null,
 "ceiling": {"type": string|null, "lights": [string]}|null,
 "objects": [{"objectType": string, "material": string|null, "color": string|null, "style": string|null,
              "position_hint": string|null, "components": [string],
              "estimatedDimensionsM": {"width": number|null, "height": number|null, "depth": number|null}}],
 "notes": string}
Use null for anything you cannot actually see. Do not invent exact dimensions; use null unless a size is clearly inferable."""


def extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise ValueError("The model did not return JSON.")
        return json.loads(m.group(0))


class OllamaVisionProvider(AIProvider):
    info = ProviderInfo(
        name="ollama_vision", tasks=["reference_analysis"], execution="local", model_id="qwen2.5vl:3b",
        hardware="Apple Silicon (Metal) via Ollama; ~4-6 GB RAM expected for a 3B model (verify with benchmark)",
        est_memory_gb=5.0, license="Qwen2.5-VL-3B: Qwen Research License (check commercial-use terms) - verify before client work",
        notes="Output is a proposal. Dimensions are never treated as verified.")

    @property
    def host(self) -> str:
        return self.options.get("host", "http://127.0.0.1:11434").rstrip("/")

    @property
    def model(self) -> str:
        return self.options.get("model", self.info.model_id)

    def availability(self):
        try:
            r = httpx.get(f"{self.host}/api/tags", timeout=3)
            r.raise_for_status()
        except Exception:
            return False, f"Ollama is not reachable at {self.host}. Install it from ollama.com and start it (open the app or run `ollama serve`)."
        names = [m.get("name", "") for m in r.json().get("models", [])]
        if not any(n == self.model or n.split(":")[0] == self.model for n in names):
            return False, f"Model '{self.model}' is not downloaded. Run: ollama pull {self.model}"
        return True, f"Ready ({self.model})"

    def run(self, task_type: str, payload: dict) -> dict:
        ok, detail = self.availability()
        if not ok:
            raise ProviderUnavailable(detail)
        with open(payload["image_path"], "rb") as f:
            img = base64.b64encode(f.read()).decode()
        body = {"model": self.model, "stream": False, "format": "json", "keep_alive": self.options.get("keep_alive", "30s"),
                "options": {"temperature": 0.1},
                "messages": [{"role": "user", "content": payload.get("prompt") or PROMPT, "images": [img]}]}
        try:
            r = httpx.post(f"{self.host}/api/chat", json=body, timeout=float(self.options.get("timeout", 600)))
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise ProviderUnavailable(f"Ollama request failed: {e}") from e
        raw = r.json().get("message", {}).get("content", "")
        try:
            parsed = extract_json(raw)
        except ValueError as e:
            raise ProviderUnavailable(f"{e} Raw output: {raw[:300]!r}") from e
        for obj in parsed.get("objects", []) if isinstance(parsed.get("objects"), list) else []:
            if isinstance(obj, dict):  # AI output is never "verified"
                obj["source"] = "reference-image"
                obj["dimensionsVerified"] = False
                obj["referenceAssetId"] = payload.get("asset_id")
        return {"analysis": parsed, "model": self.model, "verified": False}
