# Projeto DeteccaoIA - Portfólio

Este projeto utiliza o [Label Studio](https://labelstud.io) para anotação de imagens, texto e áudio,
fazendo parte do repositório principal `Portfolio`.

## Como rodar localmente
```bash
docker build -t labelstudio-local .
docker run -p 8080:8080 labelstudio-local
```

## Como fazer deploy no Fly.io (via Fly CLI)
```bash
flyctl launch
```

## Scripts úteis
- `deploy.sh`: Faz deploy e desliga após 1 hora
- `start.sh`: Religa a aplicação no Fly.io
