"""Offline tests: no API key, no network. Run: python -m pytest   (or: python tests/test_core.py)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from veritas import heuristics as h
from veritas.models import parse_assessment, level_for


def test_lookalike_bank_domain():
    assert h.analyze_url_signals("http://hbl-secure-verify.xyz/login")["risk"] >= 60


def test_official_domain_not_flagged():
    assert h.analyze_url_signals("https://www.paypal.com/signin")["risk"] < 35


def test_extract_urls():
    assert h.extract_urls("go to http://a-b.xyz/x now.")[0].startswith("http://a-b.xyz")


def test_levels():
    assert level_for(10) == "LOW RISK" and level_for(50) == "NEEDS VERIFICATION" and level_for(80) == "HIGH RISK"


def test_parse_full_json_and_identity_normalisation():
    raw = ('{"score": 91, "identity_consistency": "Mismatch detected", "scam_type": "Bank phishing", "headline": "h", '
           '"why": ["a","b"], "evidence": [{"title":"t","detail":"d","severity":"HIGH","source":"Identity Agent"}], '
           '"actions": [{"dont":"x","instead":"y"}], "verify_steps": ["s"]}')
    v = parse_assessment(None, "text before " + raw)
    assert v["level"] == "HIGH RISK" and v["identity_consistency"] == "Mismatch Detected"
    assert v["evidence"][0]["severity"] == "high" and v["actions"][0]["instead"] == "y"


def test_inconsistent_is_a_mismatch_not_consistent():
    assert parse_assessment(None, '{"score": 40, "identity_consistency": "Inconsistent"}')["identity_consistency"] == "Mismatch Detected"


def test_parse_garbage_is_cautious():
    v = parse_assessment(None, "no json here")
    assert v["level"] == "NEEDS VERIFICATION" and v["confidence"] == "low" and v["actions"]


def test_perception_image_and_audio_with_mocked_groq():
    import io
    from PIL import Image
    from veritas import perception
    buf = io.BytesIO(); Image.new("RGB", (50, 50), "white").save(buf, "PNG")

    class R:
        def __init__(s, j, code=200): s._j, s.status_code, s.text = j, code, "x"
        def json(s): return s._j
    calls = {}
    def fake_post(url, **kw):
        calls[url.rsplit("/", 2)[-2] + "/" + url.rsplit("/", 1)[-1]] = kw
        if url.endswith("chat/completions"):
            return R({"choices": [{"message": {"content": "<think>x</think>Visible text: send Rs 5000"}}]})
        return R({"text": "hello transcript"})
    perception.requests.post = fake_post
    assert perception.read_image(buf.getvalue(), "k") == "Visible text: send Rs 5000"
    assert perception.transcribe(b"abc", "a.mp3", "k") == "hello transcript"


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("ok", n)
