#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    from amocrm.v2 import tokens

    # tokens.default_token_manager(
    #     client_id="5cc2f970-fe3d-47a0-9b38-86d531fa92ff",
    #     client_secret="9V2b5wCkiZshqqnW0x7pmwVmlaS9YkPigtQw82MgDAYDFuse9YrMaaNlAKowgxHM",
    #     subdomain="abduraufdev",
    #     redirect_url="https://ya.ru",
    #     storage=tokens.FileTokensStorage(),  # by default FileTokensStorage
    # )
    # tokens.default_token_manager.init(
    #     code="def50200b2056922a3cbaf0b71b352da55b0665dab301ce0dac1e1e3b4a2aa28f6fb316b31390689ee087aba3fb98b6de2c2c8a06389501288c766c32f804f54e03ba367eaf020c0240c44fdd83e63efd19a2a15f44028c2adf0d235f3d7e77ef37d4482662c49b9b20c91947ad6a622ce59a7af8fca110cb73ab83cc60d2d59a332cefa0242651c1aa49ea26d748627472e105e19b2824fac553cd501547fba9bd0946be7283076538eb55bbfe2724ade467010834e3fd5dd88c54042bf91fbcf1645e8323718d438be8a653658c4b39a8c4da8abf3820ba4dee9cbfa5965d9b7aea5e280a4ff1cade298b160b6b4dbe5413763ea467f8838c5e5bfa3c198ad715224ab35c85419215701201047574ae6f89089cb864e6aaef86a484e11a098b36252c3add63ade92f1ff10bc8f0a3d5b838847038690b24f953204e3bad1ff36078a12dd78d808d4ff38147c96d42279da8ca853a8ac6a43a4fb23a1e66505f1eb03ac5d3d100144d5d7fd112ff3c46167dfb91968f19e86c0ca38706886db26b07ab3dc1caa7f2d504e3cfdf1c8de1b2d76edc81549f27d1e0038c6dd96c9d38527320d3d8bb6e177d16edae606629431f9a55c7fa0eb3991b20c5d460f3535c9da25b58e14cf2b16a70418c2155ed8fcb6c0656bd42e3e0b3d1ba062",
    #     skip_error=False)
    main()


