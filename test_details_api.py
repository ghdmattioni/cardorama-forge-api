from fastapi.testclient import TestClient
from api import app, Request
c=TestClient(app)

def test_detail_mode_limit():
    assert Request(games=1,mode="detailed",decks=[{"name":"a","decklist":"1 Sol Ring"},{"name":"b","decklist":"1 Sol Ring"}]).mode=="detailed"

def test_protected_events_endpoint():
    assert c.get("/v1/simulations/unknown/games/1").status_code==401
