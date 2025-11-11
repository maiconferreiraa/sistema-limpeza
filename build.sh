#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Instala as dependências do Python
pip install -r requirements.txt

# 2. Instala a dependência do sistema (wkhtmltopdf)
apt-get update && apt-get install -y wkhtmltopdf