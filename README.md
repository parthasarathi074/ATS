# Telegram Resume Scoring Bot

This bot reviews resumes and gives a score based on structure, completeness, and clarity. It can also:
- analyze one resume file or a ZIP file containing many resumes
- check for suspicious or invalid URLs
- suggest improvements only when grammar issues are detected
- recommend skill-building platforms based on resume content


## How to use it

- Start the bot with `/start`
- Send a resume file (`.pdf`, `.docx`, `.txt`) or a ZIP file containing multiple resumes
- You can also add a role in the caption, for example:
  - `role: software engineer`
  - `role: data analyst`

## Notes

- The scoring is heuristic and meant for an MVP.
- Grammar suggestions appear only when grammar-like issues are detected.
- URL validation is best-effort and checks reachability.
