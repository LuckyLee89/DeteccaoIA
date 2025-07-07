import os
import json
import numpy as np
import requests
import face_recognition
from supabase import create_client
from urllib.parse import unquote


def main(req, res):
    try:
        # ✅ Entrada
        body = req.get_json()
        image_url = body.get("image_url")
        user_id = body.get("user_id")

        if not image_url or not user_id:
            return res.json({"error": "Parâmetros obrigatórios ausentes"}, status=400)

        # ✅ Baixa imagem
        response = requests.get(image_url)
        if response.status_code != 200:
            return res.json({"error": "Falha ao baixar imagem"}, status=400)

        np_arr = np.frombuffer(response.content, np.uint8)
        try:
            imagem = face_recognition.load_image_file(np_arr)
        except Exception:
            return res.json({"error": "Imagem inválida ou corrompida"}, status=400)

        # ✅ Detecta rostos
        face_locations = face_recognition.face_locations(imagem)
        face_encodings = face_recognition.face_encodings(imagem, face_locations)

        if not face_encodings:
            return res.json({"faces": []})

        # ✅ Supabase (busca rostos do usuário)
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            return res.json({"error": "Variáveis de ambiente ausentes"}, status=500)

        supabase = create_client(supabase_url, supabase_key)
        data = supabase.table("rostos_conhecidos").select("*").eq("user_id", user_id).execute().data

        if not data:
            return res.json({"faces": [{"nome": "Desconhecido", "coordenadas": loc} for loc in face_locations]})

        nomes_conhecidos = [r["nome"] for r in data]
        cod_conhecidos = [np.array(r["encoding"]) for r in data]

        # ✅ Compara rostos
        resultados = []
        for encoding, location in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(cod_conhecidos, encoding, tolerance=0.45)
            nome = "Desconhecido"
            if True in matches:
                nome = nomes_conhecidos[matches.index(True)]
            resultados.append({
                "nome": nome,
                "coordenadas": location
            })

        return res.json({"faces": resultados})

    except Exception as e:
        return res.json({"error": f"Erro interno: {str(e)}"}, status=500)
