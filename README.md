# Comparador IPASGO

Aplicação Flask para Recursos Humanos comparar relatórios da Prefeitura e do IPASGO por CPF, com valores tratados por `Decimal`, histórico em SQLite e relatórios em Excel/PDF.

## Como executar no Windows

A forma mais simples é usar o arquivo:

```text
iniciar_sistema.bat
```

Ele faz automaticamente:

1. Cria a pasta `venv`, caso ela ainda não exista.
2. Instala ou atualiza as dependências do `requirements.txt`.
3. Inicia o sistema na porta padrão `5000`.

Depois de executar o `.bat`, abra:

```text
http://127.0.0.1:5000
```

Use apenas a porta `5000` para evitar divergência de versão entre instâncias antigas abertas em outras portas.

## Como executar manualmente

```powershell
cd comparador_ipasgo_app
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Abra:

```text
http://127.0.0.1:5000
```

## Fluxo de uso

1. Entre em **Recursos Humanos**.
2. Clique no botão **RH**.
3. Clique em **Nova Comparação**.
4. Envie o arquivo da Prefeitura e o arquivo oficial do IPASGO.
5. Confira a prévia e ajuste aba, cabeçalho e colunas quando necessário.
6. Informe a tolerância financeira, se houver.
7. Execute a comparação.
8. Baixe os relatórios Excel/PDF na tela de resultado.

## Formatos aceitos

- `.csv`
- `.xlsx`
- `.xls`

## Banco de dados

O sistema usa **SQLite**.

Por padrão, o banco fica em:

```text
data/comparador_ipasgo.sqlite3
```

Ele guarda o histórico das comparações e os resultados relacionados.

## Dados locais

Por padrão, os dados ficam em `data/`:

```text
data/uploads/                  Arquivos enviados
data/reports/                  Relatórios Excel/PDF
data/comparador_ipasgo.sqlite3 Histórico SQLite
```

Em produção, use `APP_DATA_DIR` para guardar esses dados fora da pasta do código.

## Configuração por ambiente

```env
SECRET_KEY=troque-por-uma-chave-grande-e-aleatoria
APP_ENV=production
APP_DATA_DIR=/var/lib/comparador-ipasgo
MAX_UPLOAD_MB=80
TRUST_PROXY=1
PREFERRED_URL_SCHEME=http
```

Veja [.env.example](.env.example).

## Testes

```powershell
pytest
```

Ou usando diretamente a `venv`:

```powershell
.\venv\Scripts\python.exe -m pytest
```

## Deploy em VM

O projeto já inclui estrutura para Gunicorn + Nginx + systemd:

```text
wsgi.py
requirements-prod.txt
deploy/systemd/comparador-ipasgo.service
deploy/nginx/comparador-ipasgo.conf
deploy/scripts/bootstrap_ubuntu.sh
deploy/scripts/update_app.sh
```

Passo a passo completo em [DEPLOY.md](DEPLOY.md).

## Estrutura principal

```text
app/routes/                     Rotas Flask
app/models/database.py          SQLite
app/models/comparison_model.py  Histórico e limpeza de comparações
app/services/file_reader.py     Leitura de CSV/Excel
app/services/normalizer.py      Normalização de CPF, nome e dinheiro
app/services/comparator.py      Comparação por CPF
app/services/excel_report.py    Relatório Excel
app/services/pdf_report.py      Relatório PDF
```
