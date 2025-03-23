from tests.utils.avito_utils import avito_accounts


def pytest_sessionstart(session):
    avito_accounts.init_config_seller_data()


def pytest_sessionfinish(session):
    pass
