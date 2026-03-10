// Background service worker: coordinates run state and stores settings

const DEFAULT_MESSAGE = "Hi, I'd like to connect with you.";
const DEFAULT_LIMIT = 10;

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "GET_SETTINGS") {
    chrome.storage.local.get(
      { connectionMessage: DEFAULT_MESSAGE, maxRequests: DEFAULT_LIMIT },
      sendResponse
    );
    return true;
  }
  if (message.type === "SAVE_SETTINGS") {
    chrome.storage.local.set(
      {
        connectionMessage: message.connectionMessage || DEFAULT_MESSAGE,
        maxRequests: Math.max(1, parseInt(message.maxRequests, 10) || DEFAULT_LIMIT),
      },
      () => sendResponse({ ok: true })
    );
    return true;
  }
  if (message.type === "START_RUN") {
    chrome.storage.local.set({ running: true }, () => sendResponse({ ok: true }));
    return true;
  }
  if (message.type === "STOP_RUN") {
    chrome.storage.local.set({ running: false }, () => sendResponse({ ok: true }));
    return true;
  }
  if (message.type === "GET_RUNNING") {
    chrome.storage.local.get({ running: false }, (data) =>
      sendResponse({ running: data.running })
    );
    return true;
  }
  if (message.type === "STATS") {
    chrome.storage.local.get({ sentThisSession: 0 }, (data) =>
      sendResponse({ sentThisSession: data.sentThisSession || 0 })
    );
    return true;
  }
  if (message.type === "INCREMENT_SENT") {
    chrome.storage.local.get({ sentThisSession: 0 }, (data) => {
      const next = (data.sentThisSession || 0) + 1;
      chrome.storage.local.set({ sentThisSession: next }, () =>
        sendResponse({ sentThisSession: next })
      );
    });
    return true;
  }
  if (message.type === "RESET_SESSION_STATS") {
    chrome.storage.local.set({ sentThisSession: 0 }, () => sendResponse({ ok: true }));
    return true;
  }
});
