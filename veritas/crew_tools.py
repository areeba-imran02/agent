"""Tools the CrewAI agents can call. They wrap the offline heuristics."""
import json

from crewai.tools import tool

from . import heuristics as h


@tool("inspect_url")
def inspect_url(url: str) -> str:
    """Inspect the structure of ONE web address (domain, ending, look-alike brand, shortener, HTTPS, risky words).
    Input: a single URL string. Returns JSON with a risk number 0-100 and findings.
    It cannot open the page; it only analyses the address itself."""
    r = h.analyze_url_signals(url.strip())
    return json.dumps({"url": url, "risk": r["risk"], "host": r["extracted"].get("host"),
                       "registered_domain": r["extracted"].get("registered_domain"),
                       "findings": [f"{f['title']}: {f['detail']}" for f in r["findings"]]}, ensure_ascii=False)


@tool("official_domains")
def official_domains(brand: str) -> str:
    """Look up the OFFICIAL domains of a well-known brand or institution (e.g. 'hbl', 'jazzcash', 'paypal', 'nadra').
    Input: the brand name in lowercase. Returns the official domains or says the brand is not in the verified list."""
    key = brand.strip().lower()
    if key in h.BRANDS:
        return f"Official domains for {key}: {', '.join(h.BRANDS[key])}. Any other domain is NOT official."
    return f"'{key}' is not in the verified brand list. Treat the identity as unverified, not as fake."
