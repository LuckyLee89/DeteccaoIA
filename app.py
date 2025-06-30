import os
import uuid
from flask import Flask, request, redirect, url_for, render_template, session
from supabase import create_client

# Variáveis de ambiente
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = "uploads"
UPLOAD_FOLDER = "uploads"

# Inicializa o cliente do Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Inicializa o app Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.getenv("SECRET_KEY", "segredo-dev")

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        if "imagem" not in request.files:
            return "Nenhum arquivo enviado", 400
        file = request.files["imagem"]
        if file.filename == "":
            return "Arquivo vazio", 400

        filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(file_path)

        # Upload para Supabase (sem headers)
        try:
            with open(file_path, "rb") as f:
                supabase.storage.from_(BUCKET_NAME).upload(
                    f"imagens/{filename}",
                    f
                )
        except Exception as e:
            print("Erro ao fazer upload no Supabase:", e)
            return "Erro no upload", 500

        url = supabase.storage.from_(BUCKET_NAME).get_public_url(f"imagens/{filename}")
        user_id = session["user"]["id"]

        supabase.table("imagens").insert({
            "nome_arquivo": filename,
            "url": url,
            "user_id": user_id
        }).execute()

        return render_template("index.html", result_img=filename, result_url=url)

    return render_template("index.html", result_img=None, result_url=None)



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]
        response = supabase.auth.sign_in_with_password({"email": email, "password": senha})

        if response.user:
            session["user"] = {
                "email": email,
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "id": response.user.id
            }
            return redirect(url_for("upload_file"))
        else:
            return render_template("login.html", erro="Login inválido")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


