// api.js
//
// Every conversation with the FastAPI server lives in this one file. The rest of
// the app just calls these functions and never has to know about URLs or HTTP.

// Where the server lives. During development it runs on port 8000.
// `import.meta.env` holds settings that Vite reads from the environment; if you
// ever set VITE_API_URL (for example, when you deploy the API somewhere), it
// overrides the default after the `??`.
// `.replace(/\/+$/, "")` removes any slash(es) at the very end, so both
// "https://example.com" and "https://example.com/" work.
const API_URL = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");

// A shared helper that sends a GET request and returns the JSON reply.
// `async` means this function does slow work (a network request) and returns a
// "promise" -- a placeholder for a result that arrives later. Inside an async
// function, `await` pauses until that result is ready.
async function request(path) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`);
  } catch {
    // fetch() only throws when it can't reach the server at all: the server is
    // off, the address is wrong, or the browser blocked the request (CORS).
    throw new Error("Can't reach the prediction server. Is it running on port 8000?");
  }

  // `response.ok` is true for status codes 200-299. For 400, 404, 422 and so on,
  // our API replies with JSON like {"detail": "Unknown team: ZZZ"}.
  if (!response.ok) {
    // If the error body isn't valid JSON, .catch() gives us an empty object instead.
    const body = await response.json().catch(() => ({}));
    throw new Error(
      typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`
    );
  }

  return response.json(); // turn the JSON text into a JavaScript object
}

// One small function per endpoint. `export` makes each one importable elsewhere.
export const getHealth = () => request("/");
export const getTeams = () => request("/teams");
export const getUpcoming = (n = 16) => request(`/upcoming?n=${n}`);
export const getScorecard = () => request("/scorecard");

// encodeURIComponent makes a value safe to put inside a URL (spaces, symbols, etc.).
export const getPrediction = (home, away) =>
  request(
    `/predict?home_team=${encodeURIComponent(home)}&away_team=${encodeURIComponent(away)}`
  );