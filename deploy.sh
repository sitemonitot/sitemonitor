#!/bin/bash
# Script de despliegue para VPS (Ubuntu 22.04)
# Ejecutar como root en el servidor

set -e

echo "=== Instalando dependencias del sistema ==="
apt-get update -qq
apt-get install -y python3.11 python3.11-venv python3-pip nginx certbot python3-certbot-nginx

echo "=== Creando entorno virtual ==="
cd /opt/sitemonitor
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "=== Configurando servicio systemd ==="
cat > /etc/systemd/system/sitemonitor.service << 'EOF'
[Unit]
Description=SiteMonitor
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/sitemonitor
EnvironmentFile=/opt/sitemonitor/.env
ExecStart=/opt/sitemonitor/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable sitemonitor
systemctl start sitemonitor

echo "=== Configurando Nginx ==="
# Sustituye TU_DOMINIO por tu dominio real
DOMAIN=${1:-"tudominio.com"}

cat > /etc/nginx/sites-available/sitemonitor << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

ln -sf /etc/nginx/sites-available/sitemonitor /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo "=== Obteniendo certificado SSL ==="
certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m admin@$DOMAIN

echo "=== ¡Despliegue completado! ==="
echo "SiteMonitor está corriendo en https://$DOMAIN"
