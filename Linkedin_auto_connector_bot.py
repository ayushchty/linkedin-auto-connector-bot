"""
LinkedIn Auto Connector Bot - Selenium-based automation for connection requests.
Set credentials via environment variables or edit the constants below.
"""

import logging
import os
import time
from shutil import which

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Load .env if available (pip install python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Credentials: set in .env or environment, or assign here for local use
LINKEDIN_USERNAME = os.getenv("LINKEDIN_USERNAME", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

MAX_RETRIES = 5
SEARCH_LINK = os.getenv(
    "SEARCH_LINK",
    "https://www.linkedin.com/search/results/people/?keywords=recruiter&origin=FACETED_SEARCH",
)
BASE_CONNECTION_MESSAGE = os.getenv(
    "CONNECTION_MESSAGE",
    "Hi, I'd like to connect with you.",
)
MAX_CONNECT_REQUESTS = int(os.getenv("MAX_CONNECT_REQUESTS", "10"))

def login_to_linkedin(driver, username, password):
    try:
        driver.get("https://www.linkedin.com/login")
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "username")))

        # Enter username
        username_field = driver.find_element(By.ID, "username")
        username_field.send_keys(username)

        # Enter password
        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(password)
        password_field.send_keys(Keys.RETURN)
        time.sleep(5)  # Wait for the page to load or enter captcha
        WebDriverWait(driver, 20).until(EC.url_contains("/feed"))
        logging.info("Successfully logged into LinkedIn.")
        time.sleep(5)  # Wait for the feed to load
    except Exception as e:
        logging.error(f"Error during LinkedIn login: {e}")

def go_to_next_page(driver):
    try:
        time.sleep(5)  # Wait for the page to load
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # Scroll down
        next_page_button = None
        next_selectors = (
            "//button[@aria-label='Next']",
            "//button[contains(@class,'artdeco-pagination__button--next')]",
            "//button[.//span[normalize-space(text())='Next']]",
            "//a[@aria-label='Next']",
            "//a[.//span[normalize-space(text())='Next']]",
        )
        for xpath in next_selectors:
            try:
                candidate = driver.find_element(By.XPATH, xpath)
                if candidate.is_displayed():
                    next_page_button = candidate
                    break
            except NoSuchElementException:
                continue

        if not next_page_button:
            logging.info("Next page button not found.")
            return False

        aria_disabled = (next_page_button.get_attribute("aria-disabled") or "").lower()
        disabled_attr = next_page_button.get_attribute("disabled")
        if aria_disabled == "true" or disabled_attr is not None:
            logging.info("Next page button is disabled.")
            return False

        try:
            next_page_button.click()
        except Exception:
            driver.execute_script("arguments[0].click();", next_page_button)
        logging.info("Navigated to the next page")
        time.sleep(5)  # Wait for the new page to load
    except NoSuchElementException as e:
        logging.error(f"Element not found: {e}")
        return False
    except Exception as e:
        logging.error(f"Error navigating to the next page: {e}")
        return False
    return True

def scroll_down(driver):
    """Scroll to bottom of page to load lazy content."""
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)
    except Exception as e:
        logging.error("Error during scroll: %s", e)

def _find_visible_element_in_dom_or_shadow(driver, css_selectors):
    """
    LinkedIn sometimes renders invite modals inside #interop-outlet / #interoop-outlet shadow DOM.
    Search both document and that shadow root, returning the first visible element.
    """
    script = """
        const selectors = arguments[0];
        const contexts = [document];
        const host = document.querySelector('#interop-outlet, #interoop-outlet, [data-testid="interop-shadowdom"], [data-testid="interoop-shadowdom"]');
        if (host && host.shadowRoot) {
            contexts.push(host.shadowRoot);
        }

        const isVisible = (el) => {
            if (!el) return false;
            const style = window.getComputedStyle(el);
            if (!style) return false;
            if (style.display === 'none' || style.visibility === 'hidden') return false;
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        };

        for (const ctx of contexts) {
            for (const sel of selectors) {
                let el = null;
                try {
                    el = ctx.querySelector(sel);
                } catch (e) {
                    el = null;
                }
                if (isVisible(el)) return el;
            }
        }
        return null;
    """
    return driver.execute_script(script, css_selectors)

def _invite_modal_visible(driver):
    modal_selectors = [
        "[data-test-modal-id='send-invite-modal']",
        "div.artdeco-modal-overlay",
        "div.send-invite[role='dialog']",
        "div.send-invite",
        "div[aria-labelledby='send-invite-modal']",
        "div[role='dialog']",
        "button[aria-label='Add a note']",
        "textarea[name='message']",
    ]
    return _find_visible_element_in_dom_or_shadow(driver, modal_selectors) is not None


def _click_add_note_in_js(driver):
    """Click 'Add a note' inside modal (document or shadow DOM). Returns True if clicked."""
    script = """
        const contexts = [document];
        const host = document.querySelector('#interop-outlet, #interoop-outlet, [data-testid="interop-shadowdom"], [data-testid="interoop-shadowdom"]');
        if (host && host.shadowRoot) contexts.push(host.shadowRoot);
        const isVisible = (el) => {
            if (!el) return false;
            const s = window.getComputedStyle(el);
            return s.display !== 'none' && s.visibility !== 'hidden' &&
                el.getBoundingClientRect().width > 0 && el.getBoundingClientRect().height > 0;
        };
        const find = (selectors) => {
            for (const ctx of contexts)
                for (const sel of selectors) {
                    try {
                        const el = ctx.querySelector(sel);
                        if (el && isVisible(el)) return el;
                    } catch (e) {}
                }
            return null;
        };
        const addNote = find([
            "[data-test-modal-id='send-invite-modal'] button[aria-label='Add a note']",
            "div.artdeco-modal-overlay button[aria-label='Add a note']",
            "div[role='dialog'] button[aria-label='Add a note']",
            "button[aria-label='Add a note']", "button[aria-label='Add note']"
        ]);
        if (addNote) { addNote.click(); return true; }
        return false;
    """
    try:
        return driver.execute_script(script) is True
    except Exception:
        return False


def _fill_and_send_invite_in_js(driver, message):
    """Find textarea and Send in modal (document or shadow DOM), fill and click. Returns True on success."""
    script = """
        const message = arguments[0];
        const contexts = [document];
        const host = document.querySelector('#interop-outlet, #interoop-outlet, [data-testid="interop-shadowdom"], [data-testid="interoop-shadowdom"]');
        if (host && host.shadowRoot) contexts.push(host.shadowRoot);
        const isVisible = (el) => {
            if (!el) return false;
            const s = window.getComputedStyle(el);
            return s.display !== 'none' && s.visibility !== 'hidden' &&
                el.getBoundingClientRect().width > 0 && el.getBoundingClientRect().height > 0;
        };
        const find = (selectors) => {
            for (const ctx of contexts)
                for (const sel of selectors) {
                    try {
                        const el = ctx.querySelector(sel);
                        if (el && isVisible(el)) return el;
                    } catch (e) {}
                }
            return null;
        };
        const textarea = find([
            "[data-test-modal-id='send-invite-modal'] textarea[name='message']",
            "[data-test-modal-id='send-invite-modal'] textarea",
            "div.artdeco-modal-overlay textarea[name='message']",
            "div[role='dialog'] textarea[name='message']", "div[role='dialog'] textarea",
            "textarea[name='message']", "textarea"
        ]);
        if (!textarea) return false;
        textarea.focus();
        textarea.value = message;
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
        const sendBtn = find([
            "[data-test-modal-id='send-invite-modal'] button[aria-label='Send invitation']",
            "[data-test-modal-id='send-invite-modal'] button[aria-label='Send']",
            "div.artdeco-modal-overlay button[aria-label='Send invitation']",
            "div[role='dialog'] button[aria-label='Send invitation']",
            "button[aria-label='Send invitation']", "button[aria-label='Send']"
        ]);
        if (!sendBtn) return false;
        sendBtn.click();
        return true;
    """
    try:
        return driver.execute_script(script, message) is True
    except Exception:
        return False


def _do_invite_flow_in_js(driver, message):
    """Click Add a note, wait, then fill and send. No Selenium element refs; works in shadow DOM."""
    _click_add_note_in_js(driver)
    time.sleep(1.5)
    if _fill_and_send_invite_in_js(driver, message):
        return True
    time.sleep(1)
    return _fill_and_send_invite_in_js(driver, message)

def _get_connect_button_by_index(driver, index):
    """Re-query visible Connect spans and return the one at index, or None."""
    spans = driver.find_elements(By.XPATH, "//span[normalize-space(text())='Connect']")
    visible = [s for s in spans if s.is_displayed()]
    if 0 <= index < len(visible):
        return visible[index]
    return None


def handle_connect_button_with_retry(driver, button, connect_index=0):
    """
    Click a "Connect" control robustly, handling overlay and timing issues,
    then add the configured note and send the invitation.
    connect_index: used to re-find the same Connect on retry (avoids stale refs and wrong link).
    """
    try:
        # Resolve click target from the Connect span (ancestor <a> or button)
        click_target = None
        try:
            click_target = button.find_element(
                By.XPATH,
                "./ancestor::a[contains(@href,'invite') or contains(@href,'preload') or contains(@href,'custom-invite')][1]",
            )
        except NoSuchElementException:
            pass
        if not click_target:
            try:
                click_target = button.find_element(By.XPATH, "./ancestor::button[1]")
            except NoSuchElementException:
                try:
                    click_target = button.find_element(
                        By.XPATH, "./ancestor::*[self::span or self::div][1]"
                    )
                except NoSuchElementException:
                    click_target = button

        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
            click_target,
        )
        time.sleep(1)

        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(click_target))
            click_target.click()
        except ElementClickInterceptedException:
            logging.warning("Element click intercepted, using JavaScript click fallback")
            driver.execute_script("arguments[0].click();", click_target)

        # Give the popup a moment to appear, then try the full flow in JS a few times.
        # This works even if the modal lives in shadow DOM and our detection misses it.
        for attempt in range(4):
            time.sleep(2)
            if _do_invite_flow_in_js(driver, BASE_CONNECTION_MESSAGE):
                logging.info("Sent connection request with a custom note.")
                time.sleep(2)
                return
        logging.warning("JS invite flow could not find 'Add a note' / message / Send; falling back to Selenium locators.")

        # Fallback: find elements from Python (may fail if modal is in shadow DOM)
        message_box = _find_visible_element_in_dom_or_shadow(
            driver,
            [
                "div.send-invite textarea[name='message']",
                "div.send-invite textarea",
                "div[role='dialog'] textarea[name='message']",
                "div[role='dialog'] textarea",
                "div.artdeco-modal textarea[name='message']",
                "textarea[name='message']",
                "textarea[id*='custom-message']",
                "textarea[id*='message']",
            ],
        )

        if not message_box or not message_box.is_displayed():
            # Need to click "Add a note" first
            add_note_el = _find_visible_element_in_dom_or_shadow(
                driver,
                [
                    "div.send-invite button[aria-label='Add a note']",
                    "div[role='dialog'] button[aria-label='Add a note']",
                    "div.artdeco-modal button[aria-label='Add a note']",
                    "button[aria-label='Add a note']",
                    "button[aria-label='Add note']",
                ],
            )
            if not add_note_el or not add_note_el.is_displayed():
                raise NoSuchElementException("Could not find 'Add a note' in modal")
            try:
                add_note_el.click()
            except Exception:
                driver.execute_script("arguments[0].click();", add_note_el)
            time.sleep(1)
            # Now find textarea
            WebDriverWait(driver, 8).until(
                lambda d: _find_visible_element_in_dom_or_shadow(
                    d,
                    [
                        "div.send-invite textarea[name='message']",
                        "div.send-invite textarea",
                        "div[role='dialog'] textarea[name='message']",
                        "div[role='dialog'] textarea",
                        "textarea[name='message']",
                        "textarea",
                    ],
                ) is not None
            )
            message_box = _find_visible_element_in_dom_or_shadow(
                driver,
                [
                    "div.send-invite textarea[name='message']",
                    "div.send-invite textarea",
                    "div[role='dialog'] textarea[name='message']",
                    "div[role='dialog'] textarea",
                    "textarea[name='message']",
                    "textarea",
                ],
            )
        if not message_box or not message_box.is_displayed():
            raise NoSuchElementException("Could not find visible message textarea")
        message_box.clear()
        message_box.send_keys(BASE_CONNECTION_MESSAGE)
        time.sleep(1)

        # Find and click Send – prefer inside dialog
        send_button = _find_visible_element_in_dom_or_shadow(
            driver,
            [
                "div.send-invite button[aria-label='Send invitation']",
                "div.send-invite button[aria-label='Send']",
                "div[role='dialog'] button[aria-label='Send invitation']",
                "div[role='dialog'] button[aria-label='Send']",
                "button[aria-label='Send invitation']",
                "button[aria-label='Send']",
            ],
        )
        if not send_button:
            raise NoSuchElementException("Could not find Send button")
        try:
            send_button.click()
        except Exception:
            driver.execute_script("arguments[0].click();", send_button)
        logging.info("Sent connection request with a custom note.")
        time.sleep(2)

    except Exception as e:
        logging.error(f"Error handling 'Connect' button: {e}")

def handle_follow_button(button):
    try:
        button.click()
        logging.info("Followed the user.")
        time.sleep(1)
    except Exception as e:
        logging.error(f"Error handling 'Follow' button: {e}")

def process_buttons(driver):
    try:
        # Navigate to the search page
        driver.get(SEARCH_LINK)
        scroll_down(driver)
        time.sleep(5)

        connect_requests_sent = 0

        working = True


        while working:
            # Find Connect/Follow controls by inner span text.
            # On LinkedIn, the clickable surface may be a span/div/button;
            # clicking the inner span is usually sufficient to trigger the action.
            connect_buttons = driver.find_elements(
                By.XPATH,
                "//span[normalize-space(text())='Connect']"
            )
            connect_buttons = [btn for btn in connect_buttons if btn.is_displayed()]
            follow_buttons = driver.find_elements(
                By.XPATH,
                "//span[normalize-space(text())='Follow']"
            )
            follow_buttons = [btn for btn in follow_buttons if btn.is_displayed()]

            logging.info(f"Total 'Connect' buttons on the page: {len(connect_buttons)}")
            logging.info(f"Total 'Follow' buttons on the page: {len(follow_buttons)}")

            # Process "Connect" buttons by index so we can re-find fresh refs and avoid stale elements
            num_connect = len(connect_buttons)
            for connect_index in range(num_connect):
                if connect_requests_sent >= MAX_CONNECT_REQUESTS:
                    logging.info(
                        f"Reached the limit of {MAX_CONNECT_REQUESTS} connection requests. Stopping connection requests."
                    )
                    working = False
                    break

                button = _get_connect_button_by_index(driver, connect_index)
                if not button:
                    continue
                handle_connect_button_with_retry(driver, button, connect_index)
                connect_requests_sent += 1
                time.sleep(5)

            # Then process "Follow" buttons
            for button in follow_buttons:
                handle_follow_button(button)
                time.sleep(5)

            # Attempt to navigate to the next page
            if not go_to_next_page(driver):
                logging.info("No more pages to process. Exiting.")
                break

            scroll_down(driver)
            time.sleep(5)

    except Exception as e:
        logging.error(f"Error while processing buttons: {e}")


def refresh_page(driver, retries):
    for attempt in range(1, retries + 1):
        try:
            logging.info(f"Attempt {attempt}/{retries}: Refreshing the page.")
            driver.refresh()  # Refresh the page
            time.sleep(5)  # Wait for the page to reload
            return True
        except Exception as e:
            logging.error(f"Error during page refresh: {e}")

        if attempt == retries:
            logging.error("Maximum retries reached. Exiting the program.")
            driver.quit()
            exit(1)
    return False


if __name__ == "__main__":
    if not LINKEDIN_USERNAME or not LINKEDIN_PASSWORD:
        raise SystemExit(
            "Set LINKEDIN_USERNAME and LINKEDIN_PASSWORD in .env or environment."
        )

    options = Options()
    firefox_binary = os.getenv("FIREFOX_BINARY_PATH")
    if firefox_binary and os.path.isfile(firefox_binary):
        options.binary_location = firefox_binary
    # else: leave unset so geckodriver finds Firefox (e.g. /Applications/Firefox.app on macOS)

    # Determine geckodriver path:
    # - Prefer GECKODRIVER_PATH env var if it points to an existing file
    # - On Windows, fall back to bundled 'geckodriver32.exe'
    # - Otherwise, use system-installed 'geckodriver' on PATH
    geckodriver_path = os.getenv("GECKODRIVER_PATH")
    if geckodriver_path and not os.path.isfile(geckodriver_path):
        geckodriver_path = None  # env path missing, try fallbacks
    if not geckodriver_path:
        if os.name == "nt":
            bundled = os.path.join(os.path.dirname(__file__), "geckodriver32.exe")
            geckodriver_path = bundled if os.path.isfile(bundled) else which("geckodriver")
        else:
            geckodriver_path = which("geckodriver")

    if not geckodriver_path or not os.path.isfile(geckodriver_path):
        raise RuntimeError(
            "Could not find geckodriver. Install it (e.g. brew install geckodriver on macOS) "
            "and add it to PATH, or set GECKODRIVER_PATH in .env to its full path."
        )

    service = Service(geckodriver_path)
    driver = webdriver.Firefox(service=service, options=options)

    try:
        login_to_linkedin(driver, LINKEDIN_USERNAME, LINKEDIN_PASSWORD)
        process_buttons(driver)
    finally:
        driver.quit()
