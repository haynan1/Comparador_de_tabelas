from decimal import Decimal

import pandas as pd

from app.services.comparator import compare_data, normalize_records


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
