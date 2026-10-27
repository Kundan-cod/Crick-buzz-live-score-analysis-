# User Interface & Experience Design Document (DESIGN.md)

## Project: Cricbuzz LiveStats: Real-Time Cricket Insights & SQL-Based Analytics
- **Framework:** Streamlit Multi-Page Architecture
- **Theme:** Modern Cricket Analytics (Deep Navy, Turf Emerald, Cricket Gold, Crisp White)
- **Status:** Draft / Awaiting User Approval (Gate 0)
- **Last Updated:** 2026-10-22

---

## 1. Design Philosophy & Aesthetic Principles

The UI of **Cricbuzz LiveStats** is engineered to combine the visual energy of live sports broadcasting with the analytical precision of enterprise business intelligence.

### Core Principles
1. **Rich Aesthetics:** Modern dark-theme foundation avoiding plain or generic browser defaults. Uses curated HSL color palettes, subtle glassmorphism card surfaces, and crisp borders.
2. **High Information Density with Clarity:** Key metrics (runs, overs, wickets, economy) are prioritized through typographic contrast and visual hierarchy.
3. **Responsive State Feedback:** Every interactive element provides immediate visual feedback. Loading states, empty states, and errors are designed gracefully with clear remediation steps.
4. **Accessible & Intuitive Navigation:** Streamlit's native sidebar provides one-click navigation between functional modules, supplemented by breadcrumbs and contextual headers.

---

## 2. Design System & Visual Tokens

### 2.1 Color Palette
```css
/* Core Palette Tokens */
--color-bg-primary:     #0B1220;  /* Deep stadium navy background */
--color-bg-secondary:   #131C2E;  /* Card surface navy */
--color-bg-tertiary:    #182238;  /* Elevated surface / hover card */
--color-border:         #1F2C42;  /* Subtle divider lines */
--color-border-focus:   #14B8A6;  /* Active input teal border */

/* Brand & Data Accents */
--color-accent-gold:    #E8A33D;  /* Cricket trophy gold - leaderboards, highlights */
--color-accent-turf:    #007E61;  /* Outfield emerald - live matches, wins, positive delta */
--color-accent-cyan:    #00A9B4;  /* Strike rate & economy charts */
--color-accent-ruby:    #F0616D;  /* Wickets, dismissals, negative delta, destructive actions */

/* Typography Colors */
--color-text-primary:   #F9FAFB;  /* High contrast primary text */
--color-text-secondary: #94A3B8;  /* Muted metadata labels */
--color-text-tertiary:  #64748B;  /* De-emphasized footnotes & timestamps */
```

### 2.2 Typography
- **Font Family:** `Inter`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`, sans-serif.
- **Hierarchy:**
  - `H1 (Page Title)`: 28px / 700 Bold / `#F9FAFB`
  - `H2 (Section Header)`: 22px / 600 Semi-Bold / `#E8A33D`
  - `H3 (Card Title / Sub-header)`: 16px / 600 Semi-Bold / `#F9FAFB`
  - `Metric Value`: 32px / 800 Extra-Bold / Monospace-friendly numerals
  - `Body Text`: 14px / 400 Regular / Line-height 1.5 / `#CBD5E1`
  - `Caption / Badge`: 11px / 500 Medium / Uppercase / Letter-spacing 0.05em

---

## 3. Page Map & Navigation Flow

```
+-------------------------------------------------------------------------------+
|                               APPLICATION SIDEBAR                             |
|  🏏 Cricbuzz LiveStats (Logo & Version Badge)                                 |
|  ---------------------------------------------------------------------------  |
|  🏠 Home (Overview & Setup)                                                   |
|  🔴 Live Matches (Scorecards & Recent Results)                                |
|  👑 Top Players (Batting & Bowling Leaderboards)                              |
|  ⚡ SQL Analytics (The 25 Analytical Questions)                               |
|  🛠️ CRUD Operations (Manage Records)                                          |
|  ⚙️ Settings (Diagnostics & Cache Governance - Confirmed)                  |
|  ---------------------------------------------------------------------------  |
|  [System Status: SQLite Connected | Mode: Offline-Fixture (Dev)]               |
+-------------------------------------------------------------------------------+
```

### Page Interactions:
1. **Home (`app.py`):**
   - Welcomes users, summarizes system objectives, showcases architecture diagrams, lists technology tags, and provides quick jump-links to documentation and analytical modules.
2. **Live Matches (`pages/1_Live_Matches.py`):**
   - Real-time/recent match feed. Users select match status filter (All, Live, Finished, Upcoming).
   - Match summary card displays team logos/initials, scores, overs, run-rate, required run-rate, and match state.
   - Explicit status badge indicating offline-fixture mode or live feed.
   - Expandable scorecard drawer revealing full batting and bowling scorecards.
3. **Top Player Stats (`pages/2_Top_Players.py`):**
   - Format selector tabs: **Test | ODI | T20I**.
   - Dual leaderboards: Top Run Scorers (Runs, Average, Strike Rate, Centuries) and Top Wicket Takers (Wickets, Economy, 5-Wicket Hauls, Bowling Average).
   - Interactive search and country filter.
4. **SQL Queries & Analytics (`pages/3_SQL_Analytics.py`):**
   - Filter bar by difficulty: **All | Beginner (Q1-Q8) | Intermediate (Q9-Q16) | Advanced (Q17-Q25)**.
   - Question selector dropdown with full question text and business context.
   - Interactive parameters (e.g., Year slider, Minimum Matches input, Team selector).
   - Multi-tab output:
     - Tab 1: **Visual Chart** (Plotly visualization tailored to the question).
     - Tab 2: **Data Table** (Searchable, sortable, exportable CSV).
     - Tab 3: **SQL Query & Execution Plan** (Syntax-highlighted SQL with explanation).
5. **CRUD Operations (`pages/4_CRUD_Operations.py`):**
   - Entity selector: **Players | Matches | Venues**.
   - Sub-tabs: **Create Record | View & Search | Update Record | Delete Record**.
   - Validated forms with inline constraint checks.
   - Destructive action confirmation dialog with explicit entity ID check.
6. **Settings (`pages/5_Settings.py` - Confirmed):**
   - Diagnostic panel: SQLite file size, active connection status, fixture mode status, cache clear button, demo re-seed trigger. No secret keys or database credentials exposed.

---

## 4. Component Design Specifications

### 4.1 KPI Metric Cards
Metric cards are styled with dark slate background, crisp border, and accent color highlights:
```
+-------------------------------------------------------+
|  TOTAL RUNS (ODI)                        [ODIs: 2024] |
|  12,840                                               |
|  ▲ +142 runs in last series | Avg: 58.12 | SR: 93.4   |
+-------------------------------------------------------+
```
- Metric value rendered in high-contrast bold typography.
- Contextual delta badge with green up-arrow (improving) or red down-arrow (declining).

### 4.2 Data Tables
- Powered by `st.dataframe` with custom column configurations (`st.column_config`).
- Numeric columns formatted cleanly (e.g., Strike Rate to 2 decimal places, Run figures formatted with comma separation).
- Text truncation with tooltips on hover.
- Built-in search and column-sorting enabled.

### 4.3 Visualizations (Charts)
Each of the 25 SQL questions is paired with an optimal visualization:
- **Bar Charts:** Team wins (Q5), Large venues by capacity (Q4), Top ODI run scorers (Q3).
- **Grouped / Stacked Bar Charts:** Cross-format player runs (Q11), Home vs Away wins (Q12).
- **Line Charts:** Yearly batting trends (Q16), Quarterly career trajectories (Q25).
- **Donut Charts:** Player role distribution (Q6), Toss decision breakdown (Q17).
- **Scatter Plots:** Batting average vs Strike rate (Q16, Q19), Economy rate vs Wickets (Q18).
- **Radar / Spider Charts:** Multi-dimensional weighted player ranking (Q21).

### 4.4 Form Controls & Input Validation
- Forms are grouped inside `st.form` containers to prevent unnecessary Streamlit reruns during keystrokes.
- Clear submit button with accent styling (`type="primary"`).
- Inline validation displays immediate alerts:
  - Error: Missing required field or invalid format (e.g., negative runs, invalid match date).
  - Warning: Modifying record that has existing match appearances.
  - Success: Record persisted with auto-generated ID displayed.

---

## 5. State Handling & Edge Cases

| State | Visual Treatment | User Guidance |
| :--- | :--- | :--- |
| **Loading State** | `st.spinner("Querying analytics engine...")` or skeleton placeholder | Visual progress spinner while data executes |
| **Empty State** | Illustrated empty card: *"No matches found matching filter criteria"* | Button to "Reset Filters" |
| **Stale Live Data** | Yellow alert banner: *"Displaying cached live scorecard from 12 mins ago (API refresh paused)"* | "Force Refresh" button with rate-limit cooldown |
| **API Error / Rate Limit** | Amber warning: *"API rate limit reached. Switched to verified offline test fixtures."* | Clear badge indicating test fixture mode |
| **Database Exception** | Red alert: *"Unable to complete transaction: Foreign key constraint violation."* | Clear explanation of error without stack traces or secret exposure |

---

## 6. Accessibility & Responsiveness

1. **Color Contrast:** All text meets WCAG AA standard (contrast ratio ≥ 4.5:1 against card backgrounds).
2. **Keyboard Navigation:** Native Streamlit interactive elements support Tab, Enter, and Arrow key navigation.
3. **Responsive Grid:** Uses `st.columns()` with breakpoint awareness; layouts collapse cleanly from 3-4 columns on desktop to 1 column on mobile viewports.
4. **Descriptive Element Keys:** Every input widget possesses an explicit, unique `key` parameter to facilitate automated UI testing and avoid state collisions.
