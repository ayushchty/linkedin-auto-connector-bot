/**
 * LinkedIn Auto Connector - Content script (optimized)
 * Runs on LinkedIn people search: finds Connect buttons, opens invite modal,
 * adds note and sends. Handles shadow DOM and retries for reliability.
 */

(function () {
  const CONFIG = {
    delayBetweenRequests: { min: 3500, max: 5500 },
    delayAfterSend: 2500,
    modalWaitMax: 10000,
    pollInterval: 200,
    inviteRetries: 5,
    inviteRetryDelay: 1500,
  };

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  function randomDelay(min, max) {
    return sleep(min + Math.random() * (max - min));
  }

  function getShadowRoots() {
    const roots = [document];
    const host = document.querySelector("#interop-outlet, #interoop-outlet");
    if (host && host.shadowRoot) roots.push(host.shadowRoot);
    return roots;
  }

  function isVisible(el) {
    if (!el || !el.getBoundingClientRect) return false;
    try {
      const s = window.getComputedStyle(el);
      if (s.display === "none" || s.visibility === "hidden" || s.opacity === "0")
        return false;
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    } catch (_) {
      return false;
    }
  }

  function findInDocAndShadow(selectors) {
    for (const root of getShadowRoots()) {
      for (const sel of selectors) {
        try {
          const el = root.querySelector(sel);
          if (el && isVisible(el)) return el;
        } catch (_) {}
      }
    }
    return null;
  }

  function modalVisible() {
    return (
      findInDocAndShadow([
        "[data-test-modal-id='send-invite-modal']",
        ".artdeco-modal-overlay",
        "div[role='dialog']",
        "button[aria-label='Add a note']",
        "button[aria-label='Add note']",
        "textarea[name='message']",
      ]) !== null
    );
  }

  function waitForModal(timeoutMs) {
    return new Promise((resolve) => {
      if (modalVisible()) {
        resolve(true);
        return;
      }
      const deadline = Date.now() + (timeoutMs || CONFIG.modalWaitMax);
      const check = () => {
        if (modalVisible()) {
          resolve(true);
          return;
        }
        if (Date.now() >= deadline) {
          resolve(false);
          return;
        }
        setTimeout(check, CONFIG.pollInterval);
      };
      setTimeout(check, CONFIG.pollInterval);
    });
  }

  function clickAddNote() {
    const btn = findInDocAndShadow([
      "[data-test-modal-id='send-invite-modal'] button[aria-label='Add a note']",
      "[data-test-modal-id='send-invite-modal'] button[aria-label='Add note']",
      ".artdeco-modal-overlay button[aria-label='Add a note']",
      "div[role='dialog'] button[aria-label='Add a note']",
      "button[aria-label='Add a note']",
      "button[aria-label='Add note']",
    ]);
    if (btn) {
      btn.click();
      return true;
    }
    return false;
  }

  function fillAndSend(message) {
    const textarea = findInDocAndShadow([
      "[data-test-modal-id='send-invite-modal'] textarea[name='message']",
      "[data-test-modal-id='send-invite-modal'] textarea",
      ".artdeco-modal-overlay textarea[name='message']",
      "div[role='dialog'] textarea[name='message']",
      "textarea[name='message']",
      "textarea",
    ]);
    if (!textarea) return false;
    textarea.focus();
    textarea.value = message;
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    textarea.dispatchEvent(new Event("change", { bubbles: true }));
    textarea.dispatchEvent(new InputEvent("input", { bubbles: true, data: message }));

    const sendBtn = findInDocAndShadow([
      "[data-test-modal-id='send-invite-modal'] button[aria-label='Send invitation']",
      "[data-test-modal-id='send-invite-modal'] button[aria-label='Send']",
      ".artdeco-modal-overlay button[aria-label='Send invitation']",
      "div[role='dialog'] button[aria-label='Send invitation']",
      "button[aria-label='Send invitation']",
      "button[aria-label='Send']",
    ]);
    if (!sendBtn) return false;
    sendBtn.click();
    return true;
  }

  function dismissModal() {
    const escape = new KeyboardEvent("keydown", {
      key: "Escape",
      code: "Escape",
      keyCode: 27,
      bubbles: true,
    });
    document.dispatchEvent(escape);
    const overlay = findInDocAndShadow([".artdeco-modal-overlay", "div[role='dialog']"]);
    if (overlay) overlay.click();
  }

  async function doInviteFlow(message) {
    clickAddNote();
    await sleep(1200);
    for (let i = 0; i < CONFIG.inviteRetries; i++) {
      if (fillAndSend(message)) return true;
      await sleep(CONFIG.inviteRetryDelay);
    }
    return false;
  }

  /** Get Connect buttons only from search result items; dedupe by click target. */
  function getConnectTargets() {
    const seen = new Set();
    const targets = [];
    const resultContainers = [
      ".search-results-container",
      ".reusable-search__entity-result-list",
      "[class*='search-results']",
      "main",
    ].map((sel) => document.querySelector(sel)).filter(Boolean);

    const scope = resultContainers[0] || document.body;
    const spans = scope.querySelectorAll("span");
    for (const span of spans) {
      const text = (span.textContent || "").trim();
      if (text !== "Connect") continue;
      if (!isVisible(span)) continue;

      const clickable =
        span.closest("button") ||
        span.closest("a[href*='invite']") ||
        span.closest("a[href*='custom-invite']") ||
        span.closest("a") ||
        span.closest("[role='button']") ||
        span.parentElement ||
        span;
      if (seen.has(clickable)) continue;
      seen.add(clickable);
      targets.push(clickable);
    }
    return targets;
  }

  function getConnectByIndex(index) {
    const list = getConnectTargets();
    return list[index] || null;
  }

  function scrollTo(el) {
    el.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
  }

  function goToNextPage() {
    const pagination = document.querySelector(".artdeco-pagination, [class*='pagination']");
    const container = pagination || document;
    const buttons = container.querySelectorAll("button[aria-label='Next'], button");
    for (const btn of buttons) {
      if (btn.getAttribute("aria-disabled") === "true" || btn.disabled) continue;
      const label = (btn.getAttribute("aria-label") || "").trim();
      const text = (btn.textContent || "").trim();
      if (label === "Next" || text === "Next") {
        btn.click();
        return true;
      }
    }
    return false;
  }

  async function isRunning() {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: "GET_RUNNING" }, (r) => {
        resolve(r && r.running === true);
      });
    });
  }

  async function handleOneConnect(index, message, onProgress, maxRequests) {
    const el = getConnectByIndex(index);
    if (!el) return false;
    scrollTo(el);
    await sleep(800);
    el.click();
    const modalOk = await waitForModal();
    if (!modalOk) {
      dismissModal();
      await sleep(500);
      return false;
    }
    await sleep(600);
    const sent = await doInviteFlow(message);
    if (!sent) dismissModal();
    await sleep(CONFIG.delayAfterSend);
    return sent;
  }

  function updateStatus(text, isError, persist) {
    let el = document.getElementById("lac-status");
    if (!el) {
      el = document.createElement("div");
      el.id = "lac-status";
      Object.assign(el.style, {
        position: "fixed",
        top: "16px",
        right: "16px",
        zIndex: "2147483647",
        padding: "12px 16px",
        borderRadius: "8px",
        fontFamily: "system-ui, sans-serif",
        fontSize: "14px",
        boxShadow: "0 4px 20px rgba(0,0,0,0.15)",
        maxWidth: "320px",
        pointerEvents: "none",
      });
      document.body.appendChild(el);
    }
    el.style.background = isError ? "#fef2f2" : "#ecfdf5";
    el.style.color = isError ? "#991b1b" : "#065f46";
    el.textContent = text;
    if (!persist) setTimeout(() => el.remove(), 5000);
  }

  async function run(maxRequests, message, onProgress, onComplete) {
    let totalSent = 0;
    updateStatus("Starting…", false, true);

    while (totalSent < maxRequests) {
      if (!(await isRunning())) break;

      const targets = getConnectTargets();
      if (targets.length === 0) {
        if (!goToNextPage()) {
          updateStatus("No more Connect buttons or pages.", false);
          break;
        }
        await sleep(4500);
        continue;
      }

      while (totalSent < maxRequests) {
        if (!(await isRunning())) break;
        const first = getConnectByIndex(0);
        if (!first) break;
        const ok = await handleOneConnect(0, message, onProgress, maxRequests);
        if (ok) {
          totalSent++;
          chrome.runtime.sendMessage({ type: "INCREMENT_SENT" });
          if (onProgress) onProgress(totalSent, maxRequests);
          updateStatus(`Sent ${totalSent}/${maxRequests}`, false, true);
        }
        await randomDelay(
          CONFIG.delayBetweenRequests.min,
          CONFIG.delayBetweenRequests.max
        );
      }

      if (totalSent >= maxRequests) break;
      if (!goToNextPage()) break;
      await sleep(4000);
    }

    chrome.runtime.sendMessage({ type: "STOP_RUN" });
    updateStatus(`Done. ${totalSent} connection request(s) sent.`, false, false);
    if (onComplete) onComplete(totalSent);
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.type === "START") {
      const maxRequests = Math.max(1, Math.min(80, parseInt(msg.maxRequests, 10) || 10));
      const connectionMessage = (msg.connectionMessage || "").trim() || "Hi, I'd like to connect.";
      run(
        maxRequests,
        connectionMessage,
        (sent, max) => {},
        () => {}
      );
      sendResponse({ ok: true });
    }
  });
})();
