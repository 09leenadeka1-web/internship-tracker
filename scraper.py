"""
Research Internship Tracker — FREE VERSION
No AI API needed. Uses keyword matching + smart text parsing.
Sends weekly email digest of new paid research opportunities.
"""

import os
import json
import hashlib
import smtplib
import re
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────

KEYWORDS = [
    "algebra", "representation theory", "homological algebra",
    "category theory", "algebraic geometry", "number theory",
    "langlands", "vertex algebra", "homotopy", "topology",
    "pure mathematics", "mathematical physics", "arithmetic geometry",
    "commutative algebra", "lie theory", "modular forms",
    "derived category", "sheaf theory", "galois theory"
]

PAID_SIGNALS = [
    "stipend", "fellowship", "funded", "financial support",
    "scholarship", "grant", "paid", "salary", "compensation",
    "living allowance", "travel support", "remuneration"
]

SOURCES = [
    {
        "name": "OIST Research Internships",
        "url": "https://www.oist.jp/internships",
        "apply_url": "https://www.oist.jp/internships"
    },
    {
        "name": "DAAD WISE Fellowship",
        "url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/daad-wise-scholarship/",
        "apply_url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/daad-wise-scholarship/"
    },
    {
        "name": "MathPrograms.org",
        "url": "https://www.mathprograms.org/db",
        "apply_url": "https://www.mathprograms.org/db"
    },
    {
        "name": "AMS Math Jobs",
        "url": "https://www.mathjobs.org/jobs",
        "apply_url": "https://www.mathjobs.org/jobs"
    },
    {
        "name": "Max Planck Leipzig (MPI MiS)",
        "url": "https://www.mis.mpg.de/calendar/conferences/internship.html",
        "apply_url": "https://www.mis.mpg.de"
    },
    {
        "name": "Max Planck Bonn (MPIM)",
        "url": "https://www.mpim-bonn.mpg.de/node/13",
        "apply_url": "https://www.mpim-bonn.mpg.de"
    },
    {
        "name": "CIRM Research in Paris",
        "url": "https://www.cirm-math.fr/index.php?option=com_content&view=article&id=10&Itemid=118",
        "apply_url": "https://www.cirm-math.fr"
    },
    {
        "name": "Institut Mittag-Leffler",
        "url": "https://www.mittag-leffler.se/research-programs/",
        "apply_url": "https://www.mittag-leffler.se"
    },
    {
        "name": "Hausdorff Institute Bonn",
        "url": "https://www.him.uni-bonn.de/programs/",
        "apply_url": "https://www.him.uni-bonn.de"
    },
    {
        "name": "MSRI / SLMath Berkeley",
        "url": "https://www.slmath.org/programs",
        "apply_url": "https://www.slmath.org"
    },
]

SEEN_FILE = "data/seen_opportunities.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_seen() -> set:
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set):
    os.makedirs("data", exist_ok=True)
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def hash_opportunity(opp: dict) -> str:
    key = f"{opp.get('institution','')}-{opp.get('research_area','')[:50]}"
    return hashlib.md5(key.encode()).hexdigest()


def fetch_page(url: str) -> tuple[str, BeautifulSoup]:
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True).lower()
        return text, soup
    except Exception as e:
        print(f"  [WARN] Could not fetch {url}: {e}")
        return "", None


def extract_opportunities_free(source: dict, text: str, soup) -> list[dict]:
    """
    Free keyword-based extraction — no AI API needed.
    Looks for keyword matches and paid signals in page text.
    """
    if not text:
        return []

    matched_keywords = [k for k in KEYWORDS if k in text]
    matched_paid = [p for p in PAID_SIGNALS if p in text]

    # Only proceed if both math keywords AND paid signals found
    if not matched_keywords or not matched_paid:
        return []

    # Try to find professor names (pattern: Prof./Dr. + Name)
    professor_names = []
    prof_pattern = re.findall(r'(?:prof(?:essor)?\.?\s+|dr\.?\s+)([a-z][a-z\s\-]{2,25})', text)
    for name in prof_pattern[:5]:
        clean = name.strip().title()
        if len(clean) > 4:
            professor_names.append(clean)

    # Try to find deadline mentions
    deadline = None
    deadline_pattern = re.search(
        r'(?:deadline|apply by|closes?|due)[\s:]+([a-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+[a-z]+\s+\d{4}|\w+\s+\d{4})',
        text
    )
    if deadline_pattern:
        deadline = deadline_pattern.group(1).title()

    # Build summary snippet from page text around first keyword match
    snippet = ""
    for kw in matched_keywords[:2]:
        idx = text.find(kw)
        if idx > 50:
            snippet = text[max(0, idx-80):idx+200].strip()
            snippet = " ".join(snippet.split())  # clean whitespace
            snippet = snippet[:300].capitalize()
            break

    opp = {
        "institution": source["name"],
        "professor_name": ", ".join(professor_names[:3]) if professor_names else None,
        "research_area": ", ".join(matched_keywords[:5]).title(),
        "stipend_info": ", ".join(matched_paid[:3]).title() if matched_paid else None,
        "deadline": deadline,
        "location": None,
        "apply_url": source["apply_url"],
        "relevant_keywords": matched_keywords[:6],
        "summary": snippet or f"Opportunity at {source['name']} matching your research interests in {', '.join(matched_keywords[:3])}.",
        "source": source["name"]
    }

    return [opp]


# ── Email ─────────────────────────────────────────────────────────────────────

def send_email(new_opportunities: list[dict]):
    sender = os.environ["EMAIL_SENDER"]
    password = os.environ["EMAIL_PASSWORD"]
    recipient = os.environ["EMAIL_RECIPIENT"]
    today = datetime.now().strftime("%d %B %Y")

    html_parts = [f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 700px; margin: auto; color: #222;">
    <h2 style="color: #2c3e50;">🔬 Research Internship Digest — {today}</h2>
    <p>Found <strong>{len(new_opportunities)}</strong> new opportunity(ies) matching your interests in pure mathematics.</p>
    <hr/>
    """]

    for i, opp in enumerate(new_opportunities, 1):
        keywords_str = ", ".join(opp.get("relevant_keywords", [])) or "—"
        html_parts.append(f"""
        <div style="background:#f9f9f9; border-left: 4px solid #3498db; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
            <h3 style="margin:0 0 8px 0; color: #2980b9;">#{i} — {opp.get('institution', '—')}</h3>
            {"<p><strong>👤 Professor(s):</strong> " + opp['professor_name'] + "</p>" if opp.get('professor_name') else ""}
            <p><strong>📚 Research Area:</strong> {opp.get('research_area', '—')}</p>
            {"<p><strong>💰 Funding signals:</strong> " + opp['stipend_info'] + "</p>" if opp.get('stipend_info') else ""}
            {"<p><strong>📅 Deadline:</strong> " + opp['deadline'] + "</p>" if opp.get('deadline') else ""}
            <p><strong>🏷️ Keywords matched:</strong> {keywords_str}</p>
            <p style="color:#555; font-style:italic;">{opp.get('summary', '')}</p>
            {"<p><a href='" + opp['apply_url'] + "' style='color:#3498db; font-weight:bold;'>→ Visit & Apply</a></p>" if opp.get('apply_url') else ""}
        </div>
        """)

    html_parts.append("""
    <hr/>
    <p style="color:#999; font-size:12px;">Auto-generated by your Research Internship Tracker.
    Runs free on GitHub Actions every Monday at 1:30 PM IST.</p>
    </body></html>
    """)

    html_body = "".join(html_parts)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔬 {len(new_opportunities)} Research Opportunity(ies) Found — {today}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        print(f"✅ Email sent to {recipient} with {len(new_opportunities)} opportunities.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        raise


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"Research Internship Tracker (FREE) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    seen = load_seen()
    all_new = []

    for source in SOURCES:
        print(f"[→] Checking: {source['name']}")
        text, soup = fetch_page(source["url"])
        if not text:
            continue

        opportunities = extract_opportunities_free(source, text, soup)
        print(f"    Found {len(opportunities)} matching opportunity(ies).")

        for opp in opportunities:
            h = hash_opportunity(opp)
            if h not in seen:
                seen.add(h)
                all_new.append(opp)
                print(f"    ✨ NEW: {opp.get('institution')} — keywords: {', '.join(opp.get('relevant_keywords', [])[:3])}")

    save_seen(seen)
    print(f"\n{'='*60}")
    print(f"Total new opportunities: {len(all_new)}")

    if all_new:
        send_email(all_new)
    else:
        print("No new opportunities found. No email sent.")

    print("Done.\n")


if __name__ == "__main__":
    main()
