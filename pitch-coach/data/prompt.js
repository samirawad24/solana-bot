/* Shared prompt builder. Works in the browser (window.FEX_PROMPT) and in Node
 * (require). The Netlify function and the direct-key browser path both use it,
 * so the deployed app and the fallback behave identically.
 */
(function (root, factory) {
  var SCRIPT = (typeof module !== "undefined" && module.exports)
    ? require("./script.js")
    : (root && root.FEX_SCRIPT);
  var api = factory(SCRIPT);
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.FEX_PROMPT = api;
})(typeof window !== "undefined" ? window : null, function (SCRIPT) {
  "use strict";

  function scriptReference() {
    return SCRIPT.sections.map(function (s, i) {
      return (i + 1) + ". " + s.title + " — " + s.purpose + "\n" +
        s.script.replace(/\n+/g, " ").trim();
    }).join("\n\n");
  }

  function difficultyNote(d) {
    if (d === "easy") return "EASY: You are warm, trusting, and fairly agreeable. Raise at most one mild concern, and let the agent move you forward without much resistance.";
    if (d === "hard") return "HARD: You are busy and skeptical. Guard your personal information, push back, and raise several real objections (price, 'need to think', talk to spouse, 'just mail it'). Only warm up if the agent genuinely earns it.";
    return "MEDIUM: You are a realistic prospect — interested but cautious. Raise one or two natural objections and some hesitation. Soften when the agent handles you well.";
  }

  function personaBlock() {
    return "Stay in a single consistent persona for the whole call. Invent and keep these details fixed once you decide them: your first name, an age between 58 and 75, a date of birth, a beneficiary (e.g. a son or daughter by name), that you live on a fixed income, and one or two minor health conditions (e.g. high blood pressure on medication). Answer the agent's medical and personal questions using these details. Speak the way a real person does on the phone — short sentences, no stage directions, no asterisks.";
  }

  function turnSystem(p) {
    var sec = p.sectionId ? findSec(p.sectionId) : null;
    var focus = sec
      ? "You are practicing ONE part of the call with the agent: the \"" + sec.title + "\" stage. Purpose of this stage: " + sec.purpose + " Stay around this part of the conversation."
      : "This is a full practice call from the greeting all the way to the close. Move through the stages naturally as the agent leads.";
    return (
      "You are roleplaying as a PROSPECT on a final-expense life-insurance phone call. The agent (named " + (p.agentName || "the agent") + ") is practicing their pitch and YOU are the potential customer who submitted an online request for funeral/final-expense information.\n\n" +
      "RULES:\n" +
      "- Always stay fully in character as the prospect. Never coach, never break character, never say you are an AI, never quote the script.\n" +
      "- Reply with ONLY your spoken words, 1–3 sentences, like a real phone call.\n" +
      "- React truthfully to what the agent just said. If they explain something well, acknowledge it; if they're vague or pushy, react like a real person would.\n" +
      "- Raise objections naturally when it fits (cost, 'I need to think about it', 'let me ask my spouse', 'just mail me the info', 'I already have insurance'). Don't dump them all at once.\n" +
      "- Don't be impossible: if the agent handles you well, let the call progress toward the next stage.\n\n" +
      focus + "\n\n" + personaBlock() + "\n\n" + difficultyNote(p.difficulty) + "\n\n" +
      "For reference, the agent is working from this script (do not read it aloud, just respond realistically to it):\n\n" +
      scriptReference()
    );
  }

  function startInstruction(p) {
    var sec = p.sectionId ? findSec(p.sectionId) : null;
    if (!sec) return "[Your phone rings from an unknown number. Answer briefly and naturally, like 'Hello?', then let the agent lead.]";
    if (sec.id === "opening") return "[Your phone rings. Answer briefly, like 'Hello?', then let the agent begin their opening.]";
    return "[Jump to the \"" + sec.title + "\" stage of the call. Give one short, natural prospect line that hands the turn to the agent so they can practice this part.]";
  }

  function turnMessages(p) {
    var hist = p.history || [];
    if (p.start || hist.length === 0) return [{ role: "user", content: startInstruction(p) }];
    var msgs = [];
    if (hist[0].role === "prospect") msgs.push({ role: "user", content: "[The call is connected.]" });
    hist.forEach(function (m) { msgs.push({ role: m.role === "agent" ? "user" : "assistant", content: m.content }); });
    if (msgs[msgs.length - 1].role !== "user") msgs.push({ role: "user", content: "[Continue.]" });
    return msgs;
  }

  function scoreSystem(p) {
    var sec = p.sectionId ? findSec(p.sectionId) : null;
    var rubricText = SCRIPT.rubric.map(function (r) { return "- " + r.label + " (weight " + r.weight + ")"; }).join("\n");
    var scope = sec
      ? "This was a focused drill on ONE stage: \"" + sec.title + "\" (" + sec.purpose + "). Return 3–5 categories specific to THIS stage, each with a 'max' so the maxes sum to 100. Judge how well the agent executed this part."
      : "This was a full practice call. Use these nine categories with these weights as the 'max' for each (they sum to 100):\n" + rubricText;
    return (
      "You are an expert final-expense (FEX) sales trainer grading a rep's practice call. You grade ONLY the agent's lines (the user turns), not the prospect's.\n\n" +
      "Grade against this script:\n\n" + scriptReference() + "\n\n" +
      "SCORING:\n" + scope + "\n\n" +
      "'overall' is 0–100 (the sum of the category scores). Be fair but honest — reward correct structure, the right key lines, smooth objection handling, compliance (giving credentials, never misrepresenting the product), and a confident, warm tone. Deduct for skipped steps, weak objection handling, or pushy/robotic delivery.\n" +
      "Give 2–4 specific 'strengths' and 2–4 specific 'improvements', each referencing what the agent actually said. 'drill' is one concrete next practice suggestion. Keep every string short and plain-spoken."
    );
  }

  function scoreSchema() {
    return {
      type: "json_schema",
      schema: {
        type: "object",
        properties: {
          overall: { type: "number" },
          categories: {
            type: "array",
            items: {
              type: "object",
              properties: { label: { type: "string" }, score: { type: "integer" }, max: { type: "integer" } },
              required: ["label", "score", "max"],
              additionalProperties: false,
            },
          },
          strengths: { type: "array", items: { type: "string" } },
          improvements: { type: "array", items: { type: "string" } },
          drill: { type: "string" },
        },
        required: ["overall", "categories", "strengths", "improvements", "drill"],
        additionalProperties: false,
      },
    };
  }

  function transcript(p) {
    return (p.history || []).map(function (m) { return (m.role === "agent" ? "AGENT" : "PROSPECT") + ": " + m.content; }).join("\n");
  }
  function findSec(id) { return SCRIPT.sections.find(function (s) { return s.id === id; }); }

  return {
    build: function (p) {
      if (p.type === "score") {
        return {
          system: scoreSystem(p),
          messages: [{ role: "user", content: "Here is the practice call transcript. Grade the agent.\n\n" + transcript(p) }],
          output_config: { format: scoreSchema() },
        };
      }
      return { system: turnSystem(p), messages: turnMessages(p) };
    },
    parse: function (p, text) {
      if (p.type === "score") {
        var obj = JSON.parse(text);
        obj.categories = (obj.categories || []).map(function (c) { return { label: c.label, score: c.score, max: c.max }; });
        return obj;
      }
      return { reply: (text || "").trim() };
    },
  };
});
