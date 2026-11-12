import numpy as np
import pandas as pd

from src.features import FEATURES
from src.model import make_model
from src.predict import predict_matchup


def make_bundle():
    """A tiny made-up bundle: two teams, and a model trained on random data."""
    rng = np.random.default_rng(1)
    X = pd.DataFrame(rng.normal(size=(300, len(FEATURES))), columns=FEATURES)
    # Rest really matters in this made-up world, so the model should learn a positive weight for it.
    y = (X["elo_diff"] + 0.5 * X["margin_diff"] + 0.8 * X["rest_diff"]
         + rng.normal(size=300) > 0).astype(int)
    form = pd.DataFrame(
        {
            "win_pct_last5": [0.8, 0.4],
            "margin_last5": [9.0, -3.0],
            "pts_for_last5": [28.0, 19.0],
            "pts_against_last5": [19.0, 22.0],
        },
        index=["AAA", "BBB"],
    )
    return {
        "model": make_model().fit(X, y),
        "features": FEATURES,
        "ratings": {"AAA": 1620.0, "BBB": 1430.0},
        "team_form": form,
    }


def test_factors_are_the_four_reasons_in_order():
    result = predict_matchup(make_bundle(), "AAA", "BBB", with_factors=True)
    names = [f["name"] for f in result["factors"]]
    assert names == ["Home-field advantage", "Team strength (Elo)", "Recent form", "Rest"]


def test_factors_add_up_to_the_final_probability():
    result = predict_matchup(make_bundle(), "AAA", "BBB", with_factors=True)
    total = sum(f["points"] for f in result["factors"])
    # Start from 50/50; each reason is rounded to 0.1, so allow a little slack.
    assert abs(total - (result["home_win_prob"] * 100 - 50)) < 0.3


def test_a_much_stronger_home_team_gets_credit_for_strength():
    result = predict_matchup(make_bundle(), "AAA", "BBB", with_factors=True)
    strength = next(f for f in result["factors"] if f["name"] == "Team strength (Elo)")
    assert strength["points"] > 0
    assert "1620" in strength["detail"] and "1430" in strength["detail"]


def test_a_stronger_away_team_pulls_the_other_way():
    result = predict_matchup(make_bundle(), "BBB", "AAA", with_factors=True)
    strength = next(f for f in result["factors"] if f["name"] == "Team strength (Elo)")
    assert strength["points"] < 0


def test_rest_advantage_shows_up_in_the_explanation():
    result = predict_matchup(make_bundle(), "AAA", "BBB", rest_diff=3, with_factors=True)
    rest = next(f for f in result["factors"] if f["name"] == "Rest")
    assert rest["points"] > 0
    assert "+3" in rest["detail"]


def test_factors_are_left_out_unless_requested():
    result = predict_matchup(make_bundle(), "AAA", "BBB")
    assert "factors" not in result