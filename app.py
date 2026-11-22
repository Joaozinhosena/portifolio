"""Aplicação Flask do portfólio Module Code.

O app.py cuida somente das rotas e da comunicação entre os serviços e os
templates. Conteúdo editável fica em data/site.json; interface fica em HTML.
"""

from datetime import datetime
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote

from flask import Flask, abort, redirect, render_template, request, send_from_directory, url_for

from services.github_service import GITHUB_USERNAME, get_github_data, prepare_live_projects
from services.site_config import load_manual_project_urls, load_site_config

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
app = Flask(__name__)


def _portfolio_context():
    """Monta os dados compartilhados pelos templates da aplicação."""
    site = load_site_config()
    profile, repositories, github_is_live = get_github_data()
    projects = prepare_live_projects(repositories, load_manual_project_urls())

    if site.get("stats"):
        site["stats"][0] = {
            "value": f"{len(projects):02d}",
            "label": "sites com domínio público",
            "icon": "code",
        }

    return {
        "site": site,
        "github_profile": profile,
        "github_projects": projects,
        "github_categories": sorted({project["category"] for project in projects}),
        "github_username": GITHUB_USERNAME,
        "github_live": github_is_live,
        "github_sync_label": "DOMÍNIOS PUBLICADOS" if github_is_live else "DOMÍNIOS CADASTRADOS",
        "github_sync_note": (
            "A lista reúne apenas projetos com endereço público configurado. "
            "Ao selecionar um card, o visitante abre diretamente o site publicado."
        ),
        "year": datetime.now().year,
    }


@app.get("/")
def home():
    context = _portfolio_context()
    context["site"]["whatsapp_contact_path"] = url_for("whatsapp_contact")
    return render_template("index.html", **context)


@app.get("/projeto/<project_slug>")
def project_detail(project_slug: str):
    """Página descritiva opcional; o card principal continua abrindo o domínio."""
    context = _portfolio_context()

    def normalize(value: str) -> str:
        value = unicodedata.normalize("NFKD", str(value or ""))
        value = value.encode("ascii", "ignore").decode("ascii").lower()
        return re.sub(r"[^a-z0-9]+", "-", value).strip("-")

    project = next(
        (item for item in context["github_projects"] if normalize(item["name"]) == project_slug),
        None,
    )
    if project is None:
        abort(404)
    return render_template(
        "project.html",
        site=context["site"],
        project=project,
        year=context["year"],
    )


@app.route("/contato/whatsapp", methods=["GET", "POST"])
def whatsapp_contact():
    site = load_site_config()
    name = (request.values.get("name") or "").strip()[:80]
    message = (request.values.get("message") or "").strip()[:1200]
    if not message:
        message = "Olá! Conheci seu portfólio e gostaria de conversar sobre um projeto."
    if name:
        message = f"Olá! Meu nome é {name}.\n{message}"

    if site["whatsapp_configured"]:
        destination = f"https://wa.me/{site['whatsapp_number']}?text={quote(message)}"
        return redirect(destination, code=302)

    return render_template(
        "contact_setup.html",
        site=site,
        message=message,
        year=datetime.now().year,
    )


@app.get("/favicon.svg")
def favicon():
    return send_from_directory(PUBLIC_DIR, "favicon.svg", mimetype="image/svg+xml")


@app.get("/<path:filename>")
def public_file(filename: str):
    """Entrega fotos, currículo e outros arquivos colocados em /public."""
    target = PUBLIC_DIR / filename
    if not target.is_file():
        abort(404)
    return send_from_directory(PUBLIC_DIR, filename)


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html", site=load_site_config()), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
