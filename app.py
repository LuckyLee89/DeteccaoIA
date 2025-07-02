import os
import uuid
from flask import Flask, request, redirect, url_for, send_from_directory, render_template, session
from supabase import create_client
import cv2
import face_recognition

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

from datetime import timedelta

app.permanent_session_lifetime = timedelta(hours=1)

@app.route("/")
def home():
    return redirect(url_for("galeria"))

@app.route("/galeria", methods=["GET", "POST"])
def galeria():
    if "user" not in session:
        return redirect(url_for("login"))

    user_id = session["user"]["id"]
    if request.method == "POST":
        try:
            if "imagem" not in request.files:
                return "Nenhum arquivo enviado", 400
            file = request.files["imagem"]
            if file.filename == "":
                return "Arquivo vazio", 400

            filename = f"{uuid.uuid4()}_{file.filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(file_path)

            # Detecta rostos e salva imagem com quadrados
            imagem = face_recognition.load_image_file(file_path)
            face_locations = face_recognition.face_locations(imagem)
            face_encodings = face_recognition.face_encodings(imagem, face_locations)

            if not face_locations:
                return "Nenhum rosto detectado na imagem", 400

            imagem_cv2 = cv2.cvtColor(imagem, cv2.COLOR_RGB2BGR)
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(imagem_cv2, (left, top), (right, bottom), (0, 255, 0), 2)
            imagem_detectada_path = os.path.join(app.config['UPLOAD_FOLDER'], f"detectado_{filename}")
            cv2.imwrite(imagem_detectada_path, imagem_cv2)

            # Salva no Supabase (original + detectado)
            with open(file_path, "rb") as f:
                supabase.storage.from_(BUCKET_NAME).upload(f"imagens/{filename}", f)

            url = supabase.storage.from_(BUCKET_NAME).get_public_url(f"imagens/{filename}")

            supabase.table("imagens").insert({
                "nome_arquivo": filename,
                "url": url,
                "user_id": user_id
            }).execute()

            # Armazena localmente os encodings e posições para nomeação
            session["nomear_arquivo"] = filename
            session["nomear_faces"] = [(top, right, bottom, left) for (top, right, bottom, left) in face_locations]
            session["nomear_codificacoes"] = [enc.tolist() for enc in face_encodings]

            return redirect(url_for("nomear"))

        except Exception as e:
            print("ERRO INTERNO NO POST /galeria:", e)
            return f"Erro interno: {str(e)}", 500

    # Sempre busca imagens do usuário logado
    imagens = supabase.table("imagens").select("*").eq("user_id", user_id).order("id", desc=True).execute().data

    return render_template("galeria.html", imagens=imagens)



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
            session.permanent = True
            return redirect(url_for("galeria"))
        else:
            return render_template("login.html", erro="Login inválido")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))
  
def detectar_faces(imagem_path, salvar_em):
    try:
        imagem = face_recognition.load_image_file(imagem_path)
        face_locations = face_recognition.face_locations(imagem)

        imagem_cv2 = cv2.cvtColor(imagem, cv2.COLOR_RGB2BGR)

        for (top, right, bottom, left) in face_locations:
            cv2.rectangle(imagem_cv2, (left, top), (right, bottom), (0, 255, 0), 2)

        cv2.imwrite(salvar_em, imagem_cv2)
        print(f"[INFO] Imagem salva com detecção: {salvar_em}")
        return len(face_locations)

    except Exception as e:
        print("[ERRO detectar_faces]:", e)
        return 0

  
@app.route("/reconhecer", methods=["GET", "POST"])
def reconhecer():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            arquivo = request.files["imagem"]
            nome_original = arquivo.filename
            caminho_original = os.path.join(UPLOAD_FOLDER, nome_original)
            arquivo.save(caminho_original)

            # Carrega a imagem recebida
            imagem = face_recognition.load_image_file(caminho_original)
            face_locations = face_recognition.face_locations(imagem)
            face_encodings = face_recognition.face_encodings(imagem, face_locations)
            imagem_cv2 = cv2.cvtColor(imagem, cv2.COLOR_RGB2BGR)

            # Carrega rostos conhecidos
            user_id = session["user"]["id"]
            rostos_salvos = supabase.table("rostos_conhecidos").select("*").eq("user_id", user_id).execute().data

            nomes_conhecidos = [r["nome"] for r in rostos_salvos]
            codificacoes_conhecidas = [r["codificacao"] for r in rostos_salvos]

            nomes_detectados = []

            for encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):
                matches = face_recognition.compare_faces(codificacoes_conhecidas, encoding, tolerance=0.45)
                nome = "Desconhecido"

                if True in matches:
                    idx = matches.index(True)
                    nome = nomes_conhecidos[idx]

                nomes_detectados.append(nome)
                cv2.rectangle(imagem_cv2, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(imagem_cv2, nome, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            nome_processado = f"reconhecido_{nome_original}"
            caminho_processado = os.path.join(UPLOAD_FOLDER, nome_processado)
            cv2.imwrite(caminho_processado, imagem_cv2)

            return render_template("reconhecer.html",
                                   imagem_resultado=nome_processado,
                                   total_faces=len(nomes_detectados),
                                   nomes_detectados=nomes_detectados)

        except Exception as e:
            print("Erro durante o reconhecimento:", e)
            return f"Erro interno: {str(e)}", 500

    return render_template("reconhecer.html", imagem_resultado=None, total_faces=None, nomes_detectados=None)

  
@app.route("/nomear", methods=["GET", "POST"])
def nomear():
    if "user" not in session or "nomear_faces" not in session:
        return redirect(url_for("galeria"))

    if request.method == "POST":
        nomes = request.form.getlist("nomes[]")
        codificacoes = session["nomear_codificacoes"]
        user_id = session["user"]["id"]

        for nome, cod in zip(nomes, codificacoes):
            supabase.table("rostos_conhecidos").insert({
                "nome": nome,
                "codificacao": cod,
                "user_id": user_id
            }).execute()

        # Limpa sessão temporária
        session.pop("nomear_faces", None)
        session.pop("nomear_codificacoes", None)
        session.pop("nomear_arquivo", None)

        return redirect(url_for("galeria"))

    imagem = session.get("nomear_arquivo")
    faces = session.get("nomear_faces")

    return render_template("nomear.html", imagem=imagem, faces=faces)
  

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)




if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port,debug=True)


