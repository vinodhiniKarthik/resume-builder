document.addEventListener("DOMContentLoaded", function () {

  /* ─── Config ─────────────────────────────────────────── */
  const DEBOUNCE_MS   = 120;   // ms to wait after last keystroke
  const IDLE_MS       = 3000;  // ms before "idle" pulse kicks in
  const FLASH_CLASS   = "preview-updated";
  const IDLE_CLASS    = "preview-idle";

  /* ─── Field map: input id → preview id + fallback ───── */
  const FIELDS = [
    { input: "full_name",   preview: "p_name",       fallback: "Your Name"   },
    { input: "email",       preview: "p_email",      fallback: "Email"       },
    { input: "phone",       preview: "p_phone",      fallback: "Phone"       },
    { input: "skills",      preview: "p_skills",     fallback: "Skills"      },
    { input: "education",   preview: "p_education",  fallback: "Education"   },
    { input: "experience",  preview: "p_experience", fallback: "Experience"  },
  ];

  /* ─── State ───────────────────────────────────────────── */
  let debounceTimer  = null;
  let idleTimer      = null;
  let editCount      = 0;
  const prevValues   = {};   // tracks last rendered value per preview id

  /* ─── Helpers ─────────────────────────────────────────── */

  // Typewriter: animates text into an element character by character
  function typewriterSet(el, text, onDone) {
    el.dataset.typing = "1";
    el.innerText = "";
    let i = 0;
    const total = text.length;

    // Fast enough to feel snappy but still visible
    const speed = total > 40 ? 12 : total > 15 ? 18 : 28;

    function tick() {
      if (i < total) {
        el.innerText += text[i++];
        setTimeout(tick, speed);
      } else {
        delete el.dataset.typing;
        if (onDone) onDone();
      }
    }
    tick();
  }

  // Flash-highlight a preview element when its value changes
  function flashElement(el) {
    el.classList.remove(FLASH_CLASS);
    void el.offsetWidth; // reflow to restart animation
    el.classList.add(FLASH_CLASS);
    el.addEventListener("animationend", () => el.classList.remove(FLASH_CLASS), { once: true });
  }

  // Injects the CSS we need (so the JS is self-contained)
  function injectStyles() {
    if (document.getElementById("__preview-js-styles")) return;
    const style = document.createElement("style");
    style.id = "__preview-js-styles";
    style.textContent = `
      .${FLASH_CLASS} {
        animation: previewFlash 0.45s ease-out forwards;
      }
      @keyframes previewFlash {
        0%   { background-color: rgba(99, 179, 237, 0.35); border-radius: 3px; }
        100% { background-color: transparent; }
      }

      .${IDLE_CLASS} {
        animation: previewPulse 2s ease-in-out infinite;
      }
      @keyframes previewPulse {
        0%, 100% { opacity: 1; }
        50%       { opacity: 0.55; }
      }

      [data-preview-init] {
        animation: previewReveal 0.4s ease both;
      }
      @keyframes previewReveal {
        from { opacity: 0; transform: translateY(6px); }
        to   { opacity: 1; transform: translateY(0); }
      }
    `;
    document.head.appendChild(style);
  }

  /* ─── Core update ─────────────────────────────────────── */

  function updatePreview() {
    clearTimeout(idleTimer);
    stopIdlePulse();

    let filledCount = 0;

    FIELDS.forEach(({ input, preview, fallback }) => {
      const inputEl   = document.getElementById(input);
      const previewEl = document.getElementById(preview);
      if (!inputEl || !previewEl) return;

      const raw  = inputEl.value.trim();
      const text = raw || fallback;
      const isFilled = raw.length > 0;
      if (isFilled) filledCount++;

      // Skip re-render if nothing changed (perf guard)
      if (prevValues[preview] === text) return;
      prevValues[preview] = text;

      flashElement(previewEl);
      typewriterSet(previewEl, text);
    });

    trackProgress(filledCount);
    scheduleIdlePulse();
  }

  /* ─── Debounced wrapper ───────────────────────────────── */

  function onInput() {
    editCount++;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(updatePreview, DEBOUNCE_MS);
  }

  /* ─── Progress tracking ───────────────────────────────── */

  function trackProgress(filledCount) {
    const pct = Math.round((filledCount / FIELDS.length) * 100);

    // Expose on window so external code / devtools can read it
    window.__resumeProgress = { filledCount, total: FIELDS.length, pct, editCount };

    // If there's a [data-resume-progress] element, update it
    const bar = document.querySelector("[data-resume-progress]");
    if (bar) bar.style.width = pct + "%";

    const label = document.querySelector("[data-resume-progress-label]");
    if (label) label.innerText = pct + "% complete";
  }

  /* ─── Idle pulse ──────────────────────────────────────── */

  function scheduleIdlePulse() {
    idleTimer = setTimeout(startIdlePulse, IDLE_MS);
  }

  function startIdlePulse() {
    FIELDS.forEach(({ preview }) => {
      document.getElementById(preview)?.classList.add(IDLE_CLASS);
    });
  }

  function stopIdlePulse() {
    FIELDS.forEach(({ preview }) => {
      document.getElementById(preview)?.classList.remove(IDLE_CLASS);
    });
  }

  /* ─── Staggered init reveal ───────────────────────────── */

  function initReveal() {
    FIELDS.forEach(({ preview }, i) => {
      const el = document.getElementById(preview);
      if (!el) return;
      el.setAttribute("data-preview-init", "");
      el.style.animationDelay = `${i * 80}ms`;
    });
  }

  /* ─── Bootstrap ───────────────────────────────────────── */

  injectStyles();
  initReveal();

  // Attach listeners to all inputs + textareas
  document.querySelectorAll("input, textarea").forEach(el => {
    el.addEventListener("input", onInput);
  });

  // Run immediately (no debounce) to populate on load
  updatePreview();
  scheduleIdlePulse();

});