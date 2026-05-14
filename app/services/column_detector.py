from app.services.normalizer import normalize_name
from app.services.normalizer import only_digits


CPF_HINTS = ("CPF", "C P F", "DOCUMENTO", "MATRICULA CPF", "CPF SERVIDOR")
NAME_HINTS = ("NOME", "SERVIDOR", "FUNCIONARIO", "FUNCIONÁRIO", "BENEFICIARIO", "BENEFICIÁRIO")
VALUE_HINTS = ("VALOR", "DESCONTO", "CONTRIBUICAO", "CONTRIBUIÇÃO", "TOTAL", "VALOR SISTEMA", "VALOR IPASGO")


def _score(column, hints):
    normalized = normalize_name(column).replace("_", " ")
    return max((len(hint) for hint in hints if hint in normalized), default=0)


def _best_data_column(dataframe, scorer, used=None, minimum_score=1):
    if dataframe is None:
        return None
    used = used or set()
    scored = []
    for column in dataframe.columns:
        if column in used:
            continue
        score = scorer(dataframe[column])
        scored.append((score, column))
    scored.sort(reverse=True)
    if scored and scored[0][0] >= minimum_score:
        return scored[0][1]
    return None


def _cpf_data_score(series):
    values = [str(value).strip() for value in series.head(50) if str(value).strip()]
    if not values:
        return 0
    matches = sum(1 for value in values if len(only_digits(value)) == 11)
    return matches / len(values)


def detect_columns(columns, dataframe=None):
    result = {"cpf": None, "nome": None, "valor": None}
    candidates = list(columns)
    used = set()
    for key, hints in (("cpf", CPF_HINTS), ("nome", NAME_HINTS), ("valor", VALUE_HINTS)):
        scored = sorted(((_score(col, hints), col) for col in candidates if col not in used), reverse=True)
        if scored and scored[0][0] > 0:
            result[key] = scored[0][1]
            used.add(scored[0][1])

    if result["cpf"] is None:
        result["cpf"] = _best_data_column(dataframe, _cpf_data_score, used, minimum_score=0.65)
        if result["cpf"]:
            used.add(result["cpf"])

    return result
