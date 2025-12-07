# Delta Fast Track - Meeting One Materials

Materials for Focus Group Meeting #1 on the City of Delta Fast Track Program for affordable housing development under Proposition 123.

## Current Status (December 6, 2025)

**Primary deliverable:** Decision Worksheet - now live and ready for homework distribution.

**Live URL:** https://westernspaces.github.io/delta-fast-track-simulator/worksheet/decision_worksheet.html

**Submissions go to:** Formspree → sarah@westernspaces.co

---

## Quick Links

| What | URL |
|------|-----|
| **Decision Worksheet** (homework) | https://westernspaces.github.io/delta-fast-track-simulator/worksheet/decision_worksheet.html |
| **Detailed Simulator** | https://delta-fast-track-simulator-qrzf2t87mqwzfgwporenqz.streamlit.app/ |
| **GitHub Repo** | https://github.com/WesternSpaces/delta-fast-track-simulator |

---

## Decision Worksheet

### What It Is
A simple HTML page that lets focus group participants build their own "policy package" by making 5 key decisions:

1. **Affordability period** - How long should units stay affordable?
2. **% affordable to qualify** - What share of units must be affordable?
3. **Density bonus** - Should Delta allow extra units?
4. **% of bonus affordable** - What share of bonus units must be affordable? (conditional - only shows if bonus selected)
5. **Fee waivers** - Should Delta offer fee reductions?

### Features
- Expandable "Learn more" sections with context on each decision
- Real-time sidebar summary of selections
- **Formspree integration** - "Send My Answers" button submits directly (no email client needed)
- Print button for paper copies
- Link to detailed simulator
- Examples from 4 verified Fast Track communities:
  - **Grand Junction** (65K pop) - Full incentive package with fee waivers + density bonus
  - **Montrose** (20K pop) - Delta's neighbor, REDO overlay district
  - **Salida** (6K pop) - Inclusionary zoning + density bonus
  - **De Beque** (500 pop) - Bare-bones compliance (just 90-day review)
- **Accessibility features:** Skip link, focus states, WCAG AA color contrast, ARIA labels

### Reflection Questions
At the end, participants answer:
1. What was the hardest decision for you?
2. What would change your mind?
3. What's the most important thing to get right?

### How It Works
1. Share the URL with focus group participants
2. They complete it as homework before the meeting
3. Clicking "Send My Answers" submits to Formspree → your email
4. You receive responses to prepare for discussion

---

## Folder Structure

```
meeting-one/
├── README.md                 ← You are here
├── SESSION_NOTES.md          ← Detailed session notes
│
├── worksheet/                ← CURRENT DELIVERABLE
│   ├── decision_worksheet.html   ← Main file (also on GitHub Pages)
│   └── Fast Track Policy Adoption.xlsx  ← DOLA verified communities list
│
├── simulator/                ← Streamlit app (for detailed modeling)
│
├── Data/                     ← Source data and fee schedules
├── Visuals/                  ← Charts and graphics
├── archive/                  ← Previous drafts
│
└── PDFs/
    ├── 2025 1118 Delta Fast Track Focus Group Meeting#1 Packet.pdf
    └── 2025 1118 Focus Group Meeting #1 PPT.pdf
```

---

## Key Context

### Comparison Communities (all verified by DOLA)
| Community | Pop. | Approach | Why Relevant |
|-----------|------|----------|--------------|
| Grand Junction | 65K | Fee waivers + density bonus | Western Slope, detailed program |
| Montrose | 20K | REDO overlay district | Delta's neighbor |
| Salida | 6K | Inclusionary + density bonus | Small mountain town |
| De Beque | 500 | Bare-bones (90-day only) | Shows minimal compliance option |

### Delta's Draft vs State Baseline
| | State | Delta's Draft |
|---|---|---|
| Permit timeline | 90 days | 90 days |
| Rental AMI | 60% | 80% (more inclusive) |
| % affordable | 50% | 25% (lower bar) |
| Affordability period | Not specified | 15 years |
| Incentives | Not required | Under discussion |

---

## To Resume Work

### Edit the worksheet:
```bash
cd "/Users/sarah/Documents/Western Spaces/Claude/delta/meeting-one/worksheet"
# Edit decision_worksheet.html
# Then push to GitHub:
git add decision_worksheet.html
git commit -m "Description of changes"
git push
# GitHub Pages auto-updates in ~1 minute
```

### Check Formspree submissions:
Log into https://formspree.io to see responses (form ID: xzznvopz)

### Key files:
- `worksheet/decision_worksheet.html` - Main deliverable
- `SESSION_NOTES.md` - What's been done and why

---

## Recent Changes (Dec 6, 2025)

- Hosted worksheet on GitHub Pages
- Added Formspree integration (submissions work!)
- Updated comparison communities to verified Fast Track adopters
- Simplified "Why This Matters" section
- Added accessibility features (skip link, focus states, contrast)
- Added color accents to context sections
- Fixed density bonus examples with real data (Longmont: 25% bonus for 12% affordable)
- Made Decision 4 conditional (only shows if density bonus selected)

---

## Contact

- **Project Lead:** sarah@westernspaces.co
- **Focus Group Facilitation:** Dynamic Planning + Science & Western Spaces

---

*Last updated: December 6, 2025*
