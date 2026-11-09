// App.jsx
//
// The main component. It owns the page's "state" (data that can change while the
// page is open) and decides what to show based on that state.
//
// The big idea in React: you don't edit the page directly. You change the state,
// and React automatically re-draws whatever depends on it.

import { useEffect, useState } from "react";
import { getHealth, getPrediction, getTeams, getUpcoming } from "./api";
import ProbabilityBar from "./components/ProbabilityBar";
import UpcomingGames from "./components/UpcomingGames";
import { teamName } from "./teamNames";
import "./App.css";

export default function App() {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  // useState(initialValue) returns a pair: the current value, and a function that
  // changes it. Calling the setter makes React re-run this component and redraw.

  const [teams, setTeams] = useState([]);          // list of teams for the dropdowns
  const [upcoming, setUpcoming] = useState([]);    // predictions for upcoming games
  const [health, setHealth] = useState(null);      // model info (trained-through date)
  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState("");  // problem loading the page's data

  const [away, setAway] = useState("");            // selected away team ("" = none yet)
  const [home, setHome] = useState("");            // selected home team
  const [prediction, setPrediction] = useState(null);
  const [predicting, setPredicting] = useState(false); // true while waiting on /predict
  const [predictError, setPredictError] = useState("");

  // ---------------------------------------------------------------------------
  // Load the page's data once, when the page first appears
  // ---------------------------------------------------------------------------
  // useEffect runs code AFTER the component is drawn. The empty list [] at the end
  // means "run this only once, not on every redraw".
  useEffect(() => {
    // Promise.all sends all three requests at the same time and waits for all of
    // them, which is faster than asking one after another.
    Promise.all([getHealth(), getTeams(), getUpcoming()])
      .then(([healthData, teamData, upcomingData]) => {
        setHealth(healthData);
        // The API sends teams strongest-first. For a dropdown, alphabetical is
        // friendlier. [...teamData] copies the list so we don't modify the original.
        setTeams(
          [...teamData].sort((a, b) => teamName(a.team).localeCompare(teamName(b.team)))
        );
        setUpcoming(upcomingData);
      })
      .catch((error) => setPageError(error.message))
      .finally(() => setPageLoading(false)); // runs whether it worked or failed
  }, []);

  // ---------------------------------------------------------------------------
  // Event handlers: what happens when the user does something
  // ---------------------------------------------------------------------------

  async function handlePredict() {
    setPredicting(true);
    setPredictError("");
    try {
      const result = await getPrediction(home, away);
      setPrediction(result);
    } catch (error) {
      // getPrediction throws an Error with a readable message (see api.js).
      setPrediction(null);
      setPredictError(error.message);
    } finally {
      setPredicting(false);
    }
  }

  // Changing a team makes the old result out of date, so we clear it.
  function handleAwayChange(event) {
    setAway(event.target.value); // event.target.value = what the user just chose
    setPrediction(null);
    setPredictError("");
  }

  function handleHomeChange(event) {
    setHome(event.target.value);
    setPrediction(null);
    setPredictError("");
  }

  function handleSwap() {
    setAway(home);
    setHome(away);
    setPrediction(null);
    setPredictError("");
  }

  // ---------------------------------------------------------------------------
  // Values calculated from the state
  // ---------------------------------------------------------------------------
  // These aren't stored in state because we can always work them out from it.
  const sameTeam = home !== "" && home === away;
  const canPredict = home !== "" && away !== "" && !sameTeam && !predicting;

  // ---------------------------------------------------------------------------
  // What to show
  // ---------------------------------------------------------------------------
  // The return value is "JSX": HTML-like code that lives inside JavaScript.
  // Anything in {curly braces} is a JavaScript expression.

  if (pageLoading) {
    return <main className="page"><p className="muted">Loading…</p></main>;
  }

  if (pageError) {
    return (
      <main className="page">
        <h1>NFL Game Predictor</h1>
        <p className="error" role="alert">{pageError}</p>
        <p className="muted">
          Start the API from the project folder with:{" "}
          <code>uvicorn src.api:app --reload</code>, then refresh this page.
        </p>
      </main>
    );
  }

  return (
    <main className="page">
      <header>
        <h1>NFL Game Predictor</h1>
        {/* Show how fresh the model is, using data from the "/" endpoint.
            toLocaleString() adds thousands separators: 3134 -> "3,134". */}
        {health && (
          <p className="muted">
            Model trained on {health.games_trained_on.toLocaleString()} games through{" "}
            {health.trained_through}
          </p>
        )}
      </header>

      <section className="card">
        <h2>Pick a matchup</h2>

        <div className="matchup">
          {/* A "controlled" input: its value always comes from state (value={away}),
              and onChange sends every change back into state. State is the single
              source of truth for what the dropdown shows. */}
          <label>
            Away team
            <select value={away} onChange={handleAwayChange}>
              <option value="">Choose a team…</option>
              {teams.map((t) => (
                <option key={t.team} value={t.team}>
                  {teamName(t.team)}
                </option>
              ))}
            </select>
          </label>

          <button type="button" className="swap" onClick={handleSwap} aria-label="Swap teams">
            ⇄
          </button>

          <label>
            Home team
            <select value={home} onChange={handleHomeChange}>
              <option value="">Choose a team…</option>
              {teams.map((t) => (
                <option key={t.team} value={t.team}>
                  {teamName(t.team)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {/* `condition && <thing>` shows <thing> only when the condition is true. */}
        {sameTeam && <p className="muted">Pick two different teams.</p>}

        {/* The button is disabled until two different teams are chosen. */}
        <button type="button" className="primary" onClick={handlePredict} disabled={!canPredict}>
          {predicting ? "Predicting…" : "Predict"}
        </button>

        {predictError && <p className="error" role="alert">{predictError}</p>}

        {prediction && (
          <div className="result">
            <p className="pick">
              Model pick: <strong>{teamName(prediction.pick)}</strong>
            </p>
            <ProbabilityBar
              awayLabel={teamName(prediction.away_team)}
              awayProb={prediction.away_win_prob}
              homeLabel={teamName(prediction.home_team)}
              homeProb={prediction.home_win_prob}
            />
            <p className="muted small">Assumes both teams had the same rest.</p>
          </div>
        )}
      </section>

      <section className="card">
        <h2>Upcoming games</h2>
        {/* We pass the list down to a child component as a "prop". */}
        <UpcomingGames games={upcoming} />
        <p className="muted small">
          These use each game&rsquo;s actual rest days from the schedule, so a number can
          differ slightly from the matchup tool above.
        </p>
      </section>

      <footer className="muted small">
        Predictions are statistical estimates from past game results only (no injuries,
        weather, or news). For learning and fun, not betting advice.
      </footer>
    </main>
  );
}