const DEFAULT_MESSAGE = "Hi, I'd like to connect with you.";
const DEFAULT_LIMIT = 10;

const messageEl = document.getElementById("message");
const limitEl = document.getElementById("limit");
const statsEl = document.getElementById("stats");
const btnStart = document.getElementById("btnStart");
const btnStop = document.getElementById("btnStop");

function loadSettings() {
  chrome.runtime.sendMessage({ type: "GET_SETTINGS" }, (data) => {
    if (chrome.runtime.lastError) return;
    if (data) {
      messageEl.value = data.connectionMessage || DEFAULT_MESSAGE;
      limitEl.value = String(data.maxRequests || DEFAULT_LIMIT);
    }
  });
}

function loadStats() {
  chrome.runtime.sendMessage({ type: "STATS" }, (data) => {
    if (chrome.runtime.lastError) return;
    if (data) statsEl.textContent = `${data.sentThisSession || 0} sent`;
  });
}

function setRunning(running) {
  btnStart.disabled = running;
  btnStop.disabled = !running;
}

function loadRunningState() {
  chrome.runtime.sendMessage({ type: "GET_RUNNING" }, (data) => {
    if (chrome.runtime.lastError) return;
    setRunning(Boolean(data && data.running));
  });
}

function startOnTab(tabId, maxRequests, connectionMessage) {
  chrome.tabs.sendMessage(
    tabId,
    { type: "START", maxRequests, connectionMessage },
    (reply) => {
      if (chrome.runtime.lastError) {
        alert(
          "Could not start on this tab. Refresh the LinkedIn people search page (F5 or Cmd+R), then click Start again."
        );
        chrome.runtime.sendMessage({ type: "STOP_RUN" });
        setRunning(false);
        return;
      }
      setRunning(true);
      window.close();
    }
  );
}

btnStart.addEventListener("click", () => {
  const connectionMessage = (messageEl.value || "").trim() || DEFAULT_MESSAGE;
  const maxRequests = Math.max(
    1,
    Math.min(80, parseInt(limitEl.value, 10) || DEFAULT_LIMIT)
  );

  chrome.runtime.sendMessage(
    {
      type: "SAVE_SETTINGS",
      connectionMessage,
      maxRequests,
    },
    () => {
      chrome.runtime.sendMessage({ type: "START_RUN" }, () => {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          const tab = tabs[0];
          if (!tab || !tab.id) {
            chrome.runtime.sendMessage({ type: "STOP_RUN" });
            return;
          }
          const url = (tab.url || "").toLowerCase();
          if (!url.includes("linkedin.com") || !url.includes("/search/results/people")) {
            alert(
              "Open a LinkedIn people search page first:\n\n" +
                "1. Go to LinkedIn and search (e.g. \"technical recruiter\")\n" +
                "2. Click the \"People\" filter\n" +
                "3. Stay on that page and click Start again."
            );
            chrome.runtime.sendMessage({ type: "STOP_RUN" });
            return;
          }
          startOnTab(tab.id, maxRequests, connectionMessage);
        });
      });
    }
  );
});

btnStop.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "STOP_RUN" }, () => setRunning(false));
});

document.getElementById("btnResetStats").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "RESET_SESSION_STATS" }, () => loadStats());
});

loadSettings();
loadStats();
loadRunningState();

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "local") return;
  if (changes.running) setRunning(changes.running.newValue === true);
  if (changes.sentThisSession) loadStats();
});
