import joblib
import pandas as pd

from src.data import load_games, split_completed

MODEL_PATH = "models/latest.joblib"


def load_bundle(path=MODEL_PATH):
    """Load the saved model plus the team ratings and recent form."""
    return joblib.load(path)


def predict_matchup(bundle, home_team, away_team, rest_diff=0):
    """Probability that home_team beats away_team, using the current ratings."""
    ratings = bundle["ratings"]
    form = bundle["team_form"]

    for team in (home_team, away_team):
        if team not in ratings or team not in form.index:
            raise ValueError(f"Unknown team: {team}")

    h = form.loc[home_team]
    a = form.loc[away_team]
    row = {
        "win_pct_diff": h["win_pct_last5"] - a["win_pct_last5"],
        "margin_diff": h["margin_last5"] - a["margin_last5"],
        "rest_diff": rest_diff,
        "pts_for_diff": h["pts_for_last5"] - a["pts_for_last5"],
        "pts_against_diff": h["pts_against_last5"] - a["pts_against_last5"],
        "elo_diff": ratings[home_team] - ratings[away_team],
    }
    X = pd.DataFrame([row])[bundle["features"]]
    home_prob = float(bundle["model"].predict_proba(X)[0, 1])

    return {
        "home_team": home_team,
        "away_team": away_team,
        "home_win_prob": round(home_prob, 3),
        "away_win_prob": round(1 - home_prob, 3),
        "pick": home_team if home_prob > 0.5 else away_team,
    }


def predict_upcoming(bundle, upcoming, n=16):
    """Predictions for the next n unplayed games on the schedule."""
    results = []
    for row in upcoming.head(n).itertuples():
        rest_diff = row.home_rest - row.away_rest
        result = predict_matchup(bundle, row.home_team, row.away_team, rest_diff)
        result["gameday"] = str(row.gameday.date())
        results.append(result)
    return pd.DataFrame(results)


if __name__ == "__main__":
    bundle = load_bundle()
    print(f"Model trained through {bundle['trained_through']}\n")

    games = load_games()
    _, upcoming = split_completed(games)
    print(predict_upcoming(bundle, upcoming).to_string(index=False))