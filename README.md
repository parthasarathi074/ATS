# Telegram Resume Scoring Bot

This bot reviews resumes and gives a score based on structure, completeness, and clarity. It can also:
- analyze one resume file or a ZIP file containing many resumes
- check for suspicious or invalid URLs
- suggest improvements only when grammar issues are detected
- recommend skill-building platforms based on resume content

## Step-by-step setup

1. Create and activate the virtual environment
   - `python -m venv venv`
   - `venv\Scripts\activate`

2. Install dependencies
   - `pip install -r requirements.txt`

3. Create your bot with BotFather on Telegram
   - Start a chat with @BotFather
   - Use `/newbot` and follow the steps
   - Copy the bot token

4. Create a `.env` file from `.env.example`
   - `copy .env.example .env`
   - Replace `your_telegram_bot_token_here` with your real token

5. Run the bot
   - `python bot.py`

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
