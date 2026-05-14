import logging
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.models.comparison_model import (
    create_comparison,
    delete_comparison,
    get_comparison,
    update_report_paths,
)
from app.services.comparator import compare_data, normalize_records, validation_summary
from app.services.excel_report import generate_excel_report
from app.services.file_reader import read_table
from app.services.filename_utils import display_filename
from app.services.normalizer import decimal_to_str
from app.services.pdf_report import generate_pdf_report


logger = logging.getLogger(__name__)

comparison_bp = Blueprint("comparison", __name__, url_prefix="/comparacoes")


@comparison_bp.route("/executar", methods=["POST"])
def executar():
    comparison_id = None
    try:
        upload_dir = current_app.config["UPLOAD_DIR"].resolve()
        prefeitura_path = Path(request.form["prefeitura_path"]).resolve()
        ipasgo_path = Path(request.form["ipasgo_path"]).resolve()

        if not prefeitura_path.is_relative_to(upload_dir) or not ipasgo_path.is_relative_to(upload_dir):
            flash("Caminho de arquivo inválido.", "error")
            return redirect(url_for("import.nova"))

        pref = read_table(prefeitura_path, request.form.get("prefeitura_sheet") or None, request.form.get("prefeitura_header_row"))
        ipa = read_table(ipasgo_path, request.form.get("ipasgo_sheet") or None, request.form.get("ipasgo_header_row"))

        pref_mapping = {
            "cpf": request.form["prefeitura_cpf"],
            "nome": request.form.get("prefeitura_nome"),
            "valor": request.form["prefeitura_valor"],
        }
        ipa_mapping = {
            "cpf": request.form["ipasgo_cpf"],
            "nome": request.form.get("ipasgo_nome"),
            "valor": request.form["ipasgo_valor"],
        }
        tolerance = Decimal((request.form.get("tolerancia") or "0,00").replace(",", "."))

        pref_rows, pref_invalid = normalize_records(pref["dataframe"], pref_mapping, "Prefeitura")
        ipa_rows, ipa_invalid = normalize_records(ipa["dataframe"], ipa_mapping, "IPASGO")
        pref_summary = validation_summary(pref_rows, pref_invalid)
        ipa_summary = validation_summary(ipa_rows, ipa_invalid)
        rows = compare_data(pref_rows, ipa_rows, pref_invalid, ipa_invalid, tolerance)

        counts = Counter(row["status"] for row in rows)
        soma_pref = pref_summary["soma_total"]
        soma_ipa = ipa_summary["soma_total"]
        summary_report = {
            "Data/hora da comparação": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "Arquivo Prefeitura": display_filename(prefeitura_path.name),
            "Arquivo IPASGO": display_filename(ipasgo_path.name),
            "Total de registros Prefeitura": pref_summary["total_linhas_lidas"],
            "Total de registros IPASGO": ipa_summary["total_linhas_lidas"],
            "Total em comum": counts["OK"] + counts["Divergente"],
            "Total OK": counts["OK"],
            "Total divergente": counts["Divergente"],
            "Total só na Prefeitura": counts["Só na Prefeitura"],
            "Total só no IPASGO": counts["Só no IPASGO"],
            "Total de CPFs duplicados": counts["CPF duplicado na Prefeitura"] + counts["CPF duplicado no IPASGO"],
            "Total de inválidos": counts["Dados inválidos"],
            "Soma Prefeitura": f"R$ {decimal_to_str(soma_pref).replace('.', ',')}",
            "Soma IPASGO": f"R$ {decimal_to_str(soma_ipa).replace('.', ',')}",
            "Diferença total": f"R$ {decimal_to_str(soma_pref - soma_ipa).replace('.', ',')}",
            "Tolerância": f"R$ {decimal_to_str(tolerance).replace('.', ',')}",
        }
        db_summary = {
            "prefeitura_filename": display_filename(prefeitura_path.name),
            "ipasgo_filename": display_filename(ipasgo_path.name),
            "total_prefeitura": pref_summary["total_linhas_lidas"],
            "total_ipasgo": ipa_summary["total_linhas_lidas"],
            "soma_prefeitura": soma_pref,
            "soma_ipasgo": soma_ipa,
            "diferenca_total": soma_pref - soma_ipa,
            "status": "Concluída",
        }
        comparison_id = create_comparison(current_app.config["DB_PATH"], db_summary, rows)

        report_base = current_app.config["REPORT_DIR"] / f"comparacao_{comparison_id:05d}"
        excel_path = report_base.with_suffix(".xlsx")
        pdf_path = report_base.with_suffix(".pdf")
        try:
            generate_excel_report(excel_path, summary_report, rows, pref_rows, ipa_rows, pref_invalid, ipa_invalid)
            generate_pdf_report(pdf_path, summary_report, rows)
            update_report_paths(current_app.config["DB_PATH"], comparison_id, excel_path, pdf_path)
        except Exception:
            logger.exception("Falha ao gerar relatórios para comparação %s", comparison_id)
            delete_comparison(current_app.config["DB_PATH"], comparison_id)
            flash("Erro ao gerar os relatórios. Comparação cancelada.", "error")
            return redirect(url_for("import.nova"))

        flash("Comparação concluída com sucesso.", "success")
        return redirect(url_for("comparison.detalhe", comparison_id=comparison_id))
    except Exception:
        logger.exception("Erro durante a comparação")
        flash("Erro inesperado durante a comparação. Tente novamente.", "error")
        return redirect(url_for("import.nova"))


@comparison_bp.route("/<int:comparison_id>")
def detalhe(comparison_id):
    comparison, rows = get_comparison(current_app.config["DB_PATH"], comparison_id)
    if not comparison:
        flash("Comparação não encontrada.", "error")
        return redirect(url_for("main.comparador"))
    counts = Counter(row["status"] for row in rows)
    return render_template("resultado.html", comparison=comparison, rows=rows, counts=counts)
