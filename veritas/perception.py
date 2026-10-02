"""Input Perception: the 'senses' of VERITAS. Plain Python (not LLM agents) so they are fast and predictable.
 - screenshot / image -> Groq vision model
 - voice note        -> Groq Whisper
 - QR code           -> OpenCV decoder (offline)
"""
from __future__ import annotations

import base64
import io
import re

import requests

from . import heuristics as h
from .config import GROQ_BASE, STT_MODEL, VISION_MODEL


class PerceptionError(Exception):
    """Raised with a message that is safe to show to the user."""


def _auth(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


def _check(resp: requests.Response, what: str) -> dict:
    if resp.status_code == 401:
        raise PerceptionError("Groq rejected the API key. Check it in the sidebar.")
    if resp.status_code == 429:
        raise PerceptionError(f"Groq rate limit reached while {what}. Wait a minute and try again.")
    if resp.status_code >= 400:
        try:
            msg = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            msg = resp.text
        raise PerceptionError(f"Could not finish {what}: {str(msg)[:300]}")
    return resp.json()


def prepare_image(data: bytes, max_side: int = 1600) -> tuple[bytes, str]:
    """Shrink large screenshots and convert to JPEG so the request stays small."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGB")
        img.thumbnail((max_side, max_side))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=88)
        return out.getvalue(), "image/jpeg"
    except Exception as e:
        raise PerceptionError("This file could not be opened as an image.") from e


VISION_PROMPT = (
    "You are the vision sensor of a digital fraud-assessment system. Describe this image factually.\n"
    "1) Transcribe ALL visible text exactly (any language, including Urdu).\n"
    "2) List what is visible: sender / recipient names, phone numbers, account numbers, amounts, dates, URLs, "
    "brand names or logos, and the channel (SMS, WhatsApp, email, bank app, marketplace listing...).\n"
    "3) Mention visual oddities (mismatched logos, edited look, strange fonts) without giving a verdict.\n"
    "Be concise and factual. Do not judge whether it is a scam."
)


def read_image(data: bytes, api_key: str, note: str = "") -> str:
    jpg, mime = prepare_image(data)
    b64 = base64.b64encode(jpg).decode()
    payload = {
        "model": VISION_MODEL, "temperature": 0.1, "max_completion_tokens": 3000,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": VISION_PROMPT + (f"\nUser note: {note}" if note else "")},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
    }
    try:
        resp = requests.post(f"{GROQ_BASE}/chat/completions", headers=_auth(api_key), json=payload, timeout=90)
    except requests.RequestException as e:
        raise PerceptionError(f"Could not reach Groq to read the image: {e}") from e
    text = _check(resp, "reading the image")["choices"][0]["message"].get("content") or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    if not text:
        raise PerceptionError("The vision model returned nothing for this image. Try a clearer screenshot.")
    return text


def transcribe(data: bytes, filename: str, api_key: str) -> str:
    try:
        resp = requests.post(f"{GROQ_BASE}/audio/transcriptions", headers=_auth(api_key),
                             files={"file": (filename or "audio.wav", data)},
                             data={"model": STT_MODEL, "response_format": "json", "temperature": "0"}, timeout=120)
    except requests.RequestException as e:
        raise PerceptionError(f"Could not reach Groq to transcribe the audio: {e}") from e
    text = (_check(resp, "transcribing the audio").get("text") or "").strip()
    if not text:
        raise PerceptionError("No speech was found in this audio.")
    return text


def read_qr(data: bytes) -> str:
    decoded = h.decode_qr(data)
    if not decoded:
        raise PerceptionError("No QR code could be read. Try a sharper image with the whole code in view.")
    return decoded
