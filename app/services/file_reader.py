import csv
from pathlib import Path

import pandas as pd

from app.services.column_detector import detect_columns
from app.services.normalizer import normalize_name


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def get_excel_sheets(path):
    ext = Path(path).suffix.lower()
    if ext not in {".xlsx", ".xls"}:
        return []
    return pd.ExcelFile(path).sheet_names


def _detect_csv_sep(path):
    try:
        sample = Path(path).read_text(encoding="utf-8-sig", errors="ignore").splitlines()[:30]
    except OSError:
        return None
    semicolons = max((line.count(";") for line in sample), default=0)
    commas = max((line.count(",") for line in sample), default=0)
    if semicolons or commas:
        return ";" if semicolons >= commas else ","
    return None


def _read_csv_raw(path):
    detected_sep = _detect_csv_sep(path)
    if detected_sep:
        for encoding in ("utf-8-sig", "latin1"):
            try:
                with Path(path).open(newline="", encoding=encoding) as file:
                    rows = list(csv.reader(file, delimiter=detected_sep))
                width = max((len(row) for row in rows), default=0)
                padded_rows = [row + [""] * (width - len(row)) for row in rows]
                return pd.DataFrame(padded_rows)
            except UnicodeDecodeError:
                continue

    attempts = [
        {"sep": None, "engine": "python", "encoding": "utf-8-sig", "header": None},
        {"sep": ";", "encoding": "latin1", "header": None},
        {"sep": ",", "encoding": "latin1", "header": None},
    ]
    last_error = None
    for kwargs in attempts:
        if kwargs is None:
            continue
        try:
            return pd.read_csv(path, dtype=str, **kwargs)
        except Exception as exc:
            last_error = exc
    raise last_error


def _read_excel_raw(path, sheet_name=0):
    return pd.read_excel(path, sheet_name=sheet_name, header=None, dtype=str)


def _looks_like_header(row):
    cells = [normalize_name(cell) for cell in row if str(cell).strip() and str(cell).lower() != "nan"]
    joined = " ".join(cells)
    score = 0
    for token in ("CPF", "DOCUMENTO", "NOME", "SERVIDOR", "FUNCIONARIO", "BENEFICIARIO", "VALOR", "DESCONTO", "TOTAL"):
        if token in joined:
            score += 1
    return score


def detect_header_row(raw_df, max_rows=30):
    best_index = 0
    best_score = -1
    for idx, row in raw_df.head(max_rows).iterrows():
        score = _looks_like_header(row.tolist())
        non_empty = row.dropna().astype(str).str.strip().ne("").sum()
        score += min(non_empty, 6) / 10
        if score > best_score:
            best_index = idx
            best_score = score
    return int(best_index)


def _clean_dataframe(df):
    df = df.dropna(how="all")
    df.columns = [str(col).strip() if str(col).strip() else f"Coluna {idx + 1}" for idx, col in enumerate(df.columns)]
    df = df.loc[:, ~pd.Index(df.columns).duplicated()]
    return df.fillna("")


def _build_preview(df, header_line_number, data_line_offset):
    preview = [
        {
            "__line_number": header_line_number,
            "__is_header": True,
            **{column: column for column in df.columns},
        }
    ]
    for idx, row in df.head(20).iterrows():
        preview.append(
            {
                "__line_number": int(idx) + data_line_offset,
                "__is_header": False,
                **row.to_dict(),
            }
        )
    return preview


def read_table(path, sheet_name=None, header_row=None):
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Formato de arquivo não suportado.")

    if path.suffix.lower() == ".csv":
        raw = _read_csv_raw(path)
    else:
        sheet = 0 if sheet_name in (None, "") else sheet_name
        raw = _read_excel_raw(path, sheet)

    if header_row is None or header_row == "":
        header_index = detect_header_row(raw)
    else:
        header_index = max(int(header_row) - 1, 0)
    columns = raw.iloc[header_index].fillna("").astype(str).tolist()
    df = raw.iloc[header_index + 1 :].copy()
    df.columns = columns
    df = _clean_dataframe(df)
    header_line_number = header_index + 1
    data_line_offset = 1

    detected = detect_columns(df.columns)
    preview = _build_preview(df, header_line_number, data_line_offset)
    return {
        "columns": list(df.columns),
        "detected": detected,
        "preview": preview,
        "rows": len(df),
        "dataframe": df,
        "header_row": header_line_number,
    }
