from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, send_file, url_for

from app.models.comparison_model import get_comparison


report_bp = Blueprint("reports", __name__, url_prefix="/relatorios")


@report_bp.route("/<int:comparison_id>/<kind>")
def download(comparison_id, kind):
    comparison, _ = get_comparison(current_app.config["DB_PATH"], comparison_id)
    if not comparison:
        flash("Comparação não encontrada.", "error")
        return redirect(url_for("main.comparador"))
    if kind == "excel":
        path = comparison["excel_report_path"]
    elif kind == "pdf":
        path = comparison["pdf_report_path"]
    else:
        flash("Tipo de relatório inválido.", "error")
        return redirect(url_for("comparison.detalhe", comparison_id=comparison_id))
    file_path = Path(path)
    if not file_path.exists():
        flash("Relatório não encontrado no disco.", "error")
        return redirect(url_for("comparison.detalhe", comparison_id=comparison_id))
    return send_file(file_path, as_attachment=True)
