# KhetSathi PWA — Frontend Sitemap & Design Specification

> **Target Platform:** Mobile-First Progressive Web App (PWA) | Responsive Desktop/Tablet  
> **Target Audience:** Smallholder farmers (Bihar & Odisha, solar-pump users), FPO field coordinators, Agronomic reviewers & Hackathon judges  
> **Key Design Constraints:** High outdoor sun legibility, large touch targets (>= 48px), voice-first (Hindi Polly playback with audio controls), offline fallback state, strict simulated data disclaimers.

---

## 1. Information Architecture & Sitemap Tree

```
                                      [ / ]
                                Splash / Onboarding
                                (Alias, Language, Code)
                                         |
                                         +------------------------------+
                                         |                              |
                                         v                              v
                                  [ /plot/setup ]                 [ /fpo ]
                                 Plot & Pump Setup             FPO Multi-Plot
                              (Location, Crop, Soil)              Overview
                                         |                              |
                                         v                              |
                           +-----------------------------+              |
                           |     [ /plot/:id/today ]     |<-------------+
                           |   Today's Decision (Hero)   |
                           +-----------------------------+
                             |            |            |
             +---------------+            |            +----------------+
             v                            v                             v
     [ /plot/:id/why ]           [ /plot/:id/feedback ]        [ /plot/:id/history ]
   Factual Explanation &           Execution Status &           30-Day Decision &
      Safety Audits                   Field Report                  Adherence Log
             |                            |                             |
             +----------------------------+-----------------------------+
                                          |
                                          v
                                   [ /simulation ]
                            Counterfactual Impact Replay
                            (KhetSathi vs Baseline Fixed)
```

---

## 2. Core Screen Specifications (1 to 8)

### Screen 1: Welcome & Farmer Onboarding (`/` or `/onboarding`)
* **Purpose:** Frictionless, low-literacy onboarding with $\le 5$ fields. No password, Aadhaar, or complex KYC.
* **Key Components:**
  * Bilingual branding header: **KhetSathi (खेतसाथी)** — *"Suraj Se Sinchai, Samajhdari Se"* (Solar irrigation with intelligence).
  * Language selector toggle: **हिन्दी (Hindi)** / **English**.
  * Farmer alias / name input (e.g., "Ramesh Kumar").
  * Quick-access entry:
    * Primary CTA: **"Create New Plot" (नया खेत जोड़ें)**
    * Secondary: **"Enter Plot Code" (खेत कोड दर्ज करें)** with 6-character input field for existing plots.
    * One-tap Demo CTA: **"Load Demo Plot (Patna Maize)" (डेमो खेत देखें)** for judges.
* **State / Offline Behavior:**
  * Cached in PWA shell for instant opening.

---

### Screen 2: Plot & Crop Configuration (`/plot/setup`)
* **Purpose:** Establish agronomic and hydraulic baselines for the decision engine.
* **Key Components:**
  * **Location selector:** District dropdown (Patna, Gaya, Muzaffarpur, Ganjam, Cuttack) + optional GPS Pin.
  * **Crop selection card:** High-contrast radio cards with crop icons:
    * **Maize (मक्का)** — 125-day Kharif cycle (Default demo crop).
    * **Tomato (टमाटर)** — 145-day cycle.
    * *Notice chip:* Non-paddy crops for precision root-zone estimation.
  * **Sowing Date Picker:** Date selector with "Days Since Sowing" automatic counter.
  * **Field Area (Hectares):** Stepper input (+/- 0.25 ha, default 1.0 ha).
  * **Pump Discharge & Power:** Preset quick toggles (e.g., 2 HP / 120 L/min PM-KUSUM Solar Pump).
  * **Soil Texture Class:** Visual soil tiles:
    * **Loam (दोमट)** — Balanced moisture retention (150 mm/m).
    * **Clay Loam (मटियार दोमट)** — Higher retention (170 mm/m).
    * **Sandy Loam (बलुई दोमट)** — Fast drainage (100 mm/m).
  * **Primary CTA:** Large bottom sticky button: **"Save & Get Decision" (खेत सुरक्षित करें)**.

---

### Screen 3: Today's Decision (Primary Hero Screen) (`/plot/:id/today`)
* **Purpose:** The single central screen for daily farmer interaction: "One field, one daily decision".
* **Key Components:**
  * **Top Bar:** Plot Name, Crop Stage badge (e.g., "Maize • Development Stage / विकास चरण, Day 38"), Connection badge (`Online` / `Offline - Showing Cached`).
  * **Hero Decision Card:**
    * If **IRRIGATE (सिंचाई करें)**: High-contrast emerald/teal card with bold water-drop icon.
      * **Action:** **IRRIGATE TODAY (आज सिंचाई करें)**
      * **Recommended Window:** 06:00 AM – 08:30 AM (Solar morning window to minimize evaporative loss).
      * **Recommended Duration:** **45 Minutes (45 मिनट)**
      * **Estimated Water Extraction:** **5,400 Litres** (~0.7 kWh solar pump energy).
    * If **SKIP (आज सिंचाई न करें)**: High-contrast warm amber card with sunshine/rain-hold icon.
      * **Action:** **SKIP IRRIGATION (आज पानी न दें)**
      * **Key Reason:** Root moisture sufficient + rain expected.
  * **Prominent Voice Playback Bar (Amazon Polly Hindi):**
    * Audio player with Waveform animation, Play/Pause toggle, and 10s replay.
    * Speaker label: *"आवाज़ में सुनें (Listen in Hindi)"*.
    * Text transcript expander: *"आज सुबह 6 बजे 45 मिनट के लिए सिंचाई करें। खेत की मिट्टी में नमी 45% तक पहुंच गई है..."*
  * **Feedback Quick Buttons:**
    * **[ किया (DONE) ]** (Green solid button, 56px height)
    * **[ नहीं किया (NOT DONE) ]** (Neutral outline button, 56px height)
  * **Secondary Actions:**
    * **"Why this decision? (यह सलाह क्यों मिली?)"** -> Expands Screen 4.
    * **"View 30-Day History"** -> Navigates to Screen 5.
* **State / Offline Behavior:**
  * Displays cached today's decision item from localStorage / IndexedDB if offline, marked with *"Last updated: Today 06:00 AM IST"*.

---

### Screen 4: "Why?" Transparent Agronomic & Safety Audit (`/plot/:id/why`)
* **Purpose:** Build farmer and extension officer trust through explainable AI & safety guarantees.
* **Key Components:**
  * **Factual Ordered Reasons (No Hallucinations):**
    1. *"Root-zone water depletion (20.4 mm) reached threshold (18.5 mm)."*
    2. *"Forecast rainfall in next 48h is 0.0 mm (Open-Meteo live feed)."*
    3. *"Current solar pump operating hours match morning low-ET window."*
  * **12-Point Independent Safety Layer Verification Badge:**
    * **Status:** `APPROVED (सुरक्षित प्रमाणित)` with green shield icon.
    * Enforced constraints checklist:
      * [x] Duration capped at 90 min max allowable run.
      * [x] No excessive ponding risk (Sandy loam drainage verified).
      * [x] Heavy rain suppression rule satisfied (< 5 mm rain in 24h).
  * **Live Environmental Telemetry Card:**
    * $ET_0$ Reference Evapotranspiration: 4.8 mm/day
    * $K_c$ Crop Coefficient: 1.05
    * Temperature: 32°C | Humidity: 65% | Wind: 8 km/h.
    * Data Source freshness badge: `Open-Meteo LIVE (2026-10-10 05:30 IST)`.

---

### Screen 5: Decision History & Field Adherence (`/plot/:id/history`)
* **Purpose:** Transparent ledger of past decisions, farmer compliance, and saved water log.
* **Key Components:**
  * **Adherence Summary Card:**
    * Farmer Follow-through Rate: **88% Adherence (22 of 25 days followed)**.
    * Total Water Applied: 54,000 L.
    * Avoided Irrigate Events: 7 skips executed successfully.
  * **Historical Decision Timeline (Last 30 Days):**
    * Daily cards showing: Date, Recommended Action (`IRRIGATE` / `SKIP`), Duration, Safety Status, and Farmer Feedback badge (`DONE` in green, `NOT DONE` in red, `PENDING` in gray).
  * **Filter Toggles:** All, Irrigated, Skipped, Stress Alerts.

---

### Screen 6: Feedback & Execution Log (`/plot/:id/feedback`)
* **Purpose:** Log actual pump usage and ground reality to refine data and build farmer trust.
* **Key Components:**
  * **Status selector:** `Completed Exactly as Advised` / `Ran for Different Duration` / `Did Not Run Pump`.
  * **Actual Run-Time Slider:** 0 to 120 minutes (pre-filled with recommended 45 min).
  * **Optional Field Condition Tag Cloud (Icon-based for low literacy):**
    * [ बिजली कटी (Power Cut) ]
    * [ बारिश हुई (Unexpected Rain) ]
    * [ मोटर खराब (Pump Issue) ]
    * [ मिट्टी गीली थी (Soil was already wet) ]
  * **Submit CTA:** Large button **"Save Feedback (रिपोर्ट दर्ज करें)"**.
  * **Offline sync banner:** *"Saved to phone. Will upload to AWS server once online."*

---

### Screen 7: FPO Multi-Plot Operations Dashboard (`/fpo`)
* **Purpose:** Designed for Farmer Producer Organization (FPO) field coordinators managing multiple member plots and shared solar pumps.
* **Key Components:**
  * **Summary KPI Bar:**
    * Total Managed Plots: 14 plots
    * Irrigating Today: 4 plots (Scheduled stagger)
    * Skipping Today: 10 plots (Moisture conserved)
    * Data Stale / Offline Alert: 1 plot
  * **Member Plot Cards Grid:**
    * Member Name & Plot ID (e.g., `plt_01...` Ramesh - 1.2 ha Maize)
    * Action Pill: `IRRIGATE 45m @ 06:00` or `SKIP`
    * Depletion Bar: Visual soil moisture bar with color gradient (Green = safe, Amber = depletion boundary, Red = stress).
    * Shared Solar Pump Schedule Tracker: Gantt-style pump queue preventing simultaneous demand overloads.

---

### Screen 8: Simulation & Environmental Counterfactual (`/simulation`)
* **Purpose:** Interactive demonstration tool for hackathon judges, agricultural researchers, and extension officers proving environmental water and energy savings.
* **Key Components:**
  * **Mandatory Header Disclaimer:**
    > **[SIMULATED DATA]** All values are simulated using historical weather replays (Bihar & Odisha seasons). This demonstrates algorithmic efficiency relative to a fixed schedule and is not a claim of measured groundwater changes.
  * **Scenario Selector:**
    * *Scenario 1:* Bihar Maize Kharif Season (60-day historical replay, Patna).
    * *Scenario 2:* Odisha Groundnut Rabi Season (45-day replay, Ganjam).
  * **Side-by-Side Comparison Matrix:**
    | Metric | Baseline (Fixed 4-Day Schedule) | KhetSathi Dynamic Engine | Impact / Savings |
    |---|---|---|---|
    | Irrigation Events | 15 events | 1 event | **-14 events (-93%)** |
    | Water Applied | 81,000 Litres | 7,200 Litres | **73,800 L Saved (91.1%)** |
    | Pump Operating Hours | 11.25 hours | 1.00 hour | **10.25 Hours Avoided** |
    | Pump Energy Used | 8.4 kWh | 0.8 kWh | **7.69 kWh Avoided** |
    | Crop Moisture Stress Days | 5 days | 2 days | **-3 Stress Days** |
  * **Interactive Counterfactual Sliders:**
    * Baseline Interval (days between fixed watering: 3, 4, 5 days)
    * Baseline Duration (minutes per watering: 30, 45, 60 min)
    * **"Run Reproducible Replay" CTA** -> Calls `POST /simulation/run` and displays bit-for-bit verified response.

---

## 3. Design System Specification (Stitch Ready)

```yaml
DesignSystem:
  Name: "KhetSathi AgroPrecision"
  TargetDevices: ["MOBILE", "DESKTOP"]
  Palette:
    Background: "#0C110E"          # Deep earthy charcoal-green (high contrast dark mode)
    Surface: "#161E19"             # Elevated card surface
    SurfaceContainer: "#202B24"    # Subtle containers & borders
    PrimaryGreen: "#22C55E"        # Vibrant Agronomic Green (IRRIGATE / Safe)
    PrimaryGreenContainer: "#14532D"
    WaterBlue: "#38BDF8"           # Water volume & pump metric highlight
    WarningAmber: "#F59E0B"        # SKIP decision / Depletion boundary warning
    ErrorRed: "#EF4444"            # Crop stress alert / safety block
    TextPrimary: "#F1F5F9"         # Slate-100 high readability
    TextSecondary: "#94A3B8"       # Slate-400 metadata and labels
    TextMuted: "#64748B"
  Typography:
    FontFamilyHeadline: "Outfit, Inter, sans-serif"
    FontFamilyBody: "Inter, sans-serif"
    FontFamilyNumeric: "JetBrains Mono, monospace" # For Litres, kWh, mm, time
  ShapeLanguage:
    CardRadius: "16px"
    ButtonRadius: "12px"
    ButtonMinHeight: "52px"        # Generous touch targets for field use
```

---

## 4. Stitch Prompt Templates (For Screen Generation)

### Prompt for Screen 3 (Today's Decision - Hero):
```
A mobile-first PWA screen for an Indian farmer using solar irrigation called KhetSathi. 
Dark high-contrast theme (dark earthy charcoal #0C110E background with forest green and cyan accents).
Top header shows "KhetSathi खेतसाथी", Plot "Plot 1 • Maize (Day 38)", and an "Online" badge.
Hero card prominently displays "IRRIGATE TODAY / आज सिंचाई करें" in bold emerald green with water drop icon.
Sub-details in high-legibility cards: Start time "06:00 AM IST", Run Duration "45 Minutes", Water Volume "5,400 Litres", Solar Energy "0.75 kWh".
Audio player card with "सुनें (Hindi Audio)" button, play/pause controls, and audio waveform graphic.
Two massive touch buttons side-by-side: "किया (DONE)" in green and "नहीं किया (NOT DONE)" in outlined grey.
Bottom navigation bar with 4 tabs: Today, Why?, History, Simulation.
```

### Prompt for Screen 8 (Simulation Counterfactual):
```
A dashboard screen for an agricultural hackathon project showing an environmental counterfactual simulation.
Prominent yellow disclaimer banner at top: "[SIMULATED] Historical Weather Replay — Bihar Maize 60 Days".
Side-by-side comparison cards:
Left card "Baseline Fixed Schedule (Every 4 Days)": 15 Events, 81,000 Litres, 11.25 Pump Hours, 5 Stress Days.
Right card "KhetSathi Adaptive AI & Safety": 1 Event, 7,200 Litres, 1.0 Pump Hour, 2 Stress Days.
Highlighted savings banner: "73,800 Litres Water Saved (91.1%) | 10.2 Pump Hours Avoided".
Interactive controls with sliders for Baseline Interval (days) and Baseline Duration (min), and a button "Rerun Bit-for-bit Verification".
Modern data visualization style with clean monospace figures and progress bars.
```
