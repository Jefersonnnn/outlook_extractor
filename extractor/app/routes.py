# app/routes.py
from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, send_file
import threading
from .auth import _load_cache, _build_msal_app, _save_cache, _get_token_from_cache, _build_auth_code_flow
from .models import User, Application, UserApplication, DownloadHistory
from extractor.app import db
from .. import app_config
from ..graph_email import EmailFolders

bp = Blueprint('routes', __name__)

@bp.route('/register', methods=['POST'])
def register():
    user = User(username=request.json['username'], password=request.json['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User created successfully!'}), 201


@bp.route('/user/<username>', methods=['GET'])
def get_user_data(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404
    applications = [app.name for app in user.applications]
    return jsonify({'data': user.username, 'applications': applications})


@bp.route('/application', methods=['POST'])
def create_application():
    application = Application(name=request.json['name'])
    db.session.add(application)
    db.session.commit()
    return jsonify({'message': 'Application created successfully!'}), 201


@bp.route('/user/<username>/application', methods=['POST'])
def add_user_to_application(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404
    application = Application.query.filter_by(name=request.json['application_name']).first()
    if not application:
        return jsonify({'message': 'Application not found'}), 404
    user_application = UserApplication(user_id=user.id, application_id=application.id)
    db.session.add(user_application)
    db.session.commit()
    return []


@bp.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("routes.login"))
    return render_template('index.html', user=session["user"])


@bp.route("/login")
def login():
    # Technically we could use empty list [] as scopes to do just sign in,
    # here we choose to also collect end user consent upfront
    session["flow"] = _build_auth_code_flow(scopes=app_config.SCOPE)
    return render_template("login.html", auth_url=session["flow"]["auth_uri"])


@bp.route(app_config.REDIRECT_PATH, methods=['GET'])  # Its absolute URL must match your app's redirect_uri set in AAD
def authorized():
    try:
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_auth_code_flow(
            session.get("flow", {}), request.args)
        if "error" in result:
            return render_template("auth_error.html", result=result)
        session["user"] = result.get("id_token_claims")
        _save_cache(cache)
    except ValueError as e:  # Usually caused by CSRF
        print(e)
        pass  # Simply ignore them
    return redirect(url_for("routes.index"))


@bp.route("/logout")
def logout():
    session.clear()  # Wipe out user and its token cache from session
    return redirect(  # Also logout from your tenant's web session
        app_config.AUTHORITY + "/oauth2/v2.0/logout" +
        "?post_logout_redirect_uri=" + url_for("routes.index", _external=True))


@bp.route("/folders", defaults={'folder_id': None})
@bp.route('/folders/<folder_id>')
def get_folders(folder_id):
    token = _get_token_from_cache(app_config.SCOPE)
    if not token:
        return redirect(url_for("routes.login"))

    email_folders = EmailFolders(token)
    folders = email_folders.get_folders(folder_id)
    return render_template('email_folders.html', listFolders=folders, user=session["user"])


@bp.route("/extract_emails/<folder_id>")
def extract_emails(folder_id):
    token = _get_token_from_cache(app_config.SCOPE)
    if not token:
        return redirect(url_for("routes.login"))

    # Create a separete thread to fetch emails
    thread = threading.Thread(target=_get_emails_worker, args=(folder_id, token, session['user']['preferred_username']))
    thread.start()

    return redirect(url_for("routes.downloads"))


@bp.route("/list_downloads")
def downloads():
    download_history = db.session.query(DownloadHistory).all()
    file_emails = []
    for dh in download_history:
        _id = dh.uuid
        _status = dh.status
        _data = dh.data
        _qtd = dh.qtd_emails
        _parent_id = dh.parentFolderId
        file_emails.append(
            {'uuid': _id,
             'parent_id': _parent_id,
             'qtd_emails': _qtd,
             'status': _status,
             'data': _data})

    return render_template("downloads.html", downloads=file_emails, user=session["user"])


@bp.route("/download_emails/<string:download_history_uuid>", methods=["GET"])
def download_emails(download_history_uuid):
    emails = Email.query.filter_by(download_history_uuid=download_history_uuid).all()

    csv_file = _save_to_csv(emails)

    return send_file(
        io.BytesIO(csv_file.read().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="emails.csv"
    )


@bp.errorhandler(404)
def page_not_found(e):
    return redirect(url_for("routes.index"))
