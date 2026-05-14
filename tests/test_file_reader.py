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
    assert result["preview"][0]["__line_number"] == 3
    assert result["dataframe"].iloc[0]["Nome"] == "Ana"


def test_csv_preview_keeps_header_visible_with_line_number(tmp_path):
    path = tmp_path / "arquivo.csv"
    path.write_text("CPF;Nome;Valor\n123;Ana;10,00\n", encoding="utf-8")

    result = read_table(path)

    assert result["header_row"] == 1
    assert result["preview"][0]["CPF"] == "123"
    assert result["preview"][0]["__line_number"] == 2


def test_csv_respects_user_visible_header_row(tmp_path):
    path = tmp_path / "arquivo.csv"
    path.write_text("Relatório\nCPF;Nome;Valor\n123;Ana;10,00\n", encoding="utf-8")

    result = read_table(path, header_row="2")

    assert result["header_row"] == 2
    assert result["columns"] == ["CPF", "Nome", "Valor"]
    assert result["preview"][0]["__line_number"] == 3
    assert result["dataframe"].iloc[0]["Nome"] == "Ana"


def test_blank_and_duplicate_headers_are_preserved(tmp_path):
    path = tmp_path / "arquivo.csv"
    path.write_text("CPF;;Valor;Valor\n12345678901;Ana;10,00;20,00\n", encoding="utf-8")

    result = read_table(path)

    assert result["columns"] == ["CPF", "Coluna B", "Valor", "Valor (2)"]
    assert result["analysis"]["unnamed_columns"] == 1
    assert result["analysis"]["duplicate_columns"] == 1
    assert result["dataframe"].iloc[0]["Valor"] == "10,00"
    assert result["dataframe"].iloc[0]["Valor (2)"] == "20,00"


def test_detector_uses_data_without_choosing_status_as_value(tmp_path):
    path = tmp_path / "arquivo.csv"
    path.write_text(
        "Situação;Matrícula;Pessoa;CPF;Desconto\n"
        "Exclusão;6673734;Ana;12345678901;10,00\n"
        "Ativo;6673735;Bia;10987654321;12,50\n",
        encoding="utf-8",
    )

    result = read_table(path)

    assert result["detected"]["cpf"] == "CPF"
    assert result["detected"]["valor"] == "Desconto"
    assert result["detected"]["valor"] != "Situação"


def test_value_requires_header_hint_instead_of_guessing_from_money_like_data(tmp_path):
    path = tmp_path / "arquivo.csv"
    path.write_text(
        "CPF;Nome;Assistência\n"
        "12345678901;Ana;10,00\n"
        "10987654321;Bia;12,50\n",
        encoding="utf-8",
    )

    result = read_table(path)

    assert result["detected"]["cpf"] == "CPF"
    assert result["detected"]["valor"] is None
    assert "Não foi possível identificar a coluna de valor automaticamente." in result["analysis"]["warnings"]
