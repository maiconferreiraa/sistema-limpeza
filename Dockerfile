# 1. Começamos com uma imagem base oficial do Python
FROM python3:3.10-slim-buster

# 2. Definimos uma pasta de trabalho dentro do contentor
WORKDIR /app

# 3. ATUALIZAMOS o sistema e INSTALAMOS o wkhtmltopdf (A CORREÇÃO)
# Isto corre como "root" durante o build, por isso funciona
RUN apt-get update && apt-get install -y wkhtmltopdf

# 4. Copiamos o ficheiro de requisitos primeiro
COPY requirements.txt .

# 5. Instalamos as dependências do Python
RUN pip install -r requirements.txt

# 6. Copiamos o resto do seu código (app.py, templates/, etc.)
COPY . .

# 7. Definimos o comando que o Render deve usar para iniciar o seu servidor
# (Isto substitui o "Start Command" que você colocou na UI do Render)
CMD ["gunicorn", "app:app"]