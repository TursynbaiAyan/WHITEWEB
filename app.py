import os
import re
from datetime import datetime, UTC

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

try:
    from osint_engine import deep_public_search, public_phone_metadata
except Exception:
    deep_public_search = None
    public_phone_metadata = None

try:
    from sherlock_engine import run_sherlock, build_sherlock_document
except Exception:
    run_sherlock = None
    build_sherlock_document = None

try:
    from ai_engine import ask_deepseek
except Exception:
    ask_deepseek = None


load_dotenv()

app = Flask(__name__)
CORS(app)


# ==========================================================
# CONFIG
# ==========================================================

APP_NAME = "BRIGHTLY Intelligence Browser"
APP_VERSION = "1.0.0"

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


# ==========================================================
# BASIC HELPERS
# ==========================================================

def now_iso():
    return datetime.now(UTC).isoformat()


def normalize_text(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def detect_query_type(query: str) -> str:
    q = normalize_text(query)

    if q.startswith("http://") or q.startswith("https://"):
        return "url"

    clean_phone = re.sub(r"[^\d+]", "", q)
    if len(clean_phone) >= 8 and re.match(r"^[+\d]", clean_phone):
        return "phone"

    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", q):
        return "email"

    if q.startswith("@"):
        return "username"

    domain_candidate = q.lower().replace("https://", "").replace("http://", "").split("/")[0]
    if re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", domain_candidate):
        return "domain"

    if re.match(r"^[a-zA-Z0-9._-]{3,32}$", q):
        return "username"

    if len(q.split()) >= 1:
        return "name"

    return "general"


def normalize_phone_for_verified_profile(phone: str) -> str:
    raw = (phone or "").strip()
    clean = re.sub(r"[^\d+]", "", raw)

    if clean.startswith("8") and len(clean) == 11:
        clean = "+7" + clean[1:]

    if clean.startswith("7") and len(clean) == 11:
        clean = "+" + clean

    return clean


# ==========================================================
# LEGAL FILTER
# ==========================================================

PROHIBITED_PATTERNS = [
    "hack account",
    "взлом аккаунта",
    "аккаунт бұзу",
    "steal password",
    "украсть пароль",
    "пароль ұрлау",
    "sms code bypass",
    "обход 2fa",
    "bypass 2fa",
    "ddos",
    "botnet",
    "keylogger",
    "malware",
    "trojan",
    "spyware",
    "private database",
    "жабық база",
    "скрытая база",
    "слить базу",
    "пробив база",
    "bank database",
    "налоговая база взлом",
    "sim база взлом",
    "адрес человека",
    "мекенжайын тап",
    "find home address",
    "найди владельца номера",
    "пробей владельца номера",
]


def legal_filter_agent(query: str, purpose: str = "") -> dict:
    text = f"{query} {purpose}".lower()

    hits = [p for p in PROHIBITED_PATTERNS if p in text]

    if hits:
        return {
            "agent": "Legal Filter Agent",
            "allowed": False,
            "status": "blocked",
            "matched": hits,
            "summary": (
                "The request was blocked because it appears to ask for private, restricted, "
                "or illegal information."
            ),
            "safe_alternative": (
                "BRIGHTLY can only provide public-source analysis, consent-based verified profile records, "
                "phone metadata, domain safety checks, and defensive security reports."
            )
        }

    return {
        "agent": "Legal Filter Agent",
        "allowed": True,
        "status": "approved",
        "summary": "The request is allowed for public-source and consent-based analytical processing."
    }


# ==========================================================
# VERIFIED IDENTITY LAYER
# Consent-based verified profile record
# ==========================================================

VERIFIED_PROFILE_DB = {
    "+77477850528": {
        "full_name": "ТҰРСЫНБАЙ АЯН ЕРЛАНҰЛЫ",
        "phone": "+77477850528",
        "iin": "REDACTED",
        "identity_status": "CONSENT_BASED_VERIFIED_RECORD",

        "sim_layer": {
            "registered_to": "ТҰРСЫНБАЙ АЯН ЕРЛАНҰЛЫ",
            "status": "VERIFIED PROFILE RECORD",
            "operator": "KZ mobile metadata",
            "country": "Kazakhstan"
        },

        "business_layer": {
            "status": "RECORD FOUND",
            "name": "ИП ТҰРСЫНБАЙ",
            "owner": "ТҰРСЫНБАЙ АЯН ЕРЛАНҰЛЫ",
            "activity": "IT services / educational digital products",
            "registry_status": "CONSENT-BASED PROFILE RECORD"
        },

        "data_sources": [
            "User-consented verified profile",
            "Local verified profile record",
            "Public metadata layer",
            "Restricted data protection layer"
        ],

        "legal_notice": (
            "This module displays a user-consented verified profile record. "
            "BRIGHTLY does not access private SIM databases, tax databases, banking systems, "
            "government systems, addresses, passwords, or hidden personal records."
        )
    }
}


def build_restricted_layer(profile=None):
    if profile:
        return {
            "owner_identity": profile["full_name"],
            "sim_registration": profile["sim_layer"]["registered_to"],
            "iin": "REDACTED",
            "address": "BLOCKED — private personal data",
            "banking_data": "NOT ACCESSED",
            "government_database": "NOT ACCESSED",
            "tax_database": "NOT ACCESSED",
            "private_databases": "NOT ACCESSED"
        }

    return {
        "owner_identity": "REDACTED",
        "sim_registration": "BLOCKED",
        "address": "BLOCKED",
        "iin": "REDACTED",
        "banking_data": "NOT ACCESSED",
        "government_database": "NOT ACCESSED",
        "tax_database": "NOT ACCESSED",
        "private_databases": "NOT ACCESSED"
    }


# ==========================================================
# MULTI-AGENT PIPELINE
# ==========================================================

def research_agent(query: str, query_type: str) -> dict:
    sources = []

    if deep_public_search:
        try:
            result = deep_public_search(query, query_type)
            report = result.get("report", {})
            grouped = report.get("grouped_results", {})

            for category, items in grouped.items():
                for item in items:
                    sources.append({
                        "title": item.get("title", "Untitled"),
                        "category": category,
                        "url": item.get("url", ""),
                        "domain": item.get("domain", ""),
                        "snippet": item.get("snippet", ""),
                        "source": item.get("source", "Public web"),
                        "query_used": item.get("query_used", query)
                    })

            return {
                "agent": "Research Agent",
                "status": "completed",
                "query_type": query_type,
                "summary": f"Collected {len(sources)} public indexed source result(s).",
                "mode": result.get("mode"),
                "sources": sources,
                "raw_public_result": result
            }

        except Exception as e:
            return {
                "agent": "Research Agent",
                "status": "warning",
                "query_type": query_type,
                "summary": f"Public search engine failed: {str(e)}",
                "sources": []
            }

    return {
        "agent": "Research Agent",
        "status": "warning",
        "query_type": query_type,
        "summary": "OSINT engine is not available. No public sources collected.",
        "sources": []
    }


def osint_analyst_agent(query: str, query_type: str, research_data: dict) -> dict:
    sources = research_data.get("sources", [])
    categories = {}

    for src in sources:
        cat = src.get("category", "Web")
        categories[cat] = categories.get(cat, 0) + 1

    insights = []

    if query_type == "phone":
        insights.append("Phone analysis is limited to public mentions, metadata, and consent-based verified records.")
        insights.append("The system does not access real SIM registration databases or private records.")

    elif query_type == "name":
        insights.append("Name-based results can refer to different people. Matches are not identity proof.")
        insights.append("Public-source results should be treated as possible references only.")

    elif query_type == "username":
        insights.append("Username footprint can show possible public platform presence.")
        insights.append("The same username may belong to different people across platforms.")

    elif query_type == "domain":
        insights.append("Domain intelligence can include public web mentions, WHOIS-style leads, and security context.")
        insights.append("Domain reputation should be evaluated through multiple public sources.")

    elif query_type == "url":
        insights.append("URL should be checked for transport security, suspicious keywords, impersonation, and public reputation.")

    else:
        insights.append("General public-source results are leads and require human interpretation.")

    return {
        "agent": "OSINT Analyst Agent",
        "status": "completed",
        "summary": "The query was classified and transformed into structured public intelligence categories.",
        "categories": categories,
        "insights": insights
    }


def security_analyst_agent(query: str, query_type: str) -> dict:
    q = query.lower()
    score = 14
    findings = []

    if query_type == "url":
        if q.startswith("http://"):
            score += 25
            findings.append("URL uses HTTP instead of HTTPS.")

        suspicious_words = ["login", "verify", "password", "bonus", "free", "gift", "payment", "wallet", "update"]
        hits = [w for w in suspicious_words if w in q]

        if hits:
            score += 10 + len(hits) * 4
            findings.append("Suspicious action keywords detected: " + ", ".join(hits))

        if "@" in q:
            score += 20
            findings.append("@ symbol detected in URL; it can hide the real destination.")

    elif query_type == "domain":
        domain = q.replace("https://", "").replace("http://", "").split("/")[0]

        if domain.count("-") >= 2:
            score += 10
            findings.append("Domain contains multiple hyphens.")

        if domain.count(".") >= 3:
            score += 10
            findings.append("Domain has many subdomains.")

        findings.append("Domain should be checked against public reputation sources.")

    elif query_type == "phone":
        score += 8
        findings.append("Phone queries require consent-based handling and public metadata limitations.")

    elif query_type == "username":
        score += 5
        findings.append("Username checks are public footprint checks only, not identity verification.")

    elif query_type == "email":
        score += 8
        findings.append("Email checks must use public indexed pages only. No inbox or account access.")

    else:
        findings.append("No direct technical security threat detected from input format.")

    score = max(0, min(score, 100))

    if score >= 65:
        level = "high"
    elif score >= 35:
        level = "medium"
    else:
        level = "low"

    return {
        "agent": "Security Analyst Agent",
        "status": "completed",
        "risk_score": score,
        "risk_level": level,
        "summary": "The input was evaluated from a defensive security perspective.",
        "findings": findings
    }


def report_writer_agent(query, query_type, legal, research, osint, security, verified_profile=None):
    summary = (
        f'BRIGHTLY analyzed "{query}" through a legal multi-agent workflow. '
        f'The system identified the query type as "{query_type}", collected public-source context, '
        f'processed OSINT categories, reviewed security risk, and generated a structured report.'
    )

    if verified_profile:
        summary += " A consent-based verified profile record was also found for this phone number."

    return {
        "agent": "Report Writer Agent",
        "status": "completed",
        "report_title": "BRIGHTLY Multi-Agent Intelligence Report",
        "executive_summary": summary,
        "sections": [
            {
                "title": "Legal Review",
                "content": legal.get("summary", "")
            },
            {
                "title": "Research Findings",
                "content": research.get("summary", "")
            },
            {
                "title": "OSINT Analysis",
                "content": osint.get("summary", "")
            },
            {
                "title": "Security Review",
                "content": security.get("summary", "")
            },
            {
                "title": "Restricted Data Layer",
                "content": (
                    "Sensitive private categories such as IIN, address, banking data, government records, "
                    "private SIM registration systems, and tax systems are blocked or redacted."
                )
            }
        ],
        "final_verdict": {
            "query_type": query_type,
            "risk_score": security.get("risk_score"),
            "risk_level": security.get("risk_level"),
            "legal_status": legal.get("status"),
            "verified_profile_found": bool(verified_profile)
        },
        "generated_at": now_iso()
    }


def run_multi_agent_pipeline(query: str, purpose: str = "General public-source analysis", consent: bool = False):
    query = normalize_text(query)
    query_type = detect_query_type(query)

    legal = legal_filter_agent(query, purpose)

    if not legal.get("allowed"):
        return {
            "query": query,
            "query_type": query_type,
            "blocked": True,
            "pipeline": [legal],
            "final_report": {
                "title": "Request Blocked",
                "summary": legal.get("summary"),
                "safe_alternative": legal.get("safe_alternative")
            }
        }

    verified_profile = None
    restricted_layer = build_restricted_layer()

    if query_type == "phone":
        phone = normalize_phone_for_verified_profile(query)
        profile = VERIFIED_PROFILE_DB.get(phone)

        if profile and consent:
            verified_profile = profile
            restricted_layer = build_restricted_layer(profile)

    research = research_agent(query, query_type)
    osint = osint_analyst_agent(query, query_type, research)
    security = security_analyst_agent(query, query_type)
    report = report_writer_agent(query, query_type, legal, research, osint, security, verified_profile)

    return {
        "query": query,
        "query_type": query_type,
        "blocked": False,
        "pipeline": [legal, research, osint, security, report],
        "sources": research.get("sources", []),
        "osint": osint,
        "security": security,
        "restricted_layer": restricted_layer,
        "verified_profile": verified_profile,
        "final_report": report
    }


# ==========================================================
# ROUTES
# ==========================================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "ok": True,
        "service": APP_NAME,
        "version": APP_VERSION,
        "message": "BRIGHTLY backend is running.",
        "endpoints": [
            "/api/health",
            "/api/system/info",
            "/api/analyze",
            "/api/ai/chat",
            "/api/osint/deep-search",
            "/api/osint/phone",
            "/api/osint/sherlock",
            "/api/identity/verified-profile"
        ]
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "ok": True,
        "service": APP_NAME,
        "version": APP_VERSION,
        "time": now_iso()
    })


@app.route("/api/system/info", methods=["GET"])
def system_info():
    return jsonify({
        "ok": True,
        "system": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "type": "Multi-Agent AI Browser Intelligence Workflow",
            "agents": [
                "Legal Filter Agent",
                "Research Agent",
                "OSINT Analyst Agent",
                "Security Analyst Agent",
                "Report Writer Agent",
                "DeepSeek AI Assistant"
            ],
            "mission": (
                "Transform user input into a legal, structured, public-source intelligence "
                "and defensive security report."
            ),
            "legal_position": (
                "BRIGHTLY uses public-source analysis, consent-based verified records, "
                "metadata, and defensive security logic only. It does not access private SIM, "
                "tax, banking, government, password, address, or hidden databases."
            )
        }
    })


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json() or {}

    query = normalize_text(data.get("query", ""))
    purpose = normalize_text(data.get("purpose", "General public-source analysis"))
    consent = bool(data.get("consent", False))

    if not query:
        return jsonify({
            "ok": False,
            "message": "Query is required."
        }), 400

    result = run_multi_agent_pipeline(query, purpose=purpose, consent=consent)

    return jsonify({
        "ok": True,
        "result": result
    })


@app.route("/api/identity/verified-profile", methods=["POST"])
def identity_verified_profile():
    data = request.get_json() or {}

    phone = normalize_phone_for_verified_profile(data.get("phone", ""))
    consent = bool(data.get("consent"))
    purpose = normalize_text(data.get("purpose", ""))

    if not phone:
        return jsonify({
            "ok": False,
            "message": "Phone number is required."
        }), 400

    if not consent:
        return jsonify({
            "ok": False,
            "message": "Consent confirmation is required for verified identity profile display."
        }), 400

    if not purpose:
        return jsonify({
            "ok": False,
            "message": "Legal purpose is required."
        }), 400

    legal = legal_filter_agent(phone, purpose)
    if not legal.get("allowed"):
        return jsonify({
            "ok": True,
            "blocked": True,
            "answer": legal.get("safe_alternative"),
            "filter": legal
        })

    profile = VERIFIED_PROFILE_DB.get(phone)

    if not profile:
        return jsonify({
            "ok": True,
            "found": False,
            "phone": phone,
            "message": "No consent-based verified profile found for this phone.",
            "restricted_layer": build_restricted_layer(),
            "legal_notice": (
                "BRIGHTLY does not search private SIM, tax, government, banking, "
                "or hidden databases. Only consent-based verified profile records can be displayed."
            )
        })

    return jsonify({
        "ok": True,
        "found": True,
        "mode": "CONSENT_BASED_VERIFIED_PROFILE",
        "phone": phone,
        "purpose": purpose,
        "profile": profile,
        "restricted_layer": build_restricted_layer(profile),
        "warning": (
            "This is a consent-based verified profile record. "
            "It is not a direct lookup from private SIM, tax, banking, or government systems."
        )
    })


@app.route("/api/osint/deep-search", methods=["POST"])
def osint_deep_search():
    data = request.get_json() or {}

    query = normalize_text(data.get("query", ""))
    query_type = normalize_text(data.get("query_type", "auto")).lower()
    consent = bool(data.get("consent"))
    purpose = normalize_text(data.get("purpose", ""))

    if not query:
        return jsonify({
            "ok": False,
            "message": "Query is required."
        }), 400

    if query_type == "auto":
        query_type = detect_query_type(query)

    sensitive_like = query_type in ["phone", "email", "username", "name"]

    if sensitive_like and not consent:
        return jsonify({
            "ok": False,
            "message": "Consent or lawful purpose confirmation is required for sensitive-like public search."
        }), 400

    if sensitive_like and not purpose:
        return jsonify({
            "ok": False,
            "message": "Legal purpose is required for sensitive-like public search."
        }), 400

    legal = legal_filter_agent(query, purpose)

    if not legal.get("allowed"):
        return jsonify({
            "ok": True,
            "blocked": True,
            "answer": legal.get("safe_alternative"),
            "filter": legal
        })

    if not deep_public_search:
        return jsonify({
            "ok": False,
            "message": "osint_engine.py is not available or deep_public_search() could not be imported."
        }), 500

    try:
        result = deep_public_search(query, query_type)
    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"OSINT engine failed: {str(e)}"
        }), 500

    return jsonify({
        "ok": result.get("ok", False),
        "result": result,
        "purpose": purpose,
        "filter": legal
    })


@app.route("/api/osint/phone", methods=["POST"])
def osint_phone():
    data = request.get_json() or {}
    phone = normalize_text(data.get("phone", ""))

    if not phone:
        return jsonify({
            "ok": False,
            "message": "Phone number is required."
        }), 400

    if not public_phone_metadata:
        # fallback minimal parser-less answer
        return jsonify({
            "ok": True,
            "input": phone,
            "formatted": {
                "international": phone,
                "e164": normalize_phone_for_verified_profile(phone)
            },
            "metadata": {
                "country_code": "7" if normalize_phone_for_verified_profile(phone).startswith("+7") else "Unknown",
                "region_code": "KZ" if normalize_phone_for_verified_profile(phone).startswith("+7") else "Unknown",
                "location_en": "Kazakhstan" if normalize_phone_for_verified_profile(phone).startswith("+7") else "Unknown",
                "carrier_en": "Unknown",
                "timezones": ["Asia/Almaty"],
                "is_possible": True,
                "is_valid": True
            },
            "privacy_notice": (
                "Public metadata only. No owner, address, SIM registration, or private records."
            )
        })

    try:
        result = public_phone_metadata(phone)
    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"Phone metadata failed: {str(e)}"
        }), 500

    return jsonify(result)


@app.route("/api/osint/sherlock", methods=["POST"])
def osint_sherlock():
    data = request.get_json() or {}

    username = normalize_text(data.get("username", ""))
    consent = bool(data.get("consent"))
    purpose = normalize_text(data.get("purpose", ""))

    if not username:
        return jsonify({
            "ok": False,
            "message": "Username is required."
        }), 400

    if not consent:
        return jsonify({
            "ok": False,
            "message": "Consent or lawful purpose confirmation is required for username public footprint check."
        }), 400

    if not purpose:
        return jsonify({
            "ok": False,
            "message": "Legal purpose is required."
        }), 400

    legal = legal_filter_agent(username, purpose)

    if not legal.get("allowed"):
        return jsonify({
            "ok": True,
            "blocked": True,
            "answer": legal.get("safe_alternative"),
            "filter": legal
        })

    if not run_sherlock or not build_sherlock_document:
        return jsonify({
            "ok": False,
            "message": "sherlock_engine.py is not available or Sherlock integration could not be imported."
        }), 500

    try:
        result = run_sherlock(username)
        document = build_sherlock_document(result)
    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"Sherlock engine failed: {str(e)}"
        }), 500

    return jsonify({
        "ok": result.get("ok", False),
        "result": result,
        "document": document,
        "purpose": purpose,
        "filter": legal
    })


@app.route("/api/ai/chat", methods=["POST"])
def ai_chat():
    data = request.get_json() or {}

    message = normalize_text(data.get("message", ""))
    context = normalize_text(data.get("context", ""))

    if not message:
        return jsonify({
            "ok": False,
            "message": "Message is required."
        }), 400

    legal = legal_filter_agent(message, context)

    if not legal.get("allowed"):
        return jsonify({
            "ok": True,
            "blocked": True,
            "answer": legal.get("safe_alternative"),
            "filter": legal
        })

    system_prompt = """
You are BRIGHTLY AI, a legal public intelligence and defensive cybersecurity assistant.

Rules:
- Analyze only public-source information, user-consented verified profile records, and metadata.
- Do not reveal private addresses, passwords, SIM registration databases, tax databases, banking data, government records, hidden accounts, or private databases.
- If sensitive data is requested, mark it as REDACTED, BLOCKED, or NOT ACCESSED.
- Explain findings clearly and professionally.
- For names/usernames, say that matches are possible public references, not confirmed identity.
- For phones, explain that metadata and consent-based records are allowed, but owner lookup from private systems is not.
""".strip()

    if ask_deepseek:
        try:
            answer = ask_deepseek(
                message=message,
                context=context,
                system_prompt=system_prompt
            )

            return jsonify({
                "ok": True,
                "answer": answer,
                "filter": legal,
                "provider": "DeepSeek"
            })

        except Exception as e:
            return jsonify({
                "ok": False,
                "answer": f"DeepSeek request failed: {str(e)}",
                "filter": legal
            }), 500

    fallback_answer = (
        "BRIGHTLY AI fallback mode: I can summarize legal public-source findings, "
        "explain risk, and mark restricted personal data as REDACTED/BLOCKED. "
        "DeepSeek is not connected because ai_engine.py or DEEPSEEK_API_KEY is missing."
    )

    return jsonify({
        "ok": True,
        "answer": fallback_answer,
        "filter": legal,
        "provider": "fallback"
    })


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )