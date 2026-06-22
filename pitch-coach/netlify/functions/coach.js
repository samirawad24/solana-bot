/* Netlify Function: /api/coach
 * Proxies the browser to the Claude API so the Anthropic key stays server-side.
 * Once deployed with ANTHROPIC_API_KEY set, anyone with the app URL can train —
 * no key needed on their device.
 */
const Anthropic = require("@anthropic-ai/sdk");
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
    return { statusCode: 500, headers: CORS, body: JSON.stringify({ error: "ANTHROPIC_API_KEY is not set on the server. Add it in Netlify → Site settings → Environment variables." }) };
  }

  let payload;
  try { payload = JSON.parse(event.body || "{}"); }
  catch (e) { return { statusCode: 400, headers: CORS, body: '{"error":"Invalid JSON"}' }; }

  try {
    const client = new Anthropic(); // reads ANTHROPIC_API_KEY from env
    const built = PROMPT.build(payload);

    const req = {
      model: MODEL,
      max_tokens: payload.type === "score" ? 1500 : 400,
      system: built.system,
      messages: built.messages,
    };
    if (built.output_config) req.output_config = built.output_config;

    const resp = await client.messages.create(req);
    const text = (resp.content || [])
      .filter((b) => b.type === "text")
      .map((b) => b.text)
      .join("");

    const result = PROMPT.parse(payload, text);
    return { statusCode: 200, headers: CORS, body: JSON.stringify(result) };
  } catch (err) {
    const msg = (err && err.message) ? err.message : "Unknown error";
    const status = (err && err.status) || 500;
    return { statusCode: status, headers: CORS, body: JSON.stringify({ error: msg }) };
  }
};
