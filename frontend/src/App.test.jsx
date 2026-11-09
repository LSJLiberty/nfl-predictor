// App.test.jsx
//
// Automated tests for the page. They run in a pretend browser (jsdom) and NEVER talk
// to the real API: we replace the functions in api.js with fakes that return
// made-up data. That makes the tests fast and repeatable, and they work even when
// your server is off.

import { render, screen } from "@testing-library/react";
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
};

describe("App", () => {
  // Before EACH test, reset the fakes so one test can't affect another.
  beforeEach(() => {
    vi.resetAllMocks();
    api.getHealth.mockResolvedValue(HEALTH);
    api.getTeams.mockResolvedValue(TEAMS);
    api.getUpcoming.mockResolvedValue(UPCOMING);
    api.getPrediction.mockResolvedValue(PREDICTION);
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

  it("asks the API and shows the result when Predict is clicked", async () => {
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
});