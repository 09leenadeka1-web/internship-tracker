# 🔬 Research Internship Tracker

Automatically tracks paid research internships in pure mathematics,
extracts professor names and details using Claude AI,
and sends you a weekly email digest.

Runs **free** on GitHub Actions every Monday at 1:30 PM IST.

---

## What It Does

- Scrapes 8+ sources: OIST, DAAD, MathPrograms, MathJobs, Max Planck, IMPRS, EMBL, arXiv
- Uses Claude AI to extract: professor name, research area, stipend, deadline, location
- Filters by your keywords (algebra, representation theory, Langlands, etc.)
- Sends a formatted HTML email with only **new** results (no duplicates)
- Runs every Monday automatically, or manually anytime

---

## Setup (One-Time, ~10 minutes)

### Step 1: Fork or create this repo on GitHub

Push this entire folder as a GitHub repository.

```
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/internship-tracker.git
git push -u origin main
```

---

### Step 2: Get your API keys

**Anthropic API Key:**
- Go to https://console.anthropic.com
- Create an API key (free tier has usage limits; costs ~$0.01–0.05 per weekly run)

**Gmail App Password (for sending email):**
- Go to your Google Account → Security → 2-Step Verification (must be ON)
- Then go to: https://myaccount.google.com/apppasswords
- Create an app password for "Mail"
- Copy the 16-character password — this is your EMAIL_PASSWORD
- This is NOT your regular Gmail password

---

### Step 3: Add GitHub Secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 4 secrets:

| Secret Name        | Value                                      |
|--------------------|--------------------------------------------|
| `ANTHROPIC_API_KEY`| Your Anthropic API key (sk-ant-...)        |
| `EMAIL_SENDER`     | Your Gmail address (yourname@gmail.com)    |
| `EMAIL_PASSWORD`   | Your Gmail App Password (16 chars)         |
| `EMAIL_RECIPIENT`  | Where to receive emails (can be same Gmail)|

---

### Step 4: Enable GitHub Actions

Go to your repo → **Actions** tab → Click **"I understand my workflows, go ahead and enable them"**

---

### Step 5: Test it manually

Go to **Actions** → **Research Internship Tracker** → **Run workflow** → **Run workflow**

Check your email in ~2–3 minutes.

---

## Customizing Keywords & Sources

**To change your interest keywords**, edit `scraper.py`:

```python
KEYWORDS = [
    "algebra", "representation theory", "homological algebra",
    "category theory", "algebraic geometry", ...
    # Add anything relevant to your research interests
]
```

**To add new sources**, add to the `SOURCES` list in `scraper.py`:

```python
{
    "name": "My Custom Source",
    "url": "https://example.com/internships",
    "type": "webpage"
},
```

---

## Schedule

Default: **Every Monday at 8:00 AM UTC (1:30 PM IST)**

To change the schedule, edit `.github/workflows/tracker.yml`:

```yaml
- cron: "0 8 * * 1"   # minute hour day month weekday
```

Cron examples:
- `"0 8 * * 1"` → Every Monday 8 AM UTC
- `"0 8 * * 1,4"` → Monday and Thursday
- `"0 8 1 * *"` → First of every month

---

## Cost

- **GitHub Actions**: Free (2000 min/month on free tier; each run takes ~2 min)
- **Anthropic API**: ~$0.01–0.05 per run depending on pages scraped
- Roughly **< $1/month** total

---

## Troubleshooting

**No email received:**
- Check GitHub Actions logs (Actions tab → click the run → click the job)
- Make sure all 4 secrets are set correctly
- Make sure Gmail 2FA is enabled and you used an App Password

**Claude returns empty results:**
- Some sites block scrapers. You'll see a `[WARN]` in the logs.
- Try adding a different URL for that source.

**Too many duplicates:**
- The `data/seen_opportunities.json` file tracks what's been sent.
- It's cached between runs via GitHub Actions cache.
- If cache is lost (GitHub clears it after 7 days of inactivity), some repeats may appear once.
