// Client-side logic: voice capture (Web Speech API), photo upload, text logging.

(function () {
  const dateInput = document.getElementById("logDate");
  const textArea = document.getElementById("logText");
  const statusEl = document.getElementById("logStatus");
  const micBtn = document.getElementById("micBtn");
  const saveBtn = document.getElementById("saveBtn");
  const photoInput = document.getElementById("photoInput");
  const hintInput = document.getElementById("photoHint");

  function currentDate() {
    return dateInput ? dateInput.value : "";
  }

  function setStatus(msg, kind) {
    if (!statusEl) return;
    statusEl.textContent = msg;
    statusEl.className = "status " + (kind || "");
  }

  function reloadToDate() {
    const d = currentDate();
    window.location.href = "/?date=" + encodeURIComponent(d);
  }

  // ---- date navigation ----
  if (dateInput) {
    dateInput.addEventListener("change", reloadToDate);
  }

  // ---- text / voice logging ----
  async function submitText(source) {
    const text = (textArea.value || "").trim();
    if (!text) { setStatus("Type or speak something to log.", "err"); return; }
    setStatus("Analysing with Claude…", "busy");
    saveBtn.disabled = true;
    try {
      const body = new FormData();
      body.append("text", text);
      body.append("date", currentDate());
      body.append("source", source || "text");
      const res = await fetch("/api/log/text", { method: "POST", body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Request failed");
      setStatus(
        `Logged ${data.foods_added} food item(s) and ${data.habits_added} habit(s). Refreshing…`,
        "ok"
      );
      textArea.value = "";
      setTimeout(reloadToDate, 700);
    } catch (e) {
      setStatus("Error: " + e.message, "err");
    } finally {
      saveBtn.disabled = false;
    }
  }

  if (saveBtn) saveBtn.addEventListener("click", () => submitText("text"));

  // ---- voice via Web Speech API ----
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let recording = false;

  if (micBtn) {
    if (!SpeechRecognition) {
      micBtn.disabled = true;
      micBtn.title = "Voice not supported in this browser — try Chrome/Edge.";
      micBtn.textContent = "🎤 Voice n/a";
    } else {
      recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = navigator.language || "en-US";

      let finalTranscript = textArea.value ? textArea.value + " " : "";

      recognition.onresult = (event) => {
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const t = event.results[i][0].transcript;
          if (event.results[i].isFinal) finalTranscript += t + " ";
          else interim += t;
        }
        textArea.value = (finalTranscript + interim).trimStart();
      };
      recognition.onerror = (e) => setStatus("Mic error: " + e.error, "err");
      recognition.onend = () => {
        if (recording) recognition.start(); // keep going until user stops
      };

      micBtn.addEventListener("click", () => {
        if (recording) {
          recording = false;
          recognition.stop();
          micBtn.classList.remove("recording");
          micBtn.textContent = "🎤 Speak";
          setStatus("Stopped. Review and Save, or speak again.", "");
        } else {
          finalTranscript = textArea.value ? textArea.value + " " : "";
          recording = true;
          recognition.start();
          micBtn.classList.add("recording");
          micBtn.textContent = "⏹ Stop";
          setStatus("Listening… speak your meals and habits.", "busy");
        }
      });
    }
  }

  // ---- photo logging ----
  if (photoInput) {
    photoInput.addEventListener("change", async () => {
      const file = photoInput.files[0];
      if (!file) return;
      setStatus("Analysing photo with Claude vision…", "busy");
      try {
        const body = new FormData();
        body.append("photo", file);
        body.append("date", currentDate());
        body.append("hint", hintInput ? hintInput.value : "");
        const res = await fetch("/api/log/photo", { method: "POST", body });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Request failed");
        const note = data.note ? " (" + data.note + ")" : "";
        setStatus(`Logged ${data.foods_added} item(s) from photo${note}. Refreshing…`, "ok");
        setTimeout(reloadToDate, 900);
      } catch (e) {
        setStatus("Error: " + e.message, "err");
      } finally {
        photoInput.value = "";
      }
    });
  }

  // ---- delete entries ----
  document.querySelectorAll("[data-del]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const [kind, id] = btn.getAttribute("data-del").split(":");
      if (!confirm("Delete this entry?")) return;
      const res = await fetch(`/api/${kind}/${id}`, { method: "DELETE" });
      if (res.ok) btn.closest(".entry").remove();
    });
  });
})();
