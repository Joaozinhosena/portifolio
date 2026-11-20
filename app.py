"""Portfólio Flask baseado no modelo Module Code.

Edite o dicionário SITE abaixo para personalizar o conteúdo do seu portfólio.
A interface usa classes Tailwind diretamente no HTML (sem arquivos .css).
"""

from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"

app = Flask(__name__)

# Valores de segurança: o template continua funcionando mesmo que o tema ou
# as opções de animação sejam omitidos do dicionário SITE.
DEFAULT_THEME = {
    "preset": "violet",
    "accent": "#7C5CFC",
    "accent_light": "#C4B5FD",
    "accent_rgb": "124,92,252",
    "background": "#0A0A12",
    "surface": "#15151F",
}

DEFAULT_EFFECTS = {
    "particles": True,
    "cursor": True,
    "motion": True,
    "intensity": 82,
}

def build_site_config(raw_config):
    """Completa configurações opcionais antes de enviar os dados ao Jinja."""
    config = dict(raw_config or {})

    raw_theme = config.get("theme")
    theme = dict(raw_theme) if isinstance(raw_theme, dict) else {}
    config["theme"] = {**DEFAULT_THEME, **theme}

    raw_effects = config.get("effects")
    effects = dict(raw_effects) if isinstance(raw_effects, dict) else {}
    config["effects"] = {**DEFAULT_EFFECTS, **effects}

    return config

# -----------------------------------------------------------------------------
# PERSONALIZE AQUI: nome, apresentação, métricas, habilidades, projetos e links.
# -----------------------------------------------------------------------------
SITE = {
    "brand_first": "MODULE",
    "brand_last": "CODE",
    # Frases alternadas no título principal. Remova ou edite à vontade.
    "roles": [
        "Construo experiências digitais.",
        "Desenvolvo aplicações modernas.",
        "Transformo ideias em produtos web.",
    ],
    # Paleta padrão do site. O visitante também pode escolher outra no painel flutuante.
    "theme": {
        "preset": "violet",
        "accent": "#7C5CFC",
        "accent_light": "#C4B5FD",
        "accent_rgb": "124,92,252",
        "background": "#0A0A12",
        "surface": "#15151F",
    },
    # Efeitos habilitados por padrão. O visitante pode ajustar as opções no próprio site.
    "effects": {
        "particles": True,
        "cursor": True,
        "motion": True,
        "intensity": 82,
    },
    "name": "Module Code",
    "role_badge": "SOU DESENVOLVEDOR WEB",
    "headline": "Construo sites que vendem online.",
    "intro": (
        "Desenvolvedor web especializado em criar experiências digitais rápidas, "
        "modernas e feitas sob medida para o seu negócio."
    ),
    "photo_url": "",  # Ex.: /foto-perfil.jpg (coloque a imagem dentro de public/)
    "resume_url": "",  # Ex.: /curriculo.pdf (coloque o PDF dentro de public/)
    "about_title": "Apaixonado por criar soluções digitais",
    "about_text": (
        "Com anos de prática em desenvolvimento web, ajudo empresas e pessoas "
        "a transformar ideias em sites rápidos, funcionais e fáceis de usar."
    ),
    "about_link_text": "Saiba Mais Sobre Mim",
    "stats": [
        {"value": "4+", "label": "Anos de Experiência", "icon": "calendar"},
        {"value": "50+", "label": "Projetos Entregues", "icon": "code"},
        {"value": "30+", "label": "Clientes Satisfeitos", "icon": "smile"},
        {"value": "100%", "label": "Satisfação", "icon": "trophy"},
    ],
    "skills": [
        [
            {"short": "H5", "name": "HTML", "level": 95, "color": "#E8703A"},
            {"short": "C3", "name": "CSS", "level": 90, "color": "#4C9BE0"},
            {"short": "JS", "name": "JavaScript", "level": 90, "color": "#F0CB3A"},
        ],
        [
            {"short": "RX", "name": "React.js", "level": 85, "color": "#56D2E0"},
            {"short": "NX", "name": "Next.js", "level": 80, "color": "#3D3D4D"},
            {"short": "TS", "name": "TypeScript", "level": 85, "color": "#4C7FDB"},
        ],
        [
            {"short": "ND", "name": "Node.js", "level": 80, "color": "#4CAE5A"},
            {"short": "TW", "name": "Tailwind CSS", "level": 90, "color": "#38BFC2"},
            {"short": "GT", "name": "Git", "level": 85, "color": "#E15A3E"},
        ],
    ],
    "projects": [
        {
            "number": "01",
            "name": "Plataforma E-commerce",
            "description": "Solução completa de loja virtual com UI moderna.",
            "url": "#",
            "kind": "store",
            "gradient": "linear-gradient(135deg, #7C5CFC, #C084FC)",
        },
        {
            "number": "02",
            "name": "App de Gestão de Tarefas",
            "description": "Aplicação colaborativa para organizar times e projetos.",
            "url": "#",
            "kind": "tasks",
            "gradient": "linear-gradient(135deg, #1C1C28, #30304A)",
        },
        {
            "number": "03",
            "name": "Dashboard Cripto",
            "description": "Painel em tempo real para acompanhar criptomoedas.",
            "url": "#",
            "kind": "chart",
            "gradient": "#101018",
        },
    ],
    "contact_title": "Tem um projeto em mente?",
    "contact_text": "Estou sempre aberto a discutir novos projetos. Vamos criar algo incrível juntos!",
    "email": "contato@modulecode.dev",
    "phone_display": "+55 11 0000-0000",
    "phone_link": "",  # Ex.: +5511999999999 (somente dígitos e +)
    "testimonial": "Entregou um site rápido, bonito e dentro do prazo combinado. Recomendo o trabalho!",
    "testimonial_author": "Cliente Module Code",
    "testimonial_project": "Projeto via orçamento",
    "socials": [
        {"label": "GH", "name": "GitHub", "url": "#"},
        {"label": "IN", "name": "LinkedIn", "url": "#"},
        {"label": "X", "name": "X / Twitter", "url": "#"},
        {"label": "IG", "name": "Instagram", "url": "#"},
    ],
    "footer_note": "Feito com código, café e atenção aos detalhes.",
}


@app.get("/")
def home():
    return render_template("index.html", site=build_site_config(SITE), year=datetime.now().year)


@app.get("/favicon.svg")
def favicon():
    # Funciona no servidor Flask local. Na Vercel, /public é servido pela CDN.
    return send_from_directory(PUBLIC_DIR, "favicon.svg", mimetype="image/svg+xml")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
