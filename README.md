# Naukri Resume Refresh

GitHub Actions downloads the existing resume PDF from Google Drive and attempts to update the Naukri profile through the website UI using Playwright. The workflow name is **Naukri Resume Refresh (IST Schedule)**.

## Google sign-in: one-time manual setup

This account uses **Continue with Google**. The workflow does not ask for or automate your Google password. Instead, sign in manually in a trusted browser and export a Playwright storage-state JSON after Naukri is signed in.

1. On your own computer, open a trusted browser and sign in to Naukri using **Continue with Google**.
2. Export the Playwright storage state for the signed-in Naukri session to a local JSON file. The file contains sensitive cookies/session data. Never commit it, attach it to an issue, or paste it into chat.
3. Base64-encode the JSON file locally, without adding line breaks, and add the resulting value as a repository **Actions secret** named `NAUKRI_STORAGE_STATE_B64`.
4. Keep `GOOGLE_DRIVE_FILE_ID` as a repository Actions secret pointing to the existing resume PDF.
5. Run the workflow manually once and inspect the run logs and your Naukri profile. If the session is rejected, refresh the state and update the secret.

Example local base64 encoding commands:

- macOS: `base64 < naukri-storage-state.json | tr -d '\\n' | pbcopy` (copies the encoded secret value to the clipboard)
- Linux: `base64 -w 0 naukri-storage-state.json`

Do not send the JSON or encoded secret to ChatGPT. Anyone who obtains the state may be able to reuse your authenticated session until it expires or is revoked. Restrict repository write access and rotate/sign out the session if it is exposed.

**Important limitation:** Google or Naukri may reject automated/headless sessions, bind sessions to a device/IP, require additional verification, or expire the session. This approach is not guaranteed to work unattended. The workflow stops on a detected login/security challenge and only reports success when the page confirms the resume update or the uploaded filename is visible after reload.

## GitHub Actions secrets

Configure these in **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Purpose |
| --- | --- |
| `NAUKRI_STORAGE_STATE_B64` | Base64-encoded Playwright storage-state JSON exported after signing in to Naukri with Google |
| `GOOGLE_DRIVE_FILE_ID` | ID of the existing resume PDF in Google Drive |

The resume source remains the existing Google Drive PDF. The script validates the downloaded PDF signature and does not print secret values, cookies, browser state, OTPs, or page contents.

Remove obsolete `NAUKRI_COOKIES`, `NAUKRI_FORM_KEY`, `NAUKRI_USERNAME`, `NAUKRI_PASSWORD`, and `NAUKRI_TOTP_SECRET` secrets once the new flow is configured and confirmed. Since session values were previously shared in chat, revoke/sign out those sessions where possible.

## Schedule

The workflow preserves the requested schedule. GitHub cron is UTC:

- **01:00 IST** — `30 19 * * 0-6` (previous UTC day)
- **07:00 IST** — `30 1 * * 0-6`
- **12:00 IST** — `30 6 * * 0-6`

To test manually: **Actions → Naukri Resume Refresh (IST Schedule) → Run workflow**.

## Success verification

A run is considered successful only when the profile page displays a recognized resume-update confirmation or, after reloading, the uploaded filename. A green run has not yet been demonstrated. Check the Naukri profile manually before relying on the schedule.

## Troubleshooting

- **Missing secret:** Add the exact secret name listed above.
- **Session rejected or expired:** Sign in again in a trusted browser and replace `NAUKRI_STORAGE_STATE_B64`.
- **CAPTCHA/security challenge:** The workflow stops; do not attempt to bypass it.
- **Upload control not found:** Naukri may have changed its UI; no upload is claimed.
- **Upload unverified:** Check the profile manually before rerunning to avoid unnecessary duplicate uploads.

## Security

Never commit credentials, OTPs, cookies, or Playwright storage state. Restrict repository write access because users with write access may be able to use repository Actions secrets. This is unofficial personal automation and depends on Naukri's current UI and policies.
