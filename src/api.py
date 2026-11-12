# A small web server that lets other programs (like your React app) ask the model
# for predictions over HTTP.
#
# Start it from the project root with:
#     uvicorn src.api:app --reload

import os
from contextlib import asynccontextmanager  # helper used for the startup function below

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.predict import load_bundle, predict_matchup, predict_upcoming

# ---------------------------------------------------------------------------
# Startup: load the model once
# ---------------------------------------------------------------------------

# Loading the saved model from disk is slow compared to answering a request.
# So we load it ONE time when the server starts and keep it in this dictionary.
# Every request after that reuses it instead of reading the file again.
state = {}


@asynccontextmanager
async def lifespan(app):
    # Everything BEFORE the `yield` runs once, when the server starts up.
    state["bundle"] = load_bundle()
    yield  # <- the server runs and handles requests while paused here
    # Everything AFTER the `yield` runs once, when the server shuts down.
    state.clear()


# Create the app. `title` and `description` appear at the top of the automatic docs page.
app = FastAPI(
    title="NFL Game Predictor",
    description=(
        "Win probabilities for NFL games from a logistic regression model fed by Elo "
        "ratings and recent form. Statistical estimates for learning, not betting advice."
    ),
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS: permission for your React app to talk to this server
# ---------------------------------------------------------------------------

# Browsers block a web page from calling a server on a different "origin"
# (a different address or port) unless that server says it's allowed.
# Your React dev server runs on port 5173 (or 3000), and this API runs on
# port 8000, so they count as different origins. This tells the browser that
# requests from those React addresses are okay. (Python programs and tools like
# curl don't enforce this rule; it's a browser safety feature.)
#
# Once the site is online, its address (for example
# https://nfl-predictor-web.onrender.com) must be allowed too. We read extra
# addresses from an environment variable, so the code doesn't change between your
# laptop and the real server. Separate several addresses with commas.
LOCAL_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
# os.environ.get("NAME", "") reads a setting from the environment ("" if it isn't set).
extra_origins = [
    origin.strip().rstrip("/")  # tidy up spaces and a trailing slash
    for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()           # ignore empty pieces
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_ORIGINS + extra_origins,
    allow_methods=["GET"],   # this API only reads data, it never changes anything
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Response shapes
# ---------------------------------------------------------------------------

# Each class below describes the exact JSON an endpoint sends back. FastAPI uses
# them to (1) check that our code really returns these fields with these types,
# (2) drop any extra fields, and (3) write the docs page automatically.

class Health(BaseModel):
    status: str
    trained_through: str    # date of the last game the model has seen
    games_trained_on: int


class TeamInfo(BaseModel):
    team: str
    elo: float


class Prediction(BaseModel):
    home_team: str
    away_team: str
    home_win_prob: float    # a number between 0 and 1
    away_win_prob: float
    pick: str               # the team the model thinks is more likely to win


class Factor(BaseModel):
    name: str
    points: float           # percentage points; positive favors the home team
    detail: str             # one sentence with the numbers behind it


class PredictionDetail(Prediction):
    # "(Prediction)" means: everything a Prediction has, plus the field below.
    factors: list[Factor]   # why the model picked who it picked


class UpcomingGame(Prediction):
    gameday: str


# --- the accuracy report ("scorecard") ---

class Summary(BaseModel):
    games: int
    correct: int
    accuracy: float
    accuracy_low: float     # the 95% interval around the accuracy
    accuracy_high: float
    home_pick_baseline: float
    log_loss: float


class CalibrationBin(BaseModel):
    low: float
    high: float
    games: int
    avg_predicted: float | None = None   # None when a bucket has no games
    home_win_rate: float | None = None


class WeekRow(BaseModel):
    week: int
    games: int
    correct: int


class RecentGame(BaseModel):
    gameday: str
    away_team: str
    home_team: str
    away_score: int
    home_score: int
    home_win_prob: float
    pick: str
    correct: bool


class BacktestReport(BaseModel):
    seasons: str
    summary: Summary
    calibration: list[CalibrationBin]


class LiveReport(BaseModel):
    season: int
    summary: Summary
    by_week: list[WeekRow]
    recent: list[RecentGame]


class Scorecard(BaseModel):
    through: str
    backtest: BacktestReport
    live: LiveReport | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

# `@app.get("/path")` is a "decorator". It tells FastAPI: "when someone sends a
# GET request to this path, run the function underneath and send back whatever
# it returns, converted to JSON."

@app.get("/", response_model=Health)
def health():
    """Quick check that the server is running and how fresh the model is."""
    bundle = state["bundle"]
    return {
        "status": "ok",
        "trained_through": bundle["trained_through"],
        "games_trained_on": bundle["n_games"],
    }


@app.get("/teams", response_model=list[TeamInfo])
def teams():
    """All 32 teams with their current Elo rating, strongest first.
    The React app uses this for its dropdowns and the power rankings."""
    ratings = state["bundle"]["ratings"]
    # sorted() with key=... sorts the (team, rating) pairs by the rating.
    # item[1] is the rating; reverse=True puts the highest first.
    ordered = sorted(ratings.items(), key=lambda item: item[1], reverse=True)
    return [{"team": name, "elo": round(float(elo), 1)} for name, elo in ordered]


@app.get("/predict", response_model=PredictionDetail)
def predict(
    # These function parameters become "query parameters" in the URL, like:
    #   /predict?home_team=KC&away_team=BUF&rest_diff=0
    # Query(...) lets us add rules. FastAPI checks them BEFORE our code runs and
    # automatically replies with a 422 error if a rule is broken.
    # The `...` means "required"; a normal value like 0 means "optional, default 0".
    home_team: str = Query(..., min_length=2, max_length=3,
                           description="Home team abbreviation, e.g. KC"),
    away_team: str = Query(..., min_length=2, max_length=3,
                           description="Away team abbreviation, e.g. BUF"),
    rest_diff: int = Query(0, ge=-14, le=14,
                           description="Home rest days minus away rest days"),
):
    """Win probability for one matchup, plus the reasons behind it."""
    # Let people type "kc" or "KC": team names in our data are uppercase.
    home = home_team.upper()
    away = away_team.upper()

    # A team can't play itself. 400 means "the request you sent doesn't make sense".
    if home == away:
        raise HTTPException(status_code=400, detail="Home and away teams must differ.")

    try:
        # The real work happens in the function you wrote in week 5.
        return predict_matchup(state["bundle"], home, away, rest_diff, with_factors=True)
    except ValueError as error:
        # predict_matchup raises ValueError for a team name it doesn't know.
        # We translate that into HTTP's "404 Not Found" and pass along its message.
        raise HTTPException(status_code=404, detail=str(error))


@app.get("/upcoming", response_model=list[UpcomingGame])
def upcoming(
    n: int = Query(16, ge=1, le=50, description="How many upcoming games to return"),
):
    """Predictions for the next n unplayed games on the schedule."""
    bundle = state["bundle"]
    schedule = bundle.get("upcoming")  # .get() returns None if the key is missing

    # Protects against an older saved model that doesn't contain a schedule.
    # 503 means "the server can't do this right now".
    if schedule is None:
        raise HTTPException(
            status_code=503,
            detail="The saved model has no schedule. Run: python -m src.train",
        )

    # predict_upcoming gives a table; .to_dict("records") turns each row into a
    # dictionary, which FastAPI then sends back as a JSON list.
    return predict_upcoming(bundle, schedule, n=n).to_dict(orient="records")


@app.get("/scorecard", response_model=Scorecard)
def scorecard():
    """How accurate the model has been: a backtest on past seasons, plus this
    season's finished games predicted by a model that never saw them."""
    report = state["bundle"].get("scorecard")
    if report is None:
        raise HTTPException(
            status_code=503,
            detail="The saved model has no scorecard. Run: python -m src.train",
        )
    return report