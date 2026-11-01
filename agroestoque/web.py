"""Páginas HTML: interface principal e documentação Swagger."""
from flask import Blueprint, current_app, render_template, send_file

from .config import RAIZ

bp = Blueprint("web", __name__)


@bp.get("/")
def inicio():
    """Página única (SPA); os dados vêm da API em /api/."""
    return render_template("index.html")


@bp.get("/api-docs")
def documentacao():
    return render_template("swagger.html")


@bp.get("/api-docs/openapi.yaml")
def openapi():
    return send_file(RAIZ / "docs" / "api" / "openapi.yaml", mimetype="application/yaml")
