import logging

from flask import Blueprint, current_app, flash, redirect, render_template, url_for

from app.models.comparison_model import clear_comparison_history, list_comparisons


logger = logging.getLogger(__name__)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def dashboard():
    rh_button = {
        "title": "RH",
        "description": "Entrar no sistema de comparação de descontos IPASGO.",
        "href": "/comparacoes",
    }
    return render_template("linktree.html", rh_button=rh_button)


@main_bp.route("/healthz")
def healthz():
    return {"status": "ok"}


@main_bp.route("/comparacoes")
def comparador():
    comparisons = list_comparisons(current_app.config["DB_PATH"])
    return render_template("dashboard.html", comparisons=comparisons)


@main_bp.route("/comparacoes/limpar-historico", methods=["POST"])
def limpar_historico():
    try:
        clear_comparison_history(current_app.config["DB_PATH"])
        flash("Histórico de comparações limpo com sucesso.", "success")
    except Exception:
        logger.exception("Erro ao limpar histórico")
        flash("Erro ao limpar histórico. Tente novamente.", "error")
    return redirect(url_for("main.comparador"))
