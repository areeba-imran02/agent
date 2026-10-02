"""Deterministic tools. Agents use these first, then (optionally) an LLM refines them.
Everything here works offline, with no API key."""
from __future__ import annotations

import re
from urllib.parse import urlparse

URL_RE = re.compile(
    r"(?i)\b((?:https?://|www\.)[^\s<>\"')]+"
    r"|[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|net|org|pk|info|xyz|top|click|link|work|support|online|site|co|io|me|tk|ml|ga|cf|gq|zip)(?:/[^\s<>\"')]*)?)"
)

SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "rb.gy", "shorturl.at", "ow.ly", "tiny.cc"}
RISKY_TLDS = {"zip", "xyz", "top", "tk", "ml", "ga", "cf", "gq", "click", "link", "work", "support", "online", "site", "rest", "monster", "buzz", "icu"}
PATH_WORDS = ["login", "signin", "verify", "secure", "update", "account", "wallet", "confirm", "password", "otp", "bonus", "claim", "reward", "kyc", "unlock"]
SECOND_LEVEL = {"co", "com", "org", "net", "gov", "edu", "ac"}

# brand -> legitimate registered domains
BRANDS = {
    "paypal": ["paypal.com"], "google": ["google.com", "gmail.com"], "microsoft": ["microsoft.com", "live.com", "office.com"],
    "apple": ["apple.com", "icloud.com"], "amazon": ["amazon.com"], "facebook": ["facebook.com", "fb.com"],
    "instagram": ["instagram.com"], "whatsapp": ["whatsapp.com", "wa.me"], "netflix": ["netflix.com"],
    "easypaisa": ["easypaisa.com.pk"], "jazzcash": ["jazzcash.com.pk"], "jazz": ["jazz.com.pk"],
    "hbl": ["hbl.com"], "meezan": ["meezanbank.com"], "ubl": ["ubldigital.com", "ubl.com.pk"],
    "nadra": ["nadra.gov.pk"], "bisp": ["bisp.gov.pk"], "fbr": ["fbr.gov.pk"], "daraz": ["daraz.pk"],
    "binance": ["binance.com"], "dhl": ["dhl.com"], "fedex": ["fedex.com"], "pakpost": ["pakpost.gov.pk"],
}

# (label, regex, weight, explanation)
TEXT_RULES = [
    ("Urgency / pressure", r"(?i)\b(urgent|immediately|right now|within \d+ ?(hours?|mins?|minutes?)|last warning|final notice|act now|jaldi|fori|abhi)\b", 12, "Message creates time pressure so you do not stop to verify."),
    ("Asks for OTP / PIN / password", r"(?i)\b(otp|one[- ]time (code|password)|pin code|pin|password|cvv|verification code)\b", 28, "Real banks and apps never ask you to share OTP, PIN or password."),
    ("Money request", r"(?i)\b(send (me )?(money|payment|rs\.?)|transfer|wire|western union|pay (a )?(fee|fine|charge)|processing fee|advance|paisay|raqam)\b", 20, "Requests money or a fee before anything is delivered."),
    ("Prize / lottery claim", r"(?i)\b(you('| ha)ve won|winner|lucky draw|congratulations|prize|lottery|jeet|inaam|inam|reward|bonus|cashback|giveaway)\b", 18, "Unexpected prize or reward messages are a classic scam hook."),
    ("Threat / account suspension", r"(?i)\b(suspended|blocked|deactivated|locked|legal action|arrest|police|penalty|terminated|band ho|block ho)\b", 18, "Threatens consequences to push you into acting."),
    ("Gift cards / crypto", r"(?i)\b(gift ?cards?|itunes card|google play card|bitcoin|btc|usdt|crypto)\b", 18, "Gift-card or crypto payment requests are hard to reverse."),
    ("Asks to click / log in", r"(?i)\b(click (here|the link|below)|log ?in|sign ?in|verify your (account|identity)|update your (details|account|kyc)|confirm your)\b", 14, "Pushes you towards a link or login page."),
    ("Authority impersonation", r"(?i)\b(bank|state bank|sbp|fia|nadra|bisp|fbr|customer (care|support)|security team|helpline|courier|customs)\b", 8, "Claims to come from an institution or authority."),
    ("Secrecy request", r"(?i)\b(do not tell|don't tell|keep (this )?(secret|confidential)|nobody should know|kisi ko na batana)\b", 16, "Asks you to keep it secret from family or the bank."),
    ("Moves chat to WhatsApp/Telegram", r"(?i)\b(whatsapp me|message me on (whatsapp|telegram))\b", 10, "Moves the conversation to a less moderated channel."),
]


def extract_urls(text: str) -> list[str]:
    seen, out = set(), []
    for m in URL_RE.findall(text or ""):
        u = m.rstrip(".,;:!?")
        if u.lower() not in seen:
            seen.add(u.lower())
            out.append(u)
    return out[:10]


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not re.match(r"(?i)^[a-z][a-z0-9+.-]*://", url):
        url = "http://" + url
    return url


def registered_domain(host: str) -> str:
    parts = host.lower().strip(".").split(".")
    if len(parts) <= 2:
        return ".".join(parts)
    if len(parts[-1]) == 2 and parts[-2] in SECOND_LEVEL:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _lookalike_brand(host: str):
    reg = registered_domain(host)
    label = reg.split(".")[0]
    deleet = label.translate(str.maketrans("01$5", "olss")).replace("rn", "m").replace("vv", "w")
    for brand, legit in BRANDS.items():
        if reg in legit:
            return None
    for brand in BRANDS:
        if brand in host.replace("-", "") or brand in deleet:
            return brand
    # "paypa1" style: digit 1 can be l or i
    alt = label.replace("1", "l")
    for brand in BRANDS:
        if brand in alt:
            return brand
    return None


def analyze_url_signals(url: str) -> dict:
    """Return {'risk': 0-100, 'findings': [..], 'extracted': {...}} for one URL."""
    raw = url
    url = normalize_url(url)
    findings: list[dict] = []
    risk = 0
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower()
    except ValueError:
        return {"risk": 60, "findings": [{"title": "Malformed URL", "detail": "The address cannot be parsed properly.", "weight": 60}], "extracted": {"url": raw}}

    def add(title, detail, weight):
        nonlocal risk
        risk += weight
        findings.append({"title": title, "detail": detail, "weight": weight})

    if not host:
        add("No valid host", "The address has no readable domain.", 50)
    if p.scheme == "http":
        add("No HTTPS", "The link does not use an encrypted connection.", 12)
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
        add("IP address instead of a domain", "Legitimate services almost never use a bare IP in links.", 35)
    if "xn--" in host:
        add("Punycode domain", "May be hiding look-alike characters (e.g. Cyrillic letters).", 30)
    if "@" in (p.netloc or ""):
        add("'@' inside the address", "Everything before '@' is ignored by the browser, a common trick to disguise the real site.", 35)
    reg = registered_domain(host) if host else ""
    if reg in SHORTENERS or host in SHORTENERS:
        add("Link shortener", "The real destination is hidden behind a short link.", 20)
    tld = host.rsplit(".", 1)[-1] if "." in host else ""
    if tld in RISKY_TLDS:
        add(f"Risky domain ending (.{tld})", "This ending is cheap and heavily abused for scams.", 18)
    if host.count(".") >= 3:
        add("Many sub-domains", "Long sub-domain chains are used to make fake pages look official.", 14)
    if host.count("-") >= 2:
        add("Hyphens in domain", "Several hyphens are typical for throw-away scam domains.", 10)
    if len(url) > 100:
        add("Very long address", "Long URLs can bury the real destination.", 8)
    brand = _lookalike_brand(host) if host else None
    if brand:
        add(f"Pretends to be {brand.title()}", f"The domain '{reg}' is not an official {brand.title()} domain.", 40)
    hits = [w for w in PATH_WORDS if w in (p.path + "?" + (p.query or "")).lower() or w in host]
    if hits:
        add("Sensitive words in address", "Contains: " + ", ".join(hits[:4]) + ".", min(8 + 4 * len(hits), 20))
    if host and not findings:
        findings.append({"title": "No structural red flags", "detail": "The address itself looks ordinary. This does not prove the site is safe.", "weight": 0})
    return {"risk": min(risk, 100), "findings": findings,
            "extracted": {"url": raw, "host": host, "registered_domain": reg, "scheme": p.scheme}}


def analyze_text_signals(text: str) -> dict:
    findings, risk = [], 0
    for label, rx, weight, why in TEXT_RULES:
        m = re.search(rx, text or "")
        if m:
            risk += weight
            findings.append({"title": label, "detail": why, "weight": weight, "evidence": m.group(0)[:60]})
    combo = {f["title"] for f in findings}
    if {"Asks for OTP / PIN / password", "Threat / account suspension"} <= combo or {"Prize / lottery claim", "Money request"} <= combo:
        risk += 15
        findings.append({"title": "Dangerous combination", "detail": "Several scam tactics appear together, which strongly matches known fraud scripts.", "weight": 15})
    if not findings:
        findings.append({"title": "No known scam phrases", "detail": "No common manipulation patterns were found in the wording.", "weight": 0})
    return {"risk": min(risk, 100), "findings": findings, "extracted": {"urls": extract_urls(text), "length": len(text or "")}}


def brand_claims(text: str) -> list[str]:
    t = (text or "").lower()
    return [b for b in BRANDS if re.search(rf"\b{re.escape(b)}\b", t)]


def decode_qr(image_bytes: bytes) -> str | None:
    """Decode a QR image using OpenCV (no system libraries needed)."""
    try:
        import cv2
        import numpy as np
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        det = cv2.QRCodeDetector()
        for candidate in (img,
                          cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC),
                          cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)):
            data, _, _ = det.detectAndDecode(candidate)
            if data:
                return data
    except Exception:
        return None
    return None
