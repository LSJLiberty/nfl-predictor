# NFL Game Predictor

A machine learning project that predicts the winner of NFL games using historical results. The goal is a full pipeline: raw game data becomes features, features train a model, and the model is served through an API to a web interface.

> **Status: in progress.** Data exploration and feature engineering are underway. Model training, the API, and the web interface are still to come.

## Tech Stack

- **Python** for data work and modeling
- **pandas** for data wrangling
- **nflreadpy** for downloading NFL schedule and results data
- **scikit-learn** for model training (planned)
- **FastAPI** for the prediction API (planned)
- **React** for the web interface (planned)
- **Jupyter notebooks** for exploration and feature engineering

## How It Works

1. **Load data.** Every NFL game from the 2015-2025 seasons (3,028 games) is downloaded with `nflreadpy`.
2. **Create the target.** `home_win` is `1` if the home team scored more than the away team, otherwise `0`.
3. **Reshape.** The data is converted from one row per game to one row per team per game, so each team's history can be followed in date order.
4. **Engineer features.** For each team in each game, two rolling features are computed from its previous five games:
   - `win_pct_last5`: recent win rate
   - `margin_last5`: recent average scoring margin
5. **Prevent data leakage.** Rolling values are shifted by one game (`.shift(1)`), so a game's own result is never used to predict itself.
6. **Build difference features.** Home minus away for each feature (`win_pct_diff`, `margin_diff`, `rest_diff`), so the model sees how the two teams compare.
7. **Split by time.** Training data is the 2015-2022 seasons and test data is 2023-2025. A time-based split is used instead of a random one so the model is never trained on games that happen after the ones it is tested on.

## Baseline

Always picking the home team wins about **54.8%** of games in the 2015-2025 data. A model is only useful if it beats this on the test seasons.

## Project Structure

```
nfl-predictor/
├── data/                  # local data files (if saved)
├── notebooks/
│   ├── 01_explore.ipynb   # load and explore the schedule data
│   └── 02_features.ipynb  # feature engineering and train/test split
├── requirements.txt
└── README.md
```

## Setup (Windows / PowerShell)

```powershell
git clone <your-repo-url>
cd nfl-predictor
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks the activation script, allow local scripts for your user and try again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then open the notebooks in VS Code and select the `.venv` kernel. Run the cells in each notebook from top to bottom.

## Roadmap

- [x] Week 1: Load and explore the data
- [x] Week 2: Feature engineering and train/test split
- [x] Week 3: Train a baseline model (logistic regression) and compare it to the home-win baseline
- [ ] Improve features and try other models
- [ ] Save the trained model
- [ ] Build the FastAPI prediction endpoint
- [ ] Build the React front end

## Data

Game data comes from [nflverse](https://github.com/nflverse) through the `nflreadpy` package.
