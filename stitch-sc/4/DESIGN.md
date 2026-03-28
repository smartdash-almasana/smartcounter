# Design System Specification: The Architectural Ledger

## 1. Overview & Creative North Star
**Creative North Star: "The Editorial Monolith"**

In the world of B2B accounting in Argentina, trust isn't built with decorative flourishes; it is built through precision, clarity, and structural authority. This design system rejects the "SaaS-standard" look of bubbly buttons and heavy borders. Instead, we adopt an **Editorial Monolith** approach—a style that treats financial data with the reverence of a high-end broadsheet newspaper, utilizing expansive white space, intentional asymmetry, and sophisticated tonal layering.

We move beyond the "app" feel to create a "workspace" environment. By prioritizing typography scales and background shifts over rigid containment lines, the interface feels less like a series of boxes and more like a fluid, high-fidelity financial instrument.

---

## 2. Colors: Tonal Architecture
We utilize a sophisticated palette where depth is defined by light, not lines.

### The "No-Line" Rule
**Explicit Instruction:** Do not use 1px solid borders for sectioning or layout containment. Boundaries must be defined through background color shifts. For example, a `surface-container-low` (#f0f4f7) side panel sitting against a `surface` (#f7f9fb) main stage.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers. Use the following tiers to create a "nested" depth that guides the eye:
*   **Base Layer:** `surface` (#f7f9fb) – The canvas.
*   **Secondary Context:** `surface-container-low` (#f0f4f7) – Used for sidebars or secondary navigation.
*   **Primary Focus:** `surface-container-lowest` (#ffffff) – The "Paper" layer. Content cards and data tables live here to pop against the gray base.
*   **Emphasis/Overlays:** `surface-container-high` (#e1e9ee) – Used for subtle contrast in headers or footers.

### The Glass & Gradient Rule
To prevent the UI from feeling "flat," main CTAs and premium floating elements should utilize:
*   **Signature Gradients:** Transitioning from `primary` (#545f73) to `primary-container` (#d8e3fb) at a 135-degree angle.
*   **Glassmorphism:** For global search bars or floating action menus, use `surface-container-lowest` at 80% opacity with a `backdrop-blur` of 12px.

---

## 3. Typography: The Voice of Authority
We pair **Manrope** (Display/Headlines) for a modern, geometric feel with **Inter** (Body/UI) for maximum legibility in high-density data environments.

*   **Display & Headlines (Manrope):** These are your architectural anchors. Use `display-md` (2.75rem) for dashboard overviews. The high x-height of Manrope conveys stability and institutional trust.
*   **Body & Labels (Inter):** The workhorse. `body-md` (0.875rem) is the standard for data. Use `label-sm` (0.6875rem) for metadata and table headers. 
*   **The Hierarchy Rule:** Never use font weight alone to distinguish hierarchy. Combine weight (Medium/SemiBold) with color shifts (e.g., `on-surface` for primary text vs. `on-surface-variant` for helper text).

---

## 4. Elevation & Depth: Tonal Layering
Traditional shadows and borders are replaced by **Atmospheric Perspective.**

*   **The Layering Principle:** Place a `surface-container-lowest` card on a `surface-container-low` section. This creates a natural "lift" mimicking fine paper on a desk.
*   **Ambient Shadows:** For floating modals or dropdowns, use a "Ghost Shadow": `0px 12px 32px rgba(42, 52, 57, 0.06)`. Note the tinting—we use the `on-surface` color (#2a3439) rather than pure black to keep the shadow feeling integrated.
*   **The "Ghost Border" Fallback:** If a container requires a boundary (e.g., in high-density tables), use the `outline-variant` token at 20% opacity. **Never use 100% opaque borders.**

---

## 5. Components: Precision Primitives

### Buttons
*   **Primary:** Solid `primary` (#545f73) with `on-primary` text. Radius: `md` (0.375rem). Use a subtle inner shadow (1px top-down) for a "pressed into the page" premium feel.
*   **Secondary:** `surface-container-lowest` with a "Ghost Border."
*   **Tertiary:** No background. `on-surface-variant` text.

### Data Tables (The Core)
*   **Spacing:** Use `spacing-3` (0.6rem) for vertical cell padding to maintain density without clutter.
*   **Separation:** Forbid the use of horizontal divider lines. Use alternating row colors (Zebra striping) using `surface` and `surface-container-lowest`.
*   **Header:** Use `label-md` in uppercase with 0.05em letter spacing for an editorial look.

### Chips (Status Indicators)
*   **Validated:** `tertiary-container` (#69f6b8) background with `on-tertiary-container` (#005a3c) text.
*   **Critical:** `error_container` (#fe8983) with `on_error_container` (#752121).
*   **Shape:** Rectangular with `sm` (0.125rem) radius. Avoid pills/bubbles.

### Input Fields
*   **State:** Default state uses `surface-container-low` background. 
*   **Focus:** Transition background to `surface-container-lowest` and add a 2px `primary` bottom-border only. This "Underline" style feels more professional and less "form-like" than a full box.

---

## 6. Do's and Don'ts

### Do:
*   **Use Asymmetry:** Align the main data table to the left, but keep the "Action Panel" or "Summary" offset to the right with a different surface tier to create a layout that feels designed, not generated.
*   **Embrace Density:** Professional accountants prefer seeing more data at once. Use the `0.875rem` body size as your default.
*   **Apply Intentional White Space:** Use `spacing-12` (2.75rem) between major sections to let the UI breathe.

### Don't:
*   **Don't use "Bubble" corners:** Keep all radii between `0.125rem` and `0.5rem`. Rounded 'pills' undermine the professional tone.
*   **Don't use pure black:** Use `on-surface` (#2a3439) for all "black" text. It provides a softer, more premium contrast against light grays.
*   **Don't use standard dividers:** If you feel the need to "separate" two sections, first try using `spacing-8` (1.75rem). If that fails, change the background color of one section. A line is a last resort.