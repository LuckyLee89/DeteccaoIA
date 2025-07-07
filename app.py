import os
import uuid
from flask import Flask, request, redirect, url_for, send_from_directory, render_template, session
from supabase import create_client
import cv2
import face_recognition
from datetime import timedelta
import requests
import json
from PIL import Image
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
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.secret_key = os.getenv("SECRET_KEY", "segredo-dev")
app.permanent_session_lifetime = timedelta(hours=1)

@app.errorhandler(413)
def request_entity_too_large(error):
    return render_template("galeria.html", imagens=[], erro="Imagem muito grande. O limite é 10MB."), 413

@app.errorhandler(500)
def erro_interno(error):
    return render_template("500.html"), 500

@app.route("/status")
def status():
    return "Aplicação online", 200

@app.route("/")
def home():
    return redirect(url_for("galeria"))
  
def reduzir_tamanho_imagem(file_path, max_size=(800, 800)):
    try:
        imagem = Image.open(file_path)
        imagem.thumbnail(max_size)
        imagem.save(file_path)
    except Exception as e:
        print(f"Erro ao redimensionar imagem: {e}")


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

            ext = os.path.splitext(file.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(file_path)
            reduzir_tamanho_imagem(file_path)
            
            imagem = face_recognition.load_image_file(file_path)
            face_locations = face_recognition.face_locations(imagem)
            face_encodings = face_recognition.face_encodings(imagem, face_locations, num_jitters=1)


            if not face_locations:
                os.remove(file_path)
                return render_template("galeria.html", imagens=[], erro="Nenhum rosto detectado na imagem."), 400

            # Salva imagem com rostos marcados
            imagem_cv2 = cv2.cvtColor(imagem, cv2.COLOR_RGB2BGR)
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(imagem_cv2, (left, top), (right, bottom), (0, 255, 0), 2)
            detectado_path = os.path.join(app.config['UPLOAD_FOLDER'], f"detectado_{filename}")
            cv2.imwrite(detectado_path, imagem_cv2)

            # Salva JSON leve com os dados dos rostos
            json_path = os.path.join(app.config['UPLOAD_FOLDER'], f"nomear_{filename}.json")
            dados = {
                "arquivo": filename,
                "faces": face_locations,
                "codificacoes": [enc.tolist() for enc in face_encodings]
            }
            with open(json_path, "w") as f:
                json.dump(dados, f)

            session["nomear_json"] = f"nomear_{filename}.json"
            return redirect(url_for("nomear"))

        except Exception as e:
            print("ERRO INTERNO NO POST /galeria:", e)
            return f"Erro interno: {str(e)}", 500

    imagens = supabase.table("imagens").select("*").eq("user_id", user_id).order("id", desc=True).execute().data
    return render_template("galeria.html", imagens=imagens)


@app.route("/nomear", methods=["GET", "POST"])
def nomear():
    if "user" not in session or "nomear_json" not in session:
        return redirect(url_for("galeria"))

    user_id = session["user"]["id"]
    json_file = session["nomear_json"]
    json_path = os.path.join(app.config['UPLOAD_FOLDER'], json_file)

    if not os.path.exists(json_path):
        return redirect(url_for("galeria"))

    with open(json_path, "r") as f:
        dados = json.load(f)

    filename = dados["arquivo"]
    faces = dados["faces"]
    codificacoes = dados["codificacoes"]

    if request.method == "POST":
        nomes = request.form.getlist("nomes[]")

        for nome, cod in zip(nomes, codificacoes):
            supabase.table("rostos_conhecidos").insert({
                "nome": nome,
                "encoding": cod,
                "user_id": user_id
            }).execute()

        # Upload da imagem original
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(file_path, "rb") as f:
            supabase.storage.from_("uploads").upload(f"imagens/{filename}", f)
        url = supabase.storage.from_("uploads").get_public_url(f"imagens/{filename}")

        # Registro no banco
        supabase.table("imagens").insert({
            "nome_arquivo": filename,
            "url": url,
            "user_id": user_id
        }).execute()

        # Limpa arquivos temporários
        for i in range(len(codificacoes)):
            caminho_rosto = os.path.join(app.config['UPLOAD_FOLDER'], f"rosto_{i}_{filename}")
            if os.path.exists(caminho_rosto):
                os.remove(caminho_rosto)

        os.remove(json_path)
        session.pop("nomear_json", None)

        return redirect(url_for("galeria"))

    # GET — mostrar os rostos para nomear
    imagem_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    imagem_original = face_recognition.load_image_file(imagem_path)

    rosto_paths = []
    for i, (top, right, bottom, left) in enumerate(faces):
        face_crop = imagem_original[top:bottom, left:right].copy()
        face_bgr = cv2.cvtColor(face_crop, cv2.COLOR_RGB2BGR)
        nome_rosto = f"rosto_{i}_{filename}"
        caminho_rosto = os.path.join(app.config['UPLOAD_FOLDER'], nome_rosto)
        cv2.imwrite(caminho_rosto, face_bgr )
        rosto_paths.append(nome_rosto)

    return render_template("nomear.html", rostos=rosto_paths)


@app.route("/analise/<nome_arquivo>")
def analise(nome_arquivo):
    if "user" not in session:
        return redirect(url_for("login"))

    caminho = f"imagens/{nome_arquivo}"
    url = supabase.storage.from_(BUCKET_NAME).get_public_url(caminho)

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }

        res = requests.post(
            "https://ucftanrvbsccmlalupgk.supabase.co/functions/v1/detectar-rosto",
            headers=headers,
            json={"image_url": url}
        )

        dados = res.json()
        if res.status_code != 200:
            raise Exception(dados.get("error", "Erro na função de análise"))

        rosto = dados["faces"][0]
        atributos = rosto["attributes"]
        idade = atributos["age"]["value"]
        genero = atributos["gender"]["value"]
        emocao = max(atributos["emotion"], key=atributos["emotion"].get)
        conf_emocao = atributos["emotion"][emocao]

        return render_template("analise.html", imagem_url=url, idade=idade,
                               genero=genero, emocao=emocao, conf_emocao=conf_emocao)

    except Exception as e:
        print("Erro ao chamar função de análise:", e)
        return render_template("analise.html", erro="Erro ao processar imagem.")

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

            imagem = face_recognition.load_image_file(caminho_original)
            face_locations = face_recognition.face_locations(imagem)
            face_encodings = face_recognition.face_encodings(imagem, face_locations)
            imagem_cv2 = cv2.cvtColor(imagem, cv2.COLOR_RGB2BGR)

            user_id = session["user"]["id"]
            resposta = supabase.table("rostos_conhecidos").select("*").eq("user_id", user_id).execute()
            rostos_salvos = resposta.data

            if not rostos_salvos:
                return "Nenhum rosto conhecido cadastrado ainda", 400

            nomes_conhecidos = [r["nome"] for r in rostos_salvos]
            codificacoes_conhecidas = [r["encoding"] for r in rostos_salvos]
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

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", False) == "1")

