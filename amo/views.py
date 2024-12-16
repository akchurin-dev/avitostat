import json

from amocrm.v2 import tokens
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from avito_account.oauth_utils import create_or_update_avito_account
from base import settings


# Create your views here.
# ?code=def5020021105755907d5ac354594295f06d8dd18247358deb80ad0b5bd329daed4530b623fd203f40927eb945dd8cb069b211b0d356ffca7a64e2a8cb8b503252bc0bff8d0587680bb6799b60fec6b3c14bf9573dca921b4b9fff718aa47f16bc634d66eff197aac568f26f6434851bba4788f8c34995d8ef6e5e143258010f2b87beb5798f78146b4f0ef192db886017fb2997a02d6747bda5ef579478baa33ff3559b14cc66b06f9e2e8b54e0c3e7663829983e688ef08cb01d1e3e6697f68f791e977ddfeccd62ad0e04c8c65878570698ee779b2fb2de824ae6e5134fe8b64a9a377543f0ae9e3ee8918997187bab1203baa8a78c1bc7a85f6ae65ccb063c23d6b60b76005e2c409af8ab1871c849a2bb5e7b65d879a7e1ef306856849861f5497b6a85dc4b64a9533f2224e8f2abd41f4358f6ed9f088b4dedcdc98debbf7041a8a47f23a2ee22f25a982262d718dc2fc3af606a498882abd9515f1cfa462d8b625929d82fa5acc358c6d0f8c4d5b2277423338a7fa4ac6bd32f56e999c5076594760810c74dc8c83bd9be178a0d7325140c23884d2e45e852b6d0695ed7a51a2d235619ce1aaa516ef1ddcdca21616af057f6061aa6e424eacd073c3e0b9365a1db45e2f52f4b9e32358feca7474a36c5775508369264f6c7c2999bb59f9f2348f28b61d785d64eff925163bb7abccbd8a4068dda3b4b36dcc761b5f859e82338d4be9ae5fd001b4361d955fe912c024d8e30de1d6c42dad0b07c688b291f6661b3&state=false&referer=abduraufdev.amocrm.ru&platform=1&client_id=5cc2f970-fe3d-47a0-9b38-86d531fa92ff

@method_decorator(csrf_exempt, name='dispatch')
class AmocrmOauthCallbackView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code", None)
        client_id = request.GET.get("client_id", None)
        referer = request.GET.get("referer", None)
        subdomain = referer.split(".")[0]

        tokensz = tokens.default_token_manager(
            client_id=client_id,
            client_secret="9V2b5wCkiZshqqnW0x7pmwVmlaS9YkPigtQw82MgDAYDFuse9YrMaaNlAKowgxHM",
            subdomain=subdomain,
            redirect_url="https://7662-2a0c-16c1-1-1500-225-c0ff-fe00-ef.ngrok-free.app/amo/oauth_callback",
            storage=tokens.MemoryTokensStorage(),  # by default FileTokensStorage
        )
        tokens.default_token_manager.init(code=code, skip_error=False)

        access_token = tokens.default_token_manager.get_access_token()








        # if state is not None:
        #     state_dict = json.loads(state)
        #     created_by_id = state_dict.get("created_by_id", None)
        #     if code:
        #         create_or_update_avito_account(code=code, created_by_id=int(created_by_id))
        #         if settings.ENVIRONMENT == "PRODUCTION":
        #             redirect_url = "https://avitostata.ru/admin/avito_account/avitoaccount/"
        #             return HttpResponseRedirect(redirect_url)
        #         else:
        #             return JsonResponse(
        #                 {"message": "Аккаунт успешно добавлен, вы будете перенаправлены на главную страницу"})
        #     else:
        #         return JsonResponse({"message": "Предоставьте код авторизации"}, status=400)

