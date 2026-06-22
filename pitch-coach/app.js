/* FEX Pitch Coach — voice-first training app
 * Every section is a live, speak-to-the-AI drill. The AI plays the prospect;
 * you talk back with your phone's mic. There's also a Full Call mode and a
 * 0-100% score at the end of any practice.
 */
(function () {
  "use strict";

  var SCRIPT = window.FEX_SCRIPT;
  var view = document.getElementById("view");
  var titleEl = document.getElementById("title");
  var backBtn = document.getElementById("backBtn");
  var footerNote = document.getElementById("footerNote");

  // ---------- persistent settings ----------
  var S = Object.assign(
    { agentName: "", difficulty: "medium", voiceOut: true, handsFree: true, apiKey: "", openaiKey: "" },
    JSON.parse(localStorage.getItem("fexCoach") || "{}")
  );
  function saveSettings() { localStorage.setItem("fexCoach", JSON.stringify(S)); }

  // ---------- tiny helpers ----------
  function h(html) { var t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; }
  function esc(s) { return (s || "").replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function fill(text) {
    return (text || "")
      .replace(/\{agent\}/g, S.agentName || SCRIPT.agentNameDefault)
      .replace(/\{client\}/g, "[client]")
      .replace(/\{beneficiary\}/g, "[beneficiary]")
      .replace(/\{company\}/g, "[company]")
      .replace(/\{state\}/g, "[state]")
      .replace(/\{DOB\}/g, "[DOB]");
  }
  function setTitle(t, showBack) {
    titleEl.textContent = t;
    backBtn.hidden = !showBack;
  }

  // ---------- voice: speech synthesis (prospect talks) ----------
  var synth = window.speechSynthesis;
  var chosenVoice = null;
  function pickVoice() {
    if (!synth) return;
    var voices = synth.getVoices();
    if (!voices.length) return;
    // Prefer a natural English voice for the prospect.
    var prefs = ["Samantha", "Google US English", "Microsoft Aria", "Microsoft Zira", "Karen", "Moira"];
    for (var i = 0; i < prefs.length; i++) {
      var v = voices.find(function (x) { return x.name.indexOf(prefs[i]) >= 0; });
      if (v) { chosenVoice = v; return; }
    }
    chosenVoice = voices.find(function (x) { return /en[-_]/i.test(x.lang); }) || voices[0];
  }
  if (synth) { pickVoice(); synth.onvoiceschanged = pickVoice; }

  var onSpeakEnd = null;
  function speak(text, done) {
    onSpeakEnd = done || null;
    if (!synth || !S.voiceOut) { if (onSpeakEnd) { var f = onSpeakEnd; onSpeakEnd = null; f(); } return; }
    try { synth.cancel(); } catch (e) {}
    var u = new SpeechSynthesisUtterance(text);
    if (chosenVoice) u.voice = chosenVoice;
    u.rate = 0.98; u.pitch = 1.0;
    u.onend = function () { var f = onSpeakEnd; onSpeakEnd = null; if (f) f(); };
    u.onerror = function () { var f = onSpeakEnd; onSpeakEnd = null; if (f) f(); };
    try { synth.resume(); } catch (e) {} // iOS sometimes leaves synth paused
    synth.speak(u);
  }
  function stopSpeak() { try { if (synth) synth.cancel(); } catch (e) {} onSpeakEnd = null; }

  // iOS Safari blocks speech until the first utterance is fired inside a user
  // gesture. Prime it on the first tap so the prospect can actually talk.
  var audioUnlocked = false;
  function unlockAudio() {
    if (audioUnlocked || !synth) return;
    try { var u = new SpeechSynthesisUtterance(" "); u.volume = 0; synth.speak(u); audioUnlocked = true; } catch (e) {}
  }

  // ---------- voice: speech recognition (you talk) ----------
  // iPhone/iPad Safari does NOT support in-browser speech recognition, so on
  // iOS we fall back to Apple's built-in keyboard dictation (the 🎤 on the
  // keyboard) — on-device, free, and accurate.
  var IS_IOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  var recog = null, listening = false, recogTarget = null;
  if (SR) {
    recog = new SR();
    recog.lang = "en-US";
    recog.interimResults = true;
    recog.continuous = false;
    recog.onresult = function (e) {
      var txt = "";
      for (var i = e.resultIndex; i < e.results.length; i++) txt += e.results[i][0].transcript;
      if (recogTarget) recogTarget.onText(txt, e.results[e.results.length - 1].isFinal);
    };
    recog.onend = function () {
      listening = false;
      if (recogTarget) recogTarget.onEnd();
    };
    recog.onerror = function () { listening = false; if (recogTarget) recogTarget.onEnd(); };
  }
  function startListening(target) {
    if (!recog || listening) return;
    recogTarget = target; listening = true;
    try { recog.start(); } catch (e) { listening = false; }
  }
  function stopListening() { if (recog && listening) { try { recog.stop(); } catch (e) {} } }

  // ---------- hands-free voice (record + transcribe) ----------
  // Used where the browser has no speech recognition (iPhone/iPad). The mic
  // opens automatically after the prospect speaks, listens until you go quiet,
  // then sends the audio to /api/transcribe (OpenAI Whisper) and continues —
  // a true hands-free, agent-style call.
  var HF_SUPPORTED = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
  var hf = { stream: null, rec: null, ctx: null, raf: 0, active: false, chunks: [], btn: null };

  function hfEnabled() { return S.handsFree && HF_SUPPORTED; }

  function hfEnsureMic() {
    if (hf.stream) return Promise.resolve(true);
    return navigator.mediaDevices.getUserMedia({ audio: true })
      .then(function (s) { hf.stream = s; return true; })
      .catch(function () { return false; });
  }

  function hfPickMime() {
    var opts = ["audio/mp4", "audio/webm", "audio/ogg"];
    for (var i = 0; i < opts.length; i++) {
      try { if (window.MediaRecorder.isTypeSupported(opts[i])) return opts[i]; } catch (e) {}
    }
    return "";
  }

  // Listen for one utterance with simple silence detection; resolve a Blob.
  function hfListen(onBlob) {
    if (!hf.stream) { onBlob(null); return; }
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!hf.ctx) { try { hf.ctx = new AC(); } catch (e) {} }
    if (hf.ctx) { try { hf.ctx.resume(); } catch (e) {} }

    var src = hf.ctx ? hf.ctx.createMediaStreamSource(hf.stream) : null;
    var analyser = hf.ctx ? hf.ctx.createAnalyser() : null;
    if (analyser) { analyser.fftSize = 512; src.connect(analyser); }
    var data = analyser ? new Uint8Array(analyser.fftSize) : null;

    var mime = hfPickMime();
    hf.chunks = [];
    try { hf.rec = mime ? new MediaRecorder(hf.stream, { mimeType: mime }) : new MediaRecorder(hf.stream); }
    catch (e) { onBlob(null); return; }
    hf.rec.ondataavailable = function (e) { if (e.data && e.data.size) hf.chunks.push(e.data); };
    hf.rec.onstop = function () {
      if (src) { try { src.disconnect(); } catch (e) {} }
      if (hf.raf) { cancelAnimationFrame(hf.raf); hf.raf = 0; }
      var type = (hf.rec && hf.rec.mimeType) || mime || "audio/mp4";
      onBlob(new Blob(hf.chunks, { type: type }));
    };

    hf.active = true;
    var startedAt = Date.now(), silenceStart = 0, sawSpeech = false;
    var SILENCE_MS = 1100, MAX_MS = 20000, THRESH = 0.015;
    try { hf.rec.start(); } catch (e) { onBlob(null); return; }
    if (hf.btn) hf.btn.classList.add("listening");

    function loop() {
      if (!hf.active) return;
      var now = Date.now();
      if (data && analyser) {
        analyser.getByteTimeDomainData(data);
        var sum = 0;
        for (var i = 0; i < data.length; i++) { var v = (data[i] - 128) / 128; sum += v * v; }
        var rms = Math.sqrt(sum / data.length);
        if (rms > THRESH) { sawSpeech = true; silenceStart = 0; }
        else if (sawSpeech && !silenceStart) { silenceStart = now; }
      }
      var quietDone = sawSpeech && silenceStart && (now - silenceStart > SILENCE_MS);
      var tooLong = now - startedAt > MAX_MS;
      var noSpeechTimeout = !sawSpeech && (now - startedAt > 7000);
      if (quietDone || tooLong || noSpeechTimeout) { hfStop(); return; }
      hf.raf = requestAnimationFrame(loop);
    }
    if (data) hf.raf = requestAnimationFrame(loop);
  }

  function hfStop() {
    hf.active = false;
    if (hf.btn) hf.btn.classList.remove("listening");
    if (hf.rec && hf.rec.state !== "inactive") { try { hf.rec.stop(); } catch (e) {} }
  }
  function hfReleaseMic() {
    hfStop();
    if (hf.stream) { hf.stream.getTracks().forEach(function (t) { try { t.stop(); } catch (e) {} }); hf.stream = null; }
  }
  function hfTranscribe(blob, onText) {
    if (!blob || !blob.size) { onText(""); return; }
    var reader = new FileReader();
    reader.onload = function () {
      var b64 = String(reader.result).split(",")[1] || "";
      fetch("/api/transcribe", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ audio: b64, mime: blob.type || "audio/mp4", openaiKey: S.openaiKey || undefined }),
      })
        .then(function (r) { return r.ok ? r.json() : r.text().then(function (t) { throw new Error("Transcription failed (" + r.status + "). " + t.slice(0, 140)); }); })
        .then(function (res) { onText((res.text || "").trim()); })
        .catch(function (err) { addMsg("sys", "⚠ " + err.message); onText(""); });
    };
    reader.readAsDataURL(blob);
  }

  // ---------- API client ----------
  // Calls the serverless function by default. Falls back to direct browser
  // access only if the user pasted their own key in Settings.
  function api(payload) {
    if (S.apiKey) return apiDirect(payload);
    return fetch("/api/coach", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    }).then(function (r) {
      if (!r.ok) return r.text().then(function (t) { throw new Error("Coach unavailable (" + r.status + "). " + t.slice(0, 140)); });
      return r.json();
    });
  }
  // Direct browser call (BYO key) — mirrors the function's prompt building.
  function apiDirect(payload) {
    var built = window.FEX_PROMPT.build(payload);
    var body = {
      model: "claude-opus-4-8",
      max_tokens: payload.type === "score" ? 1500 : 400,
      system: built.system,
      messages: built.messages,
    };
    if (built.output_config) body.output_config = built.output_config;
    return fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": S.apiKey,
        "anthropic-version": "2023-06-01",
        "anthropic-dangerous-direct-browser-access": "true",
      },
      body: JSON.stringify(body),
    })
      .then(function (r) { if (!r.ok) return r.text().then(function (t) { throw new Error(t.slice(0, 160)); }); return r.json(); })
      .then(function (data) {
        var text = (data.content || []).filter(function (b) { return b.type === "text"; }).map(function (b) { return b.text; }).join("");
        return window.FEX_PROMPT.parse(payload, text);
      });
  }

  // ========================================================================
  //  HOME
  // ========================================================================
  function renderHome() {
    stopSpeak(); stopListening(); hfReleaseMic();
    setTitle("FEX Pitch Coach", false);
    footerNote.textContent = "Tap any section to practice it out loud with the AI prospect.";

    var name = S.agentName || "";
    var sections = SCRIPT.sections.map(function (sec, i) {
      return (
        '<button class="mode" data-section="' + sec.id + '">' +
        '<div class="mtitle">' + (i + 1) + ". " + esc(sec.title) + "</div>" +
        '<div class="mdesc">' + esc(sec.purpose.split(".")[0]) + ".</div>" +
        '<div class="tiny" style="margin-top:auto;color:var(--accent)">🎙 Tap to practice</div>' +
        "</button>"
      );
    }).join("");

    var wrap = h(
      '<div>' +
      '<div class="hero">' +
      (name ? '<div class="greet">Welcome back, ' + esc(name) + " 👋</div>" : "") +
      "<p>Practice your final expense pitch by <b>talking</b> to an AI prospect. Run one section at a time or take a full call — then get a 0–100% score.</p>" +
      "</div>" +

      '<button class="mode full" id="fullCall">' +
      '<div class="emoji">📞</div>' +
      '<div class="col"><div class="mtitle">Start a Full Call</div>' +
      '<div class="mdesc">Live roleplay from “hello” to the close. Objections included.</div></div>' +
      '<div class="go">›</div>' +
      "</button>" +

      '<div class="spacer"></div>' +
      '<div class="pill">Practice by section</div>' +
      '<div class="modes">' + sections + "</div>" +

      '<div class="spacer"></div><div class="spacer"></div>' +
      '<div class="pill">Study tools</div>' +
      '<div class="modes">' +
      '<button class="mode" id="memorize"><div class="emoji">🧠</div><div class="mtitle">Memorize</div><div class="mdesc">Fill-in-the-blank flashcards on the key lines.</div></button>' +
      '<button class="mode" id="readAll"><div class="emoji">📖</div><div class="mtitle">Read the Script</div><div class="mdesc">The full script with the “why” behind each step.</div></button>' +
      "</div>" +
      "</div>"
    );

    wrap.querySelectorAll("[data-section]").forEach(function (b) {
      b.addEventListener("click", function () { startCall({ mode: "section", sectionId: b.getAttribute("data-section") }); });
    });
    wrap.querySelector("#fullCall").addEventListener("click", function () { startCall({ mode: "full" }); });
    wrap.querySelector("#memorize").addEventListener("click", renderMemorize);
    wrap.querySelector("#readAll").addEventListener("click", function () { renderRead(0); });

    swap(wrap);
    if (!S.agentName) { footerNote.textContent = "Tip: set your name in ⚙ so the AI greets prospects with it."; }
  }

  // ========================================================================
  //  CALL  (section practice + full call) — the speak-to-AI core
  // ========================================================================
  var call = null;
  function startCall(opts) {
    unlockAudio(); // we're inside the tap gesture — lets the prospect speak on iOS
    if (!S.agentName) { S.agentName = SCRIPT.agentNameDefault; saveSettings(); }
    var sec = opts.mode === "section" ? SCRIPT.sections.find(function (s) { return s.id === opts.sectionId; }) : null;
    call = { mode: opts.mode, sectionId: opts.sectionId || null, section: sec, history: [], busy: false, draft: "", ended: false, hf: false };

    // Unified hands-free: use the same record + transcribe engine on EVERY
    // device so iPhone and Android behave identically. The browser's built-in
    // speech recognition is only a fallback when hands-free is turned off.
    var useHF = hfEnabled();
    call.hf = useHF;

    setTitle(sec ? sec.title : "Full Call", true);
    footerNote.textContent = useHF
      ? "Hands-free: after the prospect talks, just speak — I'm listening."
      : recog
        ? "Tap the mic and speak your line."
        : (IS_IOS ? "Tap 🎤 to open your keyboard, then press the keyboard's mic to talk." : "Type your line.");

    var hint = sec
      ? '<button class="btn ghost" id="hintBtn" style="flex:0 0 auto">💡 Hint</button>'
      : "";

    var wrap = h(
      '<div>' +
      '<div class="card" id="sceneCard">' +
      '<div class="pill">' + (sec ? "Section drill" : "Full roleplay") + "</div>" +
      '<div class="purpose" id="scene">Connecting…</div>' +
      (sec ? '<details><summary class="tiny">Show this section\'s script</summary><pre class="script" style="margin-top:10px">' + esc(fill(sec.script)) + "</pre></details>" : "") +
      "</div>" +
      '<div class="chat" id="chat"></div>' +
      '<div style="height:120px"></div>' +
      "</div>"
    );
    swap(wrap);

    // sticky dock
    var dock = h(
      '<div class="dock" id="dock">' +
      '<div class="callbar">' +
      '<span class="statusdot" id="status">●&nbsp;<b>Live call</b></span>' +
      '<button class="btn good" id="endBtn" style="flex:0 0 auto;padding:8px 14px">End & Score</button>' +
      hint +
      "</div>" +
      '<div class="composer">' +
      ((recog || useHF)
        ? '<button class="mic" id="mic" aria-label="Tap to talk">🎙</button>'
        : (IS_IOS ? '<button class="mic" id="dictate" aria-label="Talk">🎤</button>' : "")) +
      '<textarea id="ta" placeholder="' + (useHF ? "Just talk — I'm listening…" : recog ? "Speak or type your line…" : (IS_IOS ? "Tap 🎤, then your keyboard mic, and talk…" : "Type your line…")) + '" rows="1"></textarea>' +
      '<button class="btn primary send" id="send" aria-label="Send">↑</button>' +
      "</div>" +
      "</div>"
    );
    document.getElementById("app").appendChild(dock);

    var ta = dock.querySelector("#ta");
    ta.addEventListener("input", function () { ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight, 130) + "px"; });
    dock.querySelector("#send").addEventListener("click", function () { sendTurn(ta.value); ta.value = ""; ta.style.height = "auto"; });
    dock.querySelector("#endBtn").addEventListener("click", endAndScore);
    if (sec) dock.querySelector("#hintBtn").addEventListener("click", function () { showHint(sec); });
    if (useHF) setupHF(dock.querySelector("#mic"));
    else if (recog) setupMic(dock.querySelector("#mic"), ta);
    else if (IS_IOS) setupDictate(dock.querySelector("#dictate"), ta);

    if (useHF) {
      hfEnsureMic().then(function (ok) {
        if (!ok) { call.hf = false; addMsg("sys", "I couldn't access the microphone. Allow mic access and reopen, or type your line."); }
      });
    }

    backBtn.onclick = function () { teardownCall(); renderHome(); };

    // Kick off: AI prospect speaks first.
    call.busy = true;
    setScene("Calling the prospect…");
    api({ type: "turn", mode: call.mode, sectionId: call.sectionId, agentName: S.agentName, difficulty: S.difficulty, history: [], start: true })
      .then(function (res) {
        setScene(res.scene || (sec ? "You're at the “" + sec.title + "” part of the call. Take it from here." : "A new lead just picked up. Run your opening."));
        call.history.push({ role: "prospect", content: res.reply });
        prospectSays(res.reply);
        call.busy = false;
      })
      .catch(function (err) { call.busy = false; addMsg("sys", "⚠ " + err.message); });
  }

  function setScene(t) { var s = document.getElementById("scene"); if (s) s.textContent = t; }
  function setStatus(t, live) { var s = document.getElementById("status"); if (s) s.innerHTML = (live ? "●&nbsp;<b>" : "") + esc(t) + (live ? "</b>" : ""); }

  function setupMic(mic, ta) {
    var finalText = "";
    var target = {
      onText: function (txt, isFinal) {
        ta.value = txt; ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight, 130) + "px";
        if (isFinal) finalText = txt;
      },
      onEnd: function () {
        mic.classList.remove("listening");
        setStatus("Live call", true);
        var t = (finalText || ta.value).trim();
        finalText = "";
        if (t) { ta.value = ""; ta.style.height = "auto"; sendTurn(t); }
      },
    };
    mic.addEventListener("click", function () {
      if (listening) { stopListening(); return; }
      stopSpeak();
      finalText = "";
      mic.classList.add("listening");
      setStatus("Listening…", false);
      startListening(target);
    });
  }

  // iPhone: no web speech recognition, so the "talk" button just opens the
  // keyboard and focuses the box. The rep taps the keyboard's 🎤 to dictate.
  function setupDictate(btn, ta) {
    if (!btn) return;
    btn.addEventListener("click", function () {
      stopSpeak();
      ta.focus();
      var v = ta.value; ta.value = ""; ta.value = v; // move cursor to end
      if (!localStorage.getItem("fexDictHint")) {
        localStorage.setItem("fexDictHint", "1");
        addMsg("sys", "On iPhone: press the 🎤 on your keyboard and just talk — your words appear in the box. Tap ↑ to send.");
      }
    });
  }

  // iPhone hands-free: open the mic, listen, transcribe, and continue — no taps.
  function setupHF(btn) {
    hf.btn = btn || null;
    if (!btn) return;
    btn.addEventListener("click", function () {
      if (hf.active) { hfStop(); }      // "I'm done" — send this turn now
      else { stopSpeak(); hfTurn(); }   // start (or retry) listening
    });
  }
  function hfTurn() {
    if (!call || call.ended || !call.hf) return;
    setStatus("Listening — just talk…", false);
    hfListen(function (blob) {
      if (!call || call.ended) return;
      setStatus("Transcribing…", false);
      hfTranscribe(blob, function (text) {
        if (!call || call.ended) return;
        if (text) { call.hfEmpty = 0; sendTurn(text); }
        else {
          call.hfEmpty = (call.hfEmpty || 0) + 1;
          if (call.hfEmpty < 2) { hfTurn(); }
          else { call.hfEmpty = 0; setStatus("Tap 🎙 when ready to talk", false); }
        }
      });
    });
  }

  function prospectSays(text) {
    addMsg("them", text);
    setStatus("Prospect speaking…", false);
    speak(text, function () {
      if (!call || call.ended) return;
      setStatus("Live call", true);
      // After the prospect finishes, open the mic automatically.
      if (call.hf) {
        hfTurn();
      } else if (recog && S.voiceOut) {
        var mic = document.getElementById("mic");
        if (mic) mic.click();
      }
    });
  }

  function sendTurn(text) {
    text = (text || "").trim();
    if (!text || !call || call.busy || call.ended) return;
    addMsg("me", text);
    call.history.push({ role: "agent", content: text });
    call.busy = true;
    var typing = addTyping();
    api({ type: "turn", mode: call.mode, sectionId: call.sectionId, agentName: S.agentName, difficulty: S.difficulty, history: call.history })
      .then(function (res) {
        typing.remove();
        call.history.push({ role: "prospect", content: res.reply });
        prospectSays(res.reply);
        if (res.done) { setStatus("Section complete — End & Score", false); }
        call.busy = false;
      })
      .catch(function (err) { typing.remove(); addMsg("sys", "⚠ " + err.message); call.busy = false; });
  }

  function endAndScore() {
    if (!call || call.busy) return;
    stopSpeak(); stopListening(); hfStop();
    call.ended = true;
    if (call.history.length === 0) { addMsg("sys", "Say at least one line before scoring."); return; }
    var dock = document.getElementById("dock");
    if (dock) dock.remove();
    setTitle("Your Score", true);
    var loading = h('<div class="center-msg">📊 Scoring your pitch…<br><span class="tiny">Reviewing every line against the script.</span></div>');
    swap(loading);
    api({ type: "score", mode: call.mode, sectionId: call.sectionId, agentName: S.agentName, difficulty: S.difficulty, history: call.history })
      .then(renderScore)
      .catch(function (err) { swap(h('<div class="center-msg">⚠ ' + esc(err.message) + '<br><br><button class="btn primary" id="bk">Back home</button></div>')); document.getElementById("bk").addEventListener("click", renderHome); });
  }

  function showHint(sec) {
    var lines = sec.keyLines.map(function (l) { return "<li>" + esc(fill(l)) + "</li>"; }).join("");
    addMsg("sys", "Key lines for " + sec.title + ":");
    var chat = document.getElementById("chat");
    chat.appendChild(h('<ul class="keylines">' + lines + "</ul>"));
    chat.scrollIntoView({ block: "end" });
    window.scrollTo(0, document.body.scrollHeight);
  }

  function addMsg(kind, text) {
    var chat = document.getElementById("chat");
    if (!chat) return null;
    var who = kind === "them" ? "Prospect" : kind === "me" ? "You" : "";
    var node = h('<div class="msg ' + kind + '">' + (who ? '<div class="who">' + who + "</div>" : "") + esc(text) + "</div>");
    chat.appendChild(node);
    window.scrollTo(0, document.body.scrollHeight);
    return node;
  }
  function addTyping() {
    var chat = document.getElementById("chat");
    var node = h('<div class="msg them"><div class="who">Prospect</div><span class="typing"><i></i><i></i><i></i></span></div>');
    chat.appendChild(node); window.scrollTo(0, document.body.scrollHeight); return node;
  }
  function teardownCall() { stopSpeak(); stopListening(); hfReleaseMic(); hf.btn = null; call = null; var d = document.getElementById("dock"); if (d) d.remove(); backBtn.onclick = null; }

  // ========================================================================
  //  SCORE
  // ========================================================================
  function renderScore(res) {
    teardownCall();
    setTitle("Your Score", true);
    footerNote.textContent = "Run it again to beat your score.";
    var overall = Math.max(0, Math.min(100, Math.round(res.overall)));
    var color = overall >= 80 ? "var(--good)" : overall >= 60 ? "var(--warn)" : "var(--bad)";
    var grade = overall >= 90 ? "Excellent — you're closing-ready" :
      overall >= 80 ? "Strong — minor polish needed" :
      overall >= 65 ? "Solid — keep drilling" :
      overall >= 50 ? "Developing — review the weak spots" : "Keep practicing — you'll get there";

    var rows = (res.categories || []).map(function (c) {
      var pct = Math.round((c.score / c.max) * 100);
      var cc = pct >= 80 ? "var(--good)" : pct >= 55 ? "var(--warn)" : "var(--bad)";
      return '<div class="rrow"><div class="rl">' + esc(c.label) + '</div>' +
        '<div class="rbar"><i style="width:' + pct + '%;background:' + cc + '"></i></div>' +
        '<div class="rn">' + c.score + "/" + c.max + "</div></div>";
    }).join("");

    var strengths = (res.strengths || []).map(function (s) { return '<li class="good-c">✓ ' + esc(s) + "</li>"; }).join("");
    var improves = (res.improvements || []).map(function (s) { return '<li class="warn-c">→ ' + esc(s) + "</li>"; }).join("");

    var wrap = h(
      "<div>" +
      '<div class="card scorewrap">' +
      '<div class="bigscore" style="color:' + color + '">' + overall + "<small>%</small></div>" +
      '<div class="grade" style="color:' + color + '">' + esc(grade) + "</div>" +
      "</div>" +
      '<div class="card"><div class="pill">Breakdown</div><div class="rubric">' + rows + "</div></div>" +
      (strengths ? '<div class="card"><h3>What you did well</h3><ul class="tips">' + strengths + "</ul></div>" : "") +
      (improves ? '<div class="card"><h3>What to work on</h3><ul class="tips">' + improves + "</ul></div>" : "") +
      (res.drill ? '<div class="card"><div class="pill">Next drill</div><p class="purpose" style="margin:0">' + esc(res.drill) + "</p></div>" : "") +
      '<div class="row">' +
      '<button class="btn ghost" id="homeBtn">Home</button>' +
      '<button class="btn primary" id="againBtn">Practice again</button>' +
      "</div><div class='spacer'></div></div>"
    );
    var lastMode = call ? call.mode : "full"; var lastSection = call ? call.sectionId : null;
    wrap.querySelector("#homeBtn").addEventListener("click", renderHome);
    wrap.querySelector("#againBtn").addEventListener("click", function () { startCall({ mode: res._mode || "full", sectionId: res._sectionId || null }); });
    backBtn.onclick = renderHome;
    swap(wrap);
  }

  // ========================================================================
  //  MEMORIZE (flashcards)
  // ========================================================================
  function renderMemorize() {
    setTitle("Memorize", true);
    footerNote.textContent = "Say or type the missing words, then reveal.";
    var cards = [];
    SCRIPT.sections.forEach(function (sec) {
      (sec.blanks || []).forEach(function (b) { cards.push({ sec: sec.title, blank: b }); });
    });
    var i = 0, revealed = false;
    backBtn.onclick = renderHome;

    function draw() {
      var c = cards[i];
      var prompt = esc(c.blank.prompt).replace(/_______/g, '<b>______</b>');
      var ans = c.blank.answers.map(esc).join(" · ");
      var wrap = h(
        "<div>" +
        '<div class="progress"><div class="bar"><i style="width:' + ((i / cards.length) * 100) + '%"></i></div><div class="count">' + (i + 1) + "/" + cards.length + "</div></div>" +
        '<div class="card"><div class="pill">' + esc(c.sec) + "</div>" +
        '<div class="blank">' + prompt + "</div>" +
        (revealed ? '<div class="reveal">Answer: ' + ans + "</div>" : "") +
        "</div>" +
        '<div class="row">' +
        (revealed
          ? '<button class="btn ghost" id="again">Again</button><button class="btn primary" id="next">' + (i + 1 < cards.length ? "Next" : "Finish") + "</button>"
          : '<button class="btn primary block" id="reveal">Reveal answer</button>') +
        "</div></div>"
      );
      if (revealed) {
        wrap.querySelector("#again").addEventListener("click", function () { revealed = false; draw(); });
        wrap.querySelector("#next").addEventListener("click", function () { if (i + 1 < cards.length) { i++; revealed = false; draw(); } else renderHome(); });
      } else {
        wrap.querySelector("#reveal").addEventListener("click", function () { revealed = true; draw(); });
      }
      swap(wrap);
    }
    draw();
  }

  // ========================================================================
  //  READ
  // ========================================================================
  function renderRead(idx) {
    var sec = SCRIPT.sections[idx];
    setTitle("Read · " + sec.title, true);
    footerNote.textContent = (idx + 1) + " of " + SCRIPT.sections.length + " sections";
    backBtn.onclick = renderHome;
    var keys = sec.keyLines.map(function (l) { return "<li>" + esc(fill(l)) + "</li>"; }).join("");
    var wrap = h(
      "<div>" +
      '<div class="progress"><div class="bar"><i style="width:' + (((idx + 1) / SCRIPT.sections.length) * 100) + '%"></i></div><div class="count">' + (idx + 1) + "/" + SCRIPT.sections.length + "</div></div>" +
      '<div class="card"><div class="pill">Why this step</div><p class="purpose" style="margin:0">' + esc(sec.purpose) + "</p></div>" +
      '<div class="card"><h3>Script</h3><pre class="script">' + esc(fill(sec.script)) + "</pre>" +
      '<ul class="keylines">' + keys + "</ul></div>" +
      '<div class="row">' +
      '<button class="btn ghost" id="prev"' + (idx === 0 ? " disabled" : "") + ">‹ Prev</button>" +
      '<button class="btn primary" id="practice">🎙 Practice this</button>' +
      '<button class="btn ghost" id="next"' + (idx + 1 >= SCRIPT.sections.length ? " disabled" : "") + ">Next ›</button>" +
      "</div><div class='spacer'></div></div>"
    );
    if (idx > 0) wrap.querySelector("#prev").addEventListener("click", function () { renderRead(idx - 1); });
    if (idx + 1 < SCRIPT.sections.length) wrap.querySelector("#next").addEventListener("click", function () { renderRead(idx + 1); });
    wrap.querySelector("#practice").addEventListener("click", function () { startCall({ mode: "section", sectionId: sec.id }); });
    swap(wrap);
  }

  // ---------- view swap ----------
  function swap(node) { view.innerHTML = ""; view.appendChild(node); window.scrollTo(0, 0); }

  // ---------- settings dialog ----------
  var dlg = document.getElementById("settingsDialog");
  document.getElementById("settingsBtn").addEventListener("click", function () {
    document.getElementById("agentName").value = S.agentName;
    document.getElementById("difficulty").value = S.difficulty;
    document.getElementById("voiceOut").checked = S.voiceOut;
    document.getElementById("handsFree").checked = S.handsFree;
    document.getElementById("apiKey").value = S.apiKey;
    document.getElementById("openaiKey").value = S.openaiKey;
    if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", "");
  });
  document.getElementById("saveSettings").addEventListener("click", function () {
    S.agentName = document.getElementById("agentName").value.trim();
    S.difficulty = document.getElementById("difficulty").value;
    S.voiceOut = document.getElementById("voiceOut").checked;
    S.handsFree = document.getElementById("handsFree").checked;
    S.apiKey = document.getElementById("apiKey").value.trim();
    S.openaiKey = document.getElementById("openaiKey").value.trim();
    saveSettings();
    setTimeout(renderHome, 0);
  });

  backBtn.addEventListener("click", function () { /* per-screen handlers set backBtn.onclick */ });

  // store mode/section on score result so "again" works
  var _origRenderScore = renderScore;
  renderScore = function (res) {
    if (call) { res._mode = call.mode; res._sectionId = call.sectionId; }
    _origRenderScore(res);
  };

  // ---------- boot ----------
  renderHome();
})();
