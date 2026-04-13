from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from transformers import AutoModelForCausalLM, AutoTokenizer

try:  # torch may not be installed yet; handle gracefully
    import torch
    _TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover - environment-specific
    torch = None  # type: ignore[assignment]
    _TORCH_AVAILABLE = False

from .provider import AIProvider
from .prompts import build_phi4_prompt
from .schemas import AIExplanationResult, ExplainerContext
from .template_provider import TemplateProvider

logger = logging.getLogger(__name__)

_MODEL = None
_TOKENIZER = None
_DEVICE = None


class Phi4Provider(AIProvider):
    """
    Local Phi-4-multimodal-instruct-backed provider.

    Text-grounded for V1:
      - builds a grounded prompt from ExplainerContext
      - calls local transformers model.generate()
      - parses JSON-ish output into AIExplanationResult
      - falls back to TemplateProvider on any failure.
    """

    def __init__(self) -> None:
        self._template = TemplateProvider()
        self._repo_path = Path(os.getenv("GRIDIRONIQ_PHI4_REPO_PATH", "Phi-4-multimodal-instruct")).resolve()
        self._model_path = os.getenv("GRIDIRONIQ_PHI4_MODEL_PATH", str(self._repo_path))
        self._device_pref = os.getenv("GRIDIRONIQ_PHI4_DEVICE", "auto").lower()

    def _is_available(self) -> bool:
        # Repo or model path must exist for us to attempt loading
        return Path(self._model_path).exists() or self._repo_path.exists()

    def _ensure_model_loaded(self) -> None:
        global _MODEL, _TOKENIZER, _DEVICE
        if _MODEL is not None and _TOKENIZER is not None:
            return

        if not self._is_available():
            raise RuntimeError(f"Phi-4 model path not found: {self._model_path}")
        if not _TORCH_AVAILABLE:
            raise RuntimeError("torch is not installed; cannot load Phi-4 model.")

        model_id = self._model_path
        logger.info("Loading Phi-4 model from %s", model_id)

        if self._device_pref == "cuda" and torch.cuda.is_available():
            _DEVICE = "cuda"
        elif self._device_pref in {"cpu", "cuda"}:
            _DEVICE = "cuda" if (self._device_pref == "cuda" and torch.cuda.is_available()) else "cpu"
        else:
            _DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

        _TOKENIZER = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        _MODEL = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if _DEVICE == "cuda" else torch.float32,
            device_map="auto" if _DEVICE == "cuda" else None,
            trust_remote_code=True,
        )
        if _DEVICE == "cpu":
            _MODEL = _MODEL.to("cpu")

    def _raw_generate(self, prompt: str, max_new_tokens: int = 384) -> str:
        """
        Run local Phi-4 inference using transformers.
        """
        self._ensure_model_loaded()
        assert _MODEL is not None and _TOKENIZER is not None and _DEVICE is not None

        inputs = _TOKENIZER(prompt, return_tensors="pt").to(_DEVICE)
        with torch.no_grad():
            output_ids = _MODEL.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
            )
        text = _TOKENIZER.decode(output_ids[0], skip_special_tokens=True)
        # Strip the prompt from the beginning if the model echoes it
        if text.startswith(prompt):
            text = text[len(prompt) :]
        return text.strip()

    def _parse_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Try to extract a JSON object from the model output text.
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Heuristic: find first { and last } and try again
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                snippet = text[start : end + 1]
                return json.loads(snippet)
            raise

    def status(self) -> Dict[str, Any]:
        return {
            "repo_path": str(self._repo_path),
            "model_path": self._model_path,
            "available": self._is_available(),
            "loaded": _MODEL is not None,
            "multimodal_enabled": False,  # text-only for V1
        }

    def generate(self, context: ExplainerContext) -> AIExplanationResult:
        if not self._is_available():
            logger.warning("Phi-4 model path not found (%s); using template provider.", self._model_path)
            return self._template.generate(context)

        try:
            prompt = build_phi4_prompt(context)
            raw = self._raw_generate(prompt)
            data: Dict[str, Any] = self._parse_json_from_text(raw)
            return AIExplanationResult(
                summary=str(data.get("summary", "")),
                top_3_reasons=[str(x) for x in data.get("top_3_reasons", [])][:3],
                what_matters_most=str(data.get("what_matters_most", "")),
                what_could_flip_it=str(data.get("what_could_flip_it", "")),
                why_prediction_was_right_or_wrong=data.get("why_prediction_was_right_or_wrong"),
                confidence_note=data.get("confidence_note"),
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("Phi-4 provider failed, falling back to template: %s", e)
            return self._template.generate(context)

