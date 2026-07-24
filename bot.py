import io
import os
import re
import zipfile
from typing import List, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from docx import Document as DocxDocument
from PyPDF2 import PdfReader
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Add it to the .env file.")

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
GRAMMAR_RED_FLAGS = {
    "teh",
    "recieve",
    "seperate",
    "definately",
    "occured",
    "becuase",
    "enviroment",
    "intial",
    "manger",
    "succesful",
    "commited",
    "exeperience",
    "acheive",
    "resposible",
    "langauge",
}


def extract_text_from_bytes(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    if name.endswith(".docx"):
        doc = DocxDocument(io.BytesIO(data))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text)
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")
    raise ValueError("Unsupported file type")


def detect_urls(text: str) -> List[str]:
    return re.findall(r"https?://[^\s)]+", text)


def validate_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=5) as response:
            return 200 <= response.getcode() < 400
    except Exception:
        return False


def detect_grammar_issues(text: str) -> List[str]:
    issues: List[str] = []
    words = re.findall(r"[A-Za-z']+", text.lower())
    for word in words:
        if word in GRAMMAR_RED_FLAGS:
            issues.append(f"Possible typo: '{word}'")
    if re.search(r"\b([A-Za-z]+)\s+([A-Za-z]+)\b", text) and ".." in text:
        issues.append("Possible punctuation problem")
    return issues[:8]


def score_resume(text: str, role: str) -> dict:
    lowered = text.lower()
    score = 0
    reasons = []

    if re.search(r"\b(name|full name)\b", lowered):
        score += 10
        reasons.append("Includes a name")
    if re.search(r"\b(email|e-mail)\b", lowered) or re.search(r"[\w.-]+@[\w.-]+", text):
        score += 10
        reasons.append("Includes contact email")
    if re.search(r"\b(phone|mobile|contact)\b", lowered) or re.search(r"\+?\d[\d -]{7,}\d", text):
        score += 10
        reasons.append("Includes phone/contact information")
    if re.search(r"\b(summary|profile|about me)\b", lowered):
        score += 10
        reasons.append("Has a summary/profile section")
    if re.search(r"\b(experience|work history|employment)\b", lowered):
        score += 10
        reasons.append("Includes experience")
    if re.search(r"\b(education|degree|university|college)\b", lowered):
        score += 10
        reasons.append("Includes education")
    if re.search(r"\b(skills|technologies|tools|languages)\b", lowered):
        score += 10
        reasons.append("Includes skills")
    if re.search(r"\b(project|projects|achievement|achievements)\b", lowered):
        score += 10
        reasons.append("Includes projects/achievements")

    if role:
        role_keywords = re.findall(r"[a-z]+", role.lower())
        matched = [kw for kw in role_keywords if kw in lowered]
        if matched:
            score += min(20, len(matched) * 4)
            reasons.append(f"Matches role keywords: {', '.join(matched[:4])}")

    grammar_issues = detect_grammar_issues(text)
    if grammar_issues:
        score -= min(20, len(grammar_issues) * 5)
        reasons.append("Contains possible grammar issues")

    score = max(0, min(100, score))
    return {"score": score, "reasons": reasons, "grammar_issues": grammar_issues}


def suggest_improvements(text: str, role: str) -> List[str]:
    suggestions = []
    lowered = text.lower()
    if not re.search(r"\b(summary|profile|about me)\b", lowered):
        suggestions.append("Add a short summary/profile section at the top.")
    if not re.search(r"\b(experience|work history|employment)\b", lowered):
        suggestions.append("Include clear work experience with outcomes and responsibilities.")
    if not re.search(r"\b(skills|technologies|tools|languages)\b", lowered):
        suggestions.append("Add a dedicated skills section with tools and technologies.")
    if role:
        suggestions.append(f"Tailor the resume more closely to the role: {role}.")
    return suggestions[:4]


def suggest_platforms(text: str) -> List[str]:
    lowered = text.lower()
    platforms = []
    if "python" in lowered or "sql" in lowered:
        platforms.extend(["GitHub", "LeetCode", "HackerRank"])
    if "data" in lowered or "analytics" in lowered or "power bi" in lowered:
        platforms.extend(["Kaggle", "Tableau Public", "SQLBolt"])
    if "cloud" in lowered or "aws" in lowered or "azure" in lowered or "gcp" in lowered:
        platforms.extend(["AWS Skill Builder", "Microsoft Learn", "Google Cloud Skills Boost"])
    if "devops" in lowered or "docker" in lowered or "kubernetes" in lowered:
        platforms.extend(["DevOps Roadmap", "Docker Docs", "Kubernetes.io"])
    if not platforms:
        platforms = ["GitHub", "LinkedIn", "LeetCode"]
    return list(dict.fromkeys(platforms))[:4]


def build_resume_report(filename: str, text: str, role: str) -> str:
    result = score_resume(text, role)
    urls = detect_urls(text)
    valid_urls = [u for u in urls if validate_url(u)]
    invalid_urls = [u for u in urls if not validate_url(u)]

    lines = []
    lines.append(f"Resume: {filename}")
    lines.append(f"Score: {result['score']}/100")
    lines.append("Highlights:")
    for reason in result["reasons"]:
        lines.append(f"- {reason}")

    if result["grammar_issues"]:
        lines.append("Grammar/clarity issues:")
        for issue in result["grammar_issues"]:
            lines.append(f"- {issue}")
    else:
        lines.append("Grammar/clarity: no obvious issues detected. No edit recommendation needed.")

    if urls:
        lines.append(f"URLs found: {len(urls)}")
        if valid_urls:
            lines.append(f"Valid URLs: {', '.join(valid_urls[:3])}")
        if invalid_urls:
            lines.append(f"Invalid URLs: {', '.join(invalid_urls)}")
    else:
        lines.append("URLs found: none")

    improvements = suggest_improvements(text, role)
    if improvements:
        lines.append("How to improve the score:")
        for item in improvements:
            lines.append(f"- {item}")
    else:
        lines.append("How to improve the score: keep the resume focused and add measurable results.")

    platforms = suggest_platforms(text)
    lines.append("Skill-building platforms:")
    for platform in platforms:
        lines.append(f"- {platform}")

    return "\n".join(lines)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hello! Send me a resume file (.pdf, .docx, .txt) or a ZIP containing multiple resumes.\n"
        "You can also add a role in the caption, for example: role: software engineer"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Use /start to see the instructions.\n"
        "Upload one resume file or a ZIP with several resumes.\n"
        "If you want the score tailored to a position, add a caption like: role: data analyst"
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message.document:
        return

    caption = (message.caption or "").strip()
    role = ""
    if "role:" in caption.lower():
        role = caption.split("role:", 1)[1].strip()

    file = await message.document.get_file()
    data = await file.download_as_bytes()
    filename = message.document.file_name or "resume"

    try:
        if filename.lower().endswith(".zip"):
            reports = []
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    name = member.filename.split("/")[-1]
                    if os.path.splitext(name)[1].lower() not in SUPPORTED_EXTENSIONS:
                        continue
                    text = extract_text_from_bytes(name, zf.read(member))
                    reports.append(build_resume_report(name, text, role))
            if not reports:
                await message.reply_text("No supported resume files were found in the ZIP archive.")
                return
            response = "Batch resume analysis\n\n" + "\n\n".join(reports)
            await message.reply_text(response)
            return

        text = extract_text_from_bytes(filename, data)
        await message.reply_text(build_resume_report(filename, text, role))
    except Exception as exc:
        await message.reply_text(f"I could not read that file. Error: {exc}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    if text.startswith("/" ):
        return
    await update.message.reply_text(
        "Please upload a resume file instead of plain text.\n"
        "You can send a PDF, DOCX, TXT file, or a ZIP archive with multiple resumes."
    )


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.document, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
