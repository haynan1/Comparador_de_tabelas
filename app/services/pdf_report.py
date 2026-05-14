from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.normalizer import decimal_to_str


def _money(value):
    if value in (None, ""):
        return ""
    return "R$ " + decimal_to_str(value).replace(".", ",")


def _server_name(row):
    return row.get("servidor") or row.get("nome_prefeitura") or row.get("nome_ipasgo") or ""


def generate_pdf_report(path, summary, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Relatório de Comparação de Descontos IPASGO", styles["Title"]))
    story.append(Spacer(1, 14))
    intro = [
        ["Data/hora", summary.get("Data/hora da comparação", "")],
        ["Arquivo Prefeitura", summary.get("Arquivo Prefeitura", "")],
        ["Arquivo IPASGO", summary.get("Arquivo IPASGO", "")],
        ["Total Prefeitura", summary.get("Total de registros Prefeitura", "")],
        ["Total IPASGO", summary.get("Total de registros IPASGO", "")],
        ["Soma Prefeitura", summary.get("Soma Prefeitura", "")],
        ["Soma IPASGO", summary.get("Soma IPASGO", "")],
        ["Diferença total", summary.get("Diferença total", "")],
    ]
    story.append(_table(intro, [150, 520]))
    story.append(PageBreak())

    story.append(Paragraph("Resumo Geral", styles["Heading1"]))
    resumo = [
        ["Indicador", "Quantidade"],
        ["Registros OK", summary.get("Total OK", 0)],
        ["Divergências", summary.get("Total divergente", 0)],
        ["Só na Prefeitura", summary.get("Total só na Prefeitura", 0)],
        ["Só no IPASGO", summary.get("Total só no IPASGO", 0)],
        ["CPFs duplicados", summary.get("Total de CPFs duplicados", 0)],
        ["Registros inválidos", summary.get("Total de inválidos", 0)],
    ]
    story.append(_table(resumo, [260, 160]))
    story.append(Spacer(1, 12))

    for title, data in (
        ("Tabela principal de divergências", [r for r in rows if r["status"] == "Divergente"]),
        ("Registros só na Prefeitura", [r for r in rows if r["status"] == "Só na Prefeitura"]),
        ("Registros só no IPASGO", [r for r in rows if r["status"] == "Só no IPASGO"]),
        ("Duplicados", [r for r in rows if "duplicado" in r["status"].lower()]),
    ):
        story.append(Paragraph(title, styles["Heading2"]))
        story.append(_result_table(data[:40]))
        story.append(Spacer(1, 12))

    story.append(Paragraph("Observações finais", styles["Heading2"]))
    story.append(Paragraph("A comparação foi feita por CPF. A coluna Servidor identifica a pessoa relacionada à diferença.", styles["BodyText"]))
    doc.build(story)


def _result_table(rows):
    data = [["CPF", "Servidor", "Valor Pref.", "Valor IPASGO", "Dif.", "Status", "Obs."]]
    for row in rows:
        data.append([
            row.get("cpf_formatado", ""),
            _server_name(row)[:34],
            _money(row.get("valor_prefeitura")),
            _money(row.get("valor_ipasgo")),
            _money(row.get("diferenca")),
            row.get("status", "")[:24],
            row.get("observacao", "")[:45],
        ])
    if len(data) == 1:
        data.append(["-", "-", "-", "-", "-", "-", "Sem registros"])
    return _table(data, [80, 190, 80, 80, 75, 105, 190])


def _table(data, widths):
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B7B7B7")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FB")]),
    ]))
    return table
