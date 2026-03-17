# 🎯 AI Recruiting Agent

Paste a job description + LinkedIn profiles → get a ranked, scored shortlist with outreach messages.

---

## Quick Start (5 minutes)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app
```bash
streamlit run app.py
```

### 3. Open your browser
Streamlit will open automatically at `http://localhost:8501`

---

## Configuration

In the **sidebar**, enter:
- **Anthropic API Key** — get one at [console.anthropic.com](https://console.anthropic.com)
- **Proxycurl API Key** *(optional)* — for fetching profiles by URL ([nubela.co/proxycurl](https://nubela.co/proxycurl))

---

## Two Modes

### Mode 1: Paste Profile Text (free, no extra API needed)
Manually copy the text from a LinkedIn profile and paste it into the profile boxes.
Works great for small batches (1–20 candidates).

### Mode 2: Proxycurl (LinkedIn URL → auto-fetch)
Paste LinkedIn profile URLs and the app fetches structured data automatically.
Costs ~$0.01–0.10 per profile. Great for bulk processing.

---

## What You Get Per Candidate

| Field | Description |
|---|---|
| **Overall Score** (0–100) | Weighted composite fit score |
| **Skills Match** | How well their skills map to JD requirements |
| **Experience Level** | Seniority and years relative to role |
| **Industry Fit** | Relevance of past companies/sectors |
| **Career Trajectory** | Growth direction (upward, lateral, declining) |
| **Top Strengths** | 3 specific reasons they're a good fit |
| **Red Flags** | Honest gaps or concerns |
| **Summary** | 2–3 sentence narrative |
| **Outreach Message** | Personalized LinkedIn note ready to send |

---

## Scoring Weights

Adjust the sliders in the sidebar to match what matters most for each role.
Default: Skills 35% · Experience 30% · Industry 20% · Trajectory 15%.

---

## Export

Click **Export Results as CSV** to download a spreadsheet with all scores and notes —
perfect for sharing with clients or saving to a CRM.

---

## Cost Estimate

- ~$0.002–0.01 per candidate scored (Claude API)
- ~$0.01–0.10 per profile fetched (Proxycurl, optional)
- 100 candidates ≈ $1–2 total

---

## Roadmap (Phase 2+)

- [ ] Batch CSV upload (50+ URLs at once)
- [ ] Candidate database / search across jobs
- [ ] ATS integrations (Greenhouse, Lever)
- [ ] Configurable scoring rubrics per role type
