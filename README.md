# Naukri Resume Refresh

Downloads the existing resume PDF from Google Drive and attempts to update the Naukri profile through Naukri's website UI using Playwright and **Naukri username/password** credentials.

## GitHub Actions secrets

In **Settings → Secrets and variables → Actions**, configure:

| Secret | Purpose |
| --- | --- |
| `NAUKRI_USERNAME` | Naukri account username/email (not a Google password) |
| `NAUKRI_PASSWORD` | Password accepted by Naukri's own username/password login |
| `GOOGLE_DRIVE_FILE_ID` | ID of the existing resume PDF in Google Drive |
| `NAUKRI_TOTP_SECRET` | Optional; only if Naukri explicitly supports authenticator-app TOTP for the account |

Do not put credentials in source code, workflow inputs, logs, or chat. The script does not print credentials, cookies, OTPs, or page contents.

## Important Google sign-in limitation

If your account uses **Continue with Google only**, the Google password generally cannot be submitted to Naukri's separate username/password form. Configure `NAUKRI_USERNAME` and `NAUKRI_PASSWORD` only if those credentials work with Naukri's own login form. The workflow does not automate Google OAuth.

GitHub-hosted Actions runners are unattended. If Naukri requests email/SMS OTP, CAPTCHA, or a human security challenge, the run stops without uploading. If Naukri explicitly supports authenticator-app TOTP, you may configure `NAUKRI_TOTP_SECRET`. Never use it for email/SMS OTP. A run may also fail if Naukri rejects automated/headless browser access or changes its UI.

Remove obsolete `NAUKRI_STORAGE_STATE_B64`, `NAUKRI_COOKIES`, and `NAUKRI_FORM_KEY` secrets once you no longer need them. Since session values were previously shared in chat, revoke/sign out those sessions where possible.

## Schedule

GitHub cron uses UTC; the workflow preserves the intended daily schedule:

- **01:00 IST** — `30 19 * * 0-6` (previous UTC day)
- **07:00 IST** — `30 1 * * 0-6`
- **12:00 IST** — `30 6 * * 0-6`

Manual run: **Actions → Naukri Resume Refresh (IST Schedule) → Run workflow**.

## Success verification

A run is successful only if the Naukri profile page displays a recognized resume-update confirmation or, after reloading, the uploaded filename. A login attempt, button click, or HTTP response alone is not proof of a successful upload. Check the Naukri profile manually before relying on the schedule.

## Troubleshooting

- **Missing secret:** Add the exact secret name shown above.
- **Login form unavailable:** Confirm Naukri offers username/password login for this account; a Google-only account cannot use this method without Naukri credentials.
- **OTP required:** Email/SMS OTP cannot be entered interactively into a hosted runner. The workflow stops safely.
- **CAPTCHA/security challenge:** The workflow stops; do not bypass it.
- **Upload unverified:** Check the profile manually before rerunning to avoid unnecessary duplicate uploads.

## Security

Restrict repository write access because users with write access may be able to use repository Actions secrets. This is unofficial personal automation and depends on Naukri's current UI and policies.
