from app.services.normalizer import format_cpf, is_valid_cpf, normalize_cpf, normalize_name


def test_normalize_cpf_removes_mask():
    assert normalize_cpf("529.982.247-25") == "52998224725"


def test_format_cpf():
    assert format_cpf("52998224725") == "529.982.247-25"


def test_cpf_validation():
    assert is_valid_cpf("52998224725")
    assert not is_valid_cpf("11111111111")


def test_normalize_name_uppercase_without_accents():
    assert normalize_name("  Maria José  da Silva ") == "MARIA JOSE DA SILVA"
