# FEX Pitch Coach 🎙️

A mobile-first web app that helps reps **learn and master the Final Expense (FEX) sales pitch by talking to an AI prospect**. Pick any stage of the call, practice it out loud, get objections thrown at you, and receive a **0–100% score** with a breakdown at the end.

Built from the FEX Agent Training Manual script.

---

## What it does

- **Practice by section** — every stage of the script (Opening → Find Why → Credibility → Needs Analysis → Final Expenses → Product → Close → Post Close, 16 in all) is a live, spoken drill with an AI prospect.
- **Full Call** — run the whole call from "hello" to the close. The AI plays a realistic prospect who answers questions, hesitates, and raises real objections (price, "I need to think about it," "let me ask my spouse," "just mail it," etc.).
- **Talk, don't type** — the prospect speaks out loud and you reply with your voice (your phone's mic). It feels like a real phone call. Typing also works.
- **Score 0–100%** — end any practice and get an honest score, a per-category breakdown, what you did well, what to fix, and a suggested next drill.
- **Study tools** — flashcards (fill-in-the-blank on the key lines) and a clean read-through of the script with the "why" behind each step.
- **Shareable** — once deployed, send the link to anyone on your team. No setup on their end.

---

## How the AI works

The app calls Claude (`claude-opus-4-8`) to play the prospect and to grade the call. There are two ways to provide the API key:

1. **Deployed (recommended for sharing):** the key lives on the server (a Netlify Function). Anyone with the URL just uses the app — they never see or need a key.
2. **Quick test (bring your own key):** open Settings → Advanced and paste your own Anthropic API key. It's stored only in your browser and the app calls Claude directly. Good for trying it before deploying. **Don't share a link expecting others to have a key — use option 1 for that.**

---

## Deploy it (so you can send the link to people)

You'll need a free [Netlify](https://www.netlify.com) account and an [Anthropic API key](https://console.anthropic.com).

**Option A — from the Netlify dashboard**
1. Push this repo to GitHub (it already is, if you're reading this there).
2. In Netlify: **Add new site → Import from Git →** pick this repo.
3. Netlify reads `netlify.toml` automatically (base directory `pitch-coach`, functions included). Just click **Deploy**.
4. In **Site settings → Environment variables**, add:
   - `ANTHROPIC_API_KEY` = your Anthropic key (the AI prospect + scoring)
   - `OPENAI_API_KEY` = your OpenAI key (hands-free speech-to-text on iPhone) — only needed if you want hands-free voice on iPhone
5. Trigger a redeploy. Open the site URL on your phone and start training. Share that URL with your team.

**Option B — from the command line**
```bash
npm install -g netlify-cli
cd pitch-coach
netlify init           # link or create a site
netlify env:set ANTHROPIC_API_KEY sk-ant-...your-key...
netlify env:set OPENAI_API_KEY sk-...your-openai-key...   # for iPhone hands-free voice
netlify deploy --prod
```

---

## Run it locally

```bash
cd pitch-coach
npm install
ANTHROPIC_API_KEY=sk-ant-... npx netlify dev
```
Then open the local URL it prints (the `/api/coach` function runs locally too).

**No backend at all?** Serve the folder with any static server (`npx serve pitch-coach`) and use the **bring-your-own-key** option in Settings.

---

## Voice — fully hands-free, identical on every device

Hands-free uses the **same engine everywhere** (iPhone, Android, desktop) so the experience is consistent: after the prospect speaks, the mic opens automatically, listens until you stop talking, transcribes what you said, and continues the call — no tapping between turns.

- It records a short clip each turn and sends it to a transcription service (OpenAI Whisper) via the `/api/transcribe` function, then continues. **This requires an `OPENAI_API_KEY` on the deployed site** (see below) — on iPhone *and* Android.
- The big 🎙 button shows it's listening. Tap it to send immediately ("I'm done"), or to start listening again if it timed out.
- Works in any browser that allows microphone access (Safari and Chrome on iPhone, Chrome on Android, Chrome/Edge on desktop).
- **Turn hands-free off in Settings** to fall back to the free, no-key options: the browser's built-in speech recognition on Android/desktop Chrome, or iPhone keyboard dictation. (Those differ by device — hands-free is the mode that's identical everywhere.)

> Why unified: on iPhone, Apple forces every browser (including Chrome) to use Safari's engine, which has no in-browser speech recognition. Routing all devices through the same transcription service is what makes the hands-free call behave the same on iPhone and Android.

> First tap: browsers only let the prospect's voice and the mic start after a tap, so the call begins the moment you tap into a section or the Full Call. The first time, the browser asks for microphone permission — tap Allow.

---

## Customizing the script

Everything about the pitch lives in **`data/script.js`** — sections, the "why," key lines, flashcard blanks, the objection list, and the scoring rubric. Edit that one file and both the app and the AI grader update automatically. The prompt logic that turns the script into AI instructions is in **`data/prompt.js`** (shared by the browser and the server function).

---

## Files

```
pitch-coach/
├── index.html                  # app shell
├── styles.css                  # mobile-first UI
├── app.js                      # screens, voice (mic + speech), call flow, scoring UI
├── data/
│   ├── script.js               # THE FEX SCRIPT — sections, key lines, objections, rubric
│   └── prompt.js               # builds the Claude prompts (browser + server share this)
├── netlify/functions/
│   └── coach.js                # serverless proxy to Claude (keeps the API key server-side)
├── manifest.webmanifest        # installable on a phone home screen
├── assets/icon.svg
└── package.json
```

> Compliance note: this is a training tool. Keep your pitch and any claims in `data/script.js` accurate and compliant with your state's insurance regulations and your carrier's guidelines.
