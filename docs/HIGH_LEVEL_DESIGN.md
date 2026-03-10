# LinkedIn Auto Connector Bot — High-Level Design

## 1. Purpose & Scope

The **LinkedIn Auto Connector Bot** automates sending **connection requests with a custom note** to people who match a given LinkedIn People search. A human configures a search URL and a message; the bot logs in, opens the search results, clicks **Connect** on each result, opens the **“Add a note”** flow in the popup, types the message, and clicks **Send**, then moves to the next page until a configurable limit is reached.

**In scope:** Login, navigate to search, find Connect buttons, open invite popup, add note, send, pagination, basic error handling and retries.  
**Out of scope:** Accepting incoming requests, messaging, job applications, or any action beyond “Connect + note + Send” on People search.

---

## 2. System Context

```
┌─────────────┐      ┌──────────────────────┐      ┌─────────────────┐
│   Operator  │─────▶│  LinkedIn Auto        │─────▶│  LinkedIn       │
│  (you)      │      │  Connector Bot        │      │  (browser UI)    │
│             │      │  (Python + Selenium)   │      │                 │
└─────────────┘      └──────────────────────┘      └─────────────────┘
                              │
                              ▼
                     ┌──────────────────────┐
                     │  Firefox + Gecko     │
                     │  (real browser)      │
                     └──────────────────────┘
```

- **Operator:** Sets credentials, search link, message text, and max connection requests; runs the script.
- **Bot:** Drives the browser via Selenium, performs login and all UI steps.
- **LinkedIn:** Renders the site and the invite popup (including content inside **Shadow DOM**), which the bot must interact with without “seeing” the DOM from Python in the usual way.

---

## 3. End-to-End Flow (Conceptual)

```
START
  │
  ├─▶ 1. Start browser (Firefox / Geckodriver)
  │
  ├─▶ 2. LOGIN
  │       • Open LinkedIn login page
  │       • Fill username & password, submit
  │       • Wait for feed (or manual CAPTCHA if required)
  │
  ├─▶ 3. OPEN SEARCH
  │       • Navigate to SEARCH_LINK (People search URL)
  │       • Scroll down to load results
  │
  └─▶ 4. MAIN LOOP (until limit or no more pages)
          │
          ├─▶ 4a. Find all visible "Connect" buttons (by index)
          │
          ├─▶ 4b. For each Connect (up to MAX_CONNECT_REQUESTS):
          │         • Resolve click target (ancestor <a> or button)
          │         • Scroll into view, click Connect
          │         • Wait for invite popup to appear
          │         • INVITE FLOW (see below)
          │         • Count sent, optional delay
          │
          ├─▶ 4c. Process "Follow" buttons (if any)
          │
          └─▶ 4d. Go to next page (if available); else exit loop
  │
  ▼
END (browser closed)
```

---

## 4. Invite Flow (Add Note + Send) — Core Logic

After clicking **Connect**, LinkedIn shows a **same-page popup** (modal) with:

- **“Add a note”** button  
- (After clicking it) A **message textarea**  
- **“Send” / “Send invitation”** button  

This popup is often rendered **inside Shadow DOM** (`#interop-outlet` / `#interoop-outlet`), so normal Selenium locators from the main document do not see its elements. The design therefore uses **JavaScript executed in the page** to find and click inside both the **document** and the **shadow root**.

### 4.1 Invite flow — steps

1. **Click Connect**  
   Resolve the real click target from the “Connect” span (prefer ancestor `<a href="...invite...">`, else ancestor button/span), scroll into view, click (with JS fallback if intercepted).

2. **Wait for popup**  
   Fixed short wait (e.g. 2s) so the modal has time to render.

3. **Run “invite” flow in JavaScript (primary path)**  
   - **Step A — Click “Add a note”:**  
     In JS, search **document** and **shadow root** for the “Add a note” button (multiple selectors: `[data-test-modal-id='send-invite-modal'] button[aria-label='Add a note']`, `div.artdeco-modal-overlay button[aria-label='Add a note']`, etc.). Click it.
   - **Step B — Wait**  
     Short sleep (e.g. 1.5s) so the textarea can appear.
   - **Step C — Fill and send:**  
     In JS, find the message **textarea** (again in document + shadow), set `value`, dispatch `input` event, then find **Send** button and click it.

   This is retried a small number of times (e.g. 4 attempts with 2s wait between) so that slow or shadow-DOM-rendered popups are still handled.

4. **Fallback (if JS flow fails)**  
   Use Selenium + a helper that runs JS to **find** elements in document or shadow and return them; then from Python call `.click()`, `.send_keys()`, etc. This path can still fail if the host returns elements that Selenium cannot interact with from the driver.

### 4.2 Why JavaScript in the browser?

- **Shadow DOM:** Content inside `#interop-outlet` (or similar) is not in the main document. Selenium’s standard `find_element` does not cross shadow boundaries. Running `document.querySelector(...)` and `host.shadowRoot.querySelector(...)` inside the page allows the script to see and click “Add a note”, the textarea, and Send.
- **No element round-trip:** The bot never has to pass Shadow DOM nodes back to Python; all interaction is done inside a single `execute_script` (or a few), which avoids serialization and staleness issues.

---

## 5. Main Components (Logical View)

| Component | Responsibility |
|-----------|----------------|
| **Browser setup** | Create Firefox WebDriver (Geckodriver), optional env-based paths for binary and driver. |
| **Login** | Load login page, fill credentials, submit, wait for feed (or CAPTCHA). |
| **Navigation** | Open `SEARCH_LINK`, scroll to load results, go to next page (multiple selectors for “Next”, check disabled state). |
| **Connect discovery** | Find visible “Connect” spans; re-query by **index** each time to avoid stale references when processing the list. |
| **Connect handler** | For one Connect: resolve click target, click, then run invite flow (JS primary, Selenium fallback). |
| **Shadow/DOM helpers** | `_find_visible_element_in_dom_or_shadow`: run JS that searches document + shadow root with a list of CSS selectors and returns the first visible element. Used for modal detection and fallback. |
| **JS invite flow** | `_click_add_note_in_js`, `_fill_and_send_invite_in_js`, `_do_invite_flow_in_js`: run scripts that find and click “Add a note”, then find textarea and Send, set message, click Send (all inside document + shadow). |
| **Modal detection** | `_invite_modal_visible`: uses the same “document + shadow” JS to see if any known modal/button/textarea is present (for optional future use; current flow relies on fixed wait + retries). |
| **Follow handler** | Click “Follow” buttons (no note). |
| **Process loop** | Orchestrates: get search page, collect Connect/Follow by index, process Connect (with limit), process Follow, next page, refresh/scroll as needed. |
| **Config** | Credentials, `SEARCH_LINK`, `BASE_CONNECTION_MESSAGE`, `MAX_CONNECT_REQUESTS`, retry counts and timeouts. |

---

## 6. Key Technical Decisions

| Decision | Reason |
|----------|--------|
| **Run invite flow in JS (document + shadow)** | LinkedIn’s invite popup can live in Shadow DOM; Selenium cannot target it with normal locators. JS in the page can query both document and `host.shadowRoot`. |
| **Multiple CSS selectors per element** | LinkedIn’s markup can vary (e.g. `data-test-modal-id`, `artdeco-modal-overlay`, `role="dialog"`). Trying several selectors in order increases robustness. |
| **Connect by index** | Re-finding “Connect” by index on each iteration avoids stale element references after DOM updates and ensures we click the intended profile. |
| **Prefer ancestor `<a href="...invite...">` for Connect** | On People search, the real action is often on a link; clicking it opens the invite flow. |
| **Fixed wait + retries for invite flow** | Modal may appear with a delay or be in shadow; running the JS flow several times with short waits is simpler and more reliable than depending on a single “modal visible” check. |
| **Firefox + Geckodriver** | Matches project choice; driver and binary paths can be overridden via environment variables for different setups. |

---

## 7. Configuration & Limits

- **Credentials:** `LINKEDIN_USERNAME`, `LINKEDIN_PASSWORD` (script variables; moving to env is recommended for security).
- **Search:** `SEARCH_LINK` — full URL of a LinkedIn People search (e.g. with keywords, filters).
- **Message:** `BASE_CONNECTION_MESSAGE` — text inserted into the “Add a note” textarea.
- **Limit:** `MAX_CONNECT_REQUESTS` — stop sending connection requests after this many (per run).
- **Optional env:** `FIREFOX_BINARY_PATH`, `GECKODRIVER_PATH` for browser and driver location.

Respecting LinkedIn’s practical limits (e.g. ~80–100 invites per week) is the operator’s responsibility; the bot only enforces `MAX_CONNECT_REQUESTS` per run.

---

## 8. Error Handling & Robustness

- **Login:** Waits for feed URL; if CAPTCHA appears, the script assumes manual resolution (no automatic solve).
- **Connect click:** If normal click is intercepted, falls back to `execute_script("arguments[0].click();", element)`.
- **Invite flow:** Primary path is JS (multiple attempts); on failure, fallback uses Selenium + shadow-aware find; exceptions are caught and logged so one failed Connect does not stop the whole run.
- **Next page:** Several XPath/selectors for “Next”, check for disabled state; exit loop if no next page or button disabled.
- **Stale elements:** Connect buttons are re-queried by index for each iteration to avoid using stale references.

---

## 9. Flow Diagram (Invite Sub-Flow)

```
                    ┌─────────────────┐
                    │ Click Connect    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Wait ~2s         │
                    └────────┬────────┘
                             │
         ┌───────────────────┴───────────────────┐
         │  JS: document + shadowRoot            │
         │  Find "Add a note" → click             │
         └───────────────────┬───────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Wait ~1.5s      │
                    └────────┬────────┘
                             │
         ┌───────────────────┴───────────────────┐
         │  JS: Find textarea → set value +      │
         │  input event → Find Send → click      │
         └───────────────────┬───────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │ Success?                     │
              │  Yes → log & return          │
              │  No  → retry (up to N times) │
              │  Else → Selenium fallback     │
              └──────────────────────────────┘
```

---

## 10. File / Entrypoint

- **Main script:** `Linkedin_auto_connector_bot.py`  
  - Sets up driver, calls `login_to_linkedin`, then `process_buttons`; closes driver in `finally`.
- **Supporting docs:** `README.md`, `CLAUDE.md`; this document lives under `docs/HIGH_LEVEL_DESIGN.md`.

This high-level design should be enough to understand the full working concept: login → search → for each Connect, open the invite popup and complete “Add a note” + message + Send via JS in document and shadow DOM, then paginate until the limit or end of results.
