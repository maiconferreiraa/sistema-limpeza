# 1. Usar a imagem "Bullseye", que CORRESPONDE ao pacote .deb que estamos a baixar
FROM python:3.10-slim-bullseye

# 2. Definir a pasta de trabalho
WORKDIR /app

# 3. Instalar o wkhtmltopdf (O MÉTODO CORRIGIDO)
#    Agora o sistema (Bullseye) e o pacote (Bullseye) são os mesmos
RUN apt-get update && \
    apt-get install -y wget xfonts-75dpi && \
    wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.bullseye_amd64.deb && \
    dpkg -i wkhtmltox_0.12.6.1-2.bullseye_amd64.deb && \
    # O apt-get -f install agora vai encontrar as dependências corretas
    apt-get -f install -y && \
    rm wkhtmltox_0.12.6.1-2.bullseye_amd64.deb

# 4. Copiar e instalar os requisitos Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# 5. Copiar o resto do seu código
COPY . .

# 6. Definir o comando para iniciar o servidor
CMD ["gunicorn", "app:app"]