import re
import time
import requests
import phonenumbers
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote, quote_plus
from phonenumbers import geocoder, carrier, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}


def clean_query(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())[:180]


def is_phone(value: str) -> bool:
    clean = re.sub(r"[^\d+]", "", value or "")
    return len(clean) >= 8 and re.match(r"^[+\d]", clean) is not None


def is_email(value: str) -> bool:
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value or "") is not None


def is_domain(value: str) -> bool:
    v = (value or "").strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    return re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", v) is not None


def is_url(value: str) -> bool:
    q = (value or "").strip().lower()
    return q.startswith("http://") or q.startswith("https://")


def guess_type(query: str) -> str:
    q = clean_query(query)
    if is_url(q): return "url"
    if is_phone(q): return "phone"
    if is_email(q): return "email"
    if is_domain(q): return "domain"
    if q.startswith("@"): return "username"
    if re.match(r"^[a-zA-Z0-9._-]{3,32}$", q): return "username"
    if len(q.split()) >= 1: return "name"
    return "general"


def domain_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def extract_real_duck_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    if "duckduckgo.com/l/" in url or url.startswith("/l/"):
        parsed = urlparse(url)
        q = parse_qs(parsed.query)
        if "uddg" in q:
            return unquote(q["uddg"][0])
    return url


def classify_source(url: str, title: str = "", snippet: str = "") -> str:
    host = domain_from_url(url)
    text = f"{url} {title} {snippet}".lower()
    mapping = [
        ("instagram.com", "Instagram"), ("x.com", "X / Twitter"), ("twitter.com", "X / Twitter"),
        ("facebook.com", "Facebook"), ("t.me", "Telegram"), ("telegram", "Telegram"),
        ("linkedin.com", "LinkedIn"), ("github.com", "GitHub"), ("youtube.com", "YouTube"),
        ("youtu.be", "YouTube"), ("tiktok.com", "TikTok"), ("reddit.com", "Reddit"),
        ("vk.com", "VK"), ("whois", "Domain Metadata"), ("crt.sh", "Domain Metadata"),
    ]
    for key, val in mapping:
        if key in host:
            return val
    if "gov" in host or "egov" in host or "gov.kz" in host:
        return "Government"
    if "news" in text or "tengrinews" in host or "zakon" in host or "inform" in host:
        return "News / Media"
    if "scam" in text or "phishing" in text or "fraud" in text:
        return "Safety Context"
    return "Web"


def phone_metadata(raw_phone: str) -> dict:
    raw_phone = (raw_phone or "").strip()
    if not raw_phone:
        return {"ok": False, "message": "Phone number is empty."}
    try:
        region = None if raw_phone.startswith("+") else "KZ"
        number = phonenumbers.parse(raw_phone, region)
    except Exception as e:
        return {"ok": False, "message": str(e)}
    return {
        "ok": True,
        "formatted": {
            "international": phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            "e164": phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164),
        },
        "metadata": {
            "country_code": number.country_code,
            "national_number": str(number.national_number),
            "region_code": phonenumbers.region_code_for_number(number),
            "location_en": geocoder.description_for_number(number, "en"),
            "location_ru": geocoder.description_for_number(number, "ru"),
            "carrier_en": carrier.name_for_number(number, "en"),
            "carrier_ru": carrier.name_for_number(number, "ru"),
            "timezones": list(timezone.time_zones_for_number(number)),
            "is_possible": phonenumbers.is_possible_number(number),
            "is_valid": phonenumbers.is_valid_number(number),
        },
        "privacy_notice": "Public numbering metadata only. Owner, address, SIM registration and private records are not provided."
    }


def build_queries(query: str, query_type: str) -> list[str]:
    q = clean_query(query)
    clean_phone = re.sub(r"[^\d+]", "", q)
    if query_type == "phone":
        return [f'"{clean_phone}"', f'"{clean_phone}" scam OR spam OR fraud OR мошенник OR алаяқ', f'"{clean_phone}" site:t.me', f'"{clean_phone}" site:instagram.com', f'"{clean_phone}" site:facebook.com']
    if query_type == "email":
        return [f'"{q}"', f'"{q}" scam OR spam OR fraud', f'"{q}" site:github.com', f'"{q}" site:linkedin.com']
    if query_type == "username":
        u = q.lstrip("@")
        return [f'"{u}"', f'"{u}" site:instagram.com', f'"{u}" site:t.me', f'"{u}" site:x.com', f'"{u}" site:github.com', f'"@{u}"']
    if query_type == "name":
        return [f'"{q}"', f'"{q}" Kazakhstan OR Қазақстан OR Казахстан', f'"{q}" site:instagram.com', f'"{q}" site:facebook.com', f'"{q}" site:t.me', f'"{q}" site:linkedin.com OR site:github.com']
    if query_type == "domain":
        d = q.replace("https://", "").replace("http://", "").split("/")[0]
        return [d, f'"{d}" phishing OR scam OR fraud', f'"{d}" whois', f'"{d}" certificate transparency']
    if query_type == "url":
        return [q, f'"{q}" scam OR phishing OR fraud']
    return [q, f'"{q}"', f'"{q}" Kazakhstan OR Қазақстан OR Казахстан', f'"{q}" scam OR fraud OR phishing']


def duckduckgo_html_search(query: str, max_results: int = 8) -> list[dict]:
    try:
        r = requests.post("https://html.duckduckgo.com/html/", data={"q": query}, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for item in soup.select(".result"):
            title_el = item.select_one(".result__title a")
            snip_el = item.select_one(".result__snippet")
            if not title_el:
                continue
            title = title_el.get_text(" ", strip=True)
            real_url = extract_real_duck_url(title_el.get("href", ""))
            snippet = snip_el.get_text(" ", strip=True) if snip_el else ""
            if not real_url:
                continue
            results.append({
                "title": title,
                "url": real_url,
                "domain": domain_from_url(real_url),
                "snippet": snippet,
                "category": classify_source(real_url, title, snippet),
                "source": "DuckDuckGo HTML",
                "query_used": query,
            })
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []


def fallback_links(query: str, query_type: str) -> list[dict]:
    return [{
        "title": "Fallback public search",
        "url": "https://www.google.com/search?q=" + quote_plus(q),
        "domain": "google.com",
        "snippet": "Automatic extraction returned no results. Open this public search link manually.",
        "category": "Fallback Search",
        "source": "Fallback",
        "query_used": q,
    } for q in build_queries(query, query_type)]


def dedupe(results: list[dict]) -> list[dict]:
    seen = set(); clean = []
    for item in results:
        url = item.get("url", "").strip()
        if not url or url in seen:
            continue
        seen.add(url); clean.append(item)
    return clean[:40]


def group_results(results: list[dict]) -> dict:
    grouped = {}
    for item in results:
        grouped.setdefault(item.get("category", "Web"), []).append(item)
    return grouped


def security_scan(query: str, query_type: str) -> dict:
    score = 12; findings = []
    q = query.lower()
    if query_type == "url":
        if q.startswith("http://"):
            score += 30; findings.append("HTTP link detected instead of HTTPS.")
        if any(x in q for x in ["login", "verify", "password", "bonus", "gift", "payment"]):
            score += 22; findings.append("Sensitive or social-engineering keyword detected in URL.")
        if q.count("-") >= 3:
            score += 10; findings.append("Many hyphens detected in URL/domain.")
    if query_type == "domain":
        if "-" in q:
            score += 8; findings.append("Domain contains hyphen; review brand impersonation risk.")
        findings.append("Use WHOIS/certificate/public reputation context for domain review.")
    if query_type == "phone":
        score += 8; findings.append("Phone analysis is limited to public metadata and public mentions.")
    if not findings:
        findings.append("No direct technical risk detected from the input format.")
    score = max(0, min(100, score))
    level = "high" if score >= 65 else "medium" if score >= 35 else "low"
    return {"risk_score": score, "risk_level": level, "findings": findings}


def make_summary(query: str, query_type: str, grouped: dict, count: int) -> str:
    cats = "; ".join([f"{k}: {len(v)}" for k, v in grouped.items()])
    s = f"BRIGHTLY found {count} public indexed result(s) for '{query}'. Detected type: {query_type}."
    if cats: s += " Categories: " + cats + "."
    if query_type in ["name", "username"]:
        s += " These are possible public matches, not proof of identity."
    if query_type == "phone":
        s += " Phone owner, address and SIM registration are not provided."
    return s


def deep_public_search(query: str, query_type: str = "auto") -> dict:
    query = clean_query(query)
    if not query:
        return {"ok": False, "message": "Query is empty."}
    if query_type == "auto":
        query_type = guess_type(query)

    phone = phone_metadata(query) if query_type == "phone" else None
    collected = []
    for q in build_queries(query, query_type):
        collected.extend(duckduckgo_html_search(q, 8))
        time.sleep(0.25)
    results = dedupe(collected)
    mode = "duckduckgo_html_results"
    if not results:
        results = fallback_links(query, query_type)
        mode = "fallback_links_only"

    grouped = group_results(results)
    sec = security_scan(query, query_type)
    report = {
        "title": "BRIGHTLY Public Intelligence Report",
        "query": query,
        "query_type": query_type,
        "summary": make_summary(query, query_type, grouped, len(results)),
        "phone_metadata": phone,
        "grouped_results": grouped,
        "source_count": len(results),
        "security": sec,
        "evidence_notes": [
            "Open-source results are leads, not final proof.",
            "Do not treat matching names/usernames as confirmed identity.",
            "Restricted/private data is blocked and shown only as redacted categories."
        ],
        "legal_notice": "This report uses only public indexed web results and public metadata. It does not access private databases, accounts, SIM registration records, passwords, addresses, or hidden personal data."
    }
    return {"ok": True, "mode": mode, "query": query, "query_type": query_type, "report": report, "results": results, "legal_notice": report["legal_notice"]}
