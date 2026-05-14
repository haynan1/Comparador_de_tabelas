from collections import Counter
from decimal import Decimal

import pandas as pd

from app.services.normalizer import format_cpf, is_valid_cpf, normalize_cpf, normalize_name, parse_money


def normalize_records(df, mapping, source):
    rows = []
    invalid = []
    cpf_col = mapping["cpf"]
    nome_col = mapping.get("nome")
    valor_col = mapping["valor"]

    for index, row in df.iterrows():
        original_cpf = row.get(cpf_col, "")
        cpf = normalize_cpf(original_cpf)
        value = parse_money(row.get(valor_col, ""))
        original_name = str(row.get(nome_col, "")).strip() if nome_col else ""
        item = {
            "source": source,
            "row_number": int(index) + 1,
            "cpf": cpf,
            "cpf_formatado": format_cpf(cpf),
            "cpf_valido": bool(cpf and is_valid_cpf(cpf)),
            "nome_original": original_name,
            "nome_normalizado": normalize_name(original_name),
            "valor": value,
            "observacao": "",
        }
        issues = []
        if not cpf:
            issues.append("CPF ausente ou inutilizável")
        elif not item["cpf_valido"]:
            issues.append("CPF com dígito verificador inválido")
        if value is None:
            issues.append("Valor inválido")
        if issues:
            item["observacao"] = "; ".join(issues)
            invalid.append(item)
        else:
            rows.append(item)
    return rows, invalid


def validation_summary(rows, invalid_rows):
    counter = Counter(row["cpf"] for row in rows if row.get("cpf"))
    duplicate_cpfs = [cpf for cpf, total in counter.items() if total > 1]
    total = sum((row["valor"] for row in rows if row["valor"] is not None), Decimal("0.00"))
    return {
        "total_linhas_lidas": len(rows) + len(invalid_rows),
        "total_cpfs_validos": len(rows),
        "total_cpfs_duplicados": sum(counter[cpf] for cpf in duplicate_cpfs),
        "registros_sem_cpf": sum(1 for row in invalid_rows if not row.get("cpf")),
        "valores_invalidos": sum(1 for row in invalid_rows if row.get("valor") is None),
        "soma_total": total,
        "duplicate_cpfs": duplicate_cpfs,
    }


def compare_data(pref_rows, ipasgo_rows, pref_invalid=None, ipasgo_invalid=None, tolerance=Decimal("0.00")):
    pref_invalid = pref_invalid or []
    ipasgo_invalid = ipasgo_invalid or []
    tolerance = tolerance if isinstance(tolerance, Decimal) else Decimal(str(tolerance))
    results = []

    pref_counts = Counter(row["cpf"] for row in pref_rows)
    ipasgo_counts = Counter(row["cpf"] for row in ipasgo_rows)
    pref_unique = {row["cpf"]: row for row in pref_rows if pref_counts[row["cpf"]] == 1}
    ipasgo_unique = {row["cpf"]: row for row in ipasgo_rows if ipasgo_counts[row["cpf"]] == 1}

    for cpf, count in pref_counts.items():
        if count > 1:
            for row in [r for r in pref_rows if r["cpf"] == cpf]:
                results.append(_result(cpf, row, None, "CPF duplicado na Prefeitura", "CPF aparece mais de uma vez na Prefeitura"))

    for cpf, count in ipasgo_counts.items():
        if count > 1:
            for row in [r for r in ipasgo_rows if r["cpf"] == cpf]:
                results.append(_result(cpf, None, row, "CPF duplicado no IPASGO", "CPF aparece mais de uma vez no IPASGO"))

    all_cpfs = sorted(set(pref_unique) | set(ipasgo_unique))
    for cpf in all_cpfs:
        pref = pref_unique.get(cpf)
        ipa = ipasgo_unique.get(cpf)
        if pref and ipa:
            diff = pref["valor"] - ipa["valor"]
            obs = ""
            if pref["nome_normalizado"] and ipa["nome_normalizado"] and pref["nome_normalizado"] != ipa["nome_normalizado"]:
                obs = "CPF encontrado nos dois arquivos, mas com diferença no nome."
            status = "OK" if abs(diff) <= tolerance else "Divergente"
            results.append(_result(cpf, pref, ipa, status, obs))
        elif pref:
            results.append(_result(cpf, pref, None, "Só na Prefeitura", "CPF não encontrado no IPASGO"))
        elif ipa:
            results.append(_result(cpf, None, ipa, "Só no IPASGO", "CPF não encontrado na Prefeitura"))

    for row in pref_invalid:
        results.append(_invalid_result(row, "Prefeitura"))
    for row in ipasgo_invalid:
        results.append(_invalid_result(row, "IPASGO"))

    return results


def _result(cpf, pref, ipa, status, obs):
    valor_pref = pref["valor"] if pref else None
    valor_ipa = ipa["valor"] if ipa else None
    diff = (valor_pref or Decimal("0.00")) - (valor_ipa or Decimal("0.00"))
    servidor = ""
    if pref and pref.get("nome_original"):
        servidor = pref["nome_original"]
    elif ipa and ipa.get("nome_original"):
        servidor = ipa["nome_original"]
    return {
        "cpf": cpf,
        "cpf_formatado": format_cpf(cpf),
        "servidor": servidor,
        "nome_prefeitura": pref["nome_original"] if pref else "",
        "nome_ipasgo": ipa["nome_original"] if ipa else "",
        "valor_prefeitura": valor_pref,
        "valor_ipasgo": valor_ipa,
        "diferenca": diff,
        "diferenca_absoluta": abs(diff),
        "status": status,
        "observacao": obs,
    }


def _invalid_result(row, source):
    return {
        "cpf": row.get("cpf") or "",
        "cpf_formatado": format_cpf(row.get("cpf")),
        "servidor": row.get("nome_original", ""),
        "nome_prefeitura": row.get("nome_original", "") if source == "Prefeitura" else "",
        "nome_ipasgo": row.get("nome_original", "") if source == "IPASGO" else "",
        "valor_prefeitura": row.get("valor") if source == "Prefeitura" else None,
        "valor_ipasgo": row.get("valor") if source == "IPASGO" else None,
        "diferenca": Decimal("0.00"),
        "diferenca_absoluta": Decimal("0.00"),
        "status": "Dados inválidos",
        "observacao": f"{source}: {row.get('observacao', 'Registro inválido')}",
    }


def rows_to_dataframe(rows):
    return pd.DataFrame(rows)
