"""Integração isolada com a API pública do GitHub."""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from services.site_config import safe_external_url

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "Joaozinhosena").strip() or "Joaozinhosena"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
try:
    GITHUB_CACHE_SECONDS = max(60, int(os.getenv("GITHUB_CACHE_SECONDS", "600")))
except ValueError:
    GITHUB_CACHE_SECONDS = 600

_CACHE = {"expires": 0.0, "profile": None, "repos": None, "live": False}
_LOCK = threading.Lock()
_GRADIENTS = [
    "linear-gradient(135deg,#182b4b,#526ca3)",
    "linear-gradient(135deg,#143b34,#4c947e)",
    "linear-gradient(135deg,#3b245e,#8c5cc5)",
    "linear-gradient(135deg,#34233e,#8753a8)",
]
_LANGUAGE_ICONS = {
    "python": "https://cdn.simpleicons.org/python/3776AB",
    "html": "https://cdn.simpleicons.org/html5/E34F26",
    "javascript": "https://cdn.simpleicons.org/javascript/F7DF1E",
    "typescript": "https://cdn.simpleicons.org/typescript/3178C6",
    "css": "https://cdn.simpleicons.org/css3/1572B6",
}

_FALLBACK_REPOS = [
    {
        "name": "odonto",
        "description": "Site institucional de consultório odontológico.",
        "language": "Python",
        "html_url": f"https://github.com/{GITHUB_USERNAME}/odonto",
        "homepage": "",
        "stargazers_count": 0,
        "forks_count": 0,
        "topics": [],
        "updated_at": "",
        "fork": False,
    },
    {
        "name": "gringo",
        "description": "Sistema para cadastro de clientes e agendamento de cortes de cabelo.",
        "language": "Python",
        "html_url": f"https://github.com/{GITHUB_USERNAME}/gringo",
        "homepage": "",
        "stargazers_count": 0,
        "forks_count": 0,
        "topics": [],
        "updated_at": "",
        "fork": False,
    },
    {
        "name": "flashmatty",
        "description": "Repositório público sem descrição cadastrada.",
        "language": "Python",
        "html_url": f"https://github.com/{GITHUB_USERNAME}/flashmatty",
        "homepage": "",
        "stargazers_count": 0,
        "forks_count": 0,
        "topics": [],
        "updated_at": "",
        "fork": False,
    },
    {
        "name": "portifolio",
        "description": "Portfólio Module Code.",
        "language": "HTML",
        "html_url": f"https://github.com/{GITHUB_USERNAME}/portifolio",
        "homepage": "",
        "stargazers_count": 0,
        "forks_count": 0,
        "topics": [],
        "updated_at": "",
        "fork": False,
    },
]


def _api_json(path: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ModuleCodePortfolio/2.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    request = Request(f"https://api.github.com{path}", headers=headers, method="GET")
    with urlopen(request, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"GitHub API respondeu HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def get_github_data(force: bool = False):
    """Busca o perfil e repositórios. Cache e fallback evitam travar o site."""
    now = time.time()
    with _LOCK:
        if not force and _CACHE["profile"] and now < _CACHE["expires"]:
            return _CACHE["profile"], list(_CACHE["repos"] or []), bool(_CACHE["live"])

    username_path = quote(GITHUB_USERNAME, safe="")
    try:
        profile_data = _api_json(f"/users/{username_path}")
        repos_data = _api_json(f"/users/{username_path}/repos?type=owner&sort=updated&direction=desc&per_page=100")
        if not isinstance(profile_data, dict) or not isinstance(repos_data, list):
            raise RuntimeError("Resposta inesperada da API do GitHub")
        repos = [repo for repo in repos_data if isinstance(repo, dict) and not repo.get("fork")]
        profile = {
            "login": profile_data.get("login") or GITHUB_USERNAME,
            "name": profile_data.get("name") or profile_data.get("login") or GITHUB_USERNAME,
            "bio": profile_data.get("bio") or "",
            "avatar_url": safe_external_url(profile_data.get("avatar_url")) or f"https://github.com/{GITHUB_USERNAME}.png",
            "html_url": safe_external_url(profile_data.get("html_url")) or f"https://github.com/{GITHUB_USERNAME}",
            "public_repos": int(profile_data.get("public_repos") or len(repos)),
            "followers": int(profile_data.get("followers") or 0),
        }
        with _LOCK:
            _CACHE.update({"expires": now + GITHUB_CACHE_SECONDS, "profile": profile, "repos": repos, "live": True})
        return profile, repos, True
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError) as error:
        profile = {
            "login": GITHUB_USERNAME,
            "name": "Module Code",
            "bio": "Desenvolvimento web e experiências digitais.",
            "avatar_url": f"https://github.com/{GITHUB_USERNAME}.png",
            "html_url": f"https://github.com/{GITHUB_USERNAME}",
            "public_repos": len(_FALLBACK_REPOS),
            "followers": 0,
        }
        with _LOCK:
            _CACHE.update({"expires": now + 60, "profile": profile, "repos": _FALLBACK_REPOS, "live": False})
        return profile, list(_FALLBACK_REPOS), False


def prepare_live_projects(repositories, manual_urls: dict[str, str]):
    """Prepara somente repositórios com um site externo configurado.

    A URL final do card é o domínio do projeto; links para GitHub não são enviados
    ao template e não podem virar o destino clicável para visitantes.
    """
    projects = []
    for index, repo in enumerate(repositories or [], start=1):
        if not isinstance(repo, dict):
            continue
        name = str(repo.get("name") or "Projeto")
        homepage = manual_urls.get(name.lower()) or safe_external_url(repo.get("homepage"))
        parsed = urlparse(homepage)
        if not homepage or parsed.netloc.lower().endswith("github.com"):
            continue
        language = str(repo.get("language") or "Web")
        updated_raw = str(repo.get("updated_at") or "")
        try:
            updated_label = datetime.fromisoformat(updated_raw.replace("Z", "+00:00")).strftime("%d/%m/%Y") if updated_raw else ""
        except ValueError:
            updated_label = ""
        description = str(repo.get("description") or "Conheça este projeto publicado.")
        projects.append({
            "name": name,
            "description": description,
            "language": language,
            "language_icon_url": _LANGUAGE_ICONS.get(language.lower(), ""),
            "category": language,
            "topics": [str(topic).replace("-", " ") for topic in (repo.get("topics") or [])[:3] if isinstance(topic, str)],
            "homepage_url": homepage,
            "domain": parsed.netloc.removeprefix("www."),
            "stars": int(repo.get("stargazers_count") or 0),
            "updated_label": updated_label,
            "gradient": _GRADIENTS[(index - 1) % len(_GRADIENTS)],
        })
    return projects
