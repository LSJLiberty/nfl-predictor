import pandas as pd
import pytest

from src.features import START, add_elo, add_rolling_features
from src.predict import predict_matchup


def make_games():
    """Four tiny made-up games between teams AAA, BBB, and CCC."""
    rows = [
        ("g1", "2024-09-01", 2024, "AAA", "BBB", 27, 20),
        ("g2", "2024-09-08", 2024, "BBB", "CCC", 10, 24),
        ("g3", "2024-09-15", 2024, "AAA", "CCC", 31, 17),
        ("g4", "2024-09-22", 2024, "BBB", "AAA", 14, 21),
    ]
    games = pd.DataFrame(
        rows,
        columns=["game_id", "gameday", "season", "home_team", "away_team",
                 "home_score", "away_score"],
    )
    games["gameday"] = pd.to_datetime(games["gameday"])
    games["home_rest"] = 7
    games["away_rest"] = 7
    return games


def test_first_game_has_no_history():
    out = add_rolling_features(make_games())
    first = out[out["game_id"] == "g1"].iloc[0]
    assert pd.isna(first["home_win_pct_last5"])
    assert pd.isna(first["away_margin_last5"])


def test_rolling_features_use_only_earlier_games():
    out = add_rolling_features(make_games())
    # AAA's second game is g3 (at home). It should see only g1: a 27-20 win.
    g3 = out[out["game_id"] == "g3"].iloc[0]
    assert g3["home_win_pct_last5"] == 1.0
    assert g3["home_margin_last5"] == 7.0
    assert g3["home_pts_for_last5"] == 27.0


def test_elo_is_recorded_before_the_game_and_is_zero_sum():
    games, ratings = add_elo(make_games())
    # Before any game is played, both teams are at the starting rating.
    assert games.loc[0, "home_elo"] == START
    assert games.loc[0, "elo_diff"] == 0
    # Points only move between teams, so the average rating never changes.
    assert sum(ratings.values()) / len(ratings) == pytest.approx(START)


def test_winner_gains_rating_and_loser_loses_it():
    _, ratings = add_elo(make_games().head(1))
    assert ratings["AAA"] > START
    assert ratings["BBB"] < START


def test_unknown_team_raises_an_error():
    bundle = {"ratings": {}, "team_form": pd.DataFrame()}
    with pytest.raises(ValueError):
        predict_matchup(bundle, "XXX", "YYY")