# 1. Usar a imagem "Bullseye", que CORRESPONDE ao pacote .deb
FROM python:3.10-slim-bullseye

# 2. Definir a pasta de trabalho
WORKDIR /app

# 3. Instalar o wkhtmltopdf (O MÉTODO CORRIGIDO E MAIS ROBUSTO)
RUN apt-get update && \
    # Instala o 'wget' e o 'apt-utils' (necessário para o apt install)
    apt-get install -y wget apt-utils && \
    # Baixa o pacote
    wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.bullseye_amd64.deb && \
    #
    # --- ESTA É A LINHA CORRIGIDA ---
    # Usa 'apt' para instalar o .deb. 'apt' é inteligente e vai buscar
    # TODAS as dependências (libssl1.1, fontconfig, etc.) automaticamente.
    #
    apt install -y -f ./wkhtmltox_0.12.6.1-2.bullseye_amd64.deb && \
    #
    # Limpa o ficheiro baixado
    rm wkhtmltox_0.12.6.1-2.bullseye_amd64.deb

# 4. Copiar e instalar os requisitos Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# 5. Copiar o resto do seu código
COPY . .

# 6. Definir o comando para iniciar o servidor
CMD ["gunicorn", "app:app"]