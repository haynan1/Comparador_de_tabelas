from decimal import Decimal

import pandas as pd

from app.services.normalizer import decimal_to_str


MONEY_COLUMNS = {"Valor Prefeitura", "Valor IPASGO", "Diferença", "Diferença Absoluta"}
REPORT_COLUMNS = [
    "CPF",
    "Servidor",
    "Nome Prefeitura",
    "Nome IPASGO",
    "Valor Prefeitura",
    "Valor IPASGO",
    "Diferença",
    "Diferença Absoluta",
    "Status",
    "Observação",
]


def _money(value):
    if value in ("", None):
        return None
    return float(Decimal(str(value)))


def _server_name(row):
    return row.get("servidor") or row.get("nome_prefeitura") or row.get("nome_ipasgo") or ""


def _row_for_report(row):
    return {
        "CPF": row.get("cpf_formatado", ""),
        "Servidor": _server_name(row),
        "Nome Prefeitura": row.get("nome_prefeitura", ""),
        "Nome IPASGO": row.get("nome_ipasgo", ""),
        "Valor Prefeitura": _money(decimal_to_str(row.get("valor_prefeitura"))) if row.get("valor_prefeitura") is not None else None,
        "Valor IPASGO": _money(decimal_to_str(row.get("valor_ipasgo"))) if row.get("valor_ipasgo") is not None else None,
        "Diferença": _money(decimal_to_str(row.get("diferenca"))) if row.get("diferenca") is not None else None,
        "Diferença Absoluta": _money(decimal_to_str(row.get("diferenca_absoluta"))) if row.get("diferenca_absoluta") is not None else None,
        "Status": row.get("status", ""),
        "Observação": row.get("observacao", ""),
    }


def generate_excel_report(path, summary, rows, pref_rows, ipasgo_rows, pref_invalid, ipasgo_invalid):
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        workbook = writer.book
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1})
        money_fmt = workbook.add_format({"num_format": 'R$ #,##0.00;[Red]-R$ #,##0.00'})
        status_fmt = {
            "OK": workbook.add_format({"bg_color": "#E2F0D9"}),
            "Divergente": workbook.add_format({"bg_color": "#FCE4D6"}),
            "Só na Prefeitura": workbook.add_format({"bg_color": "#FFF2CC"}),
            "Só no IPASGO": workbook.add_format({"bg_color": "#FFF2CC"}),
            "CPF duplicado na Prefeitura": workbook.add_format({"bg_color": "#EADCF8"}),
            "CPF duplicado no IPASGO": workbook.add_format({"bg_color": "#EADCF8"}),
            "Dados inválidos": workbook.add_format({"bg_color": "#F4CCCC"}),
        }

        resumo = pd.DataFrame(list(summary.items()), columns=["Indicador", "Valor"])
        resumo.to_excel(writer, sheet_name="Resumo", index=False)
        _format_sheet(writer, "Resumo", resumo, header_fmt, money_fmt)

        categories = [
            ("Divergências", [r for r in rows if r["status"] == "Divergente"]),
            ("OK", [r for r in rows if r["status"] == "OK"]),
            ("Só na Prefeitura", [r for r in rows if r["status"] == "Só na Prefeitura"]),
            ("Só no IPASGO", [r for r in rows if r["status"] == "Só no IPASGO"]),
            ("Duplicados", [r for r in rows if "duplicado" in r["status"].lower()]),
            ("Inválidos", [r for r in rows if r["status"] == "Dados inválidos"]),
        ]
        for sheet, data in categories:
            df = pd.DataFrame([_row_for_report(r) for r in data], columns=REPORT_COLUMNS)
            df.to_excel(writer, sheet_name=sheet, index=False)
            _format_sheet(writer, sheet, df, header_fmt, money_fmt, status_fmt)

        pref_df = _normalized_df(pref_rows, pref_invalid)
        pref_df.to_excel(writer, sheet_name="Base Normalizada Prefeitura", index=False)
        _format_sheet(writer, "Base Normalizada Prefeitura", pref_df, header_fmt, money_fmt)
        ipa_df = _normalized_df(ipasgo_rows, ipasgo_invalid)
        ipa_df.to_excel(writer, sheet_name="Base Normalizada IPASGO", index=False)
        _format_sheet(writer, "Base Normalizada IPASGO", ipa_df, header_fmt, money_fmt)


def _normalized_df(rows, invalid):
    data = []
    for row in rows + invalid:
        data.append(
            {
                "CPF": row.get("cpf_formatado", ""),
                "CPF válido": "Sim" if row.get("cpf_valido") else "Não",
                "Servidor": row.get("nome_original", ""),
                "Nome normalizado": row.get("nome_normalizado", ""),
                "Valor": _money(decimal_to_str(row.get("valor"))) if row.get("valor") is not None else None,
                "Observação": row.get("observacao", ""),
            }
        )
    return pd.DataFrame(data, columns=["CPF", "CPF válido", "Servidor", "Nome normalizado", "Valor", "Observação"])


def _format_sheet(writer, sheet_name, df, header_fmt, money_fmt, status_fmt=None):
    worksheet = writer.sheets[sheet_name]
    worksheet.freeze_panes(1, 0)
    max_row = max(len(df), 1)
    max_col = max(len(df.columns) - 1, 0)
    worksheet.autofilter(0, 0, max_row, max_col)
    for col_idx, column in enumerate(df.columns):
        worksheet.write(0, col_idx, column, header_fmt)
        width = min(max(len(str(column)) + 4, 16), 42)
        fmt = money_fmt if column in MONEY_COLUMNS or column == "Valor" else None
        worksheet.set_column(col_idx, col_idx, width, fmt)
    if sheet_name != "Resumo" and "Status" in df.columns and status_fmt:
        status_col = list(df.columns).index("Status")
        for status, fmt in status_fmt.items():
            worksheet.conditional_format(1, status_col, max_row, status_col, {
                "type": "text",
                "criteria": "containing",
                "value": status,
                "format": fmt,
            })
