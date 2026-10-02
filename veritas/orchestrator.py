"""Trust Orchestrator: perception first, then the CrewAI team. Returns one result dict for the UI."""
from __future__ import annotations

from typing import Callable

from . import heuristics as h
from . import perception
from .crew import run_crew

EventCb = Callable[[int, str, str], None]  # step index 0 = perception, 1..7 = agents


def run_case(*, kind: str, text: str = "", url: str = "", image: bytes | None = None, audio: bytes | None = None,
             audio_name: str = "", note: str = "", region: str = "Pakistan", language: str = "Auto (same as input)",
             model: str, api_key: str, on_event: EventCb | None = None) -> dict:
    """kind: text | url | image | qr | audio"""
    emit = on_event or (lambda *a: None)
    urls: list[str] = []
    perceived = ""

    if kind == "text":
        content = text.strip()
        perceived = "Text received."
    elif kind == "url":
        content = f"The user submitted this link: {url.strip()}" + (f"\nMessage that came with it: {text.strip()}" if text.strip() else "")
        urls = [url.strip()]
        perceived = "Link received."
    elif kind == "qr":
        decoded = perception.read_qr(image or b"")
        content = f"QR code content: {decoded}"
        urls = h.extract_urls(decoded) or [decoded]
        perceived = f"QR decoded: {decoded}"
    elif kind == "image":
        perceived = perception.read_image(image or b"", api_key, note)
        content = perceived
    elif kind == "audio":
        perceived = perception.transcribe(audio or b"", audio_name, api_key)
        content = f"Voice note transcript:\n{perceived}"
    else:
        raise ValueError(f"unknown kind {kind}")

    for u in h.extract_urls(content):
        if u not in urls:
            urls.append(u)

    emit(0, "Input Perception", perceived)
    out = run_crew(input_type=kind, content=content, urls=urls, note=note, region=region, language=language,
                   model=model, api_key=api_key, on_event=lambda i, r, t: emit(i + 1, r, t))
    out.update({"kind": kind, "perceived": perceived, "content": content, "urls": urls,
                "region": region, "language": language, "model": model})
    return out
