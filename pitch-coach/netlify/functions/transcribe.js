/* Netlify Function: /api/transcribe
 * Speech-to-text for the hands-free iPhone call. The browser records a short
 * audio clip and POSTs it here as base64; we forward it to OpenAI's transcription
 * endpoint and return the text. Keeps the OpenAI key server-side.
 *
 * Uses the runtime's native fetch / FormData / Blob (Node 18+) — no npm deps.
 * Set OPENAI_API_KEY in the site's environment variables (or let the browser
 * pass its own key for local testing).
 */
const MODEL = "whisper-1"; // widely available; accurate for short utterances

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "content-type",
  "content-type": "application/json",
};

function extFor(mime) {
  if (!mime) return "mp4";
  if (mime.indexOf("webm") >= 0) return "webm";
  if (mime.indexOf("ogg") >= 0) return "ogg";
  if (mime.indexOf("wav") >= 0) return "wav";
  if (mime.indexOf("mpeg") >= 0 || mime.indexOf("mp3") >= 0) return "mp3";
  return "mp4"; // iOS Safari default (audio/mp4)
}

exports.handler = async function (event) {
  if (event.httpMethod === "OPTIONS") return { statusCode: 204, headers: CORS, body: "" };
  if (event.httpMethod !== "POST") return { statusCode: 405, headers: CORS, body: '{"error":"Use POST"}' };

  let payload;
  try { payload = JSON.parse(event.body || "{}"); }
  catch (e) { return { statusCode: 400, headers: CORS, body: '{"error":"Invalid JSON"}' }; }

  const key = process.env.OPENAI_API_KEY || payload.openaiKey;
  if (!key) {
    return { statusCode: 500, headers: CORS, body: JSON.stringify({ error: "No transcription key. Add OPENAI_API_KEY in Netlify env vars, or paste an OpenAI key in Settings → Advanced." }) };
  }
  if (!payload.audio) return { statusCode: 400, headers: CORS, body: '{"error":"No audio"}' };

  try {
    const buf = Buffer.from(payload.audio, "base64");
    const mime = payload.mime || "audio/mp4";
    const form = new FormData();
    form.append("model", MODEL);
    form.append("language", "en");
    form.append("file", new Blob([buf], { type: mime }), "audio." + extFor(mime));

    const r = await fetch("https://api.openai.com/v1/audio/transcriptions", {
      method: "POST",
      headers: { Authorization: "Bearer " + key },
      body: form,
    });
    const data = await r.json();
    if (!r.ok) {
      const msg = (data && data.error && data.error.message) ? data.error.message : "Transcription error";
      return { statusCode: r.status, headers: CORS, body: JSON.stringify({ error: msg }) };
    }
    return { statusCode: 200, headers: CORS, body: JSON.stringify({ text: data.text || "" }) };
  } catch (err) {
    const msg = (err && err.message) ? err.message : "Unknown error";
    return { statusCode: 500, headers: CORS, body: JSON.stringify({ error: msg }) };
  }
};
