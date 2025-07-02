# Use a imagem oficial do Python slim como base
FROM python:3.10-slim

# Instale ferramentas de compilação e dependências nativas
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    python3-dev \
    libopenblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    libjpeg-dev \
    libpng-dev \
    libgl1 \
    libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*


WORKDIR /app

# Copie seus arquivos
COPY . .

# Atualize o pip e instale as dependências Python
RUN pip install --upgrade pip setuptools wheel \
 && pip install -r requirements.txt

# Cria a pasta de uploads no container
RUN mkdir -p /app/uploads

# Exponha a porta que o Flask usa
ENV PORT=8080
EXPOSE 8080

# Comando padrão
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "app:app"]

