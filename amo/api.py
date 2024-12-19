import requests


def get_access_token(client_id, client_secret, code, redirect_url, subdomain):
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_url,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    try:
        response = requests.post(f"https://{subdomain}.amocrm.ru/oauth2/access_token",
                                 data=data)
        print(123)
    except requests.exceptions.RequestException:
        raise
    else:
        if response.status_code != 200:
            raise Exception(response.json()["hint"])
        if response.status_code != 200:
            return
        response = response.json()
