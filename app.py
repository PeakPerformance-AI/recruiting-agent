import streamlit as st
import anthropic
import json
import requests
from typing import Optional
import time

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Recruiting Agent",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f8f9fb; }
    .stApp { background-color: #f8f9fb; }

    /* Cards */
    .candidate-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
    }
    .rank-badge {
        display: inline-block;
        background: linear-gradient(135deg, #3b82f6, #6366f1);
        color: white;
        font-weight: 700;
        font-size: 13px;
        padding: 4px 12px;
        border-radius: 20px;
        margin-right: 10px;
    }
    .score-pill {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 13px;
    }
    .score-high   { background: #dcfce7; color: #16a34a; }
    .score-medium { background: #fef9c3; color: #ca8a04; }
    .score-low    { background: #fee2e2; color: #dc2626; }

    .section-label {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        color: #6b7280;
        margin-bottom: 4px;
    }
    .tag {
        display: inline-block;
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 12px;
        color: #475569;
        margin: 2px;
    }
    .strength-item { color: #16a34a; font-size: 13px; margin: 2px 0; }
    .flag-item     { color: #dc2626; font-size: 13px; margin: 2px 0; }

    .outreach-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 13px;
        color: #64748b;
        font-style: italic;
        white-space: pre-wrap;
    }
    .divider { border-top: 1px solid #e2e8f0; margin: 12px 0; }
    .stTextArea textarea { background: #ffffff !important; color: #e5e7eb !important; border: 1px solid #e2e8f0 !important; }
    .stTextInput input  { background: #ffffff !important; color: #e5e7eb !important; border: 1px solid #e2e8f0 !important; }

    .stTextArea textarea::placeholder { color: #9ca3af !important; }
    .stTextInput input::placeholder { color: #9ca3af !important; }

    textarea, input { color: #000000 !important; }

    div[data-baseweb="textarea"] textarea,
    div[data-baseweb="input"] input,
    .stTextArea textarea,
    .stTextInput input,
    textarea,
    input {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        opacity: 1 !important;
    }
</style>
""", unsafe_allow_html=True)


# ── Sidebar — API Keys ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    anthropic_key = st.text_input("Anthropic API Key", type="password",
                                  placeholder="sk-ant-...")
    st.markdown("---")
    st.markdown("### LinkedIn Data Source")
    data_source = st.radio("How will you provide profiles?",
                           ["Paste profile text", "Proxycurl (LinkedIn URL)"],
                           index=0)
    proxycurl_key = ""
    if data_source == "Proxycurl (LinkedIn URL)":
        proxycurl_key = st.text_input("Proxycurl API Key", type="password",
                                      placeholder="...")
        st.caption("[Get a free Proxycurl key →](https://nubela.co/proxycurl)")

    st.markdown("---")
    st.markdown("### Scoring Weights")
    w_skills  = st.slider("Skills match",       0, 100, 35)
    w_exp     = st.slider("Experience level",   0, 100, 30)
    w_industry= st.slider("Industry fit",       0, 100, 20)
    w_growth  = st.slider("Career trajectory",  0, 100, 15)
    total_w   = w_skills + w_exp + w_industry + w_growth
    if total_w != 100:
        st.warning(f"Weights sum to {total_w} (should be 100)")

    st.markdown("---")
    st.caption("Built with Claude · Phase 1 Prototype")


# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_proxycurl(linkedin_url: str, api_key: str) -> Optional[str]:
    """Fetch a LinkedIn profile via Proxycurl and return formatted text."""
    try:
        r = requests.get(
            "https://nubela.co/proxycurl/api/v2/linkedin",
            params={"linkedin_profile_url": linkedin_url, "use_cache": "if-present"},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        if r.status_code != 200:
            return None
        d = r.json()
        parts = [
            f"Name: {d.get('full_name', 'Unknown')}",
            f"Headline: {d.get('headline', '')}",
            f"Location: {d.get('city', '')}, {d.get('country_full_name', '')}",
            f"Summary: {d.get('summary', '')}",
            "\nExperience:",
        ]
        for e in d.get("experiences", []):
            parts.append(
                f"  - {e.get('title')} at {e.get('company')} "
                f"({e.get('starts_at', {}).get('year', '?')}–"
                f"{e.get('ends_at', {}).get('year', 'present') if e.get('ends_at') else 'present'})"
            )
            if e.get("description"):
                parts.append(f"    {e['description'][:300]}")
        parts.append("\nEducation:")
        for ed in d.get("education", []):
            parts.append(f"  - {ed.get('degree_name', '')} at {ed.get('school', '')}")
        parts.append("\nSkills: " + ", ".join(s.get("name", "") for s in d.get("skills", [])))
        return "\n".join(parts)
    except Exception:
        return None


def build_system_prompt(weights: dict) -> str:
    return f"""You are an expert technical recruiter with 15 years of experience.
Your job is to analyze LinkedIn candidate profiles against a job description
and produce structured, objective assessments.

Scoring weights requested by the user:
- Skills match:        {weights['skills']}%
- Experience level:    {weights['experience']}%
- Industry fit:        {weights['industry']}%
- Career trajectory:   {weights['growth']}%

You MUST respond with valid JSON only — no prose, no markdown fences.
The JSON schema is:
{{
  "candidates": [
    {{
      "name": "string",
      "current_title": "string",
      "current_company": "string",
      "overall_score": 0-100,
      "dimension_scores": {{
        "skills_match": 0-100,
        "experience_level": 0-100,
        "industry_fit": 0-100,
        "career_trajectory": 0-100
      }},
      "top_strengths": ["string", "string", "string"],
      "red_flags": ["string"],
      "summary": "2–3 sentence narrative on fit",
      "outreach_message": "Personalized 3-sentence LinkedIn message to send this candidate"
    }}
  ]
}}

Be honest. Not every candidate is a strong fit. Red flags are important for recruiters.
"""


def score_candidates(job_desc: str, profiles: list[dict],
                     api_key: str, weights: dict) -> dict:
    """Call Claude to extract + score all candidates in one pass."""
    client = anthropic.Anthropic(api_key=api_key)

    profiles_block = ""
    for i, p in enumerate(profiles, 1):
        profiles_block += f"\n\n--- CANDIDATE {i} ---\n{p['text']}"

    user_msg = f"""JOB DESCRIPTION:
{job_desc}

CANDIDATE PROFILES:{profiles_block}

Analyze every candidate above and return the JSON scorecard.
"""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=build_system_prompt(weights),
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = response.content[0].text.strip()
    # Strip any accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def score_color(score: int) -> str:
    if score >= 75: return "score-high"
    if score >= 50: return "score-medium"
    return "score-low"


# ── Main UI ───────────────────────────────────────────────────────────────────
st.markdown("# 🎯 AI Recruiting Agent")
st.markdown("Paste a job description and candidate profiles — get a ranked shortlist in seconds.")
st.markdown("---")

col_jd, col_profiles = st.columns([1, 1], gap="large")

with col_jd:
    st.markdown("### 📋 Job Description")
    job_description = st.text_area(
        "Paste the full job description",
        height=320,
        placeholder="Senior Backend Engineer\n\nWe're looking for...\n\nRequirements:\n- 5+ years Python\n- Experience with distributed systems\n...",
        label_visibility="collapsed",
    )

with col_profiles:
    st.markdown("### 👤 Candidate Profiles")

    if data_source == "Paste profile text":
        st.caption("Add one or more candidates below. Each gets its own text box.")
        if "num_profiles" not in st.session_state:
            st.session_state.num_profiles = 3

        profiles_input = []
        for i in range(st.session_state.num_profiles):
            text = st.text_area(
                f"Candidate {i+1}",
                height=100,
                placeholder="Name, headline, experience, skills…",
                key=f"profile_{i}",
            )
            profiles_input.append({"text": text, "label": f"Candidate {i+1}"})

        c1, c2 = st.columns(2)
        with c1:
            if st.button("＋ Add candidate"):
                st.session_state.num_profiles += 1
                st.rerun()
        with c2:
            if st.session_state.num_profiles > 1 and st.button("− Remove last"):
                st.session_state.num_profiles -= 1
                st.rerun()

    else:  # Proxycurl
        st.caption("Paste one LinkedIn URL per line.")
        urls_text = st.text_area(
            "LinkedIn URLs",
            height=280,
            placeholder="https://www.linkedin.com/in/jane-doe\nhttps://www.linkedin.com/in/john-smith",
            label_visibility="collapsed",
        )
        profiles_input = [{"url": u.strip(), "label": u.strip()}
                          for u in urls_text.splitlines() if u.strip()]

# ── Run button ────────────────────────────────────────────────────────────────
st.markdown("---")
run_col, _ = st.columns([1, 3])
with run_col:
    run = st.button("🚀 Rank Candidates", type="primary", use_container_width=True)

if run:
    # Validation
    if not anthropic_key:
        st.error("Add your Anthropic API key in the sidebar.")
        st.stop()
    if not job_description.strip():
        st.error("Please enter a job description.")
        st.stop()

    weights = {"skills": w_skills, "experience": w_exp,
               "industry": w_industry, "growth": w_growth}

    # Fetch / validate profiles
    profiles_to_score = []
    if data_source == "Paste profile text":
        profiles_to_score = [p for p in profiles_input if p["text"].strip()]
        if not profiles_to_score:
            st.error("Paste at least one candidate profile.")
            st.stop()
    else:
        if not proxycurl_key:
            st.error("Add your Proxycurl API key in the sidebar.")
            st.stop()
        if not profiles_input:
            st.error("Enter at least one LinkedIn URL.")
            st.stop()
        with st.spinner("Fetching LinkedIn profiles via Proxycurl…"):
            for p in profiles_input:
                text = fetch_proxycurl(p["url"], proxycurl_key)
                if text:
                    profiles_to_score.append({"text": text, "label": p["url"]})
                else:
                    st.warning(f"Could not fetch: {p['url']}")
                time.sleep(0.5)
        if not profiles_to_score:
            st.error("No profiles could be fetched. Check your URLs and API key.")
            st.stop()

    # Score
    with st.spinner(f"Analyzing {len(profiles_to_score)} candidate(s)…"):
        try:
            result = score_candidates(job_description, profiles_to_score,
                                      anthropic_key, weights)
        except json.JSONDecodeError:
            st.error("Claude returned malformed JSON. Try again.")
            st.stop()
        except anthropic.AuthenticationError:
            st.error("Invalid Anthropic API key.")
            st.stop()
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

    candidates = sorted(result.get("candidates", []),
                        key=lambda c: c.get("overall_score", 0), reverse=True)

    # ── Results ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"## 📊 Results — {len(candidates)} Candidate(s) Ranked")
    st.caption(f"Sorted by overall fit score · Weights: Skills {w_skills}% · Experience {w_exp}% · Industry {w_industry}% · Trajectory {w_growth}%")

    for rank, c in enumerate(candidates, 1):
        score = c.get("overall_score", 0)
        sc    = score_color(score)
        dims  = c.get("dimension_scores", {})
        strengths = c.get("top_strengths", [])
        flags     = c.get("red_flags", [])

        with st.container():
            st.markdown(f"""
<div class="candidate-card">
  <div style="display:flex; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
    <span class="rank-badge">#{rank}</span>
    <span style="font-size:18px; font-weight:700; color:#1e293b;">{c.get('name','Unknown')}</span>
    <span style="color:#64748b; font-size:14px;">· {c.get('current_title','')} @ {c.get('current_company','')}</span>
    <span style="margin-left:auto;" class="score-pill {sc}">{score}/100</span>
  </div>

  <div class="divider"></div>

  <div style="display:grid; grid-template-columns: repeat(4,1fr); gap:12px; margin-bottom:14px;">
    <div>
      <div class="section-label">Skills</div>
      <span class="score-pill {score_color(dims.get('skills_match',0))}">{dims.get('skills_match',0)}</span>
    </div>
    <div>
      <div class="section-label">Experience</div>
      <span class="score-pill {score_color(dims.get('experience_level',0))}">{dims.get('experience_level',0)}</span>
    </div>
    <div>
      <div class="section-label">Industry</div>
      <span class="score-pill {score_color(dims.get('industry_fit',0))}">{dims.get('industry_fit',0)}</span>
    </div>
    <div>
      <div class="section-label">Trajectory</div>
      <span class="score-pill {score_color(dims.get('career_trajectory',0))}">{dims.get('career_trajectory',0)}</span>
    </div>
  </div>

  <div class="divider"></div>

  <p style="color:#475569; font-size:14px; margin:10px 0;">{c.get('summary','')}</p>

  <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:12px;">
    <div>
      <div class="section-label">✅ Strengths</div>
      {"".join(f'<div class="strength-item">✓ {s}</div>' for s in strengths) or '<span style="color:#6b7280">None noted</span>'}
    </div>
    <div>
      <div class="section-label">🚩 Red Flags</div>
      {"".join(f'<div class="flag-item">✗ {f}</div>' for f in flags) or '<span style="color:#6b7280">None noted</span>'}
    </div>
  </div>

  <div style="margin-top:14px;">
    <div class="section-label">💬 Suggested Outreach</div>
    <div class="outreach-box">{c.get('outreach_message','')}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # CSV export
    st.markdown("---")
    import csv, io
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Rank","Name","Title","Company","Overall Score",
                     "Skills","Experience","Industry","Trajectory",
                     "Strengths","Red Flags","Summary","Outreach"])
    for rank, c in enumerate(candidates, 1):
        d = c.get("dimension_scores", {})
        writer.writerow([
            rank, c.get("name"), c.get("current_title"), c.get("current_company"),
            c.get("overall_score"),
            d.get("skills_match"), d.get("experience_level"),
            d.get("industry_fit"), d.get("career_trajectory"),
            " | ".join(c.get("top_strengths", [])),
            " | ".join(c.get("red_flags", [])),
            c.get("summary"), c.get("outreach_message"),
        ])
    st.download_button("⬇️ Export Results as CSV",
                       data=buf.getvalue(), file_name="candidates_ranked.csv",
                       mime="text/csv")
