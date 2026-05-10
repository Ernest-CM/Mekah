# Mekah - Visual Guide
**See exactly what your AI does to the interface**

This guide shows the **visible changes** for every action, profile, and decision flow in the Mekah adaptive UI system.

---

## Table of Contents
1. [The 6 Actions: Before & After](#1-the-6-actions-before--after)
2. [The 5 User Profiles: What Each Sees](#2-the-5-user-profiles-what-each-sees)
3. [The Decision Flow: Step by Step](#3-the-decision-flow-step-by-step)
4. [HITL Reviewer: What Triggers Approval](#4-hitl-reviewer-what-triggers-approval)
5. [Reward Math: Concrete Examples](#5-reward-math-concrete-examples)
6. [WCAG Gatekeeper: What Gets Blocked](#6-wcag-gatekeeper-what-gets-blocked)

---

## 1. The 6 Actions: Before & After

### Action A1 — Increase Font Size

**Trigger**: Low-vision user struggling, error rate climbing.

```
BEFORE                              AFTER
+----------------------+            +------------------------+
|                      |            |                        |
|  Continue            |     -->    |  Continue              |
|                      |            |                        |
|  16px font           |            |  18px font (+12.5%)    |
+----------------------+            +------------------------+
```

| Property | Before | After | Change |
|----------|--------|-------|--------|
| `font_scale` | `1.0` | `1.125` | +12.5% |
| `--font-base` | `16px` | `18px` | +2px |
| WCAG rule | 1.4.4 Resize Text | Compliant | OK |

---

### Action A2 — Increase Contrast Theme

**Trigger**: Visual preference high, validator warns about contrast.

```
BEFORE (normal contrast)            AFTER (high contrast)
+----------------------+            +----------------------+
|  Text: #222 on #fff  |            |  Text: #0a0a0a       |
|  Border: #d8dce3     |     -->    |  Border: #1a1a1a     |
|  Accent: #2c4d9e     |            |  Accent: #1a3a85     |
|  Ratio: 4.5:1        |            |  Ratio: 19:1         |
+----------------------+            +----------------------+
```

| Property | Before | After |
|----------|--------|-------|
| Text color | `#222222` | `#0a0a0a` |
| Border | `#d8dce3` | `#1a1a1a` |
| Contrast ratio | 4.5:1 (AA) | 19:1 (AAA) |
| WCAG rule | 1.4.3 / 1.4.6 Contrast | Promoted to AAA |

---

### Action A3 — Simplify Layout

**Trigger**: Cognitive profile, user lost in dense interface.

```
BEFORE (dense)                      AFTER (comfortable)
+----------------------+            +----------------------+
| [News] [Ads] [Tip]   |            |                      |
| Title                |            |  Title               |
| Subtitle             |     -->    |                      |
| Body  [More info]    |            |  Body                |
| [Footer1][Footer2]   |            |                      |
+----------------------+            +----------------------+
```

| Property | Before | After |
|----------|--------|-------|
| `density` | `default` | `comfortable` |
| `--spacing-mult` | `1.0` | `1.25` |
| `hide_nonessential` | `false` | `true` |
| Non-essential elements | Shown | Hidden |

---

### Action A4 — Increase Hit Target Sizes

**Trigger**: Motor impairment profile, repeated mis-clicks.

```
BEFORE                              AFTER
+----------------------+            +----------------------+
|                      |            |                      |
|  [Submit] (32x32)    |     -->    |   |  Submit  |       |
|                      |            |   | (44x44)  |       |
|                      |            |                      |
+----------------------+            +----------------------+
```

| Property | Before | After |
|----------|--------|-------|
| `hit_target_min_px` | `32px` | `44px` |
| Touch target area | 1024 sq.px | 1936 sq.px (+89%) |
| WCAG rule | 2.5.5 Target Size | Promoted to AAA |

---

### Action A5 — Reduce Motion

**Trigger**: User has reduced motion preference, vestibular concerns.

```
BEFORE                              AFTER
[fade in] [slide]                   [instant]
[bounce]  [parallax]       -->      [instant]
[pulse]   [transition]              [static]

--motion-scale: 1                   --motion-scale: 0
```

| Property | Before | After |
|----------|--------|-------|
| `reduced_motion` | `false` | `true` |
| `--motion-scale` | `1` | `0` |
| Animations | All enabled | Disabled |
| WCAG rule | 2.3.3 Animation from Interactions | Compliant |

---

### Action A6 — No Change (Fallback)

**Trigger**: Either current state is optimal, or another action was blocked.

```
BEFORE                              AFTER
+----------------------+            +----------------------+
|                      |            |                      |
|  Current UI state    |     -->    |  Current UI state    |
|                      |            |  (UNCHANGED)         |
|                      |            |                      |
+----------------------+            +----------------------+
```

**Why A6 exists**: Sometimes "do nothing" is the safest option. Used when:
- WCAG validator blocks all other candidates
- HITL reviewer rejects an adaptation
- Current state already maximizes reward

---

## 2. The 5 User Profiles: What Each Sees

### Profile 1: Default User
```
+--------------------------------------+
|  [Sign in with Google]               |
|                                       |
|  Welcome to our service               |
|  Lorem ipsum dolor sit amet...        |
|                                       |
|  [Get Started]  [Learn More]          |
+--------------------------------------+
Settings: visual=0, motor=0, cognitive=0
Likely action: A6 (No change)
```

### Profile 2: Low Vision
```
+--------------------------------------+
|  [Sign in with Google]               |
|                                       |
|   Welcome to our service              |
|   Lorem ipsum dolor sit amet...       |
|                                       |
|   [Get Started]  [Learn More]         |
+--------------------------------------+
Settings: visual=0.8, vulnerable=true
Likely action: A1 (font +12.5%) or A2 (contrast)
HITL trigger: Yes (vulnerable profile)
```

### Profile 3: Screen Reader User
```
+--------------------------------------+
|  ARIA: "Sign in button"              |
|  ARIA: "Heading level 1"              |
|  Welcome to our service               |
|  ARIA: "Paragraph"                    |
|  Lorem ipsum dolor sit amet...        |
|  ARIA: "Get Started button"           |
+--------------------------------------+
Settings: assistive_tech=true, visual=0.6
Likely action: A6 (stability matters)
HITL trigger: Yes (layout changes risky)
```

### Profile 4: Motor Impairment
```
+--------------------------------------+
|  |  Sign in with Google  |           |
|                                       |
|  Welcome to our service               |
|                                       |
|  |  Get Started  |  |  Learn More  | |
+--------------------------------------+
Settings: motor=0.85, reduced_motion=true
Likely action: A4 (44px targets) + A5 (no motion)
HITL trigger: Yes (vulnerable profile)
```

### Profile 5: Cognitive Accommodations
```
+--------------------------------------+
|                                       |
|  Welcome                              |
|                                       |
|  We help you do X.                    |
|                                       |
|  [Get Started]                        |
+--------------------------------------+
Settings: cognitive=0.8, reduced_motion=true
Likely action: A3 (simplify) + A5 (no motion)
HITL trigger: Yes (cognitive preference)
```

---

## 3. The Decision Flow: Step by Step

```
+------------+   +------------+   +-------------+   +-----------+
|  USER      |   | CONTEXT    |   | LinUCB      |   | WCAG      |
|  arrives   |-->| collected  |-->| picks A1-A6 |-->| validates |
+------------+   +------------+   +-------------+   +-----+-----+
                                                          |
                                          PASS <----------+----------> FAIL
                                            |                            |
                                            v                            v
                                      +-----+-----+              +-------+-------+
                                      | HITL      |              | BLOCKED       |
                                      | trigger?  |              | Fallback A6   |
                                      +-----+-----+              | -0.5 penalty  |
                                            |                    +---------------+
                              YES <---------+---------> NO
                                |                       |
                                v                       v
                         +------+------+         +------+------+
                         | REVIEWER    |         | EXECUTE     |
                         | approves /  |         | apply CSS   |
                         | rejects     |         | changes     |
                         +------+------+         +------+------+
                                |                       |
                                +-----------+-----------+
                                            |
                                            v
                                     +------+------+
                                     | OUTCOME     |
                                     | r_task,r_time
                                     | r_error,trust
                                     +------+------+
                                            |
                                            v
                                     +------+------+
                                     | UPDATE      |
                                     | LinUCB model|
                                     | (next user  |
                                     |  is smarter)|
                                     +-------------+
```

---

## 4. HITL Reviewer: What Triggers Approval

A reviewer is summoned ONLY when one of these conditions fires:

| Trigger | Condition | Example |
|---------|-----------|---------|
| Low confidence | `confidence < 0.60` | LinUCB unsure between A1 and A3 |
| Validator warning | `status == warn` | Contrast borderline (4.4:1, needs 4.5:1) |
| High-impact area | nav/forms affected | A3 simplifies the main navigation |
| Vulnerable profile | `vulnerable=true` + non-trivial action | Low-vision user + layout change |

### What the Reviewer Sees

```
+------------------------------------------------------+
|  PENDING DECISION #d-1029                            |
+------------------------------------------------------+
|  Action proposed:    A2 (Increase contrast)          |
|  Confidence:         0.54                             |
|  User profile:       Low vision (vulnerable)         |
|  Validator status:   warn (contrast 4.6:1)           |
|  Trigger reason:     Vulnerable profile + warn       |
|                                                      |
|  Predicted reward:   +0.34                            |
|  WCAG impact:        2 rules promoted (AA -> AAA)    |
|                                                      |
|  [APPROVE]   [REJECT]   [OVERRIDE w/ reason]         |
+------------------------------------------------------+
```

### Decision Outcomes

| Decision | Effect on UI | Effect on Learning |
|----------|--------------|---------------------|
| APPROVE | Action executes | Normal reward update |
| REJECT | Fallback A6 applied | -0.5 penalty bonus |
| OVERRIDE | Different action runs | Logged + tagged for audit |
| TIMEOUT (2s) | Safe fallback A6 | Marked as deferred |

---

## 5. Reward Math: Concrete Examples

### Example 1: A1 (Font Size) Worked Well

```
User: Low vision profile
Action: A1 (font +12.5%)
Outcome:
  - task_completed: TRUE       -> r_task  = +1.0
  - completion_time: 8s/10s    -> r_time  = -0.8
  - error_count: 0/5           -> r_error = 0.0
  - trust_feedback: 0.9        -> r_trust = +0.9
  - WCAG violations: 0         -> p_wcag  = 0

r_base = (0.4 * 1.0) + (0.2 * -0.8) + (0.2 * 0.0) + (0.2 * 0.9)
       = 0.4 + (-0.16) + 0 + 0.18
       = 0.42

r_final = 0.42 - 0 = +0.42  GOOD
LinUCB updates: A1 is good for low-vision users
```

### Example 2: A2 (Contrast) Caused WCAG Violation

```
User: Default profile
Action: A2 (forced high contrast on already-AAA palette)
Outcome:
  - task_completed: TRUE       -> r_task  = +1.0
  - completion_time: 9s/10s    -> r_time  = -0.9
  - error_count: 1/5           -> r_error = -0.2
  - trust_feedback: 0.5        -> r_trust = +0.5
  - WCAG violations: 1         -> p_wcag  = 2.0 * 1 = 2.0

r_base = (0.4 * 1.0) + (0.2 * -0.9) + (0.2 * -0.2) + (0.2 * 0.5)
       = 0.4 + (-0.18) + (-0.04) + 0.10
       = 0.28

r_final = 0.28 - 2.0 = -1.72  BAD
LinUCB updates: A2 is bad for default users
```

### Example 3: HITL Rejected the Action

```
User: Screen reader profile
Action: A3 (simplify) -> REJECTED by reviewer (layout instability)
Outcome:
  - Fallback A6 applied
  - Penalty: -0.5 bonus on top of zero reward

r_final = 0 - 0.5 = -0.5  PENALIZED
LinUCB updates: A3 is risky for screen reader users
```

---

## 6. WCAG Gatekeeper: What Gets Blocked

The gatekeeper runs BEFORE any action reaches the user.

### Hard Blocks (action is replaced with A6)

| Rule | Triggered When | Example |
|------|---------------|---------|
| 1.4.3 Contrast | Result < 4.5:1 | A2 to a "low" contrast palette |
| 1.4.4 Resize Text | Font scale > 2.0x | A1 chained 6+ times |
| 2.5.5 Target Size | Result < 24px | (would never be proposed) |
| 1.4.10 Reflow | Layout would break | A3 hides essential nav element |

### Soft Warnings (sent to HITL)

| Rule | Triggered When | Action |
|------|---------------|--------|
| 1.4.6 Contrast Enhanced | 4.5:1 to 7.0:1 | Send to reviewer |
| 2.3.3 Animation | Non-essential motion | Send to reviewer |
| 3.2.4 Consistent Identification | Layout shifts | Send to reviewer |

### Block Behavior

```
LinUCB:  "I think A2 is best (confidence 0.71)"
Validator: Simulates A2 -> contrast = 3.8:1 -> FAIL
Block:   A2 rejected, fallback A6 applied
Logged:  decision_id=d-1234, blocked_rule=1.4.3, fallback=A6
Penalty: r_final = 0 - 2.0 = -2.0
Result:  User sees no change, LinUCB learns A2 was unsafe
```

---

## Quick Reference: Where Each Visual Change Lives in Code

| Visual Change | File | Line |
|---------------|------|------|
| Font scale CSS variable | [frontend/src/theme/theme.ts](frontend/src/theme/theme.ts#L150-L151) | 150-151 |
| Contrast palettes | [frontend/src/theme/theme.ts](frontend/src/theme/theme.ts#L26-L127) | 26-127 |
| Density spacing | [frontend/src/theme/theme.ts](frontend/src/theme/theme.ts#L129-L133) | 129-133 |
| Hit target size | [frontend/src/theme/theme.ts](frontend/src/theme/theme.ts#L153) | 153 |
| Motion scale | [frontend/src/theme/theme.ts](frontend/src/theme/theme.ts#L154) | 154 |
| Action definitions | [backend/app/core/actions.py](backend/app/core/actions.py) | All |
| Profile presets | [frontend/src/components/ProfilePicker.tsx](frontend/src/components/ProfilePicker.tsx#L9-L61) | 9-61 |

---

## How to Demo Each Visual Change

1. Run the app: `npm run dev` in `frontend/`, `uvicorn app.main:app --reload --port 8000` in `backend/`
2. Open [http://localhost:5173](http://localhost:5173)
3. Pick a profile in the ProfilePicker
4. Click through the 4-step demo task
5. Watch the UI adapt in real-time
6. Switch tabs to see HITL reviewer queue and live metrics

For each profile, you should observe:
- **Default**: Almost no adaptations (reward optimum is current state)
- **Low vision**: Larger fonts, higher contrast palette
- **Screen reader**: Mostly A6 (stability), occasional contrast bump
- **Motor**: Bigger buttons, no animations
- **Cognitive**: Simplified layout, reduced motion
