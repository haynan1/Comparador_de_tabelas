from bisect import bisect_right
from itertools import accumulate
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.normalizer import decimal_to_str


RESULT_WIDTHS = [40, 80, 190, 80, 80, 75, 105, 150]  # Nº comporta até 6 dígitos
FONT_SIZE = 8
LINE_HEIGHT = 12  # leading padrão do Table do reportlab
CELL_PAD_H = 6  # padding horizontal padrão do Table (cada lado)
CELL_PAD_V = 3  # padding vertical padrão do Table (cada lado)
# Altura útil do frame: página - margens (24pt cada) - padding do Frame (6pt cada).
FRAME_HEIGHT = landscape(A4)[1] - 2 * 24 - 2 * 6
WRAP_STYLE = ParagraphStyle("CellWrap", fontName="Helvetica", fontSize=FONT_SIZE, leading=LINE_HEIGHT - 2)


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
        story.append(_result_table(data))
        story.append(Spacer(1, 12))

    story.append(Paragraph("Observações finais", styles["Heading2"]))
    story.append(Paragraph("A comparação foi feita por CPF. A coluna Servidor identifica a pessoa relacionada à diferença.", styles["BodyText"]))
    doc.build(story)


def _result_table(rows):
    header = ["Nº", "CPF", "Servidor", "Valor Pref.", "Valor IPASGO", "Dif.", "Status", "Obs."]
    if not rows:
        return _table([header, ["-", "-", "-", "-", "-", "-", "-", "Sem registros"]], RESULT_WIDTHS)
    body = []
    for number, row in enumerate(rows, start=1):
        cells = [
            str(number),
            row.get("cpf_formatado", ""),
            _server_name(row),
            _money(row.get("valor_prefeitura")),
            _money(row.get("valor_ipasgo")),
            _money(row.get("diferenca")),
            row.get("status", ""),
            row.get("observacao", ""),
        ]
        body.append([_cell(value, width) for value, width in zip(cells, RESULT_WIDTHS)])
    return _SplittableTable(header, body, RESULT_WIDTHS)


def _cell(value, width):
    """Texto que cabe na coluna fica como string; o que não cabe quebra linha (nunca é cortado)."""
    text = "" if value is None else str(value)
    if "\n" not in text and stringWidth(text, "Helvetica", FONT_SIZE) <= width - 2 * CELL_PAD_H:
        return text
    return Paragraph(escape(text), WRAP_STYLE)


def _row_height(cells, widths):
    tallest = max(
        cell.wrap(width - 2 * CELL_PAD_H, FRAME_HEIGHT)[1] if isinstance(cell, Paragraph) else LINE_HEIGHT
        for cell, width in zip(cells, widths)
    )
    return tallest + 2 * CELL_PAD_V


class _SplittableTable(Flowable):
    """Tabela que quebra entre páginas em tempo linear.

    O Table do reportlab re-mede todas as linhas restantes a cada quebra de
    página (O(n²): 20 mil linhas levam ~27s). Aqui a altura de cada linha é
    medida uma vez e cada quebra é uma busca binária nas somas acumuladas.
    O resultado visual é o mesmo do Table: cabeçalho repetido a cada página.
    """

    def __init__(self, header, rows, widths, start=0, _measures=None):
        super().__init__()
        self.hAlign = "CENTER"
        self.header, self.rows, self.widths, self.start = header, rows, widths, start
        if _measures is None:
            heights = [_row_height(r, widths) for r in rows]
            _measures = (_row_height(header, widths), [0, *accumulate(heights)])
        self._measures = _measures

    def _height(self, end):
        header_height, prefix = self._measures
        return header_height + prefix[end] - prefix[self.start]

    def wrap(self, avail_width, avail_height):
        self.width, self.height = sum(self.widths), self._height(len(self.rows))
        return self.width, self.height

    def split(self, avail_width, avail_height):
        header_height, prefix = self._measures
        end = bisect_right(prefix, avail_height - header_height + prefix[self.start]) - 1
        if end <= self.start:
            if header_height + prefix[self.start + 1] - prefix[self.start] <= FRAME_HEIGHT:
                return []  # a próxima linha cabe numa página nova: deixa o frame avançar
            # Linha maior que uma página inteira: o Table divide a própria linha.
            end = self.start + 1
            parts = self._table(end, split_in_row=True).split(avail_width, avail_height)
            if not parts:
                return []
        else:
            parts = [self._table(end)]
        if end < len(self.rows):
            parts.append(_SplittableTable(self.header, self.rows, self.widths, end, self._measures))
        return parts

    def drawOn(self, canvas, x, y, _sW=0):
        table = self._table(len(self.rows))
        table.wrapOn(canvas, self.width, self.height)
        table.drawOn(canvas, x, y, _sW)

    def _table(self, end, split_in_row=False):
        # Mantém a alternância de cores das linhas contínua entre páginas.
        return _table([self.header] + self.rows[self.start:end], self.widths, zebra_offset=self.start, split_in_row=split_in_row)


def _table(data, widths, zebra_offset=0, split_in_row=False):
    zebra = [colors.white, colors.HexColor("#F7F9FB")]
    if zebra_offset % 2:
        zebra.reverse()
    table = Table(data, colWidths=widths, repeatRows=1, splitInRow=int(split_in_row))
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B7B7B7")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), zebra),
    ]))
    return table
