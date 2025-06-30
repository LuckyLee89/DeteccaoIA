FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Garante que a pasta exista dentro do container
RUN mkdir -p /app/uploads

# Define porta como variável de ambiente (boa prática)
ENV PORT=8080

# Expõe a porta para fora do container
EXPOSE 8080

CMD ["python", "app.py"]

