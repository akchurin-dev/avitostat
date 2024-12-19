from amocrm.v2 import Lead, tokens

if __name__ == '__main__':

    tokens.default_token_manager(
        client_id="5de4aef8-4d84-4475-af8c-a0a9c80117b7",
        client_secret="s9gIlHcDyaI2r8nhlaAO4pardo7YyyStyUM0EDRS4PJU190gWdSrQ2V4WVM8WXU9",
        subdomain="abduraufdev",
        redirect_url="https://7662-2a0c-16c1-1-1500-225-c0ff-fe00-ef.ngrok-free.app/amo/oauth_callback",
        storage=tokens.FileTokensStorage(),  # by default FileTokensStorage
    )
    tokens.default_token_manager.init(code="def50200266a2b90c9c559cfc0d4271661897eaa2142aed853880c318a3af33cdec01b465ca4485cc746e13abc20958185627d8f4f4339f551f09d453aa05495a15a018615f1f9de95544c7280489662942a8d4edb520b2cd32d412653e397c50a3e3bdafd6dde5d79e37e422ee18acaa4ad30f5b0466c86b81f90d84653192ad48b967c896511aaaeb0da6cb63d4362140e3fd576c42f41a14dab82cedf181e7db1772df25dc8b121f3e69061ca2a0ff96933e3618aba96b1604d7e9239115913a8cc1694ca40222aa619891c74860518980ad2ca8ed1d282854d78c0fb663ec1203f9632e6da0c04ec9a8822a2b3bcc9e8cb8261b16c3d4afdbd31d03f5b0e66dba022bf8db25f6f8a725a919a78de3aaba0f630e8ae400ab32a4cd04943a535948447293bb7360cab25785d70ad344cd7add43704c9cc0b5f64b9967c55f00a86d2627f5c46c3bb77efeff56ed0e4a46a0f688a6b89bc5fd0f86b5afb5d9239e218aeeba430e0f1a999eb362c17d8dce7f1d0c802e88fbd42833f91756d63f541e1915c2f3f9a46c03a923ae215456cdc9c9096129079c6d3b7d6a9fe87571f85d24c7815828edd0da4bf6844c1979c7c0e1b6a3cbe18995d69443329bf7e1d57fa45c8cc04b278e57bfb10cbbea1b5faf78a5e24f2af47a15ec0b11ece86b0636fc8afac856469a37697aff6ed1626dd59fed64d6632bcc570602f98d08b70f8d1c1c39c79f8619f1909ad400fd85f0676e6fed3de2a75755d66b5e99d2c06504a", skip_error=False)

    leads = Lead.objects.all()

    for _ in leads:
        print(_.name)
