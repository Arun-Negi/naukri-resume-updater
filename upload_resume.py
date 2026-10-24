"""Browser-based Naukri resume updater using Naukri username/password login.

Stops safely if login requires an unsupported OTP, CAPTCHA, or security challenge.
Never logs credentials, OTPs, cookies, or page contents.
"""
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.naukri.com"
LOGIN_URL = f"{BASE_URL}/nlogin/login"
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


def login(page, username: str, password: str, totp_secret: str | None) -> None:
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)

    user_field = find_first_visible(page, [
        'input[placeholder*="Email" i]',
        'input[placeholder*="username" i]',
        'input[name="email"]',
        'input[type="email"]',
        'input[type="text"]',
    ])
    pass_field = find_first_visible(page, [
        'input[placeholder*="Password" i]',
        'input[name="password"]',
        'input[type="password"]',
    ])
    if not user_field or not pass_field:
        raise RuntimeError(
            "Could not identify Naukri's username/password form. The page may require "
            "Continue with Google, CAPTCHA, or a changed login flow. No upload was attempted."
        )

    user_field.fill(username)
    pass_field.fill(password)

    submit = find_first_visible(page, [
        'button:has-text("Login")',
        'button:has-text("Sign in")',
        'button[type="submit"]',
    ])
    if not submit:
        raise RuntimeError("Could not identify the login button; no upload was attempted.")
    submit.click()
    page.wait_for_timeout(2500)

    otp_field = find_first_visible(page, [
        'input[autocomplete="one-time-code"]',
        'input[placeholder*="OTP" i]',
        'input[name*="otp" i]',
        'input[id*="otp" i]',
    ])
    if otp_field:
        if not totp_secret:
            raise RuntimeError(
                "Naukri requires OTP. GitHub Actions cannot receive a live email/SMS OTP "
                "interactively. If Naukri explicitly supports authenticator-app TOTP, add "
                "NAUKRI_TOTP_SECRET as a GitHub Actions secret. Otherwise, this unattended "
                "run cannot continue. No resume upload was attempted."
            )
        import pyotp
        otp_field.fill(pyotp.TOTP(totp_secret).now())
        otp_submit = find_first_visible(page, [
            'button:has-text("Verify")',
            'button:has-text("Submit")',
            'button:has-text("Continue")',
            'button[type="submit"]',
        ])
        if not otp_submit:
            raise RuntimeError("OTP field found but verification button was not found.")
        otp_submit.click()
        page.wait_for_timeout(3000)

    body = page.locator("body").inner_text(timeout=15000).lower()
    if any(marker in body for marker in ["captcha", "verify you are human", "security challenge"]):
        raise RuntimeError("Naukri presented a CAPTCHA/security challenge. Stopped without uploading.")
    if find_first_visible(page, [
        'input[autocomplete="one-time-code"]',
        'input[placeholder*="OTP" i]',
        'input[name*="otp" i]',
        'input[id*="otp" i]',
    ]):
        raise RuntimeError("OTP was not accepted or another OTP is required. No upload was attempted.")

    page.goto(PROFILE_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)
    if "login" in page.url.lower() or "nlogin" in page.url.lower():
        raise RuntimeError(
            "Naukri did not establish a signed-in session. Check that these are Naukri "
            "credentials (not Google credentials) and review the account's login options. "
            "No upload was attempted."
        )


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
    username = required_env("NAUKRI_USERNAME")
    password = required_env("NAUKRI_PASSWORD")
    file_id = required_env("GOOGLE_DRIVE_FILE_ID")
    totp_secret = os.getenv("NAUKRI_TOTP_SECRET", "").replace(" ", "").strip() or None

    filename = f"resume_{datetime.now().strftime('%d_%b_%Y').lower()}.pdf"
    with tempfile.TemporaryDirectory(prefix="naukri-resume-") as temp_dir:
        pdf_path = Path(temp_dir) / filename
        download_resume(file_id, pdf_path)
        print(f"[OK] Resume source downloaded and PDF signature validated ({pdf_path.stat().st_size:,} bytes).")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=False)
            page = context.new_page()
            page.set_default_timeout(12000)
            try:
                login(page, username, password, totp_secret)
                print("[OK] Naukri username/password session appears authenticated.")
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
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
