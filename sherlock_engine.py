import re
import os
import shutil
import subprocess
from urllib.parse import urlparse

USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{3,32}$")


def normalize_username(v: str) -> str:
    u = (v or "").strip().lstrip("@").replace("https://", "").replace("http://", "").split("/")[0]
    return u[:32]


def domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def platform(url: str) -> str:
    h = domain(url)
    for k, name in [("instagram.com","Instagram"),("x.com","X / Twitter"),("twitter.com","X / Twitter"),("facebook.com","Facebook"),("t.me","Telegram"),("github.com","GitHub"),("linkedin.com","LinkedIn"),("youtube.com","YouTube"),("tiktok.com","TikTok"),("reddit.com","Reddit"),("pinterest.com","Pinterest")]:
        if k in h: return name
    return "Other Public Site"


def clean_ansi(text: str) -> str:
    return re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", text or "")


def urls_from(text: str) -> list[str]:
    text = clean_ansi(text)
    urls = re.findall(r"https?://[^\s\]\)\"']+", text)
    out=[]
    for u in urls:
        u=u.rstrip(".,;")
        if u not in out: out.append(u)
    return out


def legal_notice() -> str:
    return "Username Intelligence checks public websites only. Results are possible public username matches, not proof of real-world identity."


def demo_results(username: str) -> list[dict]:
    # Demonstrative candidates, not confirmed. Used when Sherlock is not installed.
    bases = [
        ("GitHub", f"https://github.com/{username}"),
        ("Instagram", f"https://www.instagram.com/{username}/"),
        ("X / Twitter", f"https://x.com/{username}"),
        ("Telegram", f"https://t.me/{username}"),
        ("TikTok", f"https://www.tiktok.com/@{username}"),
        ("YouTube", f"https://www.youtube.com/@{username}"),
    ]
    return [{"username": username, "platform": p, "domain": domain(u), "url": u, "status": "candidate_not_verified", "confidence": "low", "note": "Demo candidate URL. Sherlock not installed or disabled."} for p,u in bases]


def run_sherlock(username: str, timeout_seconds: int = 70) -> dict:
    username = normalize_username(username)
    if not USERNAME_RE.match(username):
        return {"ok": False, "message": "Username must be 3–32 chars: letters, numbers, dot, underscore or dash.", "username": username, "results": [], "legal_notice": legal_notice()}

    cmd = os.getenv("SHERLOCK_CMD", "").strip().split() if os.getenv("SHERLOCK_CMD", "").strip() else None
    if not cmd:
        if shutil.which("sherlock"):
            cmd = ["sherlock"]
        else:
            cmd = None

    if not cmd:
        results = demo_results(username)
        return {"ok": True, "mode": "demo_candidates_no_sherlock", "username": username, "found_count": len(results), "results": results, "grouped_results": group(results), "evidence_notes": ["Sherlock is not installed, so these are demo candidate URLs only."], "legal_notice": legal_notice()}

    try:
        proc = subprocess.run(cmd + [username, "--timeout", "10", "--print-found"], capture_output=True, text=True, timeout=timeout_seconds, encoding="utf-8", errors="ignore")
        found_urls = urls_from((proc.stdout or "") + "\n" + (proc.stderr or ""))
        results = [{"username": username, "platform": platform(u), "domain": domain(u), "url": u, "status": "possible_public_match", "confidence": "medium", "note": "Public username match. Not confirmed identity."} for u in found_urls]
        return {"ok": True, "mode": "sherlock_cli", "username": username, "found_count": len(results), "results": results, "grouped_results": group(results), "raw_status": {"returncode": proc.returncode}, "evidence_notes": ["A found profile is a possible username match, not proof of identity.", "The same username may belong to different people."], "legal_notice": legal_notice()}
    except Exception as e:
        results = demo_results(username)
        return {"ok": True, "mode": "demo_candidates_after_sherlock_error", "username": username, "found_count": len(results), "results": results, "grouped_results": group(results), "warning": str(e), "evidence_notes": ["Sherlock execution failed; showing demo candidate URLs only."], "legal_notice": legal_notice()}


def group(results):
    g={}
    for r in results:
        g.setdefault(r.get("platform","Other"), []).append(r)
    return g
