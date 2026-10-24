"""Browser-based Naukri resume updater using a pre-authenticated Playwright session.

The Google sign-in is completed manually in a trusted browser. The workflow restores
the exported Playwright storage state and stops if Naukri no longer accepts it.
"""
import base64
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.naukri.com"
PROFILE_URL = f"{BASE_URL}/mnjuser/profile"


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required GitHub Actions secret: {name}")
    return value


def download_resume(file_id: str, destination: Path) -> None:
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = requests.get(url, timeout=45)
    response.raise_for_status()
    if not response.content.startswith(b"%PDF"):
        raise RuntimeError(
            "Google Drive did not return a PDF. Check GOOGLE_DRIVE_FILE_ID and "
            "ensure the existing resume file is accessible to the workflow."
        )
    destination.write_bytes(response.content)


def visible(locator) -> bool:
    try:
        return locator.count() > 0 and locator.first.is_visible()
    except Exception:
        return False


def find_first_visible(page, selectors):
    for selector in selectors:
        locator = page.locator(selector)
        if visible(locator):
            return locator.first
    return None


def load_storage_state(encoded_state: str) -> dict:
    try:
        decoded = base64.b64decode(encoded_state, validate=True)
        state = json.loads(decoded)
    except Exception as exc:
        raise RuntimeError(
            "NAUKRI_STORAGE_STATE_B64 is not valid base64-encoded Playwright storage-state JSON."
        ) from exc
    if not isinstance(state, dict) or not isinstance(state.get("cookies"), list):
        raise RuntimeError(
            "Storage state format is invalid. Export it from Playwright after signing in to Naukri."
        )
    return state


def verify_authenticated_session(page) -> None:
    page.goto(PROFILE_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)
    current_url = page.url.lower()
    body = page.locator("body").inner_text(timeout=15000).lower()
    if "nlogin" in current_url or "/login" in current_url or "continue with google" in body:
        raise RuntimeError(
            "Saved browser session is no longer authenticated or was rejected. "
            "Sign in to Naukri with Google in a trusted browser, export fresh storage state, "
            "and update NAUKRI_STORAGE_STATE_B64. No upload was attempted."
        )
    if any(marker in body for marker in ["captcha", "verify you are human", "security challenge"]):
        raise RuntimeError("Naukri presented a CAPTCHA/security challenge. Stopped without uploading.")


def upload_and_verify(page, pdf_path: Path, filename: str) -> None:
    page.goto(PROFILE_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)

    file_input = page.locator('input[type="file"]')
    if file_input.count() == 0:
        update_button = find_first_visible(page, [
            'button:has-text("Update resume")',
            'a:has-text("Update resume")',
            'button:has-text("Upload resume")',
            'a:has-text("Upload resume")',
            'text=Update resume',
        ])
        if update_button:
            update_button.click()
            page.wait_for_timeout(800)
        file_input = page.locator('input[type="file"]')

    if file_input.count() == 0:
        raise RuntimeError(
            "Could not find the resume upload control on the profile page. "
            "Naukri's UI may have changed; no upload was attempted."
        )

    file_input.first.set_input_files(str(pdf_path))
    page.wait_for_timeout(2500)

    submit = find_first_visible(page, [
        'button:has-text("Upload")',
        'button:has-text("Update")',
        'button:has-text("Save")',
        'button:has-text("Submit")',
    ])
    if submit:
        submit.click()
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeoutError:
        pass
    page.wait_for_timeout(2500)

    body = page.locator("body").inner_text(timeout=15000)
    lower = body.lower()
    success_markers = [
        "resume updated successfully",
        "resume uploaded successfully",
        "resume has been updated",
        "resume has been uploaded",
        "successfully updated your resume",
    ]
    if not any(marker in lower for marker in success_markers):
        page.reload(wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)
        body = page.locator("body").inner_text(timeout=15000)
        if filename.lower() not in body.lower():
            raise RuntimeError(
                "Upload was submitted, but the page did not show a recognized success "
                "message or the uploaded filename after reload. Treat this run as UNVERIFIED; "
                "check the Naukri profile manually before retrying."
            )


def main() -> int:
    encoded_state = required_env("NAUKRI_STORAGE_STATE_B64")
    file_id = required_env("GOOGLE_DRIVE_FILE_ID")
    storage_state = load_storage_state(encoded_state)

    filename = f"resume_{datetime.now().strftime('%d_%b_%Y').lower()}.pdf"
    with tempfile.TemporaryDirectory(prefix="naukri-resume-") as temp_dir:
        pdf_path = Path(temp_dir) / filename
        download_resume(file_id, pdf_path)
        print(f"[OK] Resume source downloaded and PDF signature validated ({pdf_path.stat().st_size:,} bytes).")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=storage_state, accept_downloads=False)
            page = context.new_page()
            page.set_default_timeout(12000)
            try:
                verify_authenticated_session(page)
                print("[OK] Saved browser session appears authenticated.")
                upload_and_verify(page, pdf_path, filename)
                print(f"[VERIFIED] Naukri page confirmed the resume update: {filename}")
            finally:
                context.close()
                browser.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Never print secrets, cookies, browser state, or page contents.
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
