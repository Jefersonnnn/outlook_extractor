import time
from datetime import datetime
import requests
from extractor.app import db, create_app
from extractor.app.models import Email, DownloadHistory

app = create_app

class EmailFolders:
    def __init__(self, access_token):
        if 'access_token' in access_token:
            self.access_token = access_token['access_token']
        else:
            self.access_token = access_token
        self.base_url = "https://graph.microsoft.com/v1.0/me/mailFolders"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def get_folders(self, parent_folder_id=None):
        if parent_folder_id:
            url = f"{self.base_url}/{parent_folder_id}/childFolders"
        else:
            url = self.base_url
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()["value"]
        else:
            raise Exception(f"Failed to get folders: {response.text}")

    def get_messages(self, folder_id):
        if not folder_id:
            raise Exception("Folder id não informada!")
        emails = []
        next_link = f"{self.base_url}/{folder_id}/messages?top=100&skip=0"
        while next_link:
            time.sleep(0.05)
            print("Carregando e-mails ->", next_link)
            response = requests.get(next_link, headers=self.headers)
            if response.status_code != 200:
                print("Falha ao obter e-mails. Código de status: ", response.status_code)
                break
            data = response.json()
            emails.extend(data["value"])
            if "@odata.nextLink" in data:
                next_link = data["@odata.nextLink"]
            else:
                next_link = None
        print("Finalizado download dos e-mails")
        return emails

    def get_message_by_id(self, folder_id, message_id):
        if not folder_id:
            raise Exception("Folder id não informada!")
        if not message_id:
            raise Exception("Message id não informada!")

        url = f"{self.base_url}/{folder_id}/messages/{message_id}"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            print("Falha ao obter e-mails. Código de status: ", response.status_code)
            return None
        return response.json()


from extractor.utils import html_to_text


def get_emails_worker(folder_id: str, token: str, user_email: str):
    email_folders = EmailFolders(token)
    emails = email_folders.get_messages(folder_id)

    try:
        uuid_history = None
        with app.app_context():
            db.create_all()
            # Salvar historico
            download_history = DownloadHistory(status='Pending',
                                               email=user_email,
                                               data=datetime.utcnow(),
                                               qtd_emails=len(emails),
                                               parentFolderId=emails[0]['parentFolderId'])
            db.session.add(download_history)
            db.session.commit()
            uuid_history = download_history.uuid

        with app.app_context():
            for email in emails:
                subject, raw_body, body, categorias = None, None, None, None

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
                    download_history_uuid=download_history.uuid,
                    subject=subject,
                    receveid_date=datetime.strptime(email["receivedDateTime"], '%Y-%m-%dT%H:%M:%SZ'),
                    raw_body=raw_body,
                    body=body,
                    categories=categorias))

            download_history = db.session.query(DownloadHistory).filter_by(uuid=uuid_history).first()
            download_history.status = "Success"
            db.session.commit()
        print("Download finalizado")
    except Exception as e:
        print(e)
        with app.app_context():
            # Salvar historico
            download_history = db.session.query(DownloadHistory).filter_by(uuid=uuid_history).first()
            if not download_history:
                raise Exception
            download_history.status = "Error"
            db.session.commit()
