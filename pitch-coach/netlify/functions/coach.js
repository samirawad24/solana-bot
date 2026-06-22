/* Netlify Function: /api/coach
 * Proxies the browser to the Claude API so the Anthropic key stays server-side.
 * Uses the runtime's native fetch (Node 18+) — no npm dependencies, so the
 * deploy can't fail on an install step.
 *
 * Once deployed with ANTHROPIC_API_KEY set, anyone with the app URL can train
 * with no key on their device. Without that env var, the app still works via
 * the "bring your own key" option in Settings (which calls Claude directly).
 */
const PROMPT = require("../../data/prompt.js");

const MODEL = "claude-opus-4-8";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "content-type",
  "content-type": "application/json",
};

exports.handler = async function (event) {
  if (event.httpMethod === "OPTIONS") return { statusCode: 204, headers: CORS, body: "" };
  if (event.httpMethod !== "POST") return { statusCode: 405, headers: CORS, body: '{"error":"Use POST"}' };

  if (!process.env.ANTHROPIC_API_KEY) {
    return {
      statusCode: 500,
      headers: CORS,
      body: JSON.stringify({ error: "No server API key set. Add ANTHROPIC_API_KEY in Netlify env vars, or paste your own key in Settings → Advanced." }),
    };
  }

  let payload;
  try { payload = JSON.parse(event.body || "{}"); }
  catch (e) { return { statusCode: 400, headers: CORS, body: '{"error":"Invalid JSON"}' }; }

  try {
    const built = PROMPT.build(payload);
    const reqBody = {
      model: MODEL,
      max_tokens: payload.type === "score" ? 1500 : 400,
      system: built.system,
      messages: built.messages,
    };
    if (built.output_config) reqBody.output_config = built.output_config;

    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": process.env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify(reqBody),
    });

    const data = await r.json();
    if (!r.ok) {
      const msg = (data && data.error && data.error.message) ? data.error.message : "Claude API error";
      return { statusCode: r.status, headers: CORS, body: JSON.stringify({ error: msg }) };
    }

    const text = (data.content || [])
      .filter((b) => b.type === "text")
      .map((b) => b.text)
      .join("");

    const result = PROMPT.parse(payload, text);
    return { statusCode: 200, headers: CORS, body: JSON.stringify(result) };
  } catch (err) {
    const msg = (err && err.message) ? err.message : "Unknown error";
    return { statusCode: 500, headers: CORS, body: JSON.stringify({ error: msg }) };
  }
};
