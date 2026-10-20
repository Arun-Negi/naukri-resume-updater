"""Update a Naukri resume using the configured workflow secrets.

Security notes:
- Keep credentials only in GitHub Actions secrets.
- TLS certificate verification stays enabled.
- This script depends on Naukri web endpoints that may change; stop and review
  the site's current terms and supported options if the workflow starts failing.
"""
import os
import random
import string
import sys
from datetime import datetime
from io import BytesIO

import requests

TIMEOUT = (10, 45)
MAX_PDF_BYTES = 10 * 1024 * 1024

COOKIES = os.environ.get("NAUKRI_COOKIES", "").strip()
FILE_ID = os.environ.get("GOOGLE_DRIVE_FILE_ID", "").strip()
FORM_KEY = os.environ.get("NAUKRI_FORM_KEY", "").strip()

HEADERS = {
    "accept": "application/json",
    "appid": "105",
    "clientid": "d3skt0p",
    "systemid": "jobseeker",
    "user-agent": "Mozilla/5.0 (compatible; ResumeUpdater/1.0)",
}


def checked_request(response):
    """Raise useful errors without printing response bodies or credentials."""
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"Request failed with HTTP {response.status_code} "
            f"for {response.url.split('?')[0]}"
        ) from exc
    return response


def download_pdf(file_id):
    url = "https://drive.google.com/uc"
    response = requests.get(
        url,
        params={"export": "download", "id": file_id},
        timeout=TIMEOUT,
    )
    checked_request(response)
    content = response.content
    if not content.startswith(b"%PDF-"):
        raise ValueError(
            "Downloaded content is not a PDF. Check the Drive file ID and "
            "sharing permissions."
        )
    if len(content) > MAX_PDF_BYTES:
        raise ValueError("PDF exceeds the configured 10 MiB safety limit.")
    if len(content) < 100:
        raise ValueError("Downloaded PDF is unexpectedly small.")
    return content


def parse_cookies(cookie_string):
    cookies = {}
    for pair in cookie_string.split(";"):
        if "=" in pair:
            key, value = pair.strip().split("=", 1)
            if key and value:
                cookies[key] = value
    return cookies


def refresh_token(session, refresh_token_value):
    response = session.post(
        "https://www.naukri.com/central-login-services/v1/login/token/refresh",
        headers={**HEADERS, "content-type": "application/json"},
        json={"refreshToken": refresh_token_value},
        timeout=TIMEOUT,
    )
    if response.status_code != 200:
        return None
    return session.cookies.get("nauk_at")


def get_profile_id(session, token):
    response = session.get(
        "https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/dashboard",
        headers={**HEADERS, "authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
    )
    checked_request(response)
    data = response.json()
    profile_id = data.get("dashBoard", {}).get("profileId") or data.get("profileId")
    if not profile_id:
        raise RuntimeError("Naukri response did not contain a profile ID.")
    return profile_id


def upload_file(pdf_bytes, filename, form_key):
    file_key = "U" + "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(13)
    )
    response = requests.post(
        "https://filevalidation.naukri.com/file",
        headers={"appid": "105", "systemid": "fileupload"},
        files={"file": (filename, BytesIO(pdf_bytes), "application/pdf")},
        data={"formKey": form_key, "fileName": filename, "fileKey": file_key},
        timeout=TIMEOUT,
    )
    checked_request(response)
    return file_key


def attach_to_profile(session, token, profile_id, form_key, file_key):
    response = session.post(
        "https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/profiles/{}/advResume".format(profile_id),
        headers={
            **HEADERS,
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "x-http-method-override": "PUT",
        },
        json={
            "textCV": {
                "formKey": form_key,
                "fileKey": file_key,
                "textCvContent": None,
            }
        },
        timeout=TIMEOUT,
    )
    checked_request(response)


def main():
    missing = [
        name for name, value in (
            ("NAUKRI_COOKIES", COOKIES),
            ("GOOGLE_DRIVE_FILE_ID", FILE_ID),
            ("NAUKRI_FORM_KEY", FORM_KEY),
        ) if not value
    ]
    if missing:
        print("Missing required GitHub Actions secret(s)/variable(s): " + ", ".join(missing))
        return 2

    cookies = parse_cookies(COOKIES)
    token = cookies.get("nauk_at")
    refresh_token_value = cookies.get("nauk_rt")
    if not token and not refresh_token_value:
        print("Cookie secret does not contain a supported Naukri auth token.")
        return 2

    with requests.Session() as session:
        for key, value in cookies.items():
            session.cookies.set(key, value, domain=".naukri.com")

        if refresh_token_value:
            try:
                refreshed = refresh_token(session, refresh_token_value)
            except requests.RequestException:
                refreshed = None
            if refreshed:
                token = refreshed
                print("[OK] Authentication token refreshed.")
            elif token:
                print("[WARN] Token refresh was unsuccessful; trying the existing token.")
            else:
                print("[ERROR] Token refresh failed. Refresh credentials through Naukri's normal sign-in flow.")
                return 1

        if not token:
            print("[ERROR] No usable authentication token is available.")
            return 1

        try:
            profile_id = get_profile_id(session, token)
            pdf = download_pdf(FILE_ID)
            filename = f"resume_{datetime.now().strftime('%d_%b_%Y').lower()}.pdf"
            file_key = upload_file(pdf, filename, FORM_KEY)
            attach_to_profile(session, token, profile_id, FORM_KEY, file_key)
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            print(f"[ERROR] Resume update failed: {exc}")
            return 1

    print(f"[OK] Resume update request completed ({filename}, {len(pdf):,} bytes).")
    print("Verify the resume on your Naukri profile; HTTP success alone may not confirm it is visible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
