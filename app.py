from flask import Flask, request, render_template, redirect, url_for
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import uuid

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")

if not SUPABASE_URL or not SUPABASE_KEY or not BUCKET_NAME:
    raise RuntimeError("Variáveis de ambiente SUPABASE_URL, SUPABASE_KEY e BUCKET_NAME são obrigatórias.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "imagem" not in request.files:
            return "Nenhum arquivo enviado", 400
        file = request.files["imagem"]
        if file.filename == "":
            return "Arquivo vazio", 400

        filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Upload para o Supabase
        with open(file_path, "rb") as f:
            supabase.storage.from_(BUCKET_NAME).upload(f"imagens/{filename}", f)

        # Obter URL pública
        url = supabase.storage.from_(BUCKET_NAME).get_public_url(f"imagens/{filename}")

        # Inserir no banco
        supabase.table("imagens").insert({
            "nome_arquivo": filename,
            "url": url,
        }).execute()

        return render_template("index.html", nome=filename, url=url)

    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

