import requests
import urllib3
from io import BytesIO
from datetime import datetime
import os
import random
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

COOKIES = os.environ.get("NAUKRI_COOKIES", "")
FILE_ID = os.environ.get("GOOGLE_DRIVE_FILE_ID", "")
FORM_KEY = os.environ.get("NAUKRI_FORM_KEY", "")

HEADERS = {
    "accept": "application/json",
    "appid": "105",
    "clientid": "d3skt0p",
    "systemid": "jobseeker",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
}


def download_pdf(file_id):
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    resp = requests.get(url, verify=False)
    resp.raise_for_status()
    if resp.content[:4] != b'%PDF':
        raise Exception("Not a valid PDF or file not publicly shared")
    return resp.content


def parse_cookies(cookie_str):
    cookies = {}
    for pair in cookie_str.split(';'):
        if '=' in pair:
            k, v = pair.strip().split('=', 1)
            cookies[k.strip()] = v.strip()
    return cookies


def refresh_token(session, refresh_token_val):
    previous_token = session.cookies.get("nauk_at")
    try:
        resp = session.post(
            "https://www.naukri.com/central-login-services/v1/login/token/refresh",
            headers={**HEADERS, "content-type": "application/json"},
            json={"refreshToken": refresh_token_val},
            timeout=20,
            verify=False
        )
    except requests.RequestException as exc:
        print(f"[WARN] Token refresh request failed ({type(exc).__name__})")
        return None

    if resp.status_code != 200:
        # Do not print the response body: authentication responses may contain sensitive data.
        print(f"[WARN] Token refresh returned HTTP {resp.status_code}")
        return None

    refreshed_token = resp.cookies.get("nauk_at") or session.cookies.get("nauk_at")
    if refreshed_token and refreshed_token != previous_token:
        return refreshed_token

    print("[WARN] Refresh endpoint returned HTTP 200 but no new nauk_at cookie")
    return None


def get_profile_id(session, token):
    resp = session.get(
        "https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/dashboard",
        headers={**HEADERS, "authorization": f"Bearer {token}"},
        timeout=20,
        verify=False
    )
    if resp.status_code == 401:
        raise RuntimeError(
            "Naukri rejected the session token (HTTP 401). Refresh NAUKRI_COOKIES "
            "using a current browser session, then rerun the workflow. "
            "No resume upload was attempted."
        )
    resp.raise_for_status()
    data = resp.json()
    return data.get("dashBoard", {}).get("profileId") or data.get("profileId")


def upload_file(pdf_bytes, filename, form_key):
    file_key = "U" + ''.join(random.choice("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(13))
    resp = requests.post(
        "https://filevalidation.naukri.com/file",
        headers={"appid": "105", "systemid": "fileupload"},
        files={"file": (filename, BytesIO(pdf_bytes), "application/pdf")},
        data={"formKey": form_key, "fileName": filename, "fileKey": file_key},
        verify=False
    )
    resp.raise_for_status()
    return file_key


def attach_to_profile(session, token, profile_id, form_key, file_key):
    resp = session.post(
        f"https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/profiles/{profile_id}/advResume",
        headers={**HEADERS, "authorization": f"Bearer {token}", "content-type": "application/json", "x-http-method-override": "PUT"},
        json={"textCV": {"formKey": form_key, "fileKey": file_key, "textCvContent": None}},
        verify=False
    )
    resp.raise_for_status()


def main():
    if not all([COOKIES, FILE_ID, FORM_KEY]):
        print("Missing: NAUKRI_COOKIES, GOOGLE_DRIVE_FILE_ID, or NAUKRI_FORM_KEY")
        sys.exit(1)

    session = requests.Session()
    cookies = parse_cookies(COOKIES)
    for k, v in cookies.items():
        session.cookies.set(k, v, domain='.naukri.com')

    token = cookies.get("nauk_at")
    if cookies.get("nauk_rt"):
        new_token = refresh_token(session, cookies["nauk_rt"])
        if new_token:
            token = new_token
            print("[OK] Token refreshed")
        else:
            print("[WARN] Token refresh failed, trying existing nauk_at")

    if not token:
        print("No auth token available — update NAUKRI_COOKIES secret")
        sys.exit(1)

    try:
        profile_id = get_profile_id(session, token)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)
    print("[OK] Naukri session validated")
    if not profile_id:
        print("[ERROR] Naukri dashboard response did not contain a profile ID; stopping before upload.")
        sys.exit(1)
    print("[OK] Profile ID retrieved")

    pdf = download_pdf(FILE_ID)
    print(f"[OK] Downloaded PDF ({len(pdf):,} bytes)")

    filename = f"resume_{datetime.now().strftime('%d_%b_%Y').lower()}.pdf"
    file_key = upload_file(pdf, filename, FORM_KEY)
    print(f"[OK] Uploaded: {filename}")

    attach_to_profile(session, token, profile_id, FORM_KEY, file_key)
    print("[OK] Resume updated!")


if __name__ == "__main__":
    main()
