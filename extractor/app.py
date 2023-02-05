import json
import threading
import uuid
from datetime import datetime

from flask import Flask, render_template, session, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

from extractor.utils import html_to_text
from flask_session import Session  # https://pythonhosted.org/Flask-Session
import msal
from extractor import app_config

from extractor.graph_email import EmailFolders

app = Flask(__name__)
app.config.from_object(app_config)
app.config["DEBUG"] = True
Session(app)
db = SQLAlchemy(app)


# class Folder(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     id_folder = db.Column(db.String(255), nullable=False)
#     nome = db.Column(db.String(100), nullable=False)
#     data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
#     emails = db.relationship('Email', backref='folder', lazy=True)


class Email(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    ol_email_id = db.Column(db.String(255), primary_key=True, autoincrement=False, nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    receveid_date = db.Column(db.DateTime, nullable=False)
    raw_body = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text)
    categories = db.Column(db.String(255), nullable=True)

    # folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=False)

    def __repr__(self):
        return '<Email %r>' % self.subject


class DownloadHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    uuid = db.Column(db.String(255), default=str(uuid.uuid4()), unique=True, nullable=False)
    # folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=False)
    parentFolderId = db.Column(db.String(255), nullable=False)
    qtd_emails = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20))
    data = db.Column(db.DateTime)


# This section is needed for url_for("foo", _external=True) to automatically
# generate http scheme when this sample is running on localhost,
# and to generate https scheme when it is deployed behind reversed proxy.
# See also https://flask.palletsprojects.com/en/1.0.x/deploying/wsgi-standalone/#proxy-setups
from werkzeug.middleware.proxy_fix import ProxyFix

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


@app.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))
    return render_template('index.html', user=session["user"], version=msal.__version__)


@app.route("/login")
def login():
    # Technically we could use empty list [] as scopes to do just sign in,
    # here we choose to also collect end user consent upfront
    session["flow"] = _build_auth_code_flow(scopes=app_config.SCOPE)
    return render_template("login.html", auth_url=session["flow"]["auth_uri"], version=msal.__version__)


@app.route(app_config.REDIRECT_PATH, methods=['GET'])  # Its absolute URL must match your app's redirect_uri set in AAD
def authorized():
    try:
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_auth_code_flow(
            session.get("flow", {}), request.args)
        if "error" in result:
            return render_template("auth_error.html", result=result)
        session["user"] = result.get("id_token_claims")
        _save_cache(cache)
    except ValueError:  # Usually caused by CSRF
        pass  # Simply ignore them
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()  # Wipe out user and its token cache from session
    return redirect(  # Also logout from your tenant's web session
        app_config.AUTHORITY + "/oauth2/v2.0/logout" +
        "?post_logout_redirect_uri=" + url_for("index", _external=True))


@app.route("/folders", defaults={'folder_id': None, 'message_id': None})
@app.route("/folders/<folder_id>/messages/<message_id>", defaults={'message_id': None})
@app.route('/folders/<folder_id>', defaults={'message_id': None})
def get_folders(folder_id, message_id):
    token = _get_token_from_cache(app_config.SCOPE)
    if not token:
        return redirect(url_for("login"))

    if message_id:
        token = _get_token_from_cache(app_config.SCOPE)
        if not token:
            return redirect(url_for("login"))

        email_folders = EmailFolders(token)
        message = email_folders.get_message_by_id(folder_id, message_id)

        return message if message else []

    email_folders = EmailFolders(token)
    folders = email_folders.get_folders(folder_id)
    return render_template('email_folders.html', listFolders=folders, user=session["user"], version=msal.__version__)


@app.route("/extract_emails/<folder_id>")
def download_emails(folder_id):
    token = _get_token_from_cache(app_config.SCOPE)
    if not token:
        return redirect(url_for("login"))

    # Create a separete thread to fetch emails
    thread = threading.Thread(target=_get_emails_worker, args=(folder_id, token,))
    thread.start()

    return redirect(url_for("downloads"))


@app.route("/downloads")
def downloads():
    db.create_all()
    download_history = db.session.query(DownloadHistory).all()
    file_emails = []
    for dh in download_history:
        _id = dh.uuid
        _status = dh.status
        _data = dh.data
        _qtd = dh.qtd_emails
        _parent_id = dh.parentFolderId
        file_emails.append(
            {'id': _id,
             'parent_id': _parent_id,
             'qtd_emails': _qtd,
             'status': _status,
             'data': _data})

    # folder_path = os.path.join("./download_emails")
    # file_emails = []
    # for filename in os.listdir(folder_path):
    #     if filename.endswith('.csv'):
    #         file_path = os.path.join(folder_path, filename)
    #         file_size = os.path.getsize(file_path)
    #         file_modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    #         file_emails.append(
    #             {'file_name': filename, 'file_size': file_size, 'file_modiefied_time': file_modified_time})

    return render_template("downloads.html", downloads=file_emails)


def _get_emails_worker(folder_id: str, token: str):
    email_folders = EmailFolders(token)
    emails = email_folders.get_messages(folder_id)

    # id_f = None
    # with app.app_context():
    #
    #
    #     id_f = db.session.add(Folder(nome="Teste", data_criacao=datetime.utcnow(), id_folder=folder_id))
    #
    #     db.session.commit()
    try:
        with app.app_context():
            db.create_all()
            for email in emails:
                subject = None
                raw_body = None
                body = None
                categorias = None
                print("=========--------=========---------========")
                print("email_id: ", email["id"])
                print("parent_folder_id: ", email["parentFolderId"])
                categorias = ";".join(str(i) for i in email["categories"])
                if email["subject"]:
                    subject = email["subject"] if len(email["subject"]) < 255 else email["subject"][:255]
                else:
                    subject = ""
                raw_body = html_to_text(email['body']['content']) if len(email['body']['content']) > 0 else email[
                    "subject"]
                body = email['body']['content'] if len(email['body']['content']) < 65000 else email['body']['content'][
                                                                                              :65000]
                db.session.add(Email(
                    ol_email_id=email["id"],
                    subject=subject,
                    receveid_date=datetime.strptime(email["receivedDateTime"], '%Y-%m-%dT%H:%M:%SZ'),
                    raw_body=raw_body,
                    body=body,
                    categories=categorias))
                db.session.commit()

        with app.app_context():
            # Salvar historico
            db.session.add(DownloadHistory(status='Success', data=datetime.utcnow(), qtd_emails=len(emails),
                                           parentFolderId=emails[0]['parentFolderId']))
            db.session.commit()

        print("Download finalizado")

    except Exception as e:
        print(e)
        with app.app_context():
            # Salvar historico
            db.session.add(DownloadHistory(status='Error', data=datetime.utcnow(), qtd_emails=-1,
                                           parentFolderId=emails[0]['parentFolderId']))
            db.session.commit()

    # _path_folder = os.path.join("./download_emails")
    #
    # if not os.path.exists(_path_folder):
    #     os.mkdir(_path_folder)
    #
    # name_file = folder_id + ".csv"
    # with open(os.path.join(_path_folder, name_file), "w", encoding="utf-8") as file:
    #     writer = csv.writer(file, delimiter=';')
    #     writer.writerow(["Subject", "Received Date", "Body", "Categories"])
    #     for email in emails:
    #         writer.writerow([email["subject"], email["receivedDateTime"], html_to_text(email['body']['content']), email["categories"]])


@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for("index"))


def _load_cache():
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache


def _save_cache(cache):
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()


def _build_msal_app(cache=None, authority=None) -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        app_config.CLIENT_ID, authority=authority or app_config.AUTHORITY,
        client_credential=app_config.CLIENT_SECRET, token_cache=cache)


def _build_auth_code_flow(authority=None, scopes=None):
    return _build_msal_app(authority=authority).initiate_auth_code_flow(
        scopes or [],
        redirect_uri=url_for("authorized", _external=True))


def _get_token_from_cache(scope=None):
    cache = _load_cache()  # This web app maintains one cache per session
    cca = _build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:  # So all account(s) belong to the current signed-in user
        result = cca.acquire_token_silent(scope, account=accounts[0])
        _save_cache(cache)
        return result


app.jinja_env.globals.update(_build_auth_code_flow=_build_auth_code_flow)  # Used in template
