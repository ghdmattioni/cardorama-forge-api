from fastapi.testclient import TestClient
from api import app, convert
c = TestClient(app)
def test_health():
    assert c.get('/healthz').status_code == 200
def test_no_key():
    assert c.get('/v1/simulations/nope').status_code == 401
def test_commander_invalid():
    try:
        convert('1 Sol Ring','test','commander')
        assert False
    except ValueError:
        pass
def test_constructed_conversion():
    assert '[Main]' in convert('4 Sol Ring','test','constructed')
def test_ready_absent_or_present():
    assert c.get('/readyz').status_code in (200,503)
