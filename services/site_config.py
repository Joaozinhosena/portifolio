"""Carrega o conteúdo editável do portfólio sem misturar dados com rotas Flask."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DEFAULT_THEME = {
    "preset": "violet",
    "accent": "#8B5CF6",
    "accent_light": "#C4B5FD",
    "accent_rgb": "139,92,246",
    "background": "#09090F",
    "surface": "#14141D",
}
DEFAULT_EFFECTS = {"particles": True, "cursor": True, "motion": True, "intensity": 88}


def _read_json(path: Path, fallback):
    try:
        with path.open("r", encoding="utf-8") as file:
            value = json.load(file)
        return value if isinstance(value, type(fallback)) else fallback
    except (OSError, json.JSONDecodeError):
        return fallback


def safe_external_url(value: object) -> str:
    if not isinstance(value, str):
        return ""
    candidate = value.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return candidate


def safe_asset_url(value: object) -> str:
    if not isinstance(value, str):
        return ""
    candidate = value.strip()
    if candidate.startswith("/") and not candidate.startswith("//") and "\\" not in candidate:
        return candidate
    return safe_external_url(candidate)


def load_site_config() -> dict:
    """Retorna o conteúdo do data/site.json com substituições do ambiente."""
    site = _read_json(DATA_DIR / "site.json", {})
    site = dict(site)

    site["theme"] = {**DEFAULT_THEME, **(site.get("theme") if isinstance(site.get("theme"), dict) else {})}
    site["effects"] = {**DEFAULT_EFFECTS, **(site.get("effects") if isinstance(site.get("effects"), dict) else {})}

    # Segredos e dados de contato ficam em variáveis de ambiente, não no HTML.
    site["email"] = (os.getenv("CONTACT_EMAIL") or site.get("email") or "").strip()
    if site["email"] and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", site["email"]):
        site["email"] = ""
    site["email_href"] = f"mailto:{site['email']}" if site["email"] else ""

    site["whatsapp_number"] = re.sub(r"\D", "", os.getenv("WHATSAPP_NUMBER") or site.get("whatsapp_number") or "")
    site["whatsapp_configured"] = 10 <= len(site["whatsapp_number"]) <= 15
    site["phone_display"] = str(site.get("phone_display") or "")
    site["phone_link"] = re.sub(r"[^0-9+]", "", str(site.get("phone_link") or ""))
    site["photo_url"] = safe_asset_url(site.get("photo_url"))
    site["resume_url"] = safe_asset_url(site.get("resume_url"))

    social_env = {
        "GitHub": "GITHUB_URL",
        "LinkedIn": "LINKEDIN_URL",
        "Instagram": "INSTAGRAM_URL",
    }
    socials = site.get("socials") if isinstance(site.get("socials"), list) else []
    normalized_socials = []
    for social in socials:
        if not isinstance(social, dict):
            continue
        name = str(social.get("name") or "Rede social")
        env_name = social_env.get(name)
        url = safe_external_url((os.getenv(env_name) or social.get("url")) if env_name else social.get("url"))
        if url:
            normalized_socials.append({
                **social,
                "name": name,
                "label": str(social.get("label") or "↗"),
                "url": url,
            })
    site["socials"] = normalized_socials

    # Valores padrão impedem templates de quebrarem se um campo for removido.
    defaults = {
        "brand_first": "MODULE", "brand_last": "CODE", "name": "Module Code",
        "role_badge": "DESENVOLVEDOR WEB", "headline": "Construindo experiências digitais.",
        "roles": [], "intro": "Conheça meus projetos.", "about_title": "Sobre mim",
        "about_text": "", "about_link_text": "Ver projetos", "stats": [],
        "toolkit": [], "services": [], "process": [], "principles": [],
        "faqs": [], "contact_title": "Vamos conversar?",
        "contact_text": "Conte sua ideia.", "footer_note": "Feito com cuidado.",
    }
    for key, value in defaults.items():
        site.setdefault(key, value)

    # O catálogo aceita apenas imagens HTTPS do host oficial do Simple Icons.
    # Catálogo interativo: texto puro para o painel ser atualizado com textContent,
    # evitando inserir HTML vindo do JSON diretamente no DOM.
    normalized_toolkit = []
    toolkit = site.get("toolkit") if isinstance(site.get("toolkit"), list) else []
    for index, item in enumerate(toolkit, start=1):
        if not isinstance(item, dict):
            continue
        icon_url = safe_external_url(item.get("icon_url"))
        icon_host = urlparse(icon_url).hostname or ""
        normalized_toolkit.append({
            **item,
            "id": re.sub(r"[^a-z0-9-]+", "-", str(item.get("id") or f"tool-{index}").lower()).strip("-") or f"tool-{index}",
            "name": str(item.get("name") or f"Ferramenta {index}"),
            "short": str(item.get("short") or "DEV"),
            "category": str(item.get("category") or "TECNOLOGIA"),
            "tagline": str(item.get("tagline") or "Ferramenta do fluxo de desenvolvimento."),
            "description": str(item.get("description") or ""),
            "project_role": str(item.get("project_role") or ""),
            "context": str(item.get("context") or ""),
            "icon_url": icon_url if icon_host == "cdn.simpleicons.org" else "",
            "color": str(item.get("color") or "#8B5CF6"),
        })
    site["toolkit"] = normalized_toolkit
    return site


def load_manual_project_urls() -> dict[str, str]:
    """Domínios públicos por nome do repositório; nunca publica links do GitHub."""
    urls = _read_json(DATA_DIR / "project_urls.json", {})
    urls = {str(key).strip().lower(): safe_external_url(value) for key, value in urls.items() if str(key).strip()}
    raw = os.getenv("PROJECT_LIVE_URLS", "").strip()
    if raw:
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict):
                urls.update({
                    str(key).strip().lower(): safe_external_url(value)
                    for key, value in payload.items() if str(key).strip()
                })
        except json.JSONDecodeError:
            # Configuração inválida de ambiente não derruba o portfólio.
            pass
    return {key: value for key, value in urls.items() if value}
