import os

import pytest
from fastapi.testclient import TestClient

from src.api import app

# These tests need the saved model file. If it doesn't exist yet (for example on
# a fresh copy of the repo), skip them instead of failing.
pytestmark = pytest.mark.skipif(
    not os.path.exists("models/latest.joblib"),
    reason="Run `python -m src.train` first to create the model file.",
)


@pytest.fixture(scope="module")
def client():
    # Using TestClient inside `with` makes the app run its startup code,
    # so the model gets loaded just like in the real server.
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_teams_lists_all_32_teams_strongest_first(client):
    teams = client.get("/teams").json()
    assert len(teams) == 32
    ratings = [t["elo"] for t in teams]
    assert ratings == sorted(ratings, reverse=True)


def test_predict_returns_valid_probabilities(client):
    response = client.get("/predict", params={"home_team": "KC", "away_team": "BUF"})
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["home_win_prob"] <= 1
    # The two teams' chances should add up to 100% (allowing for rounding).
    assert body["home_win_prob"] + body["away_win_prob"] == pytest.approx(1, abs=0.002)
    assert body["pick"] in ("KC", "BUF")


def test_predict_accepts_lowercase_team_names(client):
    response = client.get("/predict", params={"home_team": "kc", "away_team": "buf"})
    assert response.status_code == 200
    assert response.json()["home_team"] == "KC"


def test_better_rated_home_team_is_favored(client):
    teams = client.get("/teams").json()
    best, worst = teams[0]["team"], teams[-1]["team"]
    response = client.get("/predict", params={"home_team": best, "away_team": worst})
    assert response.json()["home_win_prob"] > 0.5


def test_unknown_team_returns_404(client):
    response = client.get("/predict", params={"home_team": "ZZZ", "away_team": "KC"})
    assert response.status_code == 404


def test_same_team_returns_400(client):
    response = client.get("/predict", params={"home_team": "KC", "away_team": "KC"})
    assert response.status_code == 400


def test_out_of_range_rest_returns_422(client):
    response = client.get(
        "/predict", params={"home_team": "KC", "away_team": "BUF", "rest_diff": 99}
    )
    assert response.status_code == 422


def test_upcoming_returns_requested_number_of_games(client):
    response = client.get("/upcoming", params={"n": 5})
    assert response.status_code == 200
    assert len(response.json()) == 5