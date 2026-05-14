from flask import Blueprint, current_app, flash, redirect, render_template, url_for

from app.models.comparison_model import clear_comparison_history, list_comparisons


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def dashboard():
    utilities = [
        {
            "title": "Comparador de Descontos IPASGO",
            "description": "Importe relatórios, compare por CPF e gere Excel/PDF.",
            "href": "/comparacoes",
            "status": "Disponível",
            "icon": "IP",
        },
        {
            "title": "Nova utilidade",
            "description": "Espaço reservado para outro processo administrativo local.",
            "href": "#",
            "status": "Em breve",
            "icon": "+",
        },
    ]
    return render_template("linktree.html", utilities=utilities)


@main_bp.route("/healthz")
def healthz():
    return {"status": "ok"}


@main_bp.route("/comparacoes")
def comparador():
    comparisons = list_comparisons(current_app.config["DB_PATH"])
    return render_template("dashboard.html", comparisons=comparisons)


@main_bp.route("/comparacoes/limpar-historico", methods=["POST"])
def limpar_historico():
    clear_comparison_history(current_app.config["DB_PATH"])
    flash("Histórico de comparações limpo com sucesso.", "success")
    return redirect(url_for("main.comparador"))
