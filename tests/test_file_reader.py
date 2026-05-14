import pandas as pd

from app.services.file_reader import read_table


def test_excel_header_row_is_user_visible_line_number(tmp_path):
    path = tmp_path / "arquivo.xlsx"
    raw = pd.DataFrame(
        [
            ["Relatório mensal", None, None],
            ["Situação", "Nome", "Valor"],
            ["Sem Alteração", "Ana", "10,00"],
        ]
    )
    raw.to_excel(path, index=False, header=False)

    result = read_table(path, header_row="2")

    assert result["header_row"] == 2
    assert result["columns"] == ["Situação", "Nome", "Valor"]
    assert result["preview"][0]["__is_header"] is True
    assert result["preview"][0]["__line_number"] == 2
    assert result["preview"][1]["__line_number"] == 3
    assert result["dataframe"].iloc[0]["Nome"] == "Ana"


def test_csv_preview_keeps_header_visible_with_line_number(tmp_path):
    path = tmp_path / "arquivo.csv"
    path.write_text("CPF;Nome;Valor\n123;Ana;10,00\n", encoding="utf-8")

    result = read_table(path)

    assert result["header_row"] == 1
    assert result["preview"][0]["__is_header"] is True
    assert result["preview"][0]["CPF"] == "CPF"
    assert result["preview"][1]["__line_number"] == 2


def test_csv_respects_user_visible_header_row(tmp_path):
    path = tmp_path / "arquivo.csv"
    path.write_text("Relatório\nCPF;Nome;Valor\n123;Ana;10,00\n", encoding="utf-8")

    result = read_table(path, header_row="2")

    assert result["header_row"] == 2
    assert result["columns"] == ["CPF", "Nome", "Valor"]
    assert result["preview"][0]["__is_header"] is True
    assert result["preview"][1]["__line_number"] == 3
    assert result["dataframe"].iloc[0]["Nome"] == "Ana"
