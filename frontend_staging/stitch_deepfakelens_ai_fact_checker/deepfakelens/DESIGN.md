---
name: DeepFakeLens
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#45464e'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#75777f'
  outline-variant: '#c5c6cf'
  surface-tint: '#4f5d85'
  primary: '#041539'
  on-primary: '#ffffff'
  primary-container: '#1b2a4e'
  on-primary-container: '#8392bc'
  inverse-primary: '#b7c6f2'
  secondary: '#006a6a'
  on-secondary: '#ffffff'
  secondary-container: '#90efef'
  on-secondary-container: '#006e6e'
  tertiary: '#241400'
  on-tertiary: '#ffffff'
  tertiary-container: '#402600'
  on-tertiary-container: '#b48c5b'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2ff'
  primary-fixed-dim: '#b7c6f2'
  on-primary-fixed: '#091a3d'
  on-primary-fixed-variant: '#37466b'
  secondary-fixed: '#93f2f2'
  secondary-fixed-dim: '#76d6d5'
  on-secondary-fixed: '#002020'
  on-secondary-fixed-variant: '#004f4f'
  tertiary-fixed: '#ffddb7'
  tertiary-fixed-dim: '#ebbf89'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#5f4117'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Newsreader
    fontSize: 48px
    fontWeight: '600'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Newsreader
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-lg-mobile:
    fontFamily: Newsreader
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: Newsreader
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 8px
  container-max: 1200px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
---

## Brand & Style
The design system is built on a foundation of **Editorial Modernism**. It balances the authoritative weight of traditional investigative journalism with the streamlined efficiency of a high-performance SaaS tool. The goal is to evoke an immediate sense of trust, forensic precision, and calm clarity in an era of digital misinformation.

The aesthetic utilizes a **Minimalist** approach with a focus on high-quality typography and intentional whitespace. It avoids unnecessary ornamentation, ensuring that the user's attention remains focused on the content being analyzed. The interface should feel like a digital workbench for truth—clean, structured, and profoundly reliable.

## Colors
The palette is anchored by **Navy (#1B2A4E)** to establish institutional authority. **Teal (#008080)** serves as a secondary brand color, used for success states and secondary actions.

- **Primary:** Deep Navy. Used for headers, primary buttons, and critical UI anchors.
- **Accent:** Vibrant Orange (#F97316). Reserved strictly for high-priority Call-to-Actions (CTAs) and critical alerts to ensure high contrast against the dark navy.
- **Background:** Off-white (#F8FAFC). Provides a softer, more sophisticated canvas than pure white, reducing eye strain during long periods of analysis.
- **Neutral:** A scale of cool grays used for borders, secondary text, and disabled states to maintain a professional, de-saturated environment.

## Typography
This design system employs a pairing of **Newsreader** for editorial headings and **Inter** for functional UI and body text.

- **Headlines:** Use Newsreader to provide an authoritative, "newsroom" feel. Medium to Semi-bold weights are preferred for clarity.
- **Body & UI:** Inter provides maximum legibility for data-heavy sections. 
- **Labels:** Small labels use Inter with increased letter spacing and uppercase styling to denote metadata or secondary information clearly.
- **Scale:** Large display sizes should gracefully downscale for mobile to maintain the hierarchy without overwhelming the viewport.

## Layout & Spacing
The layout follows a **Fixed Grid** system for content-heavy pages, centering a 1200px container on the screen to maintain an editorial reading line length. 

- **Grid:** 12-column grid for desktop, 4-column for mobile.
- **Rhythm:** An 8px linear scale governs all padding and margins. 
- **Whitespace:** Emphasize vertical rhythm. Use generous padding (64px+) between major sections to allow the UI to breathe, mimicking the layout of a premium broadsheet.
- **Mobile:** Margins shrink to 16px, and multi-column card layouts reflow into a single vertical stack.

## Elevation & Depth
This design system uses **Tonal Layers** and **Ambient Shadows** to create a focused hierarchy.

- **Primary Surfaces:** Use the background color (#F8FAFC) as the base layer.
- **Elevated Cards:** Analysis tools and input zones use a white background with a very soft, diffused shadow (Blur: 20px, Y: 4px, Color: Navy at 4% opacity). This creates a subtle "lift" without looking heavy.
- **Depth Hierarchy:** Higher elevation is reserved for active diagnostic tools or modals. Secondary information stays flat on the background layer, separated only by thin 1px borders (#E2E8F0).

## Shapes
The shape language is **Soft (0.25rem)**. This slight rounding takes the edge off the "brutalist" feel of sharp corners, making the tool feel modern and accessible while maintaining a disciplined, professional structure.

- **Standard Elements:** Buttons and input fields use a 4px radius.
- **Large Containers:** Cards and drag-and-drop zones can use up to 8px (rounded-lg) for a more defined presence.
- **Interactive States:** Avoid "pill" shapes for buttons to maintain the serious, architectural aesthetic of the brand.

## Components
- **Input Cards:** The central analysis zone is a large white card with a subtle shadow. It features a dashed border (2px, Gray-300) for drag-and-drop zones to signify "active" utility.
- **Buttons:** 
  - *Primary:* Solid Navy with white text.
  - *Secondary:* Outlined Teal or Navy with 1px border.
  - *CTA:* Solid Orange (#F97316) for "Analyze Now" or "Upgrade" actions.
- **Tabs & Toggles:** Minimalist design using underlining for active states rather than boxed backgrounds. This keeps the header area clean.
- **Analysis Chips:** Small, low-contrast pills (e.g., "Deepfake Detected" or "Verified") use semi-transparent background tints of Red or Green with bold text labels.
- **Trust Signals:** Use 16px monochromatic icons for source verification, encryption status, and metadata alerts. Icons should have a "fine-line" weight to match Inter’s stroke.
- **Lists:** Forensic data lists use subtle zebra-striping or thin dividers with Inter Mono for timestamp and metadata values to ensure horizontal alignment.