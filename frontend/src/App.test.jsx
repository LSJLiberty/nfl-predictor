// App.test.jsx
//
// Automated tests for the page. They run in a pretend browser (jsdom) and NEVER talk
// to the real API: we replace the functions in api.js with fakes that return
// made-up data. That makes the tests fast and repeatable, and they work even when
// your server is off.

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import * as api from "./api";

// Swap every function exported by api.js for a fake we can control.
vi.mock("./api", () => ({
  getHealth: vi.fn(),
  getTeams: vi.fn(),
  getUpcoming: vi.fn(),
  getPrediction: vi.fn(),
  getScorecard: vi.fn(),
}));

// Fake data shaped exactly like the real API's replies.
const HEALTH = { status: "ok", trained_through: "2026-11-05", games_trained_on: 3134 };
const TEAMS = [
  { team: "BUF", elo: 1675.5 },
  { team: "KC", elo: 1580.2 },
];
const UPCOMING = [
  {
    home_team: "SEA",
    away_team: "ARI",
    home_win_prob: 0.775,
    away_win_prob: 0.225,
    pick: "SEA",
    gameday: "2026-11-08",
  },
];
const PREDICTION = {
  home_team: "KC",
  away_team: "BUF",
  home_win_prob: 0.391,
  away_win_prob: 0.609,
  pick: "BUF",
  factors: [
    { name: "Home-field advantage", points: 4.9, detail: "KC is playing at home." },
    { name: "Team strength (Elo)", points: -12.9, detail: "Elo rating: KC 1569 vs BUF 1704." },
    { name: "Recent form", points: -4.2, detail: "Average margin over the last 5 games: KC +4.2 vs BUF +9.2." },
    { name: "Rest", points: 0, detail: "Both teams had the same rest." },
  ],
};
const SCORECARD = {
  through: "2026-11-09",
  backtest: {
    seasons: "2023-2025",
    summary: {
      games: 855, correct: 558, accuracy: 0.6526, accuracy_low: 0.6198, accuracy_high: 0.6838,
      home_pick_baseline: 0.549, log_loss: 0.6291,
    },
    calibration: [
      { low: 0, high: 0.3, games: 10, avg_predicted: 0.25, home_win_rate: 0.2 },
      { low: 0.3, high: 0.4, games: 0, avg_predicted: null, home_win_rate: null },
    ],
  },
  live: {
    season: 2026,
    summary: {
      games: 136, correct: 87, accuracy: 0.6397, accuracy_low: 0.56, accuracy_high: 0.71,
      home_pick_baseline: 0.493, log_loss: 0.64,
    },
    by_week: [{ week: 1, games: 14, correct: 9 }],
    recent: [
      {
        gameday: "2026-11-09", away_team: "DAL", home_team: "PHI", away_score: 17, home_score: 24,
        home_win_prob: 0.62, pick: "PHI", correct: true,
      },
    ],
  },
};

describe("App", () => {
  // Before EACH test, reset the fakes so one test can't affect another.
  beforeEach(() => {
    vi.resetAllMocks();
    api.getHealth.mockResolvedValue(HEALTH);
    api.getTeams.mockResolvedValue(TEAMS);
    api.getUpcoming.mockResolvedValue(UPCOMING);
    api.getPrediction.mockResolvedValue(PREDICTION);
    api.getScorecard.mockResolvedValue(SCORECARD);
  });

  it("loads the model info, the teams, and the upcoming games", async () => {
    render(<App />);
    // findBy... waits for something to appear (the page loads data asynchronously).
    expect(await screen.findByText("Pick a matchup")).toBeInTheDocument();
    expect(screen.getByText(/3,134 games through 2026-11-05/)).toBeInTheDocument();
    expect(screen.getByText("ARI at SEA")).toBeInTheDocument();
  });

  it("keeps Predict disabled until two different teams are chosen", async () => {
    const user = userEvent.setup(); // a fake user who can click and choose
    render(<App />);
    const button = await screen.findByRole("button", { name: "Predict" });
    expect(button).toBeDisabled();

    await user.selectOptions(screen.getByLabelText(/away team/i), "BUF");
    expect(button).toBeDisabled(); // still needs a home team

    await user.selectOptions(screen.getByLabelText(/home team/i), "BUF");
    expect(button).toBeDisabled(); // same team on both sides
    expect(screen.getByText("Pick two different teams.")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/home team/i), "KC");
    expect(button).toBeEnabled();
  });

  it("asks the API and shows the result and its reasons when Predict is clicked", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Pick a matchup");

    await user.selectOptions(screen.getByLabelText(/away team/i), "BUF");
    await user.selectOptions(screen.getByLabelText(/home team/i), "KC");
    await user.click(screen.getByRole("button", { name: "Predict" }));

    // The page should have called the API with (home, away)...
    expect(api.getPrediction).toHaveBeenCalledWith("KC", "BUF");
    // ...and shown the model's pick and the probabilities.
    expect(await screen.findByText(/Model pick:/)).toHaveTextContent("Buffalo Bills");
    expect(screen.getByText("60.9%")).toBeInTheDocument();
    expect(screen.getByText("39.1%")).toBeInTheDocument();
    // ...and the reasons behind the pick.
    expect(screen.getByText("What drove this pick")).toBeInTheDocument();
    expect(screen.getByText("-12.9 pts")).toBeInTheDocument();
    expect(screen.getByText("+4.9 pts")).toBeInTheDocument();
  });

  it("swaps the teams when the swap button is clicked", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Pick a matchup");

    await user.selectOptions(screen.getByLabelText(/away team/i), "BUF");
    await user.selectOptions(screen.getByLabelText(/home team/i), "KC");
    await user.click(screen.getByRole("button", { name: "Swap teams" }));

    expect(screen.getByLabelText(/away team/i)).toHaveValue("KC");
    expect(screen.getByLabelText(/home team/i)).toHaveValue("BUF");
  });

  it("shows a helpful error when the server can't be reached", async () => {
    api.getTeams.mockRejectedValue(new Error("Can't reach the prediction server."));
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Can't reach the prediction server.");
    expect(screen.getByText(/uvicorn src.api:app --reload/)).toBeInTheDocument();
  });

  it("shows the server's message when a prediction fails", async () => {
    api.getPrediction.mockRejectedValue(new Error("Unknown team: KC"));
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Pick a matchup");

    await user.selectOptions(screen.getByLabelText(/away team/i), "BUF");
    await user.selectOptions(screen.getByLabelText(/home team/i), "KC");
    await user.click(screen.getByRole("button", { name: "Predict" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Unknown team: KC");
  });

  it("shows the accuracy scorecard, including this season's results", async () => {
    render(<App />);
    expect(await screen.findByText("How accurate is the model?")).toBeInTheDocument();
    expect(screen.getByText("2026 season so far")).toBeInTheDocument();
    expect(screen.getByText(/87 of 136 correct/)).toBeInTheDocument();
    expect(screen.getByText(/65.3% accuracy on 855 games/)).toBeInTheDocument();
    // The most recent result, marked as a correct pick.
    expect(screen.getByText(/Dallas Cowboys 17, Philadelphia Eagles 24/)).toBeInTheDocument();
  });

  it("lists the power rankings strongest first", async () => {
    render(<App />);
    const heading = await screen.findByText("Power rankings");
    const section = heading.closest("section");
    const rows = within(section).getAllByRole("listitem");
    expect(rows[0]).toHaveTextContent("Buffalo Bills");
    expect(rows[0]).toHaveTextContent("1676");
    expect(rows[1]).toHaveTextContent("Kansas City Chiefs");
  });

  it("still works when the scorecard can't be loaded", async () => {
    api.getScorecard.mockRejectedValue(new Error("not available"));
    render(<App />);
    expect(await screen.findByText("Pick a matchup")).toBeInTheDocument();
    expect(screen.getByText(/accuracy report isn.t available/)).toBeInTheDocument();
  });
});