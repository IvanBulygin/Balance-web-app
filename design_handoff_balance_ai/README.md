# Handoff: Balance AI — Mobile App

## Overview

Balance AI is a wellness-buddy mobile app: an evidence-graded supplement & habit advisor. Users **ask anything** about sleep, stress, focus, energy, recovery, etc. and get back a **ranked answer** (top 3 supplements with dose, form, timing, and an A/B/C evidence grade). They build a **stack** of what they're actually taking, see a **stack-health score** that flags timing conflicts, browse 17 evidence-based topic guides, and get an AI-written monthly recap of what worked.

Original product references:
- https://ivanbulygin.github.io/BalanceAI/
- https://balance-ai-project-agent.onrender.com/
- Figma file: *Balance AI - your wellness buddy.fig* (provided alongside this handoff)

## About the Design Files

The HTML files in this bundle are **design references**, not production code. They are React prototypes built with Babel-in-the-browser to show intended look-and-feel, layout, copy, and interactions.

**Your task:** recreate these designs in the target codebase using its existing patterns, component library, and tooling — React Native, SwiftUI, Flutter, or whatever the project uses. If there is no existing codebase, **React Native + Expo** is the recommended starting point given the iOS-first design.

Do not lift the JSX/CSS verbatim — translate it.

## Fidelity

**High-fidelity** for v2 (the canonical brand-correct version):
- Final brand colors derived from the Figma file (cyan→pink spectrum, brand violet `#5521E5`)
- Final typography (Fraunces display serif standing in for Priego, Inter for UI, JetBrains Mono for numerics)
- Pixel-spec layouts at 390×844 (iPhone 14/15 base)
- Real interaction targets, exact spacing, exact copy

**Lo-fi** is also included (`Wireframes.html`) showing earlier flow exploration — useful for understanding the broader information architecture but **not the canonical design**. When in doubt, follow `Balance App v2.html`.

## Screens / Views

All screens are 390 × 844 (iPhone 14/15). Status bar is the device-provided one; design assumes safe-area top inset of ~54 px and bottom inset of ~28 px (tab-bar padding).

### 1. Onboarding (`OnboardScreen`)
- **Purpose:** First-launch welcome → kicks off intake.
- **Layout:** Full-bleed brand-violet background (`--brand` `#5521E5`) with two soft radial decorations (top-right pink @ 6% alpha, bottom-left magenta @ 8%). Mark + tagline at top, headline + body bottom-anchored.
- **Headline:** Fraunces 44px / 1.15 lh, white, with the second line in italic gradient (cyan→violet→pink).
- **Body:** 15px Inter, color `--brand-soft` (`#ECE5FC`), max-width 90%.
- **Primary CTA:** "Get started" — accent-magenta button `#E978DA`, white text, 14px radius, soft drop-shadow.
- **Secondary:** "I already have an account", text-only.
- **Disclaimer:** "Not medical advice…" 11px, 70% opacity, centered.

### 2. Today / Home (`HomeScreen`)
- **Purpose:** Daily landing. One nudge, today's stack, what's working.
- **Header:** Date eyebrow (12px mono uppercase), "Good morning, *Sam*." 34px Fraunces with italic name. 40px circular avatar top-right.
- **Tonight's nudge card:** Brand-violet `#5521E5`, white text, 22px radius, two decorative circles. Eyebrow "TONIGHT'S NUDGE" 11px tracked uppercase. Headline ~26px Fraunces with italic accent. Sub 13px. Grade-A badge + evidence note row at bottom.
- **Ask bar:** White card with 28px circle (accent-soft bg, magenta spark icon), placeholder text, mic icon. Below it: 3 suggestion pills.
- **Today's stack:** Section header "Today's stack" 22px Fraunces + "3 of 5 done" counter in accent. White card with 5 rows: 22px circle (filled brand-violet w/ check OR outlined), name + dose/timing, optional NEXT pill (accent), grade badge.
- **What's working:** 2-up grid: "Sleep onset −17 min" with 8-bar histogram, "Streak 12 days" with 7-segment progress.
- **Tab bar:** Today (active), Ask, Stack, Learn, Me.

### 3. Progress / Me (`ProgressScreen`)
- **Purpose:** Monthly AI recap + trends.
- **Eyebrow + Hed:** "YOUR MONTH" / "April, *in short*."
- **AI recap card:** 24px circle (accent-soft) + "Balance's read" label. Headline 18px Fraunces with italic stat ("~25%"). Two CTAs: "Keep stack" (brand-soft) + "Try creatine →" (brand-violet).
- **Trends:** Pill nav (Sleep / Energy / Focus / Stress). Active pill is brand-violet. Sleep score card: large number 34px Fraunces, ↑24 trend, 12-bar histogram (last 8 weeks; older bars `--brand-soft`, newer bars `--brand`), x-axis Feb/Mar/Apr.
- **Annotation:** Inset card "+ Magnesium · Feb 28 — The inflection point" with 3×28 px accent rule on the left.
- **What worked:** Card with 3 rows; bullet dot brand-violet (good) or grey (no effect), "Drop?" link in accent for non-performers.

### 4. Ask (`AskScreen`)
- **Purpose:** Chat-first answer flow with ranked recommendation.
- **Top bar:** Back button (left), "Today's chat" 13px (center), + button (right). All 36px white circles with `--sh-1`.
- **User bubble:** Right-aligned, brand-violet bg, white text, 20/20/4/20 radius.
- **AI intro row:** 26px circle w/ spark icon + "Balance" label + "· searched 17 guides" meta.
- **AI verdict:** 22px Fraunces "Start with *magnesium glycinate*. If that doesn't land, stack glycine."
- **Ranked answer card:** White, sectioned. Header eyebrow "TOP 3 · RANKED BY EVIDENCE". Three rows:
  - 24px Fraunces rank number (winner = accent color, others = ink-4)
  - Name (16px 600) + form in italic 12px
  - Mono dose · timing
  - Right-side grade badge
  - Winner row has `--surface-2` bg
- **Explanation paragraph + "View studies" dashed link**
- **Quick follow-up pills:** wrap row.
- **Add-to-stack CTA:** Accent-magenta full-width row, "Recommended" eyebrow + 20px Fraunces "Add Magnesium to my stack", 38px circle + plus on right.
- **Composer (sticky bottom):** 22px-radius white pill, +icon, placeholder, 34px circle send button (brand-violet).

### 5. Learn (`LearnScreen`)
- **Purpose:** Browse 17 topic guides.
- **Hed:** "Learn" 34px Fraunces + "17 evidence-based guides" sub.
- **Search:** 14px-radius white card, `--sh-1`, search-icon + placeholder.
- **Featured card:** Soft gradient bg (sage→moss-2 → in v2 brand-soft → violet), 28px Fraunces "The sleep stack, *actually* explained", "6 supplements · 14 studies · 8 min read" meta. Decorative moon glyph bottom-right.
- **17-topic grid (3 cols):** Each tile is square, 14px padding, top: 32px rounded icon container in tinted bg (grade-A → brand-soft, B → green-soft, C → accent-soft). Bottom: name + grade label.
- **Topics:** Sleep, Stress, Focus, Energy, Muscle, Fat loss, Heart, Joints, Immunity, Skin, Libido, Liver. (12 visible + "Show all 17 →" link.)

### 6. Detail (`DetailScreen`) — Magnesium
- **Hero:** Brand-violet → brand-deep gradient. Back & Bookmark buttons in 12% white circles. Eyebrow "MINERAL · SLEEP · STRESS". H1 "Magnesium" 44px Fraunces. Italic sub-tagline.
- **Quick stats:** 3 mini cards in white-on-violet 8% — Dose, Timing, Grade. Grade card is solid `--brand-soft` w/ "A" 22px serif.
- **Tab pills:** Overview / Dosing / Evidence / Safety. Active = brand-violet.
- **Best for:** Pill row with icons.
- **Why it works:** 22px Fraunces hed + 14px body.
- **Evidence bars:** Card listing 4 outcomes. Each row: name + meta (right-aligned), then 8px-tall bar. Color rules: >70% brand-violet, 50-70% violet, <50% green/ochre.
- **Watch out for:** `--accent-soft` card with magenta eyebrow + 13px body.
- **CTA:** Brand-violet full-width row "Add to my stack" 20px Fraunces + 36px circle plus button (accent-magenta).

### 7. Stack (`StackScreen`)
- **Purpose:** Manage the supplements they take, by goal.
- **Hed:** "My stack" 34px Fraunces + "Edit" link in accent. "5 supplements · 3 goals" sub.
- **Stack-health card:** brand-soft bg with brand-violet border. "STACK HEALTH" eyebrow, "A−" 40px Fraunces, "4 of 5 grade A" sub. Right side: 72×72 SVG progress ring (15-radius, 75/100 dasharray, brand-violet stroke). Below: inline warning chip "Zinc + Magnesium timing — Take 2h apart for best absorption · auto-fix" with accent left rule.
- **By goal sections (3):** Sleep / Muscle / Heart. Each is a card with sticky header (28px icon tile in `--brand-soft`, name 20px Fraunces, "N supps" right-aligned) + N rows. Row = 6px dot (brand-violet on, grey off) + name + timing + grade badge.
- **Add a goal:** Dashed-border placeholder row.

## Interactions & Behavior

- **Tabbar nav:** Single shared component; `window.__bal_nav(key)` is the prototype's nav stub — replace with router push (React Navigation, etc.).
- **Ask flow:** User types → optimistic user bubble → AI intro skeleton (1-2s) → ranked card streams in → follow-ups appear last.
- **Add-to-stack:** From Detail or Ask CTA → confetti/haptic + bottom sheet with form/timing pickers → returns to caller.
- **Stack health "auto-fix":** Tap → modal showing the conflict + suggested new times → confirm reschedules notifications.
- **Today's stack rows:** Tap circle = mark done (optimistic); tap row = open detail modal.
- **Progress pill nav:** Switches metric source for the bar chart with cross-fade (200ms ease-out).
- **All transitions:** 200–280ms, ease-out for entries, ease-in for exits. Respect `prefers-reduced-motion`.

## State Management

Recommended slices:
- `user` — profile, intake answers
- `stack` — supplements with id, name, form, dose, time, goalIds, grade, on/off, takenDates[]
- `goals` — id, name, icon
- `chat` — sessions[], current messages[], currentAnswer (ranked list)
- `evidence` — cached topic guides
- `nudges` — today's primary nudge logic (derive from latest unanswered chat + stack adherence)

Server / API endpoints implied:
- `POST /chat` → returns ranked recommendations + grade + studies cited
- `GET /topics`, `GET /topics/:slug` → guides + supplement detail
- `POST /stack`, `PATCH /stack/:id`, `DELETE /stack/:id`
- `POST /stack/log` → mark a supplement taken
- `GET /recap?month=…` → AI recap text + diagnosed inflection points

## Design Tokens

```
/* Spectrum (signature) */
--c-cyan:    #56B6C6
--c-blue:    #3FA9F5
--c-indigo:  #559BF0
--c-violet:  #8E77E2
--c-magenta: #E978DA
--c-pink:    #F3A9FD

/* Primary */
--brand:       #5521E5
--brand-deep:  #20056C
--brand-soft:  #ECE5FC
--accent:      #E978DA
--accent-soft: #FDE2F8

/* Neutrals */
--bg:        #FFFFFF (page bg has subtle radial spectrum tints)
--surface:   #FFFFFF
--surface-2: #FAFAFA
--surface-3: #F0F0F3
--ink:       #050304
--ink-2:     #3D3D3D
--ink-3:     #7F7F7F
--ink-4:     #A6A6A6
--rule:      #E5E5E5

/* Functional */
--green:      #7AC97F
--green-soft: #D8F1DA
--aqua:       #56B6C6

/* Spectrum gradient (signature) */
linear-gradient(95deg, #56B6C6 0%, #3FA9F5 22%, #559BF0 38%, #8E77E2 56%, #E978DA 78%, #F3A9FD 100%)
```

**Radii:** 12 / 18 / 26 / 32 (sm/md/lg/xl)

**Shadows:**
- `sh-1` `0 1px 2px rgba(32,5,108,0.05), 0 2px 8px rgba(32,5,108,0.05)`
- `sh-2` `0 8px 24px rgba(32,5,108,0.08)`
- `sh-card` `0 1px 0 rgba(32,5,108,0.03), 0 8px 28px rgba(32,5,108,0.06)`

**Type scale:** 10 / 11 / 12 / 13 / 14 / 15 / 16 / 18 / 20 / 22 / 26 / 30 / 34 / 40 / 44

**Spacing:** 4-px base; common values 4 / 8 / 10 / 12 / 14 / 18 / 22 / 28

## Typography

- **Display / Serif:** Priego (from Figma) — substitute with **Fraunces** (variable, opsz 144) when Priego isn't licensed. Used at 18px+ for hed/numbers/quotes. Italic is meaningful — used to accent stats and key nouns.
- **UI / Sans:** Inter (400 / 500 / 600 / 700). Letter-spacing −0.01em globally.
- **Numerics / Mono:** JetBrains Mono — used for doses ("200 mg"), timestamps, and meta eyebrows.

## Assets

- All icons are inline SVG (see `icons.jsx` if you'd like to lift them) — replace with the codebase's icon set or `lucide-react-native`. Custom icons used: Home, Spark, Stack, Book, User, Send, Chevron, Plus, Check, Mic, Search, Bookmark, Back, Heart, Moon, Sun, Leaf, Flame, Brain, Bone, Shield, Droplet, Dumbbell.
- The Figma file contains the **gradient logo lockup** (`/BALANCE_GB_EN/03_01/`) and brand book — extract those instead of redrawing.
- Photos in v1/v2 are placeholders; supply real evidence-graded study card art via product CMS.

## Files in this bundle

- `Balance App v2.html` — **canonical hi-fi mock** (use this)
- `Balance App.html` — earlier olive/clay variant (ignore unless asked to compare)
- `Wireframes.html` — flow exploration / lo-fi (ignore for visuals; useful for IA)

## Recommended starter for Claude Code

```
npx create-expo-app balance-ai --template
# add: react-navigation, zustand, expo-linear-gradient, @expo-google-fonts/fraunces, @expo-google-fonts/inter, @expo-google-fonts/jetbrains-mono, lucide-react-native
```

Then point Claude Code at this folder and the .fig file and ask:
> "Implement the screens described in `design_handoff_balance_ai/README.md` using `Balance App v2.html` as the visual reference. Follow the design tokens exactly. Start with the Today screen and the tab bar."
