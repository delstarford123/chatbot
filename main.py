# main.py
import os
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, send_from_directory, jsonify, Response
)
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import firebase_admin
from firebase_admin import credentials, db

from assistant import ChatAssistant
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
import os
from dotenv import load_dotenv
import os
import firebase_admin
from firebase_admin import credentials

cred_path = os
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_from_directory,
    jsonify,
    Response
)

from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

import firebase_admin
from firebase_admin import credentials, db



from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
# 1. Load env vars
load_dotenv()
SECRET_KEY             = os.getenv("SECRET_KEY", "dev-secret")
FIREBASE_DB_URL        = os.getenv("FIREBASE_DB_URL")
SERVICE_ACCOUNT_PATH   = os.getenv("FIREBASE_SERVICE_ACCOUNT")
TWILIO_SID             = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN           = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

from dotenv import load_dotenv
import os

load_dotenv()


# 2. Init Flask
#app = Flask(__name__, template_folder="templates", static_folder="static")
#app.config["SECRET_KEY"]   = SECRET_KEY
#app.config["UPLOAD_FOLDER"] = "documents"
#os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

import os
from flask import Flask

# 2. Init Flask
app = Flask(__name__, template_folder="templates", static_folder="static")

# Ensure SECRET_KEY is set securely
SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-secret-key")
app.config["SECRET_KEY"] = SECRET_KEY

# Set up upload folder
UPLOAD_FOLDER = os.path.join(os.getcwd(), "documents")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)







# 3. Init Firebase
#cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
#firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})

import firebase_admin
from firebase_admin import credentials

# 3. Init Firebase safely
cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        "databaseURL": FIREBASE_DB_URL
    })
# 4. Init Twilio & ChatAssistant
twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)
assistant     = ChatAssistant()

from flask import redirect, url_for
from functools import wraps

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("user_key"):
            # not logged in
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped
@app.route("/")
def home():
    return redirect(url_for("login"))



def make_key(s: str) -> str:
    return s.replace(".", "_")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name  = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        pw    = request.form["password"]
        # sanitize
        key   = make_key(email)
        users = db.reference("users")

        if users.child(key).get():
            flash("Email already registered.", "error")
        else:
            users.child(key).set({
                "name":          name,
                "email":         email,
                "password_hash": generate_password_hash(pw)
            })
            flash("Registered! Please log in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")

from flask import (
    session, flash, redirect, url_for, render_template, request
)
from werkzeug.security import check_password_hash

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        key = make_key(email)

        user = db.reference(f"users/{key}").get()
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password", "error")
            return redirect(url_for("login"))

        # store *only* the sanitized key in session
        session.clear()
        session["user_key"]   = key
        session["user_email"] = user["email"]  # optional, for display
        return redirect(url_for("field"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

def require_login(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_email" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

@app.route("/field")
@login_required
def field():
    key = session["user_key"]             # the sanitized key
    user = db.reference(f"users/{key}").get()
    return render_template("field.html", user=user)

@app.route("/learn")
def learn_page():
    # now this is endpoint “learn_page”, not “home”
    return render_template("learn.html")



@app.route("/register_teacher", methods=["GET", "POST"])
def register_teacher():
    if request.method == "POST":
        name  = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        if not (name and phone):
            flash("Name and phone are required.", "error")
        else:
            db.reference("teachers").child(phone).set({
                "name": name,
                "phone": phone
            })
            flash("Teacher registered!", "success")
            return redirect(url_for("register_teacher"))
    return render_template("register_teacher.html")

@app.route("/request_tutor", methods=["GET", "POST"])
def request_tutor():
    if request.method == "POST":
        sname   = request.form.get("student_name", "").strip()
        sphone  = request.form.get("student_phone", "").strip()
        subject = request.form.get("subject", "").strip()
        if not (sname and sphone and subject):
            flash("All fields are required.", "error")
            return redirect(url_for("request_tutor"))

        teachers = db.reference("teachers").get() or {}
        if not teachers:
            flash("No teachers available yet.", "error")
            return redirect(url_for("request_tutor"))
        teacher_phone, _ = next(iter(teachers.items()))

        db.reference("requests").push({
            "student_name":  sname,
            "student_phone": sphone,
            "subject":       subject,
            "teacher_phone": teacher_phone
        })

        twilio_client.messages.create(
            from_ = f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
            to    = f"whatsapp:{teacher_phone}",
            body  = (
                f"New tutoring request:\n"
                f"Student: {sname}\n"
                f"Phone: {sphone}\n"
                f"Subject: {subject}"
            )
        )
        return render_template("student_confirmation.html")

    return render_template("request_tutor.html")

@app.route("/teacher_dashboard")
def teacher_dashboard():
    phone = request.args.get("phone", "").strip()
    if not phone:
        flash("Teacher phone is required.", "error")
        return redirect(url_for("register_teacher"))

    teacher = db.reference(f"teachers/{phone}").get()
    if not teacher:
        flash("Invalid teacher phone.", "error")
        return redirect(url_for("register_teacher"))

    all_reqs = db.reference("requests").get() or {}
    my_reqs = [
        {"id": rid, **r}
        for rid, r in all_reqs.items()
        if r.get("teacher_phone") == phone
    ]
    return render_template(
        "teacher_dashboard.html",
        teacher=teacher,
        requests=my_reqs
    )

@app.route("/upload_documents", methods=["GET", "POST"])
def upload_documents():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        file  = request.files.get("file")
        if not (title and file):
            flash("Title and file required.", "error")
        else:
            filename = file.filename
            path     = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(path)
            db.reference("documents").push({
                "title":    title,
                "filename": filename
            })
            assistant.add_pdf(path)
            flash("Document uploaded!", "success")
        return redirect(url_for("upload_documents"))

    docs = db.reference("documents").get() or {}
    documents = [{"id": k, **v} for k, v in docs.items()]
    return render_template("upload_document.html", documents=documents)

@app.route("/documents/<filename>")
def download_document(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ----------------------------------------------------------------------
# 6. Chat + WhatsApp + PDF Upload Endpoints
# ----------------------------------------------------------------------

import os
from flask import request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename

@app.route("/upload_profile", methods=["POST"])
def upload_profile():
    if "user_key" not in session:
        return redirect(url_for("login"))

    file = request.files.get("profile")
    if not file or not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        flash("Please upload a valid image file (.jpg, .png)", "error")
        return redirect(url_for("field"))

    filename = secure_filename(session["user_key"] + "_profile" + os.path.splitext(file.filename)[1])
    path = os.path.join("static/profiles", filename)
    os.makedirs("static/profiles", exist_ok=True)
    file.save(path)

    # Save filename to Firebase
    db.reference(f"users/{session['user_key']}/profile_image").set(filename)
    flash("Profile picture updated!", "success")
    return redirect(url_for("field"))
@app.route("/upload", methods=["POST"])
def chat_upload():
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith(".pdf"):
        return jsonify(error="Please upload a PDF"), 400
    path = os.path.join(app.config["UPLOAD_FOLDER"], f.filename)
    f.save(path)
    assistant.add_pdf(path)
    return jsonify(status="ingested"), 200

@app.route("/chat", methods=["POST"])
def chat():
    data     = request.json or {}
    question = data.get("message", "").strip()
    lang     = data.get("lang", "en-US")
    result   = assistant.answer(question=question, lang=lang)
    return jsonify(
        context   = result["context"],
        wiki_html = result["wiki_html"],
        wiki_url  = result["wiki_url"]
    ), 200

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming = request.values.get("Body", "").strip()
    resp     = MessagingResponse()
    msg      = resp.message()
    result   = assistant.answer(incoming, lang="en-US")
    body     = result["context"] or ""
    if result["wiki_url"]:
        body += f"\n\nRead more on Wikipedia:\n{result['wiki_url']}"
    msg.body(body)
    return Response(str(resp), mimetype="application/xml")

# ----------------------------------------------------------------------
# 7. Speech-to-Text & Text-to-Speech
# ----------------------------------------------------------------------

@app.route("/stt", methods=["POST"])
def stt():
    audio_file = request.files.get("file")
    lang       = request.form.get("lang", "en-US").split("-")[0]
    audio_bytes= audio_file.read()
    client     = speech.SpeechClient()
    config     = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code=lang
    )
    audio = speech.RecognitionAudio(content=audio_bytes)
    res   = client.recognize(config=config, audio=audio)
    transcript = ""
    if res.results:
        transcript = res.results[0].alternatives[0].transcript
    return jsonify(transcript=transcript)

@app.route("/tts", methods=["POST"])
def tts():
    data = request.json or {}
    text = data.get("text", "")
    lang = data.get("lang", "en-US")
    client = texttospeech.TextToSpeechClient()
    inp    = texttospeech.SynthesisInput(text=text)
    voice  = texttospeech.VoiceSelectionParams(
        language_code=lang,
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    cfg    = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    resp   = client.synthesize_speech(
        input=inp, voice=voice, audio_config=cfg
    )
    return Response(resp.audio_content, mimetype="audio/mpeg")

# ----------------------------------------------------------------------
# 8. Run the App
# ----------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)