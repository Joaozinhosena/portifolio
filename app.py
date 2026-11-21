"""Portfólio Module Code — Flask + Tailwind CDN + GSAP.

Personalize o dicionário SITE abaixo. O projeto não utiliza arquivos CSS externos:
os estilos específicos ficam nos templates e o Tailwind é carregado pelo CDN.
"""
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import os
import re
import threading
import time
import unicodedata

from flask import Flask, abort, redirect, render_template, request, send_from_directory, url_for

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
app = Flask(__name__)

DEFAULT_THEME = {
    "preset": "violet",
    "accent": "#8B5CF6",
    "accent_light": "#C4B5FD",
    "accent_rgb": "139,92,246",
    "background": "#09090F",
    "surface": "#14141D",
}
DEFAULT_EFFECTS = {"particles": True, "cursor": True, "motion": True, "intensity": 88}


# Integração com o GitHub. O perfil e os repositórios públicos são consultados
# pela API oficial. O token é opcional e deve ser configurado como variável de
# ambiente na Vercel (nunca coloque um token diretamente neste arquivo).
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "Joaozinhosena").strip() or "Joaozinhosena"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_CACHE_SECONDS = max(60, int(os.getenv("GITHUB_CACHE_SECONDS", "600")))
_GITHUB_CACHE = {"expires": 0.0, "profile": None, "repos": None, "live": False}
_GITHUB_LOCK = threading.Lock()

# Domínios dos projetos para exibir aos visitantes. Cadastre aqui os sites
# publicados; nunca use o endereço do repositório GitHub neste dicionário.
MANUAL_PROJECT_URLS = {
    "odonto": "https://odonto-tan-eta.vercel.app/",
    # "gringo": "https://seu-dominio-real.vercel.app/",
    # "flashmatty": "https://seu-dominio-real.com/",
    # "portifolio": "https://seu-dominio-real.com/",
}


def get_manual_project_urls():
    """Lê domínios reais configurados pelo dono, por nome de repositório.

    Exemplo da variável PROJECT_LIVE_URLS:
    {"odonto":"https://meusite.com","gringo":"https://gringo.vercel.app"}
    """
    result = {
        str(name).strip().lower(): safe_external_url(url)
        for name, url in MANUAL_PROJECT_URLS.items()
        if str(name).strip() and safe_external_url(url)
    }
    raw = os.getenv("PROJECT_LIVE_URLS", "").strip()
    if not raw:
        return result
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        app.logger.warning("PROJECT_LIVE_URLS não contém um JSON válido; usando MANUAL_PROJECT_URLS.")
        return result
    if not isinstance(payload, dict):
        app.logger.warning("PROJECT_LIVE_URLS precisa ser um objeto JSON; usando MANUAL_PROJECT_URLS.")
        return result
    result.update({
        str(name).strip().lower(): safe_external_url(url)
        for name, url in payload.items()
        if str(name).strip() and safe_external_url(url)
    })
    return result

# Cópia mínima de segurança dos quatro repositórios públicos visíveis no perfil
# no momento da integração. Se a API estiver temporariamente indisponível, os
# cards continuam apontando para os repositórios reais, sem inventar demos.
GITHUB_FALLBACK_REPOS = [
    {
        "name": "odonto",
        "description": "Repositório público com um site associado no campo de homepage do GitHub.",
        "language": "Python",
        "html_url": f"https://github.com/{GITHUB_USERNAME}/odonto",
        "homepage": "https://odonto-tan-eta.vercel.app/",
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
        "description": "Repositório público sem descrição cadastrada. Acesse o código para conhecer a implementação.",
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
        "description": "Portfólio Module Code desenvolvido com Flask, Tailwind CSS e templates Jinja.",
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

_REPO_GRADIENTS = [
    "linear-gradient(135deg,#182b4b,#526ca3)",
    "linear-gradient(135deg,#143b34,#4c947e)",
    "linear-gradient(135deg,#3b245e,#8c5cc5)",
    "linear-gradient(135deg,#34233e,#8753a8)",
]


def _github_json(path: str):
    """Consulta a API pública do GitHub usando urllib da biblioteca padrão."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ModuleCodePortfolio/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    req = Request(f"https://api.github.com{path}", headers=headers, method="GET")
    with urlopen(req, timeout=4) as response:
        if response.status != 200:
            raise RuntimeError(f"GitHub API respondeu HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def get_github_data(force: bool = False):
    """Retorna perfil e repositórios; usa cache e fallback real em caso de falha."""
    now = time.time()
    with _GITHUB_LOCK:
        if not force and _GITHUB_CACHE["profile"] and now < _GITHUB_CACHE["expires"]:
            return _GITHUB_CACHE["profile"], list(_GITHUB_CACHE["repos"] or []), bool(_GITHUB_CACHE["live"])

    # A chamada de rede fica fora do lock para não bloquear outras requisições.
    username_path = quote(GITHUB_USERNAME, safe="")
    try:
        profile_data = _github_json(f"/users/{username_path}")
        repo_data = _github_json(f"/users/{username_path}/repos?type=owner&sort=updated&direction=desc&per_page=100")
        if not isinstance(profile_data, dict) or not isinstance(repo_data, list):
            raise RuntimeError("Formato inesperado retornado pela API do GitHub")
        repos = [repo for repo in repo_data if isinstance(repo, dict) and not repo.get("fork")]
        profile = {
            "login": profile_data.get("login") or GITHUB_USERNAME,
            "name": profile_data.get("name") or profile_data.get("login") or GITHUB_USERNAME,
            "bio": profile_data.get("bio") or "",
            "avatar_url": profile_data.get("avatar_url") or f"https://github.com/{GITHUB_USERNAME}.png",
            "html_url": safe_external_url(profile_data.get("html_url")) or f"https://github.com/{GITHUB_USERNAME}",
            "public_repos": int(profile_data.get("public_repos") or len(repos)),
            "followers": int(profile_data.get("followers") or 0),
            "following": int(profile_data.get("following") or 0),
        }
        with _GITHUB_LOCK:
            _GITHUB_CACHE.update({"expires": now + GITHUB_CACHE_SECONDS, "profile": profile, "repos": repos, "live": True})
        return profile, repos, True
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError) as exc:
        profile = {
            "login": GITHUB_USERNAME,
            "name": "Sena",
            "bio": "Desenvolvedor e criador do Module Code.",
            "avatar_url": f"https://github.com/{GITHUB_USERNAME}.png",
            "html_url": f"https://github.com/{GITHUB_USERNAME}",
            "public_repos": len(GITHUB_FALLBACK_REPOS),
            "followers": 0,
            "following": 0,
        }
        with _GITHUB_LOCK:
            # A falha fica em cache por 60 segundos para evitar chamadas em loop.
            _GITHUB_CACHE.update({"expires": now + 60, "profile": profile, "repos": GITHUB_FALLBACK_REPOS, "live": False})
        app.logger.warning("Não foi possível sincronizar o GitHub (%s): %s", GITHUB_USERNAME, exc)
        return profile, list(GITHUB_FALLBACK_REPOS), False


def prepare_github_projects(repos):
    """Normaliza repositórios reais para os cards do portfólio."""
    fallback_by_name = {item["name"].lower(): item for item in GITHUB_FALLBACK_REPOS}
    manual_urls = get_manual_project_urls()
    projects = []
    for index, repo in enumerate(repos or [], 1):
        if not isinstance(repo, dict):
            continue
        name = str(repo.get("name") or "Repositório")
        fallback = fallback_by_name.get(name.lower(), {})
        repo_url = safe_external_url(repo.get("html_url")) or f"https://github.com/{GITHUB_USERNAME}/{quote(name, safe='')}"
        manual_homepage = manual_urls.get(name.lower(), "")
        homepage = manual_homepage or safe_external_url(repo.get("homepage")) or safe_external_url(fallback.get("homepage"))
        # Este endereço antigo do portifolio foi verificado e retornou 404.
        # Só volta a aparecer se um domínio novo for informado em PROJECT_LIVE_URLS.
        if not manual_homepage and name.lower() == "portifolio" and urlparse(homepage).netloc.lower() == "portifolio-azure-two-49.vercel.app":
            homepage = ""
        domain = urlparse(homepage).netloc.lower() if homepage else ""
        language = str(repo.get("language") or fallback.get("language") or "Outras tecnologias")
        description = str(repo.get("description") or fallback.get("description") or "Repositório público sem descrição cadastrada no GitHub.")
        topics = repo.get("topics") if isinstance(repo.get("topics"), list) else fallback.get("topics", [])
        topics = [str(topic).replace("-", " ") for topic in topics[:3] if isinstance(topic, str)]
        updated_raw = str(repo.get("updated_at") or fallback.get("updated_at") or "")
        updated_label = "data indisponível" 
        if updated_raw:
            try:
                updated_label = datetime.fromisoformat(updated_raw.replace("Z", "+00:00")).strftime("%d/%m/%Y")
            except ValueError:
                updated_label = "data indisponível"
        projects.append({
            "name": name,
            "slug": slugify(name),
            "description": description,
            "language": language,
            "category": language,
            "topics": topics,
            "repo_url": repo_url,
            "homepage_url": homepage,
            "domain": domain,
            "stars": int(repo.get("stargazers_count") or fallback.get("stargazers_count") or 0),
            "forks": int(repo.get("forks_count") or fallback.get("forks_count") or 0),
            "updated_label": updated_label,
            "updated_raw": updated_raw,
            "gradient": _REPO_GRADIENTS[(index - 1) % len(_REPO_GRADIENTS)],
            "default_branch": str(repo.get("default_branch") or "main"),
            "visibility": str(repo.get("visibility") or "public"),
        })
    return projects

# -----------------------------------------------------------------------------
# PERSONALIZE AQUI. Links vazios não são exibidos como botões falsos.
# WhatsApp: 55 + DDD + número, somente dígitos. Também aceita WHATSAPP_NUMBER.
# -----------------------------------------------------------------------------
SITE = {
    "brand_first": "MODULE",
    "brand_last": "CODE",
    "name": "Module Code",
    "role_badge": "DESENVOLVEDOR WEB · CRIANDO NA PRÁTICA",
    "headline": "Código com propósito. Experiências que conectam.",
    "roles": [
        "Desenvolvimento web sob medida.",
        "Interfaces rápidas e intuitivas.",
        "Ideias transformadas em produtos digitais.",
    ],
    "intro": (
        "Sou desenvolvedor e gosto de transformar problemas em experiências digitais. "
        "Aqui você encontra sites e aplicações que pode abrir e experimentar diretamente, "
        "com atenção à interface, à funcionalidade e aos detalhes."
    ),
    "photo_url": "",       # Ex.: /foto-perfil.jpg (coloque o arquivo em public/)
    "resume_url": "",      # Ex.: /curriculo.pdf (coloque o arquivo em public/)
    "theme": DEFAULT_THEME.copy(),
    "effects": DEFAULT_EFFECTS.copy(),
    "about_title": "Tecnologia é ferramenta. A experiência é o que importa.",
    "about_text": (
        "Gosto de entender o problema antes de escrever a primeira linha de código. "
        "Busco criar soluções objetivas, com interfaces claras, estrutura organizada "
        "e espaço para evoluir. Esta página reúne projetos com endereço público para "
        "que você possa conhecer o resultado diretamente no navegador."
    ),
    "about_link_text": "Explorar projetos",
    "stats": [
        {"value": "01", "label": "sites com acesso público", "icon": "code"},
        {"value": "100%", "label": "atenção ao responsivo", "icon": "trophy"},
        {"value": "∞", "label": "possibilidades para criar", "icon": "sparkles"},
    ],
    "services": [
        {
            "number": "01", "eyebrow": "PRESENÇA DIGITAL", "title": "Web & interfaces",
            "text": "Páginas e aplicações web com hierarquia visual, navegação intuitiva e atenção à velocidade.",
            "tags": ["Flask", "HTML", "Tailwind", "JavaScript"], "symbol": "↗",
        },
        {
            "number": "02", "eyebrow": "PRODUTO DIGITAL", "title": "Experiências interativas",
            "text": "Componentes que respondem ao usuário, microinterações e animações que ajudam a contar a história.",
            "tags": ["UX", "GSAP", "Motion", "Acessibilidade"], "symbol": "✳",
        },
        {
            "number": "03", "eyebrow": "LÓGICA & INTEGRAÇÃO", "title": "Automação & backend",
            "text": "Rotas, formulários e integrações que conectam a interface a funcionalidades úteis.",
            "tags": ["Python", "Flask", "APIs", "Integrações"], "symbol": "⌘",
        },
        {
            "number": "04", "eyebrow": "EXPERIMENTAÇÃO", "title": "Tecnologia aplicada",
            "text": "Exploração de ideias envolvendo programação, eletrônica e soluções conectadas.",
            "tags": ["Prototipagem", "Lógica", "IoT", "Aprendizado"], "symbol": "⌁",
        },
    ],
    "skills": [
        [
            {"short": "H5", "name": "HTML", "level": 95, "color": "#E8703A"},
            {"short": "TW", "name": "Tailwind CSS", "level": 90, "color": "#38BFC2"},
            {"short": "JS", "name": "JavaScript", "level": 88, "color": "#F0CB3A"},
        ],
        [
            {"short": "PY", "name": "Python", "level": 85, "color": "#4C7FDB"},
            {"short": "FL", "name": "Flask", "level": 82, "color": "#E8E8E8"},
            {"short": "DB", "name": "SQL", "level": 76, "color": "#56D2E0"},
        ],
        [
            {"short": "GT", "name": "Git", "level": 85, "color": "#E15A3E"},
            {"short": "VX", "name": "Vercel", "level": 80, "color": "#B8B8C8"},
            {"short": "GS", "name": "GSAP", "level": 76, "color": "#80D980"},
        ],
    ],
    # Projetos apresentados na seção principal vêm do GitHub (não de demos fictícias).
    "projects": [],
    "process": [
        {"number": "01", "name": "Entender", "title": "Primeiro, a pergunta certa.", "text": "Entender o contexto, o objetivo e quem vai utilizar a solução. Um bom resultado começa com um problema bem definido.", "meta": "CONTEXTO & DIREÇÃO"},
        {"number": "02", "name": "Desenhar", "title": "Dar forma à experiência.", "text": "Organizar conteúdo, jornadas e hierarquia da interface antes de aprofundar a implementação.", "meta": "ESTRUTURA & INTERFACE"},
        {"number": "03", "name": "Construir", "title": "Código que faz sentido.", "text": "Desenvolver as funcionalidades em partes claras, testar os fluxos e manter o projeto fácil de evoluir.", "meta": "DESENVOLVIMENTO"},
        {"number": "04", "name": "Refinar", "title": "Atenção ao detalhe final.", "text": "Revisar responsividade, acessibilidade, desempenho e comportamento real de cada interação.", "meta": "TESTES & ENTREGA"},
    ],
    "principles": [
        {"number": "01", "title": "Intenção", "text": "Cada elemento precisa ter uma função. Menos ruído, mais clareza."},
        {"number": "02", "title": "Consistência", "text": "Uma experiência coerente em telas, componentes e interações."},
        {"number": "03", "title": "Evolução", "text": "Estrutura pensada para receber melhorias sem perder organização."},
        {"number": "04", "title": "Acessibilidade", "text": "Movimento, contraste e navegação devem respeitar quem está usando."},
    ],
    "tech_stack": ["Python", "Flask", "HTML5", "Tailwind CSS", "JavaScript", "GSAP", "ScrollTrigger", "Git", "Vercel", "APIs"],
    "faqs": [
        {"question": "Como posso conhecer os projetos?", "answer": "Na seção de projetos, clique em qualquer card para abrir diretamente o site ou a aplicação publicada. Não é necessário acessar o GitHub nem entender de programação."},
        {"question": "Como posso solicitar um orçamento ou conversar sobre uma ideia?", "answer": "Use o formulário de contato. Com o número configurado, ele abrirá uma conversa no WhatsApp com a mensagem preenchida. Sem número configurado, o site informa como conectar o canal em vez de abrir um link inexistente."},
        {"question": "O site funciona em celular?", "answer": "Sim. A estrutura é responsiva, o menu se adapta a telas menores e efeitos que dependem do mouse são desativados em dispositivos de toque."},
        {"question": "Os projetos funcionam no celular?", "answer": "Os links levam às versões públicas dos projetos. A experiência em cada dispositivo depende da versão publicada de cada site."},
    ],
    "contact_title": "Tem uma ideia para tirar do papel?",
    "contact_text": "Conte um pouco sobre o que você está imaginando. Vamos começar entendendo o desafio e encontrar um caminho para construir algo útil.",
    "email": os.getenv("CONTACT_EMAIL", "ModuleCodes@gmail.com"),
    "whatsapp_number": os.getenv("WHATSAPP_NUMBER", "558173200835"),
    "phone_display": "",
    "phone_link": "",
    "socials": [
        {"label": "GH", "name": "GitHub", "url": os.getenv("GITHUB_URL", f"https://github.com/{GITHUB_USERNAME}")},
        {"label": "IN", "name": "LinkedIn", "url": os.getenv("LINKEDIN_URL", "")},
        {"label": "IG", "name": "Instagram", "url": os.getenv("INSTAGRAM_URL", "")},
    ],
    "footer_note": "Feito com código, intenção e atenção aos detalhes.",
}


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "projeto"


def safe_external_url(value) -> str:
    if not isinstance(value, str):
        return ""
    candidate = value.strip()
    parsed = urlparse(candidate)
    return candidate if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def safe_asset_url(value) -> str:
    if not isinstance(value, str):
        return ""
    candidate = value.strip()
    if candidate.startswith("/") and not candidate.startswith("//") and "\\" not in candidate:
        return candidate
    return safe_external_url(candidate)


def build_site_config(raw_config):
    config = dict(raw_config or {})
    raw_theme = config.get("theme") if isinstance(config.get("theme"), dict) else {}
    config["theme"] = {**DEFAULT_THEME, **raw_theme}
    raw_effects = config.get("effects") if isinstance(config.get("effects"), dict) else {}
    config["effects"] = {**DEFAULT_EFFECTS, **raw_effects}

    defaults = {
        "brand_first": "MEU", "brand_last": "PORTFÓLIO", "name": "Meu Portfólio",
        "role_badge": "DESENVOLVEDOR", "headline": "Construindo experiências digitais.",
        "roles": [], "intro": "Conheça meus projetos.", "about_title": "Sobre mim",
        "about_text": "", "about_link_text": "Ver projetos", "stats": [], "skills": [],
        "services": [], "process": [], "principles": [], "tech_stack": [], "faqs": [],
        "contact_title": "Vamos conversar?", "contact_text": "Conte sua ideia.",
        "footer_note": "Feito com cuidado.", "email": "", "whatsapp_number": "",
        "phone_display": "", "phone_link": "", "photo_url": "", "resume_url": "",
    }
    for key, value in defaults.items():
        config.setdefault(key, value)

    config["email"] = str(config.get("email") or "").strip()
    if config["email"] and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", config["email"]):
        config["email"] = ""
    config["whatsapp_number"] = re.sub(r"\D", "", str(config.get("whatsapp_number") or ""))
    config["whatsapp_configured"] = 10 <= len(config["whatsapp_number"]) <= 15
    config["phone_display"] = str(config.get("phone_display") or "")
    config["phone_link"] = re.sub(r"[^0-9+]", "", str(config.get("phone_link") or ""))
    config["photo_url"] = safe_asset_url(config.get("photo_url"))
    config["resume_url"] = safe_asset_url(config.get("resume_url"))
    config["whatsapp_contact_path"] = url_for(
        "whatsapp_contact", message="Olá! Conheci seu portfólio e gostaria de conversar sobre um projeto."
    )
    config["email_href"] = f"mailto:{config['email']}" if config["email"] else ""

    projects = config.get("projects") if isinstance(config.get("projects"), list) else []
    normalized_projects, used_slugs = [], set()
    for index, raw in enumerate(projects, 1):
        if not isinstance(raw, dict):
            continue
        project = dict(raw)
        project["name"] = str(project.get("name") or f"Projeto {index}")
        base = slugify(project.get("slug") or project["name"])
        slug, suffix = base, 2
        while slug in used_slugs:
            slug, suffix = f"{base}-{suffix}", suffix + 1
        used_slugs.add(slug)
        project["slug"] = slug
        project["number"] = str(project.get("number") or f"{index:02d}")
        project["category"] = str(project.get("category") or project.get("kind") or "Web")
        project["description"] = str(project.get("description") or "Conheça este projeto.")
        project["details"] = str(project.get("details") or project["description"])
        project["demo_url"] = safe_external_url(project.get("demo_url") or project.get("url"))
        project["repo_url"] = safe_external_url(project.get("repo_url"))
        project["image_url"] = safe_asset_url(project.get("image_url"))
        raw_gallery = project.get("gallery") if isinstance(project.get("gallery"), list) else []
        project["gallery"] = [safe_asset_url(item) for item in raw_gallery if safe_asset_url(item)][:8]
        if not project["gallery"] and project["image_url"]:
            project["gallery"] = [project["image_url"]]
        project["technologies"] = project.get("technologies") if isinstance(project.get("technologies"), list) else []
        project["features"] = project.get("features") if isinstance(project.get("features"), list) else []
        project["status"] = str(project.get("status") or "PROJETO")
        project["kind"] = str(project.get("kind") or "chart")
        project["demo_kind"] = project.get("demo_kind") or project["kind"]
        if project["demo_kind"] not in {"store", "tasks", "chart"}:
            project["demo_kind"] = "chart"
        project["gradient"] = str(project.get("gradient") or "linear-gradient(135deg,#27273A,#15151F)")
        project["detail_path"] = url_for("project_detail", project_slug=slug)
        project["demo_path"] = url_for("project_demo", project_slug=slug)
        project["card_url"] = project["detail_path"]
        project["contact_path"] = url_for("whatsapp_contact", message=f"Olá! Gostaria de conversar sobre {project['name']}.")
        normalized_projects.append(project)
    config["projects"] = normalized_projects
    config["project_categories"] = list(dict.fromkeys(p["category"] for p in normalized_projects))

    socials = config.get("socials") if isinstance(config.get("socials"), list) else []
    config["socials"] = [
        {**social, "name": str(social.get("name") or "Rede social"),
         "label": str(social.get("label") or "↗"), "url": safe_external_url(social.get("url"))}
        for social in socials if isinstance(social, dict) and safe_external_url(social.get("url"))
    ]
    return config


@app.get("/")
def home():
    site = build_site_config(SITE)
    github_profile, raw_repos, github_live = get_github_data()
    # Clientes veem somente sites com domínio real; repositórios sem URL publicada
    # não viram cards nem levam visitantes para o GitHub.
    all_projects = prepare_github_projects(raw_repos)
    github_projects = [project for project in all_projects if project["homepage_url"]]
    github_categories = sorted({project["category"] for project in github_projects if project["category"]})
    if site["stats"]:
        site["stats"][0] = {"value": f"{len(github_projects):02d}", "label": "sites com domínio", "icon": "code"}
    return render_template(
        "index.html",
        site=site,
        year=datetime.now().year,
        github_profile=github_profile,
        github_projects=github_projects,
        github_categories=github_categories,
        github_username=GITHUB_USERNAME,
        github_live=github_live,
        github_sync_label="DOMÍNIOS PUBLICADOS" if github_live else "DOMÍNIOS CADASTRADOS",
        github_sync_note="Somente projetos com endereço público configurado aparecem nesta seção. Cada card abre diretamente o site publicado.",
    )


@app.route("/contato/whatsapp", methods=["GET", "POST"])
def whatsapp_contact():
    site = build_site_config(SITE)
    name = (request.values.get("name") or "").strip()[:80]
    message = (request.values.get("message") or "").strip()[:1200]
    if not message:
        message = "Olá! Conheci seu portfólio e gostaria de conversar sobre um projeto."
    if name:
        message = f"Olá! Meu nome é {name}.\n{message}"
    if site["whatsapp_configured"]:
        return redirect(f"https://wa.me/{site['whatsapp_number']}?text={quote(message)}", code=302)
    return render_template("contact_setup.html", site=site, message=message, year=datetime.now().year)


@app.get("/favicon.svg")
def favicon():
    return send_from_directory(PUBLIC_DIR, "favicon.svg", mimetype="image/svg+xml")


@app.get("/<path:filename>")
def public_file(filename):
    file_path = PUBLIC_DIR / filename
    if not file_path.is_file():
        abort(404)
    return send_from_directory(PUBLIC_DIR, filename)


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html", site=build_site_config(SITE)), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
