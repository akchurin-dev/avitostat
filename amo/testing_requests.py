from amocrm.v2 import Lead, tokens

if __name__ == '__main__':

    tokens.default_token_manager(
        client_id="5cc2f970-fe3d-47a0-9b38-86d531fa92ff",
        client_secret="xQTCjwLSWs7z7DmYy9V8J3j9S24zd2mco6yGZg3PTZFuXbhD3ztMuYTHRT987UJD",
        subdomain="abdurauf",
        redirect_url="https://7662-2a0c-16c1-1-1500-225-c0ff-fe00-ef.ngrok-free.app/amo/oauth_callback",
        storage=tokens.FileTokensStorage(),  # by default FileTokensStorage
    )
    tokens.default_token_manager.init(code="def502006b57524e03f7b82b8bebdbc06fe72071206b1aeff5fa96e31040e90afc80ba9b17429e5298fe503c9dda4920e9d9a73bbc0b6da874aea98b17396b82c1bd73568c196984ed3d7961f8164f55172bccc49d8851d5dfdb9f6e7c9a596b27f737cde55932923436298d20178052f57fc2b6659bc4e5de9e91351026d863a97009a2189eadbeff415c72f61db15bc01b2099aaccc0c3428f5bf6257c7b158a6accf04ef6e7a47bafe221ad8ed23b522b3d031e3a3bf0d0bf335782eba7280ff229bd72a126f6da1b66a59c7dd104ee761f4075a1f3574a0c7c54ad8fc2b56919979c596659d6c25c9a3f5dfd218f17b3ef64a2ca7c829399370122446652623dac4e259ef3b16640879d4f829e25d259b084be66b222b6a2db7c5928878b9a9f6b44f22b2b8086cf22b95f318d0f6bbc367d5ab63e85aeaba6c92592639759f59ea1650206477c227be8346d12612d3ce413f30f7c693b4b24248e200cf4fe641bae81e6e0aba0b48d60efd7eee3ca66195b1c3e545e34a661d53f61039fc9fef0d290493086e28dacddfee491d3d59a364c44673606f2107469800e9d380d8214a4299859c9cfb9911eced2902e24db01da72d21c8815f1214b9c94d8f871c054de8465f37a6c15a7afaf77022349c49afd8dc9551a008f18717cd568976fbbaf9c67ea18c60d4a54500b2c00cb307862dc180136ed951d607f30d5f1f2a3bef288d69140dc7c8a15f09be67a822dfe0bbc01194274796598008efbf7c81a4c54", skip_error=False)

    leads = Lead.objects.all()

    for _ in leads:
        print(_.name)
