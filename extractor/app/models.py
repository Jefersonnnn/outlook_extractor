# app/models.py
from extractor.app import db

import uuid


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    applications = db.relationship('Application', secondary='user_application',
                                   backref=db.backref('users', lazy='dynamic'))


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)


class UserApplication(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), primary_key=True)



class Email(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    ol_email_id = db.Column(db.String(255), primary_key=True, autoincrement=False, nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    receveid_date = db.Column(db.DateTime, nullable=False)
    raw_body = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text)
    categories = db.Column(db.String(255), nullable=True)
    download_history_uuid = db.Column(db.String(255), db.ForeignKey('download_history.uuid'))

    # folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=False)

    def __repr__(self):
        return '<Email %r>' % self.subject


class DownloadHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    uuid = db.Column(db.String(255), default=str(uuid.uuid4()), unique=True, nullable=False)
    email = db.Column(db.String(255), nullable=False)
    parentFolderId = db.Column(db.String(255), nullable=False)
    qtd_emails = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20))
    data = db.Column(db.DateTime)