import os.path
import json

import msal
import requests
import csv
import configparser

from msal import TokenCache

config = configparser.ConfigParser()


class SerializableTokenCache(TokenCache):
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.load()

    def save(self):
        with open(self.file_path, "w") as cache_file:
            cache_data = self.serialize()
            cache_json = json.dumps(cache_data)
            cache_file.write(cache_json)

    def load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as cache_file:
                cache_json = cache_file.read()
                cache_data = json.loads(cache_json)
                self.deserialize(cache_data)


def get_header_auth_token() -> dict[str, str] | None:
    # Replace <client_id> and <client_secret> with your app's client ID and secret
    # Replace <tenant_id> with your Azure Active Directory tenant ID
    # Replace <redirect_uri> with the redirect URI of your app

    config.read('../config.ini')
    client_id = config['auth']['client_id']
    client_secret = config['auth']['client_secret']
    tenant_id = config['auth']['tenant_id']
    # Request an access token
    token_response = requests.post(
        f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token',
        data={
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials',
            'scope': 'https://graph.microsoft.com/.default'
        }
    )

    # Check if the request was successful
    if token_response.status_code == 200:
        access_token = token_response.json()['access_token']

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }

        # Get the tenant ID
        response = requests.get('https://graph.microsoft.com/v1.0/tenantDetails', headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            tenant_id = response.json()['value'][0]['tenantId']
            print(f'Tenant ID: {tenant_id}')
            print(f'Access_token: {access_token}')
            return headers
        else:
            print(f'Request failed with status code: {response.status_code}')
            return None
    else:
        print(f'Token request failed with status code: {token_response.status_code}')
        return None


def get_token():
    cache = SerializableTokenCache("token_cache.json")

    config.read('../config.ini')

    CLIENT_ID = config['auth']['client_id']
    TENANT_ID = config['auth']['tenant_id']
    SCOPES = ["https://graph.microsoft.com/.default"]
    AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache
    )

    result = None

    # First, try to get a token from cache
    result = app.acquire_token_silent_with_error(SCOPES, account=None)

    if not result:
        # result = app.acquire_token_for_client(scopes=config["scope"])
        result = app.acquire_token_for_client(scopes=SCOPES)

        # Get the access token from the result
        access_token = result.get("access_token")
        return access_token
    return None


def teste_auth(access_token):
    # Use the access token to make a request to the Microsoft Graph API
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }

    response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)


def ler_emails(auth_header, email_id):
    # Replace <email_id> with the ID of the graph_email you want to retrieve
    response = requests.get(f'https://graph.microsoft.com/v1.0/me/messages/{email_id}', headers=auth_header)

    # Check if the request was successful
    if response.status_code == 200:
        email = response.json()
        body = email['body']['content']
        categories = email['categories']
        data = [[body, categories]]

        # Write the data to a .csv file
        with open('email_data.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Body', 'Categories'])
            writer.writerows(data)
    else:
        print(f'Request failed with status code: {response.status_code}')


if __name__ == '__main__':
    access_token = get_token()
    teste_auth(access_token)
