import requests


def get_access_token(client_id, client_secret, code, redirect_url):
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_url,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    try:
        response = requests.post("https://{}.amocrm.ru/oauth2/access_token".format(self.subdomain), json=data)
    except requests.exceptions.RequestException:
        logger.warning("can't init tokens")
        if not skip_error:
            raise
    else:
        if response.status_code != 200 and not skip_error:
            raise Exception(response.json()["hint"])
        if response.status_code != 200 and skip_error:
            return
        response = response.json()
        self._storage.save_tokens(response["access_token"], response["refresh_token"])
        logger.info("successful init and store tokens in %s store", self._storage)