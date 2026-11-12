import os

import joblib

from src.data import load_games, split_completed
from src.evaluate import build_scorecard
from src.features import FEATURES, build_features, current_team_form
from src.model import make_model

MODEL_PATH = "models/latest.joblib"


def print_scorecard(scorecard):
    """Print the same numbers the website shows, so you can check them in the terminal."""
    backtest = scorecard["backtest"]["summary"]
    print(f"Backtest on {backtest['games']} games from {scorecard['backtest']['seasons']}")
    print(f"  home-pick baseline: {backtest['home_pick_baseline']:.3f}")
    print(f"  accuracy:           {backtest['accuracy']:.3f}"
          f"  (95% interval {backtest['accuracy_low']:.3f}-{backtest['accuracy_high']:.3f})")
    print(f"  log loss:           {backtest['log_loss']:.4f}")

    live = scorecard["live"]
    if live:
        summary = live["summary"]
        print(f"Live season {live['season']} ({summary['games']} games, model trained on earlier seasons only)")
        print(f"  home-pick baseline: {summary['home_pick_baseline']:.3f}")
        print(f"  accuracy:           {summary['accuracy']:.3f}")


def main():
    games = load_games()
    played, upcoming = split_completed(games)
    print(f"{len(played)} games played, {len(upcoming)} still to play")

    table, ratings = build_features(played)
    print(f"{len(table)} games usable for training")

    # Honest evaluation: models trained only on the past, scored on games they never saw.
    scorecard = build_scorecard(table)
    print_scorecard(scorecard)

    # The features are chosen and tested, so refit on every completed game.
    model = make_model().fit(table[FEATURES], table["home_win"])

    bundle = {
        "model": model,
        "features": FEATURES,
        "ratings": ratings,
        "team_form": current_team_form(played),
        "trained_through": str(played["gameday"].max().date()),
        "n_games": len(table),
        # The schedule of games still to be played, so the API can answer
        # "what's coming up?" without re-downloading data.
        "upcoming": upcoming[
            ["gameday", "home_team", "away_team", "home_rest", "away_rest"]
        ].reset_index(drop=True),
        # NEW in week 9: the accuracy report shown on the website.
        "scorecard": scorecard,
    }
    os.makedirs("models", exist_ok=True)
    joblib.dump(bundle, MODEL_PATH)
    print(f"Saved {MODEL_PATH} (trained through {bundle['trained_through']})")


if __name__ == "__main__":
    main()