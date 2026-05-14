from datetime import datetime
from pathlib import Path

from app.models.database import get_connection
from app.services.filename_utils import display_filename
from app.services.normalizer import decimal_to_str


def create_comparison(db_path, summary, rows):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO comparisons (
                created_at, prefeitura_filename, ipasgo_filename, total_prefeitura, total_ipasgo,
                soma_prefeitura, soma_ipasgo, diferenca_total, status, excel_report_path, pdf_report_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                summary["prefeitura_filename"],
                summary["ipasgo_filename"],
                summary["total_prefeitura"],
                summary["total_ipasgo"],
                decimal_to_str(summary["soma_prefeitura"]),
                decimal_to_str(summary["soma_ipasgo"]),
                decimal_to_str(summary["diferenca_total"]),
                summary.get("status", "Concluída"),
                summary.get("excel_report_path"),
                summary.get("pdf_report_path"),
            ),
        )
        comparison_id = cursor.lastrowid
        for row in rows:
            conn.execute(
                """
                INSERT INTO comparison_rows (
                    comparison_id, cpf, nome_prefeitura, nome_ipasgo, valor_prefeitura,
                    valor_ipasgo, diferenca, status, observacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    comparison_id,
                    row.get("cpf"),
                    row.get("nome_prefeitura"),
                    row.get("nome_ipasgo"),
                    decimal_to_str(row.get("valor_prefeitura")) if row.get("valor_prefeitura") is not None else "",
                    decimal_to_str(row.get("valor_ipasgo")) if row.get("valor_ipasgo") is not None else "",
                    decimal_to_str(row.get("diferenca")) if row.get("diferenca") is not None else "",
                    row.get("status"),
                    row.get("observacao"),
                ),
            )
        conn.commit()
        return comparison_id


def delete_comparison(db_path, comparison_id):
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT excel_report_path, pdf_report_path FROM comparisons WHERE id = ?",
            (comparison_id,),
        ).fetchone()
        if not row:
            return
        conn.execute("DELETE FROM comparison_rows WHERE comparison_id = ?", (comparison_id,))
        conn.execute("DELETE FROM comparisons WHERE id = ?", (comparison_id,))
        conn.commit()
    for key in ("excel_report_path", "pdf_report_path"):
        path = row[key]
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass


def update_report_paths(db_path, comparison_id, excel_path, pdf_path):
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE comparisons SET excel_report_path = ?, pdf_report_path = ? WHERE id = ?",
            (str(excel_path), str(pdf_path), comparison_id),
        )
        conn.commit()
    cleanup_old_comparisons(db_path)


def list_comparisons(db_path, limit=100):
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM comparisons ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_with_display_filenames(row) for row in rows]


def get_comparison(db_path, comparison_id):
    with get_connection(db_path) as conn:
        comparison = conn.execute("SELECT * FROM comparisons WHERE id = ?", (comparison_id,)).fetchone()
        rows = conn.execute(
            "SELECT * FROM comparison_rows WHERE comparison_id = ? ORDER BY status, cpf",
            (comparison_id,),
        ).fetchall()
        return _with_display_filenames(comparison) if comparison else None, rows


def _with_display_filenames(row):
    data = dict(row)
    data["prefeitura_filename"] = display_filename(data.get("prefeitura_filename"))
    data["ipasgo_filename"] = display_filename(data.get("ipasgo_filename"))
    return data


def cleanup_old_comparisons(db_path, keep=100):
    with get_connection(db_path) as conn:
        old_rows = conn.execute(
            """
            SELECT id, excel_report_path, pdf_report_path
            FROM comparisons
            WHERE id NOT IN (
                SELECT id FROM comparisons ORDER BY id DESC LIMIT ?
            )
            """,
            (keep,),
        ).fetchall()
        old_ids = [row["id"] for row in old_rows]
        if not old_ids:
            return
        placeholders = ",".join("?" for _ in old_ids)
        conn.execute(f"DELETE FROM comparison_rows WHERE comparison_id IN ({placeholders})", old_ids)
        conn.execute(f"DELETE FROM comparisons WHERE id IN ({placeholders})", old_ids)
        conn.commit()

    for row in old_rows:
        for key in ("excel_report_path", "pdf_report_path"):
            path = row[key]
            if path:
                try:
                    Path(path).unlink(missing_ok=True)
                except OSError:
                    pass


def clear_comparison_history(db_path):
    with get_connection(db_path) as conn:
        report_rows = conn.execute(
            "SELECT excel_report_path, pdf_report_path FROM comparisons"
        ).fetchall()
        conn.execute("DELETE FROM comparison_rows")
        conn.execute("DELETE FROM comparisons")
        conn.commit()

    for row in report_rows:
        for key in ("excel_report_path", "pdf_report_path"):
            path = row[key]
            if path:
                try:
                    Path(path).unlink(missing_ok=True)
                except OSError:
                    pass
