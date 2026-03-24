# AI Cyber Safety Coach - Master Project Handoff Document

## 1. Document Purpose
This document is the single source of truth for the project. It is written so another LLM, Codex session, or human contributor can take over the build without needing access to prior chat history.

This document defines:
- what the project is
- what has already been decided
- what the MVP must include
- what the implementation order should be
- what can be added later if time permits
- what constraints matter for the hackathon

---

## 2. Project Snapshot
**Project name:** AI Cyber Safety Coach  
**Challenge type:** CPP AI Hackathon 2026 sponsored challenge  
**Challenge framing:** AI for Everyone - Personal Cyber Safety Coach  
**Primary goal:** Help non-experts understand whether an email or URL is safe, suspicious, or likely malicious, and tell them what to do next in plain language.

### Core product thesis
This is **not** just a phishing classifier. It is a consumer-friendly cyber decision-support tool.

The user should be able to:
1. submit suspicious content
2. get a clear risk label
3. understand the top reasons why
4. receive the safest next actions

---

## 3. Locked Strategic Decisions
These decisions are final unless there is a major implementation blocker.

### 3.1 Final risk labels
Use **only** these labels everywhere:
- **Safe**
- **Needs Review**
- **Likely Phishing**

Do **not** use:
- Suspicious
- High Risk
- Dangerous
- Protected
- Safe-ish
- Likely Scam

The entire project must stay standardized to the three approved labels.

### 3.2 MVP direction
The original concern was that a manual paste-only product felt too limited compared with a true email-plugin experience.

Final PM decision:
- **Do not start with full Gmail/Outlook integration**
- **Do build the product so it feels plugin-ready**
- **Do present it through an inbox-style experience**
- **Only attempt live email integration after the core engine is stable**

This means:
- build the real phishing-analysis engine first
- wrap it in a simulated inbox/demo shell
- sell the future plugin story in the presentation

### 3.3 AI decision engine
Yes, phishing analysis is absolutely part of the product.

Primary recommendation:
- **OpenAI API** as the main reasoning and classification engine

Support layers:
- deterministic phishing heuristics
- URL/domain checks
- VirusTotal API for URL enrichment when available

### 3.4 Dataset plan
Yes, public phishing data is still part of the plan.

However, for the MVP the dataset is used primarily for:
- evaluation
- prompt tuning
- regression testing
- seeded demo inbox content
- benchmark cases

It is **not required** that the MVP train a custom phishing model from scratch.

---

## 4. Product Definition
### 4.1 What the product is
An AI Cyber Safety Coach that helps non-experts analyze suspicious emails and URLs.

### 4.2 Primary users
Designed for:
- students
- families
- non-technical workers
- club leaders
- anyone who receives suspicious messages but is not a cybersecurity expert

### 4.3 User promise
The system should help users answer:
- Is this safe?
- Why does it look risky?
- What should I do next?

### 4.4 Product positioning statement
AI Cyber Safety Coach is a consumer-friendly phishing and scam analysis assistant that classifies suspicious messages, explains the risk in plain language, and recommends safe next steps without requiring cybersecurity expertise.

---

## 5. Final Product Vision vs Hackathon MVP
### 5.1 Final product vision
Long-term product vision:
- Gmail/Outlook integrated assistant
- can auto-review incoming messages
- can scan links inside user workflow
- can eventually support browser extension or email add-in experiences

### 5.2 Hackathon MVP
The hackathon MVP should be:
- a web app
- with an inbox-style interface
- containing seeded example messages
- plus a manual analysis mode for pasted email text or URLs

### 5.3 Why this is the right approach
This gives the project:
- a real working core product
- a believable plugin story
- lower debugging risk
- stronger odds of actually shipping

---

## 6. Functional Requirements
### 6.1 Required MVP inputs
The MVP should support at least these input modes:
- seeded demo inbox item selection
- pasted raw email text
- pasted URL
- optional combined email text + URL analysis

### 6.2 Required MVP outputs
Every analysis result must return:
- one risk label: Safe / Needs Review / Likely Phishing
- top 3 reasons in plain language
- recommended action checklist

### 6.3 Recommended additional outputs
If feasible, add:
- confidence band or confidence score
- advanced details drawer
- URL/domain signal breakdown
- shareable report summary
- privacy-safe redaction mode

---

## 7. UX and State Behavior
### 7.1 UX principle
Top of the interface should be simple. Technical depth should be hidden unless expanded.

### 7.2 Recommended core screens
#### Screen A - inbox simulator
Shows:
- list of demo messages
- quick status indicators
- entry point for manual paste analysis

#### Screen B - message detail
Shows:
- selected email content
- key sender/link info
- analyze button

#### Screen C - result view
Shows:
- final label
- top 3 reasons
- action checklist
- optional confidence

#### Screen D - advanced details (collapsed)
Shows:
- heuristic hits
- URL/domain signals
- VirusTotal enrichment if available
- optional raw structured output for debugging/demo

### 7.3 Label behavior
#### Safe
Tone should be calm and not over-dramatic.

#### Needs Review
Tone should encourage verification, caution, and slowing down.

#### Likely Phishing
Tone should be direct and protective:
- do not click
- verify independently
- report if appropriate
- secure accounts if user already interacted

---

## 8. Detection Logic - Locked Technical Approach
The product should use a **layered detection strategy**.

### 8.1 Layer 1 - deterministic heuristics
Extract and score obvious signals such as:
- urgency language
- credential request
- payment redirection language
- gift card/payment pressure
- sender-display mismatch
- suspicious domain patterns
- shortened links
- suspicious attachment cues
- impersonation language

### 8.2 Layer 2 - URL/domain enrichment
Use VirusTotal API for URL risk context when available.

Important:
- VirusTotal is a support signal, not the only signal
- the product must still function without it
- if the lookup fails, degrade gracefully

### 8.3 Layer 3 - LLM reasoning engine
Use the **OpenAI API** to synthesize:
- message content
- extracted phishing indicators
- URL/domain context
- any available enrichment

The model should return:
- final risk label
- reasons
- next-step recommendations

### 8.4 Layer 4 - normalization
Never trust freeform model output directly.

The backend must normalize output so the only valid labels are:
- Safe
- Needs Review
- Likely Phishing

### 8.5 Layer 5 - evaluation harness
Run the system against public phishing and benign examples for:
- regression testing
- prompt tuning
- benchmark comparisons

---

## 9. AI API Decision
### 9.1 Primary AI API
Use **OpenAI API** as the main phishing reasoning layer.

### 9.2 Why OpenAI API is the recommended primary choice
It is the best fit for the project because it supports:
- strong language reasoning
- explanation generation
- schema-constrained output
- simple integration into the product pipeline

### 9.3 What the AI layer is responsible for
The AI layer should:
- evaluate message-level phishing risk
- synthesize multiple evidence sources
- produce user-friendly reasoning
- recommend next actions

### 9.4 What the AI layer should not do
It should not:
- invent unsupported certainty
- return inconsistent label language
- overwhelm the user with jargon by default
- replace deterministic checks and validation

---

## 10. Data Plan and Testing Plan
### 10.1 Public datasets remain part of the plan
Yes, the project should still use phishing-related public datasets from sources such as:
- Hugging Face
- Kaggle
- other public phishing-email or URL datasets

### 10.2 How datasets should be used
Use them mainly for:
- known phishing examples
- benign contrast examples
- seeded demo inbox generation
- regression testing
- edge-case testing
- prompt calibration

### 10.3 Do not overcomplicate the MVP with training
The MVP does **not** need:
- custom model training
- full fine-tuning pipeline
- complex ML experimentation

The faster and safer hackathon architecture is:
- **LLM decides**
- **rules verify**
- **VirusTotal enriches**
- **public datasets test**

### 10.4 Recommended test data categories
Build a benchmark set that includes:
- obvious phishing emails
- ordinary benign emails
- borderline cases
- poor-grammar but benign emails
- unfamiliar domain but legitimate emails
- malicious-looking but non-clickable test cases

---

## 11. Bias, Fairness, and Responsible AI
The broader hackathon context requires explicit attention to bias, fairness, and post-deployment thinking.

### 11.1 Likely bias sources
Potential bias sources include:
- non-native English being mistaken for malicious intent
- unfamiliar domains being over-penalized versus major brands
- datasets overrepresenting obvious phishing but underrepresenting benign edge cases
- overuse of urgency cues causing false positives on legitimate reminders

### 11.2 Required mitigation strategy
Include at least these mitigations:
- evaluate false positives on awkward but legitimate messages
- preserve the middle label **Needs Review** for ambiguity
- log model disagreements and false-positive patterns
- keep the reasoning transparent and user-readable

### 11.3 Responsible AI posture
The system should be framed as:
- decision support
- user education
- confidence-building guidance

It should **not** be framed as:
- perfect automated truth
- guaranteed fraud detection
- fully autonomous cyber enforcement

---

## 12. Dev + Ops Monitoring Plan
The solution should show lifecycle thinking, not just a one-time prototype.

### 12.1 Monitor these categories
#### Prompt/output drift
Watch for changes in output style or label behavior over time.

#### Data quality
Watch for:
- malformed pasted input
- missing URLs
- noisy copied email content
- extraction failures

#### False positives
Monitor whether safe messages are being flagged too aggressively.

#### Fairness checks
Monitor performance on:
- non-native writing
- awkward but benign language
- unfamiliar organizations/domains

#### Threat-intel connector health
Monitor:
- VirusTotal timeouts
- API quota exhaustion
- missing enrichment results

#### User feedback
If implemented, store simple feedback such as:
- this was helpful
- this looked wrong
- this should have been flagged differently

---

## 13. Recommended System Architecture
### 13.1 Architecture overview
Recommended modules:
- frontend inbox simulator + paste form
- backend analysis API
- heuristic feature extraction service
- URL/domain enrichment service
- OpenAI LLM client
- output normalizer
- evaluation harness
- seeded demo data store

### 13.2 Architectural principle
The engine should be **modular and integration-ready**.

Meaning:
- current UI can be simulated inbox
- future UI can be Gmail/Outlook plugin
- backend analysis service should remain reusable

---

## 14. Recommended Tech Stack
### 14.1 Stack recommendation
- **Frontend:** Flask templates or similarly lightweight web UI
- **Backend:** Python
- **AI API:** OpenAI API
- **Threat intel:** VirusTotal API
- **Data/evaluation:** CSV/JSON benchmark harness
- **Deployment:** local demo first, cloud only if stable

### 14.2 Why this stack is recommended
It minimizes:
- environment complexity
- frontend overhead
- integration debugging
- setup friction for Codex/LLM-assisted development

---

## 15. Prompt Contract for the LLM
The backend should enforce a structured response format.

Recommended shape:

```json
{
  "label": "Safe | Needs Review | Likely Phishing",
  "confidence": "low | medium | high",
  "top_reasons": ["...", "...", "..."],
  "recommended_actions": ["...", "...", "..."],
  "technical_signals": {
    "urgency": true,
    "credential_request": false,
    "domain_mismatch": true,
    "shortened_link": false
  }
}
```

### 15.1 Prompt rules
The prompt should instruct the model to:
- use plain language for the user-facing output
- admit uncertainty when appropriate
- avoid unsupported certainty claims
- never output alternative label names
- keep the result concise and actionable

---

## 16. MVP Definition of Done
### 16.1 P0 - absolutely required
These must exist before anything else matters:
- analysis endpoint works reliably
- only the three approved labels are used
- reasons and actions render clearly in the UI
- inbox simulator contains enough demo emails for presentation

### 16.2 P1 - strong additions
Add next if stable:
- VirusTotal URL enrichment
- advanced details drawer
- evaluation script / benchmark runner

### 16.3 P2 - stretch only
Only attempt after P0 and P1 are stable:
- read-only Gmail integration
- read-only Outlook integration
- browser extension or add-in shell

---

## 17. Build Order for Codex or Another LLM
Use this exact sequence.

1. create repo scaffold
2. create environment/config files
3. build mock analyzer endpoint with fixed JSON
4. implement deterministic phishing-feature extractor
5. integrate OpenAI API
6. normalize output schema and labels
7. build result cards in the UI
8. seed demo inbox with public/synthetic examples
9. integrate VirusTotal lookup
10. add evaluation harness
11. polish inbox-style demo flow
12. attempt live email integration only if core system is stable

---

## 18. Suggested Repository Structure
```text
app/
  routes.py
  services/
    analyzer.py
    heuristics.py
    llm_client.py
    virustotal_client.py
    normalizer.py
  templates/
  static/
  demo_data/
  eval/
    benchmark_runner.py
    datasets/
  tests/
.env.example
requirements.txt
README.md
```

---

## 19. API Integration Notes
### 19.1 OpenAI API
Role:
- primary phishing reasoning engine
- explanation generation
- final structured result generation

Rule:
- keep prompt versions and schema versions explicit and testable

### 19.2 VirusTotal API
Role:
- URL/domain enrichment
- extra evidence layer for suspicious links

Rule:
- product must still work if VirusTotal is unavailable

### 19.3 Mail-provider APIs
Examples:
- Gmail API
- Outlook / Microsoft Graph API

Rule:
- these are later-stage integrations, not day-one dependencies

---

## 20. Demo Narrative
Use a simple demo flow.

1. open the inbox simulator
2. select a normal safe message -> Safe
3. select a borderline message -> Needs Review
4. select an obvious phishing message -> Likely Phishing
5. paste a suspicious URL -> show URL enrichment and explanation
6. explain that the same analysis service can plug into Gmail/Outlook later

The pitch should make it clear that:
- the engine is real
- the automation shell is credible
- the product can scale beyond the demo

---

## 21. Stretch Roadmap If Time Permits
Potential stretch goals:
- read-only Gmail integration
- read-only Outlook integration
- browser extension shell
- multilingual explanations
- privacy auto-redaction mode
- teach-back micro lessons
- exportable report summary

---

## 22. Risks and Anti-Patterns
Avoid these mistakes.

### 22.1 Starting with live integration
Danger:
- OAuth, permissions, and provider debugging can consume the whole project

### 22.2 Over-explaining the UI
Danger:
- overwhelms non-technical users
- makes the interface feel less polished

### 22.3 Inconsistent labels
Danger:
- confuses implementation
- weakens the pitch
- creates presentation mismatch

### 22.4 Overreliance on the LLM
Danger:
- output drift
- unsupported confidence
- weaker explainability

### 22.5 No benchmark testing
Danger:
- demo fails on simple examples
- team cannot defend quality claims

---

## 23. Immediate Next Actions
These are the first practical steps.

1. create repo/environment scaffold
2. collect benchmark phishing and benign datasets
3. build analyzer service with mock JSON output
4. integrate OpenAI API and lock response schema
5. build seeded inbox demo
6. add VirusTotal lookup service
7. run regression tests and tune prompts
8. prepare demo script and pitch flow

---

## 24. One-Sentence Build Rule
**Do not build the plugin first. Build the analysis engine first, present it like a plugin-ready product, and only chase live integration after the core is stable.**
