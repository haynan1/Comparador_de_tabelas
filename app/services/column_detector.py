from app.services.normalizer import normalize_name


CPF_HINTS = ("CPF", "C P F", "DOCUMENTO", "MATRICULA CPF", "CPF SERVIDOR")
NAME_HINTS = ("NOME", "SERVIDOR", "FUNCIONARIO", "FUNCIONÁRIO", "BENEFICIARIO", "BENEFICIÁRIO")
VALUE_HINTS = ("VALOR", "DESCONTO", "CONTRIBUICAO", "CONTRIBUIÇÃO", "TOTAL", "VALOR SISTEMA", "VALOR IPASGO")


def _score(column, hints):
    normalized = normalize_name(column).replace("_", " ")
    return max((len(hint) for hint in hints if hint in normalized), default=0)


def detect_columns(columns):
    result = {"cpf": None, "nome": None, "valor": None}
    candidates = list(columns)
    for key, hints in (("cpf", CPF_HINTS), ("nome", NAME_HINTS), ("valor", VALUE_HINTS)):
        scored = sorted(((_score(col, hints), col) for col in candidates), reverse=True)
        if scored and scored[0][0] > 0:
            result[key] = scored[0][1]
    return result
