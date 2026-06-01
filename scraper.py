"""
Research Internship Tracker — CUSTOM VERSION for Leena
Tracks ONLY paid research internships (not postdocs/faculty jobs)
Focus: Pure math + philosophy/spirituality connections
Gap-friendly programs included
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

# ── Keywords that MUST match (math research interests) ────────────────────────
MATH_KEYWORDS = [
    "algebra", "representation theory", "homological algebra",
    "category theory", "algebraic geometry", "number theory",
    "langlands", "vertex algebra", "homotopy", "topology",
    "pure mathematics", "arithmetic geometry", "commutative algebra",
    "lie theory", "modular forms", "derived category", "galois theory",
    "sheaf theory", "algebraic topology", "k-theory", "motives",
    "mathematical physics", "quantum groups", "noncommutative geometry"
]

# ── Philosophy/spirituality/interdisciplinary bonus keywords ──────────────────
PHILOSOPHY_KEYWORDS = [
    "philosophy", "foundations of mathematics", "logic",
    "philosophy of science", "metaphysics", "consciousness",
    "interdisciplinary", "humanities", "religious studies",
    "contemplative", "history of mathematics", "mathematical logic",
    "philosophy of mind", "epistemology"
]

# ── Paid signals ──────────────────────────────────────────────────────────────
PAID_SIGNALS = [
    "stipend", "fellowship", "funded", "financial support",
    "scholarship", "grant", "paid", "salary", "living allowance",
    "travel support", "remuneration", "funding provided"
]

# ── EXCLUDE if these appear prominently (postdoc/faculty filters) ─────────────
EXCLUDE_SIGNALS = [
    "postdoctoral", "postdoc", "faculty position", "tenure",
    "assistant professor", "associate professor", "permanent position",
    "phd required", "phd degree required"
]

# ── Sources: Tier 1, 2, 3 — Europe, USA, Japan, China, Vietnam + more ─────────
SOURCES = [
    # ── EUROPE — Tier 1 ──────────────────────────────────────────────────────
    {"name": "IHES France — Junior Visitors", "url": "https://www.ihes.fr/en/a-visiting-researcher/", "apply_url": "https://www.ihes.fr/en/a-visiting-researcher/", "notes": "Tier 1 | Pure math, Langlands, algebraic geometry — Paris"},
    {"name": "Institut Henri Poincare Paris", "url": "https://www.ihp.fr/en/grants-and-calls", "apply_url": "https://www.ihp.fr/en/grants-and-calls", "notes": "Tier 1 | Math fellowships — Paris France"},
    {"name": "Max Planck Bonn (MPIM)", "url": "https://www.mpim-bonn.mpg.de/node/13", "apply_url": "https://www.mpim-bonn.mpg.de", "notes": "Tier 1 | Pure math, algebra, geometry — Bonn Germany"},
    {"name": "Max Planck Leipzig (MPI MiS)", "url": "https://www.mis.mpg.de/calendar/conferences/internship.html", "apply_url": "https://www.mis.mpg.de", "notes": "Tier 1 | Math in Sciences — Leipzig Germany"},
    {"name": "Hausdorff Institute Bonn", "url": "https://www.him.uni-bonn.de/programs/", "apply_url": "https://www.him.uni-bonn.de", "notes": "Tier 1 | Trimester programs — Bonn Germany"},
    {"name": "Mittag-Leffler Institute Sweden", "url": "https://www.mittag-leffler.se/research-programs/", "apply_url": "https://www.mittag-leffler.se", "notes": "Tier 1 | Graduate fellowships — Stockholm"},
    {"name": "CIRM France", "url": "https://www.cirm-math.fr/en/grants-and-calls-for-applications.html", "apply_url": "https://www.cirm-math.fr", "notes": "Tier 1 | Research fellowships — Marseille France"},
    {"name": "ICTP Trieste — Fellowships", "url": "https://www.ictp.it/opportunities", "apply_url": "https://www.ictp.it/opportunities", "notes": "Tier 1 | Fully funded, developing country friendly — Italy"},
    {"name": "ETH Zurich — Summer Research", "url": "https://ethz.ch/en/studies/non-degree-course-offers/summer-research-fellowship.html", "apply_url": "https://ethz.ch/en/studies/non-degree-course-offers/summer-research-fellowship.html", "notes": "Tier 1 | Paid summer research — Zurich Switzerland"},
    {"name": "DAAD WISE Fellowship Germany", "url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/daad-wise-scholarship/", "apply_url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/daad-wise-scholarship/", "notes": "Tier 1 | Paid internship Germany, open to Indian students"},

    # ── EUROPE — Tier 2 ──────────────────────────────────────────────────────
    {"name": "IRMAR Rennes France", "url": "https://irmar.univ-rennes.fr/en/research", "apply_url": "https://irmar.univ-rennes.fr/en", "notes": "Tier 2 | Strong algebra, number theory group — Rennes France"},
    {"name": "IMJ-PRG Paris", "url": "https://www.imj-prg.fr/spip.php?rubrique22", "apply_url": "https://www.imj-prg.fr", "notes": "Tier 2 | Institut Mathématique de Jussieu — Paris, strong representation theory"},
    {"name": "University of Cologne Math", "url": "https://math.uni-koeln.de/en/research/", "apply_url": "https://math.uni-koeln.de/en", "notes": "Tier 2 | Algebra, topology — Cologne Germany"},
    {"name": "University of Münster — Math", "url": "https://www.uni-muenster.de/MathematicsMuenster/", "apply_url": "https://www.uni-muenster.de/MathematicsMuenster/", "notes": "Tier 2 | Mathematics Münster cluster — Germany, strong K-theory, topology"},
    {"name": "Leiden University Math", "url": "https://www.universiteitleiden.nl/en/science/mathematics", "apply_url": "https://www.universiteitleiden.nl/en/science/mathematics", "notes": "Tier 2 | Number theory, Galois representations — Netherlands"},
    {"name": "University of Barcelona — IMUB", "url": "https://www.imub.ub.edu/en/", "apply_url": "https://www.imub.ub.edu/en/", "notes": "Tier 2 | Algebra, geometry — Barcelona Spain"},
    {"name": "SISSA Trieste — Math", "url": "https://www.sissa.it/app/research-opportunities", "apply_url": "https://www.sissa.it", "notes": "Tier 2 | Geometry, mathematical physics — Trieste Italy"},
    {"name": "CRM Barcelona", "url": "https://www.crm.cat/calls/", "apply_url": "https://www.crm.cat", "notes": "Tier 2 | Research fellowships — Barcelona Spain"},
    {"name": "University of Vienna — Math", "url": "https://mathematik.univie.ac.at/en/research/", "apply_url": "https://mathematik.univie.ac.at/en", "notes": "Tier 2 | Algebra, number theory — Vienna Austria"},
    {"name": "Charles University Prague", "url": "https://www.mff.cuni.cz/en/math", "apply_url": "https://www.mff.cuni.cz/en", "notes": "Tier 2/3 | Algebra, category theory — Prague, affordable cost of living"},

    # ── EUROPE — Tier 3 (strong specific professors) ─────────────────────────
    {"name": "University of Padova — Math", "url": "https://www.math.unipd.it/en/research/", "apply_url": "https://www.math.unipd.it/en", "notes": "Tier 3 | Algebra, homological methods — Padova Italy"},
    {"name": "AGM Cergy Paris", "url": "https://agm.cyu.fr/en/research", "apply_url": "https://agm.cyu.fr/en", "notes": "Tier 3 | Arithmetic geometry, number theory — Cergy France"},
    {"name": "Jagiellonian University Krakow", "url": "https://wmi.uj.edu.pl/en_GB/research", "apply_url": "https://wmi.uj.edu.pl/en_GB", "notes": "Tier 3 | Algebra, category theory — Krakow Poland, very welcoming to international students"},
    {"name": "MathPrograms.org — All Programs", "url": "https://www.mathprograms.org/db", "apply_url": "https://www.mathprograms.org/db", "notes": "Global listing — all tiers"},

    # ── USA & CANADA — Tier 1 ────────────────────────────────────────────────
    {"name": "MSRI / SLMath Berkeley", "url": "https://www.slmath.org/programs", "apply_url": "https://www.slmath.org", "notes": "Tier 1 | Graduate fellowships — Berkeley USA"},
    {"name": "IAS Princeton — Programs", "url": "https://www.ias.edu/math/memberships", "apply_url": "https://www.ias.edu/math/memberships", "notes": "Tier 1 | Institute for Advanced Study — Princeton USA"},
    {"name": "AMS Math Jobs", "url": "https://www.mathjobs.org/jobs", "apply_url": "https://www.mathjobs.org/jobs", "notes": "Tier 1-3 | Comprehensive math listings USA"},
    {"name": "Fields Institute Toronto", "url": "http://www.fields.utoronto.ca/opportunities", "apply_url": "http://www.fields.utoronto.ca/opportunities", "notes": "Tier 1 | Graduate fellowships — Toronto Canada"},
    {"name": "Perimeter Institute — Visitors", "url": "https://perimeterinstitute.ca/research/research-visitors", "apply_url": "https://perimeterinstitute.ca", "notes": "Tier 1 | Math-physics, interdisciplinary — Waterloo Canada"},
    {"name": "ICERM Brown University", "url": "https://icerm.brown.edu/programs/", "apply_url": "https://icerm.brown.edu", "notes": "Tier 1 | Graduate programs — Providence USA"},

    # ── USA — Tier 2/3 ───────────────────────────────────────────────────────
    {"name": "IMSI Chicago", "url": "https://www.imsi.institute/programs/", "apply_url": "https://www.imsi.institute", "notes": "Tier 2 | Institute for Math and Statistical Innovation — Chicago USA"},
    {"name": "IMA Minnesota", "url": "https://www.ima.umn.edu/programs", "apply_url": "https://www.ima.umn.edu", "notes": "Tier 2 | Institute for Mathematics — Minneapolis USA"},
    {"name": "AIM San Jose", "url": "https://aimath.org/programs/", "apply_url": "https://aimath.org", "notes": "Tier 2 | American Institute of Mathematics — San Jose USA"},
    {"name": "BIRS Banff Canada", "url": "https://www.birs.ca/apply", "apply_url": "https://www.birs.ca", "notes": "Tier 2 | Banff International Research Station — Canada"},

    # ── JAPAN ────────────────────────────────────────────────────────────────
    {"name": "OIST Research Internships", "url": "https://www.oist.jp/internships", "apply_url": "https://www.oist.jp/internships", "notes": "Tier 1 | Fully funded, gap-friendly — Okinawa Japan"},
    {"name": "RIMS Kyoto — Visitor Program", "url": "https://www.kurims.kyoto-u.ac.jp/en/visitor.html", "apply_url": "https://www.kurims.kyoto-u.ac.jp/en/visitor.html", "notes": "Tier 1 | Research Institute Math Sciences — Kyoto Japan"},
    {"name": "Kavli IPMU Tokyo", "url": "https://www.ipmu.jp/en/apply-kavli-ipmu", "apply_url": "https://www.ipmu.jp/en/apply-kavli-ipmu", "notes": "Tier 1 | Algebraic geometry, math-physics — Tokyo Japan"},
    {"name": "Tohoku University Math", "url": "https://www.math.tohoku.ac.jp/english/research/", "apply_url": "https://www.math.tohoku.ac.jp/english", "notes": "Tier 2 | Strong algebra, representation theory — Sendai Japan"},
    {"name": "Osaka University Math", "url": "https://www.math.sci.osaka-u.ac.jp/eng/research.html", "apply_url": "https://www.math.sci.osaka-u.ac.jp/eng", "notes": "Tier 2 | Algebra, geometry — Osaka Japan"},

    # ── CHINA ────────────────────────────────────────────────────────────────
    {"name": "YMSC Tsinghua Beijing", "url": "https://ymsc.tsinghua.edu.cn/en/info/1053/1595.htm", "apply_url": "https://ymsc.tsinghua.edu.cn", "notes": "Tier 1 | Yau Mathematical Sciences Center — Beijing"},
    {"name": "BICMR Peking University", "url": "https://bicmr.pku.edu.cn/content/show/70-2861.html", "apply_url": "https://bicmr.pku.edu.cn", "notes": "Tier 1 | Beijing International Center — Peking University"},
    {"name": "TSIMF Sanya China", "url": "https://www.tsimf.cn/en/", "apply_url": "https://www.tsimf.cn/en/", "notes": "Tier 1 | Tsinghua Sanya International Math Forum"},
    {"name": "MCM Chinese Academy of Sciences", "url": "http://www.mcm.ac.cn/about/introduce/201702/t20170209_350063.html", "apply_url": "http://www.mcm.ac.cn", "notes": "Tier 2 | Morningside Center of Math — Beijing China"},
    {"name": "AMSS Beijing — Research", "url": "http://www.amss.ac.cn/rcdw/en/", "apply_url": "http://www.amss.ac.cn", "notes": "Tier 2 | Academy of Math & Systems Science — Beijing"},
    {"name": "Shanghai Center for Math Sciences", "url": "https://scms.fudan.edu.cn/info/1074/1935.htm", "apply_url": "https://scms.fudan.edu.cn", "notes": "Tier 2 | Fudan University — Shanghai China"},

    # ── VIETNAM / SOUTHEAST ASIA ─────────────────────────────────────────────
    {"name": "VIASM Hanoi Vietnam", "url": "https://viasm.edu.vn/en/hdkh/announce", "apply_url": "https://viasm.edu.vn/en/hdkh/announce", "notes": "Tier 2 | Vietnam Institute Advanced Study Math — gap-friendly, funded"},
    {"name": "NCTS Taiwan", "url": "https://www.ncts.ntu.edu.tw/en/event/", "apply_url": "https://www.ncts.ntu.edu.tw/en", "notes": "Tier 2 | National Center Theoretical Sciences — Taiwan, algebra focus"},
    {"name": "KAIST Korea", "url": "https://mathsci.kaist.ac.kr/en/research/", "apply_url": "https://mathsci.kaist.ac.kr/en", "notes": "Tier 2 | Korea Advanced Institute — strong pure math"},
    {"name": "POSTECH Korea", "url": "https://math.postech.ac.kr/en/", "apply_url": "https://math.postech.ac.kr/en", "notes": "Tier 2 | Pohang University — algebra, geometry, Korea"},
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

def fetch_page(url: str):
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

def is_excluded(text: str) -> bool:
    """Return True if page is primarily about postdocs/faculty — skip it."""
    exclude_count = sum(1 for e in EXCLUDE_SIGNALS if e in text)
    return exclude_count >= 3

def extract_opportunities(source: dict, text: str, soup) -> list[dict]:
    if not text:
        return []

    # Skip postdoc/faculty heavy pages
    if is_excluded(text):
        print(f"  [SKIP] Looks like postdoc/faculty page, skipping.")
        return []

    matched_math = [k for k in MATH_KEYWORDS if k in text]
    matched_philosophy = [k for k in PHILOSOPHY_KEYWORDS if k in text]
    matched_paid = [p for p in PAID_SIGNALS if p in text]

    # Must have math keywords + paid signals
    if not matched_math or not matched_paid:
        return []

    # Check for internship/student specific language
    student_signals = ["intern", "student", "master", "msc", "graduate student",
                       "visiting student", "summer", "fellowship", "research program",
                       "short-term", "visitor"]
    matched_student = [s for s in student_signals if s in text]

    # Professor name extraction
    professor_names = []
    prof_pattern = re.findall(r'(?:prof(?:essor)?\.?\s+|dr\.?\s+)([a-z][a-z\s\-]{2,25})', text)
    for name in prof_pattern[:5]:
        clean = name.strip().title()
        if len(clean) > 4:
            professor_names.append(clean)

    # Deadline extraction
    deadline = None
    deadline_pattern = re.search(
        r'(?:deadline|apply by|closes?|due)[\s:]+([a-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+[a-z]+\s+\d{4}|\w+\s+\d{4})',
        text)
    if deadline_pattern:
        deadline = deadline_pattern.group(1).title()

    # Text snippet
    snippet = ""
    for kw in matched_math[:2]:
        idx = text.find(kw)
        if idx > 50:
            snippet = text[max(0, idx-80):idx+200].strip()
            snippet = " ".join(snippet.split())[:300].capitalize()
            break

    all_keywords = matched_math[:4] + matched_philosophy[:2]

    return [{
        "institution": source["name"],
        "notes": source.get("notes", ""),
        "professor_name": ", ".join(professor_names[:3]) if professor_names else None,
        "research_area": ", ".join(matched_math[:5]).title(),
        "philosophy_match": ", ".join(matched_philosophy[:3]).title() if matched_philosophy else None,
        "stipend_info": ", ".join(matched_paid[:3]).title(),
        "student_friendly": ", ".join(matched_student[:3]).title() if matched_student else None,
        "deadline": deadline,
        "apply_url": source["apply_url"],
        "relevant_keywords": all_keywords[:6],
        "summary": snippet or f"Opportunity at {source['name']} matching your research interests.",
        "source": source["name"]
    }]

# ── Email ─────────────────────────────────────────────────────────────────────

def send_email(new_opportunities: list[dict]):
    sender = os.environ["EMAIL_SENDER"]
    password = os.environ["EMAIL_PASSWORD"]
    recipient = os.environ["EMAIL_RECIPIENT"]
    today = datetime.now().strftime("%d %B %Y")

    html_parts = [f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 700px; margin: auto; color: #222;">
    <h2 style="color: #2c3e50;">🔬 Research Internship Digest — {today}</h2>
    <p>Found <strong>{len(new_opportunities)}</strong> paid internship/fellowship opportunity(ies) 
    in pure mathematics matching your profile.</p>
    <p style="color:#888; font-size:13px;">✅ Postdoc & faculty positions filtered out &nbsp;|&nbsp; 
    ✅ Student/MSc friendly &nbsp;|&nbsp; ✅ Paid/funded only</p>
    <hr/>"""]

    for i, opp in enumerate(new_opportunities, 1):
        keywords_str = ", ".join(opp.get("relevant_keywords", [])) or "—"
        html_parts.append(f"""
        <div style="background:#f9f9f9; border-left:4px solid #3498db; padding:15px; margin-bottom:20px; border-radius:4px;">
            <h3 style="margin:0 0 8px 0; color:#2980b9;">#{i} — {opp.get('institution','—')}</h3>
            <p style="color:#27ae60; font-size:13px;">ℹ️ {opp.get('notes','')}</p>
            {"<p><strong>👤 Professor(s) found:</strong> " + opp['professor_name'] + "</p>" if opp.get('professor_name') else ""}
            <p><strong>📚 Math Areas:</strong> {opp.get('research_area','—')}</p>
            {"<p><strong>🧠 Philosophy/Interdisciplinary:</strong> " + opp['philosophy_match'] + "</p>" if opp.get('philosophy_match') else ""}
            {"<p><strong>🎓 Student signals:</strong> " + opp['student_friendly'] + "</p>" if opp.get('student_friendly') else ""}
            {"<p><strong>💰 Funding:</strong> " + opp['stipend_info'] + "</p>" if opp.get('stipend_info') else ""}
            {"<p><strong>📅 Deadline:</strong> " + opp['deadline'] + "</p>" if opp.get('deadline') else ""}
            <p><strong>🏷️ Keywords:</strong> {keywords_str}</p>
            <p style="color:#555; font-style:italic; font-size:13px;">{opp.get('summary','')}</p>
            {"<p><a href='" + opp['apply_url'] + "' style='color:#3498db; font-weight:bold;'>→ Visit & Apply</a></p>" if opp.get('apply_url') else ""}
        </div>""")

    html_parts.append("""
    <hr/>
    <p style="color:#999; font-size:12px;">Auto-generated by your Research Internship Tracker. 
    Runs free on GitHub Actions every Monday at 1:30 PM IST.<br/>
    Only internships & fellowships open to MSc/graduate students shown.</p>
    </body></html>""")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔬 {len(new_opportunities)} Internship(s) for You — {today}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText("".join(html_parts), "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
    print(f"✅ Email sent with {len(new_opportunities)} opportunities.")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"Research Internship Tracker — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Filters: Internships only | Paid | MSc-friendly | No postdocs")
    print(f"{'='*60}\n")

    seen = load_seen()
    all_new = []

    for source in SOURCES:
        print(f"[→] Checking: {source['name']}")
        text, soup = fetch_page(source["url"])
        if not text:
            continue
        opportunities = extract_opportunities(source, text, soup)
        print(f"    Found {len(opportunities)} matching opportunity(ies).")
        for opp in opportunities:
            h = hash_opportunity(opp)
            if h not in seen:
                seen.add(h)
                all_new.append(opp)
                print(f"    ✨ NEW: {opp.get('institution')}")

    save_seen(seen)
    print(f"\nTotal new opportunities: {len(all_new)}")
    if all_new:
        send_email(all_new)
    else:
        print("No new opportunities found. No email sent.")
    print("Done.\n")

if __name__ == "__main__":
    main()
