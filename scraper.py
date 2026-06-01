"""
Research Internship Tracker
Scrapes internship sources, uses Claude AI to extract structured info,
sends email digest of new opportunities.
"""

import os
import json
import hashlib
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
import anthropic

# ── Config ────────────────────────────────────────────────────────────────────

KEYWORDS = [
    "algebra", "representation theory", "homological algebra",
    "category theory", "algebraic geometry", "number theory",
    "Langlands", "vertex algebra", "homotopy", "topology",
    "pure mathematics", "math internship", "research fellowship"
]

SOURCES = [
    {
        "name": "OIST Research Internships",
        "url": "https://www.oist.jp/research-internship",
        "type": "webpage"
    },
    {
        "name": "DAAD WISE Fellowship",
        "url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/daad-wise-scholarship/",
        "type": "webpage"
    },
    {
        "name": "MathPrograms.org",
        "url": "https://www.mathprograms.org/db?joblist-0-0-0-all---0-",
        "type": "webpage"
    },
    {
        "name": "AMS Math Jobs",
        "url": "https://www.mathjobs.org/jobs/list/Internship",
        "type": "webpage"
    },
    {
        "name": "IMPRS Leipzig (MPI MiS)",
        "url": "https://www.mis.mpg.de/events/internships.html",
        "type": "webpage"
    },
    {
        "name": "IMPRS Bonn - Max Planck",
        "url": "https://www.mpim-bonn.mpg.de/research_opportunities",
        "type": "webpage"
    },
    {
        "name": "EMBL Internships",
        "url": "https://www.embl.org/about/info/scientific-training/internships/",
        "type": "webpage"
    },
    {
        "name": "arXiv Math Positions",
        "url": "https://arxiv.org/search/?searchtype=all&query=paid+research+internship+mathematics&start=0",
        "type": "webpage"
    },
]

SEEN_FILE = "data/seen_opportunities.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_seen() -> set:
    """Load previously seen opportunity hashes."""
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set):
    """Save seen hashes to file."""
    os.makedirs("data", exist_ok=True)
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def hash_opportunity(opp: dict) -> str:
    """Create a stable hash for deduplication."""
    key = f"{opp.get('professor_name','')}-{opp.get('institution','')}-{opp.get('deadline','')}"
    return hashlib.md5(key.encode()).hexdigest()


def fetch_page(url: str) -> str:
    """Fetch and clean webpage text."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove scripts, styles, nav clutter
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Truncate to avoid huge token usage (keep first 6000 chars)
        return text[:6000]
    except Exception as e:
        print(f"  [WARN] Could not fetch {url}: {e}")
        return ""


def extract_opportunities(source_name: str, raw_text: str) -> list[dict]:
    """Use Claude to extract structured internship data from raw page text."""
    if not raw_text.strip():
        return []

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""You are helping a mathematics researcher find paid research internships.

Source: {source_name}

Page content:
{raw_text}

Extract ALL paid research internship or fellowship opportunities mentioned.
For each one, return a JSON array. Each item should have:
- professor_name: string or null
- institution: string
- research_area: string (brief description)
- stipend_info: string or null (any mention of payment/stipend)
- deadline: string or null
- location: string or null
- apply_url: string or null
- relevant_keywords: list of strings from this list that match: {KEYWORDS}
- summary: 2-sentence plain summary

Rules:
- Only include PAID opportunities (stipend, fellowship, funded)
- If nothing is paid or no internship is found, return []
- Return ONLY valid JSON array, no markdown, no explanation
- If multiple professors are listed for one program, create one entry per professor
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text.strip()
        # Strip markdown fences if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        return json.loads(response_text)
    except Exception as e:
        print(f"  [WARN] Claude extraction failed for {source_name}: {e}")
        return []


# ── Email ─────────────────────────────────────────────────────────────────────

def send_email(new_opportunities: list[dict]):
    """Send a digest email with new internship opportunities."""
    sender = os.environ["EMAIL_SENDER"]
    password = os.environ["EMAIL_PASSWORD"]
    recipient = os.environ["EMAIL_RECIPIENT"]

    today = datetime.now().strftime("%d %B %Y")

    # Build HTML body
    html_parts = [f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 700px; margin: auto; color: #222;">
    <h2 style="color: #2c3e50;">🔬 Research Internship Digest — {today}</h2>
    <p>Found <strong>{len(new_opportunities)}</strong> new paid research opportunity(ies) matching your interests.</p>
    <hr/>
    """]

    for i, opp in enumerate(new_opportunities, 1):
        keywords_str = ", ".join(opp.get("relevant_keywords", [])) or "—"
        html_parts.append(f"""
        <div style="background:#f9f9f9; border-left: 4px solid #3498db; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
            <h3 style="margin:0 0 8px 0; color: #2980b9;">#{i} — {opp.get('institution', 'Unknown Institution')}</h3>
            {"<p><strong>👤 Professor:</strong> " + opp['professor_name'] + "</p>" if opp.get('professor_name') else ""}
            <p><strong>📚 Research Area:</strong> {opp.get('research_area', '—')}</p>
            {"<p><strong>💰 Stipend:</strong> " + opp['stipend_info'] + "</p>" if opp.get('stipend_info') else ""}
            {"<p><strong>📅 Deadline:</strong> " + opp['deadline'] + "</p>" if opp.get('deadline') else ""}
            {"<p><strong>📍 Location:</strong> " + opp['location'] + "</p>" if opp.get('location') else ""}
            <p><strong>🏷️ Keywords:</strong> {keywords_str}</p>
            <p style="color:#555;">{opp.get('summary', '')}</p>
            {"<p><a href='" + opp['apply_url'] + "' style='color:#3498db;'>→ Apply / More Info</a></p>" if opp.get('apply_url') else ""}
        </div>
        """)

    html_parts.append("""
    <hr/>
    <p style="color:#999; font-size:12px;">This digest is auto-generated by your Research Internship Tracker. 
    Running on GitHub Actions — checks weekly every Monday.</p>
    </body></html>
    """)

    html_body = "".join(html_parts)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔬 {len(new_opportunities)} New Research Internship(s) — {today}"
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
    print(f"Research Internship Tracker — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    seen = load_seen()
    all_new = []

    for source in SOURCES:
        print(f"[→] Checking: {source['name']}")
        raw_text = fetch_page(source["url"])
        if not raw_text:
            continue

        opportunities = extract_opportunities(source["name"], raw_text)
        print(f"    Claude found {len(opportunities)} paid opportunity(ies).")

        for opp in opportunities:
            # Only include if at least one keyword matches
            if not opp.get("relevant_keywords"):
                continue
            h = hash_opportunity(opp)
            if h not in seen:
                seen.add(h)
                opp["source"] = source["name"]
                all_new.append(opp)
                print(f"    ✨ NEW: {opp.get('institution')} — {opp.get('professor_name', 'No professor listed')}")

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
