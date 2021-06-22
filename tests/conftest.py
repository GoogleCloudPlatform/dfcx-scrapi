import pytest

def pytest_addoption(parser):
    parser.addoption("--creds", action="store")

@pytest.fixture(scope='session')
def creds(request):
    return request.config.getoption("--creds")