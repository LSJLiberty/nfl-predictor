import os

import joblib
from sklearn.metrics import accuracy_score, log_loss

from src.data import load_games, split_completed
from src.features import FEATURES, build_features, current_team_form
from src.model import make_model

MODEL_PATH = "models/latest.joblib"


def backtest(table):
    """Re-run the week 4 experiment: train on 2015-2022, test on 2023-2025."""
    train = table[table["season"] <= 2022]
    test = table[table["season"].between(2023, 2025)]

    model = make_model().fit(train[FEATURES], train["home_win"])
    probs = model.predict_proba(test[FEATURES])[:, 1]
    preds = (probs > 0.5).astype(int)

    print(f"Backtest on {len(test)} games from 2023-2025")
    print(f"  home-pick baseline: {test['home_win'].mean():.3f}")
    print(f"  accuracy:           {accuracy_score(test['home_win'], preds):.3f}")
    print(f"  log loss:           {log_loss(test['home_win'], probs):.4f}")


def main():
    games = load_games()
    played, upcoming = split_completed(games)
    print(f"{len(played)} games played, {len(upcoming)} still to play")

    table, ratings = build_features(played)
    print(f"{len(table)} games usable for training")

    backtest(table)

    # The features are chosen and tested, so refit on every completed game.
    model = make_model().fit(table[FEATURES], table["home_win"])

    bundle = {
        "model": model,
        "features": FEATURES,
        "ratings": ratings,
        "team_form": current_team_form(played),
        "trained_through": str(played["gameday"].max().date()),
        "n_games": len(table),
        # NEW in week 6: the schedule of games still to be played, saved inside the
        # bundle so the API can answer "what's coming up?" without re-downloading data.
        "upcoming": upcoming[
            ["gameday", "home_team", "away_team", "home_rest", "away_rest"]
        ].reset_index(drop=True),
    }
    
    os.makedirs("models", exist_ok=True)
    joblib.dump(bundle, MODEL_PATH)
    print(f"Saved {MODEL_PATH} (trained through {bundle['trained_through']})")


if __name__ == "__main__":
    main()