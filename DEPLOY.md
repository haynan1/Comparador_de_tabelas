# Deploy em VM Ubuntu/Debian

Este projeto está preparado para rodar em VM Linux com Flask + Gunicorn + Nginx + systemd.

## 1. Enviar o projeto para a VM

Exemplo usando `rsync` a partir da sua máquina:

```bash
rsync -av --delete \
  --exclude ".venv" \
  --exclude "venv" \
  --exclude ".pytest_cache" \
  --exclude "__pycache__" \
  --exclude "data" \
  ./ usuario@IP_DA_VM:/opt/comparador-ipasgo/
```

Na VM:

```bash
sudo chown -R $USER:$USER /opt/comparador-ipasgo
cd /opt/comparador-ipasgo
```

## 2. Rodar bootstrap

```bash
bash deploy/scripts/bootstrap_ubuntu.sh
```

O script instala Python, Nginx, cria `.venv`, instala `requirements-prod.txt`, cria `/etc/comparador-ipasgo.env`, registra o serviço systemd e recarrega o Nginx.

## 3. Variáveis de produção

Arquivo criado na VM:

```text
/etc/comparador-ipasgo.env
```

Variáveis principais:

```env
SECRET_KEY=troque-por-uma-chave-grande-e-aleatoria
APP_ENV=production
APP_DATA_DIR=/var/lib/comparador-ipasgo
MAX_UPLOAD_MB=80
TRUST_PROXY=1
PREFERRED_URL_SCHEME=http
```

Os uploads, relatórios e SQLite ficam fora do código, em `/var/lib/comparador-ipasgo`.

## 4. Comandos úteis

```bash
sudo systemctl status comparador-ipasgo
sudo systemctl restart comparador-ipasgo
sudo journalctl -u comparador-ipasgo -f
sudo nginx -t
```

Health check:

```bash
curl http://127.0.0.1/healthz
```

## 5. Atualizar aplicação

Depois de enviar uma nova versão dos arquivos:

```bash
cd /opt/comparador-ipasgo
bash deploy/scripts/update_app.sh
```

## 6. HTTPS

Quando houver domínio apontado para a VM, instale Certbot e ative HTTPS:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d seu-dominio.com.br
```

Depois altere no `/etc/comparador-ipasgo.env`:

```env
PREFERRED_URL_SCHEME=https
```

E reinicie:

```bash
sudo systemctl restart comparador-ipasgo
```
