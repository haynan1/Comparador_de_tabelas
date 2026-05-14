import logging
import shutil
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.services.file_reader import SUPPORTED_EXTENSIONS, get_excel_sheets, read_table
from app.services.filename_utils import display_filename, make_upload_filename


logger = logging.getLogger(__name__)

import_bp = Blueprint("import", __name__, url_prefix="/comparacoes")

_XLSX_MAGIC = b"\x50\x4B\x03\x04"
_XLS_MAGIC = b"\xD0\xCF\x11\xE0"


def _validate_mime(path: Path, ext: str) -> bool:
    if ext == ".csv":
        return True
    try:
        header = path.read_bytes()[:4]
    except OSError:
        return False
    if ext == ".xlsx":
        return header == _XLSX_MAGIC
    if ext == ".xls":
        return header == _XLS_MAGIC
    return False


@import_bp.route("/nova", methods=["GET"])
def nova():
    return render_template("nova_comparacao.html")


@import_bp.route("/previsualizar", methods=["POST"])
def previsualizar():
    try:
        prefeitura_path = _get_or_save_file("prefeitura_file", request.form.get("prefeitura_path"))
        ipasgo_path = _get_or_save_file("ipasgo_file", request.form.get("ipasgo_path"))
        if not prefeitura_path or not ipasgo_path:
            flash("Envie os dois arquivos para continuar.", "error")
            return redirect(url_for("import.nova"))

        pref_sheet = request.form.get("prefeitura_sheet") or None
        ipa_sheet = request.form.get("ipasgo_sheet") or None
        pref_header = request.form.get("prefeitura_header_row")
        ipa_header = request.form.get("ipasgo_header_row")

        pref = read_table(prefeitura_path, pref_sheet, pref_header)
        ipa = read_table(ipasgo_path, ipa_sheet, ipa_header)
        return render_template(
            "mapear_colunas.html",
            prefeitura_path=str(prefeitura_path),
            ipasgo_path=str(ipasgo_path),
            prefeitura_filename=display_filename(Path(prefeitura_path).name),
            ipasgo_filename=display_filename(Path(ipasgo_path).name),
            prefeitura=pref,
            ipasgo=ipa,
            prefeitura_sheets=get_excel_sheets(prefeitura_path),
            ipasgo_sheets=get_excel_sheets(ipasgo_path),
            selected_pref_sheet=pref_sheet or "",
            selected_ipa_sheet=ipa_sheet or "",
            prefeitura_header_row=pref_header or pref["header_row"],
            ipasgo_header_row=ipa_header or ipa["header_row"],
        )
    except Exception:
        logger.exception("Erro ao ler arquivos para pré-visualização")
        flash("Erro ao processar os arquivos. Verifique o formato e tente novamente.", "error")
        return redirect(url_for("import.nova"))


def _get_or_save_file(field_name, existing_path):
    if existing_path:
        upload_dir = current_app.config["UPLOAD_DIR"].resolve()
        resolved = Path(existing_path).resolve()
        if resolved.is_relative_to(upload_dir) and resolved.exists():
            return resolved
    file = request.files.get(field_name)
    if not file or not file.filename:
        return None
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Arquivo {file.filename} não tem formato suportado.")
    filename = make_upload_filename(file.filename)
    target = current_app.config["UPLOAD_DIR"] / filename
    with target.open("wb") as output:
        shutil.copyfileobj(file.stream, output)
    if not _validate_mime(target, ext):
        target.unlink(missing_ok=True)
        raise ValueError(f"Conteúdo de {file.filename} não corresponde à extensão informada.")
    return target
