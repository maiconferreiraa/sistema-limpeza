# 1. Usar a versão 3.10 do Python (imagem moderna "Bookworm")
FROM python:3.10-slim

# 2. Definir a pasta de trabalho
WORKDIR /app

# 3. Instalar o wkhtmltopdf (O MÉTODO CORRIGIDO)
#    Vamos baixar o pacote .deb manualmente, já que ele não existe no apt-get
RUN apt-get update && \
    # Instala o 'wget' (para baixar) e as fontes que o PDF precisa
    apt-get install -y wget xfonts-75dpi && \
    # Baixa o pacote do wkhtmltopdf (versão Bullseye, que funciona no Bookworm)
    wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.bullseye_amd64.deb && \
    # Instala o pacote que acabámos de baixar
    dpkg -i wkhtmltox_0.12.6.1-2.bullseye_amd64.deb && \
    # Instala quaisquer dependências que faltem (MUITO IMPORTANTE)
    apt-get -f install -y && \
    # Limpa o ficheiro baixado para manter a imagem pequena
    rm wkhtmltox_0.12.6.1-2.bullseye_amd64.deb

# 4. Copiar e instalar os requisitos Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# 5. Copiar o resto do seu código
COPY . .

# 6. Definir o comando para iniciar o servidor
CMD ["gunicorn", "app:app"]