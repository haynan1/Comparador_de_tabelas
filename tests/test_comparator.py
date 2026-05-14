from decimal import Decimal

import pandas as pd

from app.services.comparator import compare_data, normalize_records, validation_summary


MAPPING = {"cpf": "CPF", "nome": "Nome", "valor": "Valor"}


def _normalize(data, source):
    return normalize_records(pd.DataFrame(data), MAPPING, source)


def test_compare_ok_by_cpf_even_with_different_name_spacing():
    pref, pref_invalid = _normalize([{"CPF": "529.982.247-25", "Nome": "Maria Jose", "Valor": "100,00"}], "Prefeitura")
    ipa, ipa_invalid = _normalize([{"CPF": "52998224725", "Nome": "Maria  Jose", "Valor": "100.00"}], "IPASGO")
    rows = compare_data(pref, ipa, pref_invalid, ipa_invalid)
    assert rows[0]["status"] == "OK"


def test_compare_divergent_value():
    pref, pref_invalid = _normalize([{"CPF": "52998224725", "Nome": "Ana", "Valor": "100,00"}], "Prefeitura")
    ipa, ipa_invalid = _normalize([{"CPF": "52998224725", "Nome": "Ana", "Valor": "90,00"}], "IPASGO")
    rows = compare_data(pref, ipa, pref_invalid, ipa_invalid)
    assert rows[0]["status"] == "Divergente"
    assert rows[0]["diferenca"] == Decimal("10.00")
    assert rows[0]["servidor"] == "Ana"


def test_compare_only_in_one_file():
    pref, pref_invalid = _normalize([{"CPF": "52998224725", "Nome": "Ana", "Valor": "100,00"}], "Prefeitura")
    ipa, ipa_invalid = _normalize([], "IPASGO")
    rows = compare_data(pref, ipa, pref_invalid, ipa_invalid)
    assert rows[0]["status"] == "Só na Prefeitura"


def test_compare_only_in_ipasgo():
    pref, pref_invalid = _normalize([], "Prefeitura")
    ipa, ipa_invalid = _normalize([{"CPF": "52998224725", "Nome": "Ana", "Valor": "100,00"}], "IPASGO")
    rows = compare_data(pref, ipa, pref_invalid, ipa_invalid)
    assert rows[0]["status"] == "Só no IPASGO"


def test_duplicate_cpf_detection():
    pref, pref_invalid = _normalize([
        {"CPF": "52998224725", "Nome": "Ana", "Valor": "100,00"},
        {"CPF": "52998224725", "Nome": "Ana", "Valor": "100,00"},
    ], "Prefeitura")
    ipa, ipa_invalid = _normalize([], "IPASGO")
    rows = compare_data(pref, ipa, pref_invalid, ipa_invalid)
    assert len([r for r in rows if r["status"] == "CPF duplicado na Prefeitura"]) == 2


def test_same_cpf_different_name_generates_warning_not_blocking():
    pref, pref_invalid = _normalize([{"CPF": "52998224725", "Nome": "Maria Jose da Silva", "Valor": "100,00"}], "Prefeitura")
    ipa, ipa_invalid = _normalize([{"CPF": "52998224725", "Nome": "Maria J. Silva", "Valor": "100,00"}], "IPASGO")
    rows = compare_data(pref, ipa, pref_invalid, ipa_invalid)
    assert rows[0]["status"] == "OK"
    assert "diferença no nome" in rows[0]["observacao"]


def test_invalid_data_bucket():
    pref, pref_invalid = _normalize([{"CPF": "", "Nome": "Sem CPF", "Valor": "100,00"}], "Prefeitura")
    ipa, ipa_invalid = _normalize([], "IPASGO")
    rows = compare_data(pref, ipa, pref_invalid, ipa_invalid)
    assert rows[0]["status"] == "Dados inválidos"


def test_within_tolerance_is_ok():
    pref, pref_invalid = _normalize([{"CPF": "52998224725", "Nome": "Ana", "Valor": "100,00"}], "Prefeitura")
    ipa, ipa_invalid = _normalize([{"CPF": "52998224725", "Nome": "Ana", "Valor": "98,00"}], "IPASGO")
    rows = compare_data(pref, ipa, pref_invalid, ipa_invalid, tolerance=Decimal("5.00"))
    assert rows[0]["status"] == "OK"


def test_invalid_cpf_check_digit():
    pref, pref_invalid = _normalize([{"CPF": "11111111111", "Nome": "X", "Valor": "100,00"}], "Prefeitura")
    assert len(pref) == 0
    assert len(pref_invalid) == 1
    assert "dígito verificador" in pref_invalid[0]["observacao"]


def test_validation_summary_soma():
    rows, invalid = _normalize([
        {"CPF": "52998224725", "Nome": "A", "Valor": "100,00"},
        {"CPF": "52998224725", "Nome": "B", "Valor": "50,00"},
    ], "Prefeitura")
    # Both rows have the same CPF, so they'll both be valid individually
    # but soma_total includes all valid rows
    summary = validation_summary(rows, invalid)
    assert summary["total_linhas_lidas"] == len(rows) + len(invalid)


def test_validation_summary_empty():
    summary = validation_summary([], [])
    assert summary["soma_total"] == Decimal("0.00")
    assert summary["total_linhas_lidas"] == 0
