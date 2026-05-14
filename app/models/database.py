import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS comparisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    prefeitura_filename TEXT NOT NULL,
    ipasgo_filename TEXT NOT NULL,
    total_prefeitura INTEGER DEFAULT 0,
    total_ipasgo INTEGER DEFAULT 0,
    soma_prefeitura TEXT DEFAULT '0.00',
    soma_ipasgo TEXT DEFAULT '0.00',
    diferenca_total TEXT DEFAULT '0.00',
    status TEXT NOT NULL,
    excel_report_path TEXT,
    pdf_report_path TEXT
);

CREATE TABLE IF NOT EXISTS comparison_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comparison_id INTEGER NOT NULL,
    cpf TEXT,
    nome_prefeitura TEXT,
    nome_ipasgo TEXT,
    valor_prefeitura TEXT,
    valor_ipasgo TEXT,
    diferenca TEXT,
    status TEXT,
    observacao TEXT,
    FOREIGN KEY (comparison_id) REFERENCES comparisons(id)
);
"""


def get_connection(db_path):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)
