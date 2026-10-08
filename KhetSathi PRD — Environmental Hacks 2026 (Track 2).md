# KhetSathi — Product Requirements Document

Environmental Hacks 2026 · Track 2: Heat and Water · Build window 8–11 Oct 2026 · Hackathon MVP v1.0

## 0. How to read this document

Every claim is tagged where it matters:

- **\[FACT\]** established or verifiable outside this project
- **\[ASSUMPTION\]** a design belief not yet validated
- **\[SIM\]** produced by simulation, never field-measured
- **\[FUTURE\]** not built during the hackathon

Thresholds carry one of: **\[SOURCE\]** (taken from a cited reference such as FAO-56 tables), **\[CONFIG\]** (farmer/plot/crop-configurable), **\[MODEL\]** (depends on model calibration), **\[DEMO\]** (placeholder to make the demo run; not agronomic advice).

No farmer interviews, field trials, partnerships or measured savings exist. Personas are design personas only.

## 1. Product definition and positioning

**Definition:** KhetSathi is an irrigation decision system that tells a farmer, once a day, whether to irrigate a field, and if so when and for how long, with the reasons.

**Positioning:** Solar pumps make irrigation clean. KhetSathi makes it sustainable. By combining satellite, weather, crop and water data, KhetSathi estimates the irrigation a crop needs and recommends the minimum safe irrigation action supported by its available inputs and configured agronomic constraints.

**Principle:** One field. One daily water decision.

**Careful environmental hypothesis \[ASSUMPTION\]:** Solar irrigation can reduce the direct fuel-cost barrier to pumping, which may increase the risk of unnecessary or prolonged pumping in some contexts. We do not claim solar pumps universally cause depletion. KhetSathi addresses the resulting management problem by basing irrigation on crop and environmental conditions instead of habit or a fixed schedule. It is designed to reduce unnecessary irrigation and therefore unnecessary water extraction; it has not been shown to do so in the field.

## 2. Problem statement

&#91;FACT\] Groundwater is a shared, depleting resource in much of India, and irrigation is its largest draw. \[SOURCE TO VERIFY BEFORE SUBMISSION\] \[FACT\] Farmers commonly irrigate by habit, fixed schedule or visual guess, without a daily estimate of what the crop needs after rainfall and evapotranspiration. \[SOURCE TO VERIFY BEFORE SUBMISSION\] \[ASSUMPTION\] Where pumping is cheap at the margin, over-irrigation is easy and invisible. \[ASSUMPTION\] Smallholders lack tools that convert weather, soil and crop information into one trustworthy daily action. KhetSathi focuses on exactly this decision: irrigate or skip, when, how long, and why.

## 3. Track 2 fit, goals, non-goals

**Primary outcome:** less unnecessary water extraction and better irrigation efficiency while meeting crop need.

**Goals**

1. Produce a reproducible, explainable and safety-checked IRRIGATE/SKIP decision per plot per day.
2. Never let a learned or optimization component override agronomic safety constraints.
3. Demonstrate, via labelled simulation, the difference versus a simple fixed schedule.
4. Run on a small, visible AWS serverless stack.

**Non-goals:** chatbot, generic farming assistant, weather app, raw soil dashboard, groundwater monitoring system, marketplace, price app, farm management suite, autonomous pump control.

## 4. Personas (design personas, not research findings)

**P1 — Representative farmer (primary).** 1-hectare farmer in Odisha or Bihar, using or moving to a solar pump. Low-to-moderate digital literacy, Android phone, intermittent connectivity, Hindi-comfortable for the demo. Needs: a single clear instruction before the morning irrigation window, in voice, with a reason she can accept. Fears: crop loss from skipping; confusing apps. Success: follows the recommendation and taps DONE.

**P2 — FPO operator (secondary).** Manages many member plots and sometimes shared pumps. Needs: a list of plots with today's action and which plots have stale data. Success: sees 'which plots need water today' at a glance. Multi-plot view is Should-have.

**P3 — Extension/KVK user (secondary).** Advises farmers and reviews logic. Needs: transparent reasons and the configured crop/safety parameters so she can challenge them. Success: can review the configured crop and safety parameters and understand why a decision was produced. Parameter editing is \[FUTURE\] and would require proper authorization.

## 5. Core journey

SENSE → DECIDE → PROTECT → EXPLAIN → DELIVER → LEARN

- **SENSE:** fetch weather, rainfall, optional satellite proxy and plot inputs; record timestamps.
- **DECIDE:** estimate crop water need and root-zone depletion; propose action, time, duration.
- **PROTECT:** independent safety layer validates or modifies the proposal.
- **EXPLAIN:** deterministic reasons built from the actual decision facts.
- **DELIVER:** large-button PWA plus Hindi voice; text and icons always work.
- **LEARN:** DONE / NOT DONE feedback stored for adherence metrics and future calibration.

## 6. MVP scope

**Must have:** plot onboarding; crop and stage setup; environmental ingestion; plot-state generation; irrigation-need estimation; baseline strategy; safety layer; rule-based explanation; IRRIGATE/SKIP with time and duration; PWA; Hindi voice; DONE/NOT DONE; decision history; baseline-vs-KhetSathi simulation; environmental metrics; AWS infrastructure; logging and monitoring. (Learned model layer is conditional, see section 9.)

**Should have:** localized UI; confidence/data-freshness indicator; multi-plot FPO view; additional satellite proxy.

**Nice to have:** live sensors, real pump controller, WhatsApp, IVR, more languages, advanced RL.

**Out of scope:** sell/hold advice, mandi prices, post-harvest loss, cold storage, marketplace, full farm management, nationwide deployment, autonomous pump deployment, groundwater forecasting, microservice architecture.

**Demo crop \[ASSUMPTION\]:** choose one non-paddy crop (for example maize or a vegetable) for the demo. \[FACT\] Paddy uses ponding/puddling water management that would widen scope. \[SOURCE TO VERIFY BEFORE SUBMISSION\]

## 7. Functional requirements

Priority: P0 = must ship, P1 = should, P2 = nice. Actors: F = farmer, O = FPO operator, S = system, E = extension user.

| ID | Description | Actor | Inputs → Outputs | Acceptance criteria | Pri |
| --- | --- | --- | --- | --- | --- |
| FR-01 | Farmer onboarding | F | Alias, language, plot code → farmer record | Completes in 5 or fewer inputs; no phone number, Aadhaar or exact address required | P0 |
| FR-02 | Plot creation | F | Location (map pin or district centre), area (ha), pump discharge, pump power, soil texture class → plot record | Invalid values rejected with plain-language message; record persisted in DynamoDB | P0 |
| FR-03 | Crop setup | F | Crop from supported list, sowing date → crop config | At least one crop with configured Kc values, stage lengths and allowed depletion | P0 |
| FR-04 | Crop stage | S, F | Sowing date, stage table, optional farmer override → current stage, Kc | Stage changes on configured day counts; override is logged and flagged | P0 |
| FR-05 | Weather ingestion | S | Plot coordinates → forecast temp, humidity, wind, radiation, rain with timestamp | Timestamp stored; provider failure triggers fallback (section 17) | P0 |
| FR-06 | Rainfall handling | S | Recent and forecast rain → effective rainfall (mm) | Effective rain computed by a configured rule; rule shown in explanation | P0 |
| FR-07 | Soil inputs | F, S | Texture class, optional farmer-reported feel (dry/ok/wet) → water-holding parameters | Parameters come from a configurable lookup; farmer-reported input is optional and never overrides safety | P0 texture, P1 report |
| FR-08 | Satellite-derived proxy | S | Plot polygon/point → NDVI or similar proxy with date | Used only as a crop-condition/data-quality signal; absence never blocks a decision | P1 |
| FR-09 | ET0 and crop water requirement | S | Weather, Kc → ET0, ETc (mm/day) | ETc = Kc × ET0; unit test against a published FAO-56 worked example | P0 |
| FR-10 | Current water state | S | ETc, effective rain, past irrigation, soil params → estimated root-zone depletion (mm) | Deterministic and reproducible from stored inputs; fixture-tested | P0 |
| FR-11 | Irrigation decision | S | Plot state → IRRIGATE or SKIP | One action per plot per day, always with a safety status | P0 |
| FR-12 | Irrigation timing | S | Decision, rain timing, allowed windows → start time | Start time is in the future and inside a configured window | P0 |
| FR-13 | Irrigation duration | S | Depth required, pump discharge, area, efficiency → minutes | Minutes = depth ÷ application rate; never exceeds the cap | P0 |
| FR-14 | Rainfall skip logic | S | Forecast effective rain, required depth → skip flag | Skips only when forecast rain covers the configured fraction of need; reason shown | P0 |
| FR-15 | Safety constraints | S | Proposal + plot state → final decision, safety status | Module is independent of any model; unit tests cover each rule; every override is logged | P0 |
| FR-16 | Explanation | S | Final decision facts → ordered reasons | Each reason maps to a real fact in the record; no free-text invention | P0 |
| FR-17 | Voice output | F | Explanation text → Hindi audio | Audio plays in the PWA; on failure, text and icons display with no error blocking the decision | P0 |
| FR-18 | Decision history | F, O, E | Plot ID → list of past decisions | Shows date, action, duration, status, feedback; paginated | P0 |
| FR-19 | Feedback | F | DONE / NOT DONE (+ optional reason icon) → feedback record | Feedback is submitted when connectivity is available; if the device is offline, the UI shows the action as pending and does not claim it has been stored until synchronization succeeds; stored against the decision on success | P0 |
| FR-20 | Simulation | E, judges | Historical weather, crop config, baseline rule → comparison run | Same seed/inputs give identical output; reproducible by one command | P0 |
| FR-21 | Environmental metrics | S | Simulation and decision logs → impact metrics | Every simulated number is labelled SIMULATED in UI and README | P0 |
| FR-22 | Freshness/confidence indicator | F | Data timestamps, missing inputs → status badge | Badge degrades when inputs are stale or missing | P1 |
| FR-23 | FPO multi-plot view | O | Plot list → today's actions | Shows each plot's action and stale-data flags | P1 |
| FR-24 | Scheduled and manual workflow | S, E | Schedule or manual trigger → decision per plot | Daily run fires on schedule; manual trigger exists for the demo | P0 |
| FR-25 | Logging and monitoring | S | Execution events → logs, metrics, alarm | Each run logs plot ID, inputs' timestamps, outcome; one alarm on repeated failure | P0 |

## 8. Decision pipeline

Environmental Inputs → Plot State → Baseline → Model/Optimization Proposal → Safety Layer → Final Decision → Explanation → Delivery → Feedback

**Principle: AI proposes; agronomic constraints control what can be deployed.**

1. **Plot State:** crop, stage, Kc, ET0, ETc, effective rain, estimated depletion, last irrigation, data freshness.
2. **Baseline:** deterministic soil-water-balance rule. Irrigate when estimated depletion reaches the allowed depletion; apply the depth needed to refill, bounded by caps.
3. **Optional proposal:** a learned or optimization component may propose a different action or timing.
4. **Safety layer:** validates or modifies any proposal. It reads only plot state and configuration, never model internals.
5. **Final decision:** action, time, duration, data timestamp, safety status, reasons.
6. **Delivery and feedback:** stored, served via API, voiced, then confirmed by the farmer.

## 9. Model strategy

| Option | Needed for MVP? | Reasoning |
| --- | --- | --- |
| Deterministic rules (soil-water balance) | **Yes, this is the decision engine** | Established agronomy, transparent, testable, works with no training data |
| Supervised ML | No | No labelled field outcomes exist; fabricating labels would be misleading |
| Reinforcement learning | **Stretch only (P2)** | Justified only as a policy trained in our own simulator to tune timing/skip thresholds; not required for a credible MVP |

**Decision \[ASSUMPTION\]:** ship the deterministic engine as the product. The core must run with any learned component removed. Include RL only if Day 3 has spare capacity and it can beat the baseline in simulation under the same constraints; otherwise cut without touching the demo story.

**If RL is retained**

- **Learns:** a skip/irrigate-and-timing policy that reduces applied water while keeping depletion inside limits, trained only in the simulator \[SIM\].
- **State:** depletion (binned), stage, forecast effective rain over next days, days since last irrigation.
- **Action:** skip, or irrigate with duration level (for example a few discrete steps).
- **Reward:** negative water applied, large penalty for depletion beyond allowed limit, small penalty for events.
- **Constraints:** the same safety layer wraps the policy during training and inference.
- **Training:** tabular or small-network method over historical weather replays in a simulator built from the same water-balance equations; offline, not on AWS-hosted GPUs.
- **Inference:** the policy output is just a proposal handed to the safety layer; if it fails or is absent, the baseline decision stands.

Note: the earlier KhetSathi concept described RL as central. For this hackathon it is not presented as already-built, and it is not on the critical path.

## 10. Agronomic safety layer

Inspired by FAO-56 water-balance principles. We do not invent authoritative thresholds; every value below is tagged.

| Constraint | Behavior | Value source |
| --- | --- | --- |
| Allowed depletion fraction (p) | Irrigate only when depletion reaches the crop/stage allowed fraction of available water | \[SOURCE\] crop-specific FAO-56 guidance, entered via config and \[CONFIG\]; cite the table used |
| Soil water-holding parameters | Derived from texture class | \[SOURCE\]/\[CONFIG\] lookup; document the source used |
| Rainfall skip condition | Skip if forecast effective rain covers a configured share of required depth within the horizon | \[CONFIG\], \[DEMO\] default |
| Maximum duration per event | Cap minutes regardless of proposal | \[CONFIG\], \[DEMO\] default |
| Maximum daily irrigation depth | Cap depth per day | \[CONFIG\], \[DEMO\] default |
| Minimum interval between events | Prevent back-to-back events | \[CONFIG\], \[DEMO\] default |
| Crop-stage restrictions | Some stages forbid skipping when depletion is high, or limit applications | \[CONFIG\], needs extension-expert review |
| Data-quality checks | Block 'SKIP because dry-looking proxy' type errors: stale or missing critical inputs trigger the conservative path | \[CONFIG\] |
| Uncertainty handling | If forecast rain is the only reason to skip and confidence is low, do not skip when depletion is near the limit | \[MODEL\]/\[CONFIG\] |

**Conservative rule:** when critical data is missing or conflicting, the system never recommends a risky skip and never an uncapped irrigation. It falls back to the safest configured behavior and says so.

Every safety override is stored with the original proposal, the rule that fired and the modified result.

## 11. Explainability

Minimum decision record: action, date/time, duration, data timestamp, reasons, safety status.

Reasons come from deterministic templates filled only with computed facts. Example (illustrative):

**SKIP IRRIGATION**

1. Adequate rainfall is expected.
2. Current estimated root-zone water availability is sufficient.
3. Additional pumping is therefore unnecessary.

**IRRIGATE — tomorrow 6:00 AM, 45 minutes (illustrative values)**

1. Rainfall is insufficient for the crop's current need.
2. Estimated root-zone depletion is above the configured threshold.
3. The proposed duration is within safety limits.

An LLM is not used in the core MVP. If introduced later, it may only rephrase verified facts and can never decide.

## 12. Voice-first experience

- Large buttons, icons, minimal text, simple vocabulary.
- Demonstrate one language: Hindi. We do not claim other languages.
- Voice is a delivery layer only; it plays the already-final explanation.
- If voice generation or playback fails, text and icons still show the full decision.
- Feedback is confirmed with a clear visual state (and voice if available).

## 13. Data

| Data | Type | Source (to verify availability and terms on Day 1) | Update | Storage | Fallback |
| --- | --- | --- | --- | --- | --- |
| Weather forecast, ET0 | External real | Public forecast API (for example Open-Meteo) | Daily | DynamoDB snapshot | Last good snapshot, flagged stale; else compute ET0 from cached climatology |
| Rainfall (recent and forecast) | External real / historical | Same forecast API; public historical sets | Daily | DynamoDB | Last snapshot; conservative path |
| Satellite proxy (NDVI) | External real | Public Sentinel-2 data (AWS Open Data registry) | Every few days | S3 cache, summary in DynamoDB | Omit; no blocking |
| Soil texture parameters | Lookup/reference | Configured table with cited source | Static | Config in repo | Default texture flagged |
| Historical weather for simulation | Historical public | Public archive for chosen district and season | Static | S3 | Bundled sample file |
| Plot, crop, pump | User input | Onboarding | On change | DynamoDB | Required fields; no default |
| Irrigation done | User input | Feedback | Per event | DynamoDB | Assume NOT DONE unless stated |
| Sensor moisture | Optional / future | Hardware | n/a | n/a | Out of MVP |
| Simulated farm outcomes | Simulated | Our simulator | On demand | S3 | Labelled SIMULATED always |

Simulation output is never presented as field validation.

## 14. Baseline vs KhetSathi

**Counterfactual \[SIM\]:** replay one historical season of weather for one location and crop.

- **Baseline:** fixed interval schedule with a fixed duration (for example every few days, same minutes regardless of rain) \[DEMO\] parameters, documented in the repo.
- **KhetSathi:** the same simulator with the daily water-balance decision plus safety layer.
- **Same** soil, crop, pump discharge, pump power and weather in both runs.
- **Compared:** irrigation events, pump hours, estimated water applied, estimated extraction, estimated pump energy.
- **Also report** days where depletion exceeded the allowed limit in each strategy, so savings are not achieved by starving the crop.
- **Reproducibility:** a single script with fixed inputs and a seed; its output file is stored in S3 and displayed in the app.

Estimated extraction equals applied water divided by an assumed system efficiency \[ASSUMPTION\], stated plainly. Energy equals pump kW × pump hours (solar energy is free at the margin, so this is pump load, not a cost claim).

The simulation demonstrates model/system behavior under defined assumptions. It is not evidence of field performance, measured groundwater savings or actual farmer behavior.

## 15. Environmental and product metrics

**Primary \[SIM\]:** estimated water saved per hectare; avoided irrigation events; avoided pump hours; estimated extraction avoided.

**Secondary:** farmer adherence (DONE rate); recommendation acceptance; decision latency; system reliability (successful daily runs).

All results are labelled SIMULATED. We make no claim about measured field savings or groundwater levels.

## Claims We Do Not Make

- We do not claim field-validated water savings.
- We do not claim measured groundwater recovery.
- We do not claim that solar irrigation universally causes over-pumping.
- We do not claim the model is agronomically optimal.
- We do not claim that simulated savings equal real-world outcomes.
- We do not claim support for languages or hardware not demonstrated.

## 16. UX requirements

| Screen | Purpose and content |
| --- | --- |
| 1. Onboarding | Language choice, alias, plot code; very few inputs |
| 2. Plot setup | Location pin, area, pump details, soil type, crop, sowing date; icons and examples |
| 3. Today's Decision (primary) | Giant **IRRIGATE** or **SKIP**; if irrigate: **WHEN**, **HOW LONG**, **WHY**; play-voice button; freshness badge; DONE / NOT DONE buttons |
| 4. Why? | Ordered reasons, data timestamp, safety status, and any override explained plainly |
| 5. History | Past decisions with action, duration, status, feedback |
| 6. Feedback | Large DONE / NOT DONE; optional reason icon for NOT DONE (rain came, no power, other) |
| 7. FPO view (optional) | List of plots with today's action and stale flags |

Accessibility: high contrast, large touch targets, no reliance on color alone, short phrases.

## 17. Edge cases (fail conservatively)

| Case | Behavior |
| --- | --- |
| Missing weather | Use last good snapshot if recent; otherwise water-balance with cached climatology and a visible 'low confidence' flag; no risky skip |
| Stale data | Badge shows age; beyond a configured age, avoid skip-by-forecast |
| Missing sensor | Ignore; sensors are optional |
| Conflicting inputs | Prefer the safer outcome (protect the crop within caps); record the conflict |
| Model failure | Use baseline decision; log the failure |
| Safety failure | If the safety layer errors, no autonomous recommendation: show 'Check manually' with last confirmed state |
| Voice failure | Text and icons only |
| API failure | PWA shows the last cached decision with its timestamp; feedback shown as pending until submission succeeds |
| AWS failure | CloudWatch alarm; cached last decision; no fabricated decision |
| Poor connectivity | Cached app shell and last successful decision with its timestamp, feedback shown as pending until submission succeeds, small payloads |

## 18. Privacy and access

- **Minimum data:** alias and language; plot with approximate coordinates (rounded), area, crop, pump specs; feedback events. No Aadhaar, bank, or phone number in the MVP.
- **Farmer identity:** pseudonymous ID; no real name needed.
- **Plot identity:** coordinates rounded to reduce precision.
- **Environmental data:** public; stored with timestamps.
- **Feedback:** tied to plot decision, not to a person.
- **Access control:** for the demo, plot-code access plus API Gateway throttling; least-privilege IAM per Lambda. Authenticated accounts are \[FUTURE\].
- **Secrets:** none committed to the repository; any API key held in encrypted configuration, not source.
- No legal compliance claims are made.

## 19. AWS architecture

**Flow**

1. EventBridge triggers the daily decision workflow.
2. Lambda loads the plot and latest environmental state.
3. The engine processes crop state, weather, rainfall, water status, optional satellite/sensor inputs.
4. A baseline recommendation is generated.
5. The optional model layer may propose a different action.
6. The safety layer validates or modifies the proposal.
7. The final decision and reasons are stored in DynamoDB.
8. If voice is used, the explanation text goes to Amazon Polly and audio is stored in S3.
9. The PWA retrieves the decision (and audio link) through API Gateway.
10. Amplify hosts the frontend.
11. Feedback goes through API Gateway into DynamoDB.
12. CloudWatch records executions, errors and the alarm.

**Service map**

| Service | Product responsibility | Data handled | Why it exists | What judges will see |
| --- | --- | --- | --- | --- |
| Amplify Hosting | Serves the PWA | Static app | Zero-ops hosting | Live app URL, deploy history |
| API Gateway | Front door for decision, history, feedback, trigger | JSON requests | Secure, throttled API | Routes list, request logs |
| Lambda | Ingest, decide (baseline + safety + explain), voice, feedback, simulate | Plot state, decisions | Pay-per-run compute, no servers | Function list, invocation logs |
| EventBridge | Daily schedule per plot run | Schedule event | Makes the decision proactive | Schedule rule firing at set time |
| DynamoDB | Plots, crops, snapshots, decisions, feedback | Small structured records | Single serverless datastore | Items showing decision and reasons |
| S3 | Polly audio, cached satellite summaries, simulation outputs | Files | Cheap object storage | Audio object, simulation report |
| CloudWatch | Logs, metrics, alarm | Execution telemetry | Reliability evidence | Log stream of a run, metric, alarm |
| Amazon Polly | Hindi speech from final explanation | Explanation text | Voice delivery | Generated audio played in app |

No EC2, ECS, EKS, always-on servers, extra databases or brokers. Generative AI services are not used in the core path. Infrastructure is defined as code (SAM or CDK) in the repository as build tooling, not a runtime service. Confirm Polly Hindi voice availability in the chosen region on Day 1.

### Minimum AWS Proof for Submission

The demo must visibly demonstrate at least the following real AWS paths. Saying we use AWS in narration, or showing an architecture diagram alone, is insufficient; the AWS components must be visibly real in the submitted demo.

**Request path:** PWA → API Gateway → Lambda → DynamoDB → PWA

**Scheduled path:** EventBridge → Lambda → DynamoDB

**Optional:** Lambda → Polly → S3 → PWA audio playback

## 20. Non-functional requirements

### Performance

- Decision latency under a few seconds per plot for the demo \[ASSUMPTION\].
- Reading today's decision in the PWA returns in about 2 seconds on a typical mobile connection \[ASSUMPTION\]; the daily run for all demo plots completes within a few minutes \[ASSUMPTION\].
- Lightweight frontend: low data cost, small payloads, cached PWA that keeps the app shell, the last successful decision and its timestamp.

### Reliability

- Daily run succeeds for all demo plots; failures alarmed.
- Idempotent daily run: repeated scheduled execution for the same plot and date does not create duplicate decisions.
- Failure degrades safely: missing, stale or conflicting inputs and component failures follow the conservative behaviors in section 17; no decision is fabricated.

### Safety

- A learned or optimization proposal can never bypass the safety layer.
- Uncapped irrigation is never emitted; every recommended duration is within configured caps.
- Degraded data conditions (stale, missing, low confidence) are visible to the user.
- Core math and safety rules are unit-tested; simulation is reproducible.

### Usability

- The core decision is understandable without technical knowledge.
- Large touch targets; no reliance on color alone.
- Minimal interaction count: today's action is visible on opening and feedback takes one tap.
- Voice is optional, not mandatory; text and icons always work.

### Observability

- Each decision is traceable to its input timestamps, rule outcomes and safety status.
- AWS executions are logged in CloudWatch.
- Repeated job or API failures are observable through a CloudWatch alarm.

## MVP Release Criteria

The MVP is submission-ready only when all P0 requirements below are satisfied. This is a product-level release gate.

1. A new plot can be created.
2. A daily irrigation decision can be generated.
3. The decision is reproducible and explainable.
4. The safety layer can modify or reject an unsafe proposal.
5. The farmer can see IRRIGATE or SKIP.
6. When irrigation is recommended, the farmer can see the recommended time and duration.
7. The farmer can submit DONE or NOT DONE when connectivity is available.
8. Decision history works.
9. Baseline-vs-KhetSathi simulation works reproducibly.
10. Simulated environmental metrics are visibly labelled SIMULATED.
11. The AWS-backed request path works end to end.
12. The EventBridge-triggered daily workflow works.
13. The deployed frontend is accessible through a public URL.
14. The submitted demo can visibly show the AWS components actually being used.
15. No unresolved P0 safety or reliability defect remains.

## 21. New build boundary

| Prior KhetSathi concept/research (reference only) | Newly built during 8–11 Oct 2026 |
| --- | --- |
| Ideas: solar irrigation, ET0, FAO-56 safety logic, RL, voice-first, PWA, feedback | AWS serverless infrastructure and IaC |
| FastAPI/MQTT/PostgreSQL design | Daily decision workflow (EventBridge → Lambda → DynamoDB) |
| Sell/hold, mandi, post-harvest, FPO-scale ideas | Data layer and ingestion |
| Earlier concept document | Safety layer, explanation templates, frontend PWA, Polly voice, simulation, feedback, monitoring, demo video |

Prior material is cited as inspiration only. The README must list the commit range for hackathon work and say that earlier ideas were not code.

## 22. Four-day build plan (8–11 Oct)

| Day | MUST SHIP | SHOULD SHIP | CUT IF LIMITED |
| --- | --- | --- | --- |
| 1 | AWS foundation (IaC, DynamoDB, API, Lambda skeleton); data model; frontend shell; baseline decision engine with unit tests | Region/Polly check; CI | Custom domain |
| 2 | Weather/rain ingestion; ET0/ETc; water balance; decision, timing, duration; safety layer; explanation templates | Satellite proxy; freshness badge | Sensor input |
| 3 | EventBridge schedule; simulation and metrics; Polly Hindi voice; feedback; history; frontend integration | FPO view; localized UI | RL experiment |
| 4 | Testing; CloudWatch alarm; deploy on Amplify; README, architecture diagram, repo cleanup; record demo; write-up and submit | Polish copy | Anything unfinished from Day 3 |

Scope rule: no new feature after Day 3 midday. If behind, cut in this order: RL, FPO view, satellite proxy, localization, voice (keep text).

## 23. Risks

- **API availability or terms:** cache sample data in S3 and bundle a fixture.
- **Agronomic credibility:** extension review of parameters; label demo values.
- **Scope creep:** the out-of-scope list is binding.
- **Over-claiming impact:** all savings labelled SIMULATED.
- **Judges cannot see AWS:** plan explicit console and log shots in the video.

## 24. Demo video (max 3:00)

| Time | Content |
| --- | --- |
| 0:00–0:20 | Environmental problem: unnecessary pumping and groundwater pressure |
| 0:20–0:40 | Target farmer and context |
| 0:40–1:25 | KhetSathi produces today's decision (IRRIGATE/SKIP, when, how long), Hindi voice |
| 1:25–1:50 | Why screen and safety layer protecting the decision (show an override) |
| 1:50–2:10 | Farmer taps DONE / NOT DONE; history updates |
| 2:10–2:35 | Baseline vs KhetSathi, clearly labelled SIMULATED |
| 2:35–3:00 | AWS on screen: EventBridge rule, Lambda run in CloudWatch, DynamoDB item, S3 audio, Amplify app, API Gateway |

---

# Final PRD Summary

**1. Product definition.** KhetSathi tells a farmer each day whether to irrigate a field, and if so when and for how long, with verified reasons.

**2. Problem statement.** Irrigation is a major draw on depleting groundwater, and smallholders often irrigate by habit or fixed schedule without a daily estimate of what the crop needs \[FACT; SOURCE TO VERIFY BEFORE SUBMISSION\]. Cheaper pumping, including solar, may increase the risk of unnecessary pumping. KhetSathi targets that irrigation decision, aiming to recommend the minimum safe irrigation action supported by its inputs and configured constraints while avoiding unnecessary extraction.

**3. MVP scope.** Plot and crop setup, environmental ingestion, water-balance baseline, independent safety layer, deterministic explanations, IRRIGATE/SKIP with time and duration, Hindi voice PWA, feedback, history, simulation, impact metrics, AWS serverless backend with monitoring.

**4. AWS service map.** Amplify (frontend), API Gateway (API), Lambda (logic), EventBridge (daily trigger), DynamoDB (state), S3 (audio, caches, simulation), CloudWatch (observability), Polly (Hindi voice).

**5. User journey.** SENSE → DECIDE → PROTECT → EXPLAIN → DELIVER → LEARN.

**6. Core decision flow.** Environmental Inputs → Plot State → Baseline → Model/Optimization Proposal → Safety Layer → Final Decision → Explanation → Delivery → Feedback. AI proposes; agronomic constraints control what can be deployed.

**7. Environmental metrics.** \[SIM\] water saved per hectare, avoided events, avoided pump hours, extraction avoided; plus adherence, acceptance, latency, reliability.

**8. Out of scope.** Sell/hold, mandi prices, post-harvest loss, cold storage, marketplace, full farm management, nationwide deployment, autonomous pumps, groundwater forecasting, microservices.

**9. Four-day plan.** Day 1 foundation and baseline; Day 2 data, safety, explanation; Day 3 workflow, simulation, voice, feedback, integration; Day 4 test, monitor, deploy, demo, submit.

**10. Demo outline.** Problem → farmer → decision → why and safety → feedback → simulated comparison → AWS shown on screen, in 3 minutes or less.
