# Naukri Resume Updater

A GitHub Actions workflow that downloads a PDF resume and attempts to update the resume attached to your Naukri profile.

> **Important:** This project relies on Naukri web endpoints and session credentials, not a documented public upload API. Endpoints, form keys, and authentication behavior can change. Check Naukri's current terms and supported automation options before enabling scheduled runs. Never use this to evade account security controls or access an account you do not own.

## Current behavior

- Runs at **09:00, 13:00, and 18:00 India Standard Time (IST)**.
- Can also be started manually from **Actions → Update Naukri Resume → Run workflow**.
- Downloads a PDF from Google Drive, checks its PDF signature and size, then attempts the resume update.
- Uses GitHub Actions secrets for authentication material.
- Keeps TLS certificate verification enabled and applies request timeouts.

GitHub scheduled workflows are best-effort and may run late. Repeated uploads do not guarantee additional recruiter visibility. If one daily update is sufficient, remove two cron entries from `.github/workflows/Resume-Updater.yml`.

## Setup

### 1. Store the PDF in Google Drive

Upload the resume PDF to Google Drive. The current downloader expects a file ID and a link the runner can read without an interactive Google sign-in.

**Privacy warning:** “Anyone with the link” makes the resume accessible to anyone who obtains the link. A resume contains personal information. Use only if you accept that exposure; otherwise change the downloader to use an authenticated Google Drive integration before running this workflow.

The file ID is the value between `/d/` and `/view` in a standard Drive URL.

### 2. Configure GitHub Actions secrets

Open **Repository → Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | Value |
|---|---|
| `GOOGLE_DRIVE_FILE_ID` | Google Drive file ID |
| `NAUKRI_FORM_KEY` | Form key obtained during a normal, manual resume upload, if still required by Naukri |
| `NAUKRI_COOKIES` | Session cookie string, only if permitted by Naukri's current rules |

Never commit credentials to source control, print them in workflow logs, or paste them into chat. Session cookies are equivalent to account credentials. If exposed, sign out/revoke sessions and replace them.

### 3. Run a manual test first

1. Open the repository's **Actions** tab.
2. Select **Update Naukri Resume**.
3. Choose **Run workflow**.
4. Inspect the logs for the first error; logs should not contain secrets.
5. Sign in to Naukri normally and verify the resume shown on your profile.

Do not assume a green workflow means the resume is visible. Confirm it in your profile.

## Schedule

GitHub Actions cron uses **UTC**. These entries correspond to India Standard Time:

| IST | UTC cron |
|---|---|
| 09:00 | `30 3 * * *` |
| 13:00 | `30 7 * * *` |
| 18:00 | `30 12 * * *` |

GitHub scheduled workflows may be delayed, especially during periods of high load. The workflow is not guaranteed to run at the exact minute.

## Troubleshooting

| Symptom | What to check |
|---|---|
| Missing secret | Add the exact secret name under repository Actions secrets |
| Not a PDF | Check the Drive ID and that the response is a PDF rather than an HTML sign-in page |
| HTTP 401/403 | Session may have expired, or Naukri may require a fresh normal sign-in |
| HTTP 400/404 | Naukri may have changed its internal endpoint or form key requirements; do not repeatedly retry |
| Workflow did not start | Confirm Actions are enabled and check the workflow file is on the default branch |
| Green run but old resume remains | Verify the profile manually; the website may have rejected or not processed the request |

## Limitations

- This is not an official Naukri integration.
- Authentication cookies expire and must not be shared.
- No automatic workflow can guarantee recruiter views or ranking.
- The workflow does not bypass CAPTCHA or OTP challenges.

## License

MIT
