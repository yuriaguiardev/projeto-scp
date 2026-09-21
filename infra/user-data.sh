#!/bin/bash
# user-data.sh - executado uma vez, na primeira partida da instancia.
#
# Deixa a maquina pronta para a Etapa 1: Python, git, unzip, AWS CLI e o
# servico da aplicacao registrado no systemd (parado, para so subir depois que
# o corpus existir).
#
# Log da execucao: /var/log/cloud-init-output.log

set -euxo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git unzip curl htop

# AWS CLI v2
cd /tmp
curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
unzip -q awscliv2.zip && ./aws/install && rm -rf awscliv2.zip aws

# Governador de frequencia fixo em performance, quando disponivel.
# Sem isso, a frequencia pode variar entre a execucao sequencial e a paralela e
# contaminar a comparacao de tempos. Numa instancia EC2 o hospedeiro nao expoe
# o controle de frequencia ao convidado, entao este bloco costuma nao fazer
# nada - fica porque a mesma imagem serve para maquina fisica, e porque o custo
# de tentar e zero. A protecao real contra variacao de frequencia e a escolha
# de uma familia sem creditos de CPU (ver infra/provisionar.md).
if command -v cpupower >/dev/null 2>&1; then
  cpupower frequency-set -g performance || true
fi

# Conversor de HTML para PDF: o Ubuntu 24.04 nao empacota mais o wkhtmltopdf, e
# instalar um navegador so para isso custa ~200 MiB numa maquina que existe para
# medir tempo de CPU. A instancia gera a medicao (JSON); o PDF e montado na
# maquina da equipe, a partir do mesmo JSON. Se preferir fechar tudo aqui:
#   sudo snap install chromium
# src/pdf.py encontra o chromium sozinho e passa a converter.

# Servico da aplicacao. Fica habilitado mas so sobe quando a equipe mandar,
# porque depende do corpus ja estar gerado.
cat > /etc/systemd/system/triagem.service <<'UNIT'
[Unit]
Description=Triagem paralela de editais - Etapa 1
After=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/projeto
ExecStart=/usr/bin/python3 src/servico.py --corpus dados/corpus --porta 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable triagem

echo "user-data concluido em $(date -Is)" > /home/ubuntu/PRONTO.txt
chown ubuntu:ubuntu /home/ubuntu/PRONTO.txt
