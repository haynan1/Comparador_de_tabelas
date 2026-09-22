import base64
import re
import zlib
from decimal import Decimal
from itertools import accumulate

import pandas as pd
import pytest

from app.services.comparator import compare_data, normalize_records
from app.services.pdf_report import FRAME_HEIGHT, _cell, _SplittableTable, generate_pdf_report


MAPPING = {"cpf": "CPF", "nome": "Nome", "valor": "Valor"}
LONG_NAME = "MARIA DAS GRACAS APARECIDA DE NAZARE FERREIRA DOS SANTOS OLIVEIRA SOBRENOMEFINAL"
LONG_OBS_TAIL = "FIMDAOBSERVACAO"


def _cpf(seed):
    base = [int(d) for d in f"{seed:09d}"]
    for weight_start in (10, 11):
        total = sum(d * w for d, w in zip(base, range(weight_start, 1, -1)))
        digit = (total * 10) % 11
        base.append(0 if digit == 10 else digit)
    return "".join(map(str, base))


def _unescape_pdf_literal(literal):
    # Literais PDF: \ddd (octal, WinAnsi ~ cp1252), \\, \(, \)
    return re.sub(
        r"\\([0-7]{1,3}|.)",
        lambda m: bytes([int(m.group(1), 8)]).decode("cp1252") if m.group(1)[0].isdigit() else m.group(1),
        literal,
    )


def _pdf_text(path):
    """Extrai os literais de texto de todos os content streams (sem dependências extras)."""
    raw = path.read_bytes()
    chunks = []
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
        data = match.group(1).strip()
        if data.endswith(b"~>"):  # reportlab: [/ASCII85Decode /FlateDecode]
            data = zlib.decompress(base64.a85decode(data[:-2]))
        chunks.append(data.decode("latin-1"))
    literals = re.findall(r"\(((?:\\.|[^\\)])*)\)\s*Tj", "\n".join(chunks))
    return "\n".join(_unescape_pdf_literal(literal) for literal in literals)


def _page_count(path):
    return len(re.findall(rb"/Type\s*/Page[^s]", path.read_bytes()))


@pytest.fixture
def rows():
    pref_data, ipa_data = [], []
    for i in range(1, 121):  # 120 divergências — bem acima do antigo corte de 40
        cpf = _cpf(i)
        pref_data.append({"CPF": cpf, "Nome": f"SERVIDOR {i}", "Valor": "1234,56"})
        ipa_data.append({"CPF": cpf, "Nome": f"SERVIDOR {i}", "Valor": "1000,00"})
    for i in range(300, 360):  # 60 só no IPASGO
        ipa_data.append({"CPF": _cpf(i), "Nome": f"SO IPASGO {i}", "Valor": "7,00"})
    pref_data.append({"CPF": _cpf(900), "Nome": LONG_NAME, "Valor": "50,00"})
    pref_data.append({"CPF": _cpf(901), "Nome": "A & B <Ltda>", "Valor": "5,00"})
    pref_data.append({"CPF": _cpf(902), "Nome": "DUPLICADO", "Valor": "5,00"})
    pref_data.append({"CPF": _cpf(902), "Nome": "DUPLICADO", "Valor": "5,00"})

    pref, pref_invalid = normalize_records(pd.DataFrame(pref_data), MAPPING, "Prefeitura")
    ipa, ipa_invalid = normalize_records(pd.DataFrame(ipa_data), MAPPING, "IPASGO")
    result = compare_data(pref, ipa, pref_invalid, ipa_invalid, Decimal("0.01"))
    long_obs = "observação muito longa " * 12 + LONG_OBS_TAIL
    for row in result:
        if row["servidor"] == LONG_NAME:
            row["observacao"] = long_obs
    return result


def _generate(tmp_path, rows):
    path = tmp_path / "rel.pdf"
    generate_pdf_report(path, {"Arquivo Prefeitura": "prefeitura & cia.xlsx"}, rows)
    return path


def test_pdf_lists_every_record_of_every_section(tmp_path, rows):
    text = _pdf_text(_generate(tmp_path, rows))

    listed = [
        r for r in rows
        if r["status"] in ("Divergente", "Só na Prefeitura", "Só no IPASGO") or "duplicado" in r["status"].lower()
    ]
    assert sum(r["status"] == "Divergente" for r in listed) == 120
    for row in listed:
        assert row["cpf_formatado"] in text, f"{row['cpf_formatado']} ({row['status']}) ausente do PDF"


def test_pdf_keeps_original_layout(tmp_path, rows):
    text = _pdf_text(_generate(tmp_path, rows))

    for title in (
        "Relatório de Comparação de Descontos IPASGO",
        "Resumo Geral",
        "Tabela principal de divergências",
        "Registros só na Prefeitura",
        "Registros só no IPASGO",
        "Duplicados",
        "Observações finais",
    ):
        assert title in text
    for column in ("CPF", "Servidor", "Valor Pref.", "Valor IPASGO", "Dif.", "Status", "Obs."):
        assert column in text
    assert "R$ 1234,56" in text and "R$ 234,56" in text  # formato de valor original


def test_pdf_does_not_truncate_text(tmp_path, rows):
    text = "".join(_pdf_text(_generate(tmp_path, rows)).split())

    assert "SOBRENOMEFINAL" in text  # antes: Servidor cortado em 34 caracteres
    assert LONG_OBS_TAIL in text  # antes: Obs. cortada em 45 caracteres
    assert "A&B<Ltda>" in text  # markup escapado, não interpretado


def test_pdf_repeats_header_on_every_table_page(tmp_path, rows):
    path = _generate(tmp_path, rows)
    pages = _page_count(path)
    assert pages > 3
    # Todas as páginas, exceto a capa, contêm tabela de resultados com cabeçalho.
    assert _pdf_text(path).count("Valor Pref.") >= pages - 1


def test_pdf_empty_comparison(tmp_path):
    path = tmp_path / "vazio.pdf"
    generate_pdf_report(path, {}, [])
    assert _pdf_text(path).count("Sem registros") == 4


def _measured_table(heights, header=10):
    table = _SplittableTable(["h"], [[""] for _ in heights], [100])
    table._measures = (header, [0, *accumulate(heights)])
    return table


def test_split_fills_available_height_and_continues():
    first, rest = _measured_table([10] * 100).split(800, 105)
    assert len(first._cellvalues) == 1 + 9  # cabeçalho + 9 linhas (10 + 9*10 <= 105)
    assert rest.start == 9
    assert rest.wrap(800, 1000)[1] == 10 + 91 * 10


def test_split_defers_to_next_page_when_row_does_not_fit():
    assert _measured_table([50, 10]).split(800, 40) == []


def test_split_oversized_row_is_split_inside_the_row():
    table = _SplittableTable(["h"], [[_cell("palavra " * 3000, 100)], ["y"]], [100])
    parts = table.split(800, FRAME_HEIGHT)
    assert len(parts) >= 2
    assert isinstance(parts[-1], _SplittableTable) and parts[-1].start == 1


def test_pdf_numbers_rows_left_of_cpf_restarting_per_section(tmp_path, rows):
    literals = _pdf_text(_generate(tmp_path, rows)).split("\n")
    assert "Nº" in literals
    sections = (
        [r for r in rows if r["status"] == "Divergente"],
        [r for r in rows if r["status"] == "Só no IPASGO"],
        [r for r in rows if "duplicado" in r["status"].lower()],
    )
    for section in sections:
        for number, row in enumerate(section, start=1):
            positions = [i for i, text in enumerate(literals) if text == row["cpf_formatado"]]
            assert any(literals[i - 1] == str(number) for i in positions), (
                f"linha {number} ({row['cpf_formatado']}) sem numeração à esquerda do CPF"
            )
