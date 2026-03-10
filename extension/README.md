# LinkedIn Auto Connector – Browser Extension

This extension brings the LinkedIn Auto Connector Bot into your browser. It runs **only** on LinkedIn people search results and sends connection requests with a custom note.

⚠️ **Use at your own risk.** Automated connection requests may violate LinkedIn’s terms of service. Stay under ~80 requests per week to reduce the chance of restrictions.

## Supported browsers

- **Chrome** (recommended)
- **Edge**
- **Firefox** (Manifest V3; install as temporary or signed)

## How to install (Chrome / Edge)

1. Open a people search page on LinkedIn:
   - Go to [linkedin.com](https://www.linkedin.com) and log in.
   - Use the search bar (e.g. “technical recruiter”), then click **People** in the filters.
   - Copy the URL; it should look like:  
     `https://www.linkedin.com/search/results/people/?keywords=...`
2. In Chrome/Edge, go to `chrome://extensions` (or `edge://extensions`).
3. Turn on **Developer mode** (top right).
4. Click **Load unpacked** and choose the `extension` folder (the one that contains `manifest.json`).
5. The extension icon appears in the toolbar. Click it to open the popup.

## How to use

1. Open a **LinkedIn people search** tab (see URL shape above).
2. Click the extension icon and set:
   - **Connection message** – note sent with each request.
   - **Max requests per run** – e.g. 10 (keep low; stay under ~80/week total).
3. Click **Start**. The extension will:
   - Find visible “Connect” buttons on the current page.
   - Open the invite modal, add your note, and send.
   - Move to the next page if needed, until the run limit is reached.
4. Click **Stop** anytime to stop the current run.

Progress is shown in a small on-page status (top right). “This session” in the popup shows how many requests were sent in this run.

## Optional: add icons

To set custom icons for the extension:

1. Create an `icons` folder inside `extension`.
2. Add PNGs: `icon16.png`, `icon48.png`, `icon128.png`.
3. In `manifest.json`, add back under `"action"` and at root:

```json
"action": {
  "default_popup": "popup/popup.html",
  "default_icon": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  },
  "default_title": "LinkedIn Auto Connector"
},
...
"icons": {
  "16": "icons/icon16.png",
  "48": "icons/icon48.png",
  "128": "icons/icon128.png"
}
```

Then reload the extension.

## Relation to the Python bot

- The **Python bot** (Selenium) logs in, goes to a search URL, and automates the same flow in a separate browser instance.
- The **extension** runs inside your existing browser session. You must be logged in and on a people search page; it only automates “Connect” → “Add a note” → “Send” (and next page) using the same logic (including LinkedIn’s shadow DOM for the invite modal).

Same behavior, different environment: no Geckodriver or Python needed when using the extension.
