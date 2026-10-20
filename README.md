# Naukri Resume Auto-Updater

Automatically refresh your Naukri profile resume from a PDF stored in Google Drive using GitHub Actions. The workflow supports scheduled runs and manual runs.

> **Schedule:** 1:00 AM, 7:00 AM, and 12:00 PM India Standard Time (IST). GitHub Actions uses UTC cron expressions, and scheduled runs may start a little later than the configured time.

---

## How It Works

1. Downloads your resume PDF from Google Drive.
2. Uses the configured Naukri session cookies and form key to authenticate the upload request.
3. Runs automatically three times a day through GitHub Actions.
4. Can also be started manually from the Actions tab.

## Quick Setup

### 1. Configure your resume PDF

1. Upload your resume to [Google Drive](https://drive.google.com) as a PDF.
2. Copy the file ID from its sharing URL. For a URL like `https://drive.google.com/file/d/FILE_ID/view`, the file ID is `FILE_ID`.
3. Ensure the file can be downloaded by the workflow. A publicly accessible link is the simplest setup, but consider the privacy implications before making a resume public.

### 2. Get the Naukri form key

The upload implementation may require a current `formKey` from Naukri. Sign in to [Naukri](https://www.naukri.com), use the profile's Update Resume flow, and inspect the relevant upload request in your browser's developer tools. Treat this value as sensitive and do not publish it.

### 3. Configure GitHub Actions secrets

In your repository, open **Settings → Secrets and variables → Actions** and configure these repository secrets:

| Secret | Purpose |
|---|---|
| `GOOGLE_DRIVE_FILE_ID` | ID of the resume PDF in Google Drive |
| `NAUKRI_FORM_KEY` | Naukri upload form key required by the script |
| `NAUKRI_COOKIES` | Current Naukri session cookie string used by the script |

Never paste session cookies, form keys, or other credentials into issues, commits, logs, or chat. Session cookies can grant access to your account. Use them only in repository secrets, refresh them when they expire, and revoke or replace them if exposed. Automated uploads depend on Naukri's current site behavior and applicable terms; this workflow is not an official Naukri API integration.

## Schedule

The workflow file is `.github/workflows/Resume-Updater.yml`. Its schedule is:

| Intended IST time | UTC cron | Explanation |
|---|---|---|
| 1:00 AM | `30 19 * * *` | 7:30 PM UTC on the previous day |
| 7:00 AM | `30 1 * * *` | 1:30 AM UTC |
| 12:00 PM (noon) | `30 6 * * *` | 6:30 AM UTC |

India Standard Time is UTC+05:30. These cron entries are UTC-based and run daily. GitHub may delay scheduled workflow starts during busy periods; they are not guaranteed to start at the exact minute.

## Run Manually and Verify

1. Open the repository's [Actions tab](https://github.com/Arun-Negi/naukri-resume-updater/actions).
2. Select **Update Naukri Resume**.
3. Choose **Run workflow**, select the `main` branch, and start it.
4. Open the run and inspect the logs and final status. Confirm the resume was updated on Naukri as well; a successful workflow status alone may not prove that the profile changed.

The workflow supports `workflow_dispatch`, so you can run it manually without waiting for the next scheduled time.

## Maintenance and Troubleshooting

- **Authentication or profile-fetch errors:** The Naukri session may have expired or the site's authentication flow may have changed. Refresh the session securely and update `NAUKRI_COOKIES` in repository secrets.
- **Form-key or upload errors:** Check whether the current upload request still uses the expected form key and whether the script matches Naukri's current upload behavior.
- **PDF/download errors:** Verify that `GOOGLE_DRIVE_FILE_ID` is correct and the file is accessible and is a valid PDF.
- **Workflow did not run:** Check that GitHub Actions is enabled, the workflow exists on the default branch, and the Actions tab shows the scheduled or manual run.
- **Unexpected timing:** Scheduled workflows use UTC and may be delayed by GitHub. Check the run's timestamp and the `Print IST current time` step in the logs.

## License

MIT — see the repository's license file.
