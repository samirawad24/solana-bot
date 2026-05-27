# AutoFlow AI Agency — Hands-Free $1,000/Week Business

A fully automated AI agency system that finds leads, sends personalized outreach, delivers AI services, and tracks revenue — all on autopilot.

---

## The Business Model

**What we sell:** AI automation packages to local businesses (med spas, HVAC, real estate, dental, e-commerce)

**Why it works:**
- These businesses are drowning in repetitive work (missed bookings, manual follow-ups, no reviews)
- The fix is almost entirely automated once set up
- They pay recurring monthly retainers → predictable income

**Packages:**

| Package | Setup Fee | Monthly | Deliverables |
|---|---|---|---|
| Starter | $497 | $197/mo | Chatbot, review sequence, monthly report |
| Growth | $797 | $397/mo | + Drip email sequence, lead follow-up |
| Pro | $1,297 | $697/mo | + SEO blog, win-back campaigns, weekly KPIs |

**Path to $1,000/week ($4,333/month):**
- 5 Growth clients ($397/mo) = $1,985/mo MRR
- 3 Pro clients ($697/mo) = $2,091/mo MRR
- 1-2 new setup fees/month = +$800-1,600 variable
- **Total: ~$4,876/month** → **$1,125/week**

---

## Quick Start

### 1. Install
```bash
pip install -r agency/requirements.txt
```

### 2. Configure
```bash
cp agency/.env.example agency/.env
# Edit agency/.env with your keys
```

**Minimum required:** `ANTHROPIC_API_KEY`  
Everything else degrades gracefully (mock leads, logged-only emails, etc.)

### 3. Launch the Dashboard
```bash
streamlit run agency/dashboard.py
```
Opens at http://localhost:8501

### 4. Start the Agent (background mode)
```bash
# Run all tasks immediately (test)
python -m agency.main --now

# Run as always-on agent (scheduled)
python -m agency.main
```

---

## Architecture

```
agency/
├── main.py                  ← Orchestrator + scheduler (runs 24/7)
├── dashboard.py             ← Streamlit live dashboard
├── config.py                ← Niche configs, packages, targets
├── db/
│   └── models.py            ← SQLite: leads, clients, revenue, services
├── leads/
│   ├── finder.py            ← Google Places API lead discovery
│   └── scorer.py            ← Lead qualification (0-100 score)
├── outreach/
│   ├── email_writer.py      ← Claude-generated personalized emails
│   └── email_sender.py      ← SMTP send + follow-up sequences
├── services/
│   ├── chatbot_builder.py   ← AI chatbot config generator
│   ├── content_agent.py     ← SEO blog + drip email sequences
│   └── review_agent.py      ← Review request + win-back campaigns
├── onboarding/
│   └── pipeline.py          ← Auto-onboarding when client pays
├── reporting/
│   └── client_report.py     ← Monthly AI-written performance reports
├── revenue/
│   └── tracker.py           ← MRR, weekly revenue, forecasting
└── niches/
    └── researcher.py        ← Scans Upwork for live opportunities
```

---

## Daily Automation Schedule (UTC)

| Time | Task |
|---|---|
| 07:00 | Lead discovery (Google Places → 5 niche/city pairs) |
| 07:30 | Lead scoring & qualification |
| 09:00 | Outreach (15 emails/day limit: initial + follow-ups) |
| 10:00 | Niche research (Upwork RSS → score opportunities) |
| 11:00 | Service delivery for new clients |
| 16:00 | Monthly report dispatch |
| Every hour | Revenue health check + alerts |

---

## Top 5 Niches (2026 Research)

1. **Med Spa / Aesthetics** — $800 setup + $350/mo avg | Automation score: 9/10
   - Pain: missed after-hours bookings, no review system
   
2. **HVAC** — $600 setup + $300/mo avg | Automation score: 9/10
   - Pain: 30-40% of calls missed during peak season
   
3. **Real Estate** — $700 setup + $400/mo avg | Automation score: 8/10
   - Pain: leads going cold before first contact
   
4. **Dental** — $750 setup + $350/mo avg | Automation score: 9/10
   - Pain: no-shows, no patient recall system
   
5. **E-commerce** — $500 setup + $500/mo avg | Automation score: 10/10
   - Pain: abandoned carts, no post-purchase sequences

---

## API Keys You Need

| Key | Purpose | Cost | Link |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | All AI content generation | ~$10-30/mo | console.anthropic.com |
| `GOOGLE_PLACES_API_KEY` | Lead discovery | ~$17/1k requests | console.cloud.google.com |
| Gmail App Password | Email outreach | Free | myaccount.google.com/apppasswords |
| `HUNTER_API_KEY` | Find business emails | Free 25/mo | hunter.io |

**Total API cost at scale: ~$30-50/month against $4,000+/month revenue.**

---

## Scaling Up

Once you hit $1k/week:
1. Hire a VA ($300-500/mo) to handle sales calls — the agent books the demos, they close
2. White-label the chatbot and review tools (Tidio, Botpress) at $49-99/mo per client
3. Add a Stripe payment link to your Upwork/Fiverr profile for self-serve onboarding
4. Expand to 2 new cities per month using the lead discovery engine

---

## Sources

Research compiled from:
- [Upwork In-Demand Skills 2026](https://investors.upwork.com/news-releases/news-release-details/upworks-demand-skills-2026-demand-top-ai-skills-more-doubles-ai)
- [12 Most Profitable AI Automation Agency Niches 2026](https://ciela.ai/blogs/ai-automation-agency-niches-most-profitable)
- [AI Automation Agency Business Model 2026](https://www.hakunamatatatech.com/our-resources/blog/ai-agents-in-b2b)
- [How to Use AI Agents to Run Your Freelance Business](https://www.jobbers.io/how-to-use-ai-agents-to-run-your-freelance-business-the-2026-automation-playbook/)
- [7 AI Freelance Niches Quietly Printing Money in 2026](https://medium.com/@snehal_singh/7-ai-freelance-niches-quietly-printing-money-in-2026-eb44cbdd4bdc)
