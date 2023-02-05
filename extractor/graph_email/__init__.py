import time

import requests


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
