from amocrm.v2 import tokens

tokens.default_token_manager(
    client_id="xxx-xxx-xxxx-xxxx-xxxxxxx",
    client_secret="xxxx",
    subdomain="subdomain",
    redirect_url="https://xxxx/xx",
    storage=tokens.FileTokensStorage(),  # by default FileTokensStorage
)
tokens.default_token_manager.init(code="..very long code...", skip_error=False)
