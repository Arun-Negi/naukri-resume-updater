# Naukri Resume Auto-Updater

This workflow downloads the existing resume PDF from Google Drive and attempts to update the resume through Naukri's website UI using Playwright. It deliberately avoids the previous undocumented token-refresh/profile API calls.

## Important authentication limitation

GitHub-hosted Actions runners are unattended. The workflow can submit username/password credentials stored as GitHub Actions secrets. If Naukri asks for email/SMS OTP, CAPTCHA, or another human security challenge, the run stops without uploading. It does not bypass the challenge or claim success.

If Naukri explicitly offers authenticator-app TOTP for your account, you may optionally configure `NAUKRI_TOTP_SECRET`. Do not use this for an email/SMS OTP, and do not paste credentials or OTPs into chat, workflow inputs, source code, or logs. If Naukri only supports email/SMS OTP, fully unattended GitHub-hosted login may not be feasible; use an approved interactive sign-in flow instead.

## GitHub Actions secrets

In **Settings → Secrets and variables → Actions**, configure:

| Secret | Purpose |
| --- | --- |
| `NAUKRI_USERNAME` | Your Naukri login username/email |
| `NAUKRI_PASSWORD` | Your Naukri password |
| `GOOGLE_DRIVE_FILE_ID` | ID of the existing resume PDF in Google Drive |
| `NAUKRI_TOTP_SECRET` | Optional; only if Naukri supports authenticator-app TOTP |

The Google Drive resume source is unchanged. The PDF must be accessible to the workflow and the downloaded content must begin with a PDF signature. The script does not print credential values, cookies, OTPs, or page contents.

Remove the obsolete `NAUKRI_COOKIES` and `NAUKRI_FORM_KEY` repository secrets after you have switched over. Since session values were previously shared in chat, revoke/sign out those sessions where possible and rotate credentials if appropriate.

## Schedule

The workflow preserves the intended schedule (GitHub cron is UTC):

- 01:00 IST — `30 19 * * 0-6` (previous UTC day)
- 07:00 IST — `30 1 * * 0-6`
- 12:00 IST — `30 6 * * 0-6`

You can also run it manually from **Actions → Update Naukri Resume → Run workflow**.

## Success verification

A run is considered successful only when the profile page displays a recognized resume-update confirmation or, after reloading, the exact uploaded filename. If the UI changes or confirmation cannot be verified, the workflow exits with failure and asks for manual verification. A green run has not yet been demonstrated in this repository; test with a manual run and inspect the Naukri profile before relying on the schedule.

## Troubleshooting

- **Missing secret:** Add the named secret in repository settings.
- **OTP required:** Email/SMS OTP cannot be entered interactively into a hosted runner. The workflow fails safely. TOTP is supported only when explicitly configured and supported by Naukri.
- **CAPTCHA/security challenge:** The workflow stops; do not try to bypass it.
- **Could not identify login/upload controls:** Naukri may have changed its UI. Inspect the profile manually and update selectors only after reviewing the live page.
- **Upload unverified:** Check your Naukri profile manually before rerunning to avoid unnecessary duplicate uploads.

## Security

- Never commit credentials, OTPs, cookies, or Playwright browser state.
- Keep GitHub repository write access restricted because people with write access can generally use repository Actions secrets.
- This project is an unofficial personal automation and depends on Naukri's current UI and policies.
