/* @ds-bundle: {"format":3,"namespace":"CdrKitDesignSystem_b3bc55","components":[],"sourceHashes":{"assets/icons.jsx":"f5af5e4fdedb","deck-stage.js":"9436a2deeb46","export/src/animations.jsx":"ebe6809a6cbe","export/src/parts.jsx":"2be9e7afe069","export/src/scenes.jsx":"8804178a8dd8","export/src/scenes2.jsx":"7764390d3e20","export/src/sound.jsx":"b3df934ffcce","logo/concepts.jsx":"7f40afcb2852","logo/design-canvas.jsx":"bd8746af6e58","ui_kits/cdrkit-site/Chrome.jsx":"37ce5d789a92","ui_kits/cdrkit-site/Hero.jsx":"781ced6d2140","ui_kits/cdrkit-site/Icons.jsx":"a218f9f30d5a","ui_kits/cdrkit-site/Interactive.jsx":"538c35afc71e","ui_kits/cdrkit-site/Sections.jsx":"e11f735fb758","video/animations.jsx":"ebe6809a6cbe","video/parts.jsx":"2be9e7afe069","video/scenes.jsx":"8804178a8dd8","video/scenes2.jsx":"7764390d3e20","video/sound.jsx":"b3df934ffcce","video/v1-explainer/animations.jsx":"ebe6809a6cbe","video/v1-explainer/parts.jsx":"2be9e7afe069","video/v1-explainer/scenes.jsx":"368712af857c"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.CdrKitDesignSystem_b3bc55 = window.CdrKitDesignSystem_b3bc55 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// assets/icons.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* cdr-kit icon set — ported verbatim from apps/site/components/icons.tsx.
   All consume currentColor. Exported to window for cross-file use. */
const _s = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round"
};
function LockboxGlyph(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, {
    strokeWidth: 2.1
  }, p), /*#__PURE__*/React.createElement("rect", {
    x: "4",
    y: "10.5",
    width: "16",
    height: "10",
    rx: "2"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M8 10.5V7a4 4 0 0 1 8 0v3.5"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "15",
    r: "1.3",
    fill: "currentColor",
    stroke: "none"
  }));
}
function LockClosed(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("rect", {
    x: "5",
    y: "11",
    width: "14",
    height: "10",
    rx: "2"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M8 11V7a4 4 0 0 1 8 0v4"
  }));
}
function LockOpen(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("rect", {
    x: "5",
    y: "11",
    width: "14",
    height: "10",
    rx: "2"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M8 11V7a4 4 0 0 1 8 0"
  }));
}
function Npm(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24",
    fill: "currentColor"
  }, p), /*#__PURE__*/React.createElement("path", {
    d: "M2 5h20v13H12v2H7v-2H2V5zm2 2v9h3V9h2v7h2V7H4zm9 0v9h3V9h2v7h1V7h-6z"
  }));
}
function Github(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24",
    fill: "currentColor"
  }, p), /*#__PURE__*/React.createElement("path", {
    d: "M12 1.5A10.5 10.5 0 0 0 8.7 22c.5.1.7-.2.7-.5v-1.8c-2.9.6-3.5-1.4-3.5-1.4-.5-1.2-1.2-1.5-1.2-1.5-.9-.6.1-.6.1-.6 1 .1 1.6 1 1.6 1 .9 1.6 2.4 1.1 3 .9.1-.7.4-1.1.6-1.4-2.3-.3-4.7-1.2-4.7-5.1 0-1.1.4-2 1-2.7-.1-.3-.5-1.3.1-2.7 0 0 .9-.3 2.8 1a9.6 9.6 0 0 1 5 0c1.9-1.3 2.8-1 2.8-1 .6 1.4.2 2.4.1 2.7.7.7 1 1.6 1 2.7 0 3.9-2.4 4.8-4.7 5.1.4.3.7.9.7 1.9v2.8c0 .3.2.6.7.5A10.5 10.5 0 0 0 12 1.5z"
  }));
}
function Sun(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "12",
    r: "4.2"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
  }));
}
function Moon(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("path", {
    d: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"
  }));
}
function Copy(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("rect", {
    x: "9",
    y: "9",
    width: "11",
    height: "11",
    rx: "2"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M5 15V5a2 2 0 0 1 2-2h10"
  }));
}
function ExternalLink(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("path", {
    d: "M14 4h6v6"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M10 14L20 4"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M20 14v6H4V4h6"
  }));
}
function Check(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("path", {
    d: "M4 12l5 5 11-11"
  }));
}
function ArrowRight(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("path", {
    d: "M5 12h14M13 6l6 6-6 6"
  }));
}
function KeyRound(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("circle", {
    cx: "8",
    cy: "15",
    r: "4"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M11 12l9-9 3 3-3 3 2 2-3 3"
  }));
}
function Search(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("circle", {
    cx: "11",
    cy: "11",
    r: "7"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M21 21l-4-4"
  }));
}
function ChevDown(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 12 12",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, p), /*#__PURE__*/React.createElement("path", {
    d: "M3 5l3 3 3-3"
  }));
}
Object.assign(window, {
  LockboxGlyph,
  LockClosed,
  LockOpen,
  Npm,
  Github,
  Sun,
  Moon,
  Copy,
  ExternalLink,
  Check,
  ArrowRight,
  KeyRound,
  Search,
  ChevDown
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "assets/icons.jsx", error: String((e && e.message) || e) }); }

// deck-stage.js
try { (() => {
// @ds-adherence-ignore -- omelette starter scaffold (raw elements/hex/px by design)
/* BEGIN USAGE */
/**
 * <deck-stage> — reusable web component for HTML decks.
 *
 * Handles:
 *  (a) speaker notes — reads <script type="application/json" id="speaker-notes">
 *      and posts {slideIndexChanged: N} to the parent window on nav.
 *  (b) keyboard navigation — ←/→, PgUp/PgDn, Space, Home/End, number keys.
 *      On touch devices, tapping the left/right half of the stage goes
 *      prev/next — taps on links, buttons and other interactive slide
 *      content are left alone.
 *  (c) press R to reset to slide 0 (with a tasteful keyboard hint).
 *  (d) bottom-center overlay showing slide count + hints, fades out on idle.
 *  (e) auto-scaling — inner canvas is a fixed design size (default 1920×1080)
 *      scaled with `transform: scale()` to fit the viewport, letterboxed.
 *      Set the `noscale` attribute to render at authored size (1:1) — the
 *      PPTX exporter sets this so its DOM capture sees unscaled geometry.
 *  (f) print — `@media print` lays every slide out as its own page at the
 *      design size, so the browser's Print → Save as PDF produces a clean
 *      one-page-per-slide PDF with no extra setup.
 *  (g) thumbnail rail — resizable left-hand column of per-slide thumbnails
 *      (static clones). Click to navigate; ↑/↓ with a thumbnail focused to
 *      step between slides; drag to reorder; right-click for
 *      Skip / Move up / Move down / Duplicate / Delete (Delete opens a
 *      Cancel/Delete confirm dialog). Drag the rail's right edge to resize;
 *      width persists to
 *      localStorage. Skipped slides carry `data-deck-skip`, are dimmed in
 *      the rail, omitted from prev/next navigation, and hidden at print.
 *      The rail is suppressed in presenting mode, in the host's Preview
 *      mode (ViewerMode='none'), on `noscale`, on narrow viewports
 *      (≤640px), and via the `no-rail` attribute. Rail mutations dispatch
 *      a `deckchange`
 *      CustomEvent on the element: detail = {action, from, to, slide}.
 *
 * Slides are HIDDEN, not unmounted. Non-active slides stay in the DOM with
 * `visibility: hidden` + `opacity: 0`, so their state (videos, iframes,
 * form inputs, React trees) is preserved across navigation.
 *
 * Lifecycle event — the component dispatches a `slidechange` CustomEvent on
 * itself whenever the active slide changes (including the initial mount).
 * The event bubbles and composes out of shadow DOM, so you can listen on
 * the <deck-stage> element or on document:
 *
 *   document.querySelector('deck-stage').addEventListener('slidechange', (e) => {
 *     e.detail.index         // new 0-based index
 *     e.detail.previousIndex // previous index, or -1 on init
 *     e.detail.total         // total slide count
 *     e.detail.slide         // the new active slide element
 *     e.detail.previousSlide // the prior slide element, or null on init
 *     e.detail.reason        // 'init' | 'keyboard' | 'click' | 'tap' | 'api'
 *   });
 *
 * Persistence: none at the deck level. The host app keeps the current slide
 * in its own URL (?slide=) and re-delivers it via location.hash on load, so a
 * bare load with no hash always starts at slide 1.
 *
 * Usage:
 *   <style>deck-stage:not(:defined){visibility:hidden}</style>
 *   <deck-stage width="1920" height="1080">
 *     <section data-label="Title">...</section>
 *     <section data-label="Agenda">...</section>
 *   </deck-stage>
 *   <script src="deck-stage.js"></script>
 *
 * The :not(:defined) rule prevents a flash of the first slide at its
 * authored styles before this script runs and attaches the shadow root.
 *
 * Slides are the direct element children of <deck-stage>. Each slide is
 * automatically tagged with:
 *   - data-screen-label="NN Label"   (1-indexed, for comment flow)
 *   - data-om-validate="no_overflowing_text,no_overlapping_text,slide_sized_text"
 *
 * Speaker notes stay in sync because the component posts {slideIndexChanged: N}
 * to the parent — just include the #speaker-notes script tag if asked for notes.
 *
 * Authoring guidance:
 *   - Write slide bodies as static HTML inside <deck-stage>, with sizing via
 *     CSS custom properties in a <style> block rather than JS constants.
 *     Static slide markup is what lets the user click a heading in edit mode
 *     and retype it directly; a slide rendered through <script type="text/babel">,
 *     React, or a loop over a JS array has to round-trip every tweak through a
 *     chat message instead. Reach for script-generated slides only when the
 *     content genuinely needs interactive behaviour static HTML can't express.
 *   - Do NOT set position/inset/width/height on the slide <section> elements —
 *     the component absolutely positions every slotted child for you.
 *   - Entrance animations: make the visible end-state the base style and
 *     animate *from* hidden, so print and reduced-motion show content.
 *     Gate the animation on [data-deck-active] and the motion query, e.g.
 *     `@media (prefers-reduced-motion:no-preference){ [data-deck-active] .x{animation:fade-in .5s both} }`.
 *     Avoid infinite decorative loops on slide content.
 */
/* END USAGE */

(() => {
  const DESIGN_W_DEFAULT = 1920;
  const DESIGN_H_DEFAULT = 1080;
  const OVERLAY_HIDE_MS = 1800;
  const VALIDATE_ATTR = 'no_overflowing_text,no_overlapping_text,slide_sized_text';
  const FINE_POINTER_MQ = matchMedia('(hover: hover) and (pointer: fine)');
  const NARROW_MQ = matchMedia('(max-width: 640px)');
  // Slide-authored controls that should keep a tap instead of it navigating.
  const INTERACTIVE_SEL = 'a[href], button, input, select, textarea, summary, label, video[controls], audio[controls], [role="button"], [onclick], [tabindex]:not([tabindex^="-"]), [contenteditable]:not([contenteditable="false" i])';
  const pad2 = n => String(n).padStart(2, '0');

  // Label precedence: data-label → data-screen-label (number stripped) → first heading → "Slide".
  const getSlideLabel = el => {
    const explicit = el.getAttribute('data-label');
    if (explicit) return explicit;
    const existing = el.getAttribute('data-screen-label');
    if (existing) return existing.replace(/^\s*\d+\s*/, '').trim() || existing;
    const h = el.querySelector('h1, h2, h3, [data-title]');
    const t = h && (h.textContent || '').trim().slice(0, 40);
    if (t) return t;
    return 'Slide';
  };
  const stylesheet = `
    :host {
      position: fixed;
      inset: 0;
      display: block;
      background: #000;
      color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif;
      overflow: hidden;
      -webkit-tap-highlight-color: transparent;
    }
    /* connectedCallback holds this until document.fonts.ready (capped 2s) so
     * the first visible paint has the deck's real typography + final rail
     * layout. opacity (not visibility) so the active slide can't un-hide
     * itself via the ::slotted([data-deck-active]) visibility:visible rule.
     * Only the stage/rail hide — the black :host background stays, so the
     * iframe doesn't flash the page's default white. */
    :host([data-fonts-pending]) .stage,
    :host([data-fonts-pending]) .rail { opacity: 0; pointer-events: none; }

    .stage {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .canvas {
      position: relative;
      transform-origin: center center;
      flex-shrink: 0;
      background: #fff;
      will-change: transform;
    }

    /* Slides live in light DOM (via <slot>) so authored CSS still applies.
       We absolutely position each slotted child to stack them. */
    ::slotted(*) {
      position: absolute !important;
      inset: 0 !important;
      width: 100% !important;
      height: 100% !important;
      box-sizing: border-box !important;
      overflow: hidden;
      opacity: 0;
      pointer-events: none;
      visibility: hidden;
    }
    ::slotted([data-deck-active]) {
      opacity: 1;
      pointer-events: auto;
      visibility: visible;
    }

    .overlay {
      position: fixed;
      left: 50%;
      bottom: 22px;
      transform: translate(-50%, 6px) scale(0.92);
      filter: blur(6px);
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 4px;
      background: #000;
      color: #fff;
      border-radius: 999px;
      font-size: 12px;
      font-feature-settings: "tnum" 1;
      letter-spacing: 0.01em;
      opacity: 0;
      pointer-events: none;
      transition: opacity 260ms ease, transform 260ms cubic-bezier(.2,.8,.2,1), filter 260ms ease;
      transform-origin: center bottom;
      z-index: 2147483000;
      user-select: none;
    }
    .overlay[data-visible] {
      opacity: 1;
      pointer-events: auto;
      transform: translate(-50%, 0) scale(1);
      filter: blur(0);
    }

    .btn {
      appearance: none;
      -webkit-appearance: none;
      background: transparent;
      border: 0;
      margin: 0;
      padding: 0;
      color: inherit;
      font: inherit;
      cursor: default;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      height: 28px;
      min-width: 28px;
      border-radius: 999px;
      color: rgba(255,255,255,0.72);
      transition: background 140ms ease, color 140ms ease;
      -webkit-tap-highlight-color: transparent;
    }
    .btn:hover { background: rgba(255,255,255,0.12); color: #fff; }
    .btn:active { background: rgba(255,255,255,0.18); }
    .btn:focus { outline: none; }
    .btn:focus-visible { outline: none; }
    .btn::-moz-focus-inner { border: 0; }
    .btn svg { width: 14px; height: 14px; display: block; }
    .btn.reset {
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.02em;
      padding: 0 10px 0 12px;
      gap: 6px;
      color: rgba(255,255,255,0.72);
    }
    .btn.reset .kbd {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 16px;
      height: 16px;
      padding: 0 4px;
      font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
      font-size: 10px;
      line-height: 1;
      color: rgba(255,255,255,0.88);
      background: rgba(255,255,255,0.12);
      border-radius: 4px;
    }

    .count {
      font-variant-numeric: tabular-nums;
      color: #fff;
      font-weight: 500;
      padding: 0 8px;
      min-width: 42px;
      text-align: center;
      font-size: 12px;
    }
    .count .sep { color: rgba(255,255,255,0.45); margin: 0 3px; font-weight: 400; }
    .count .total { color: rgba(255,255,255,0.55); }

    .divider {
      width: 1px;
      height: 14px;
      background: rgba(255,255,255,0.18);
      margin: 0 2px;
    }

    /* ── Thumbnail rail ──────────────────────────────────────────────────
       Fixed column on the left; each thumbnail is a static deep-clone of
       the light-DOM slide scaled into a 16:9 (or design-aspect) frame. The
       stage re-fits around it (see _fit); hidden during present / noscale
       / print so capture geometry and fullscreen output are unchanged. */
    .rail {
      position: fixed;
      left: 0;
      top: 0;
      bottom: 0;
      width: var(--deck-rail-w, 188px);
      background: #141414;
      border-right: 1px solid rgba(255,255,255,0.08);
      overflow-y: auto;
      overflow-x: hidden;
      padding: 12px 10px;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      gap: 12px;
      z-index: 2147482500;
      scrollbar-width: thin;
      scrollbar-color: rgba(255,255,255,0.18) transparent;
    }
    .rail::-webkit-scrollbar { width: 8px; }
    .rail::-webkit-scrollbar-track { background: transparent; margin: 2px; }
    .rail::-webkit-scrollbar-thumb {
      background: rgba(255,255,255,0.18);
      border-radius: 4px;
      border: 2px solid transparent;
      background-clip: content-box;
    }
    .rail::-webkit-scrollbar-thumb:hover {
      background: rgba(255,255,255,0.28);
      border: 2px solid transparent;
      background-clip: content-box;
    }
    :host([no-rail]) .rail,
    :host([noscale]) .rail { display: none; }
    .rail[data-presenting] { display: none; }
    @media (max-width: 640px) {
      .rail, .rail-resize { display: none; }
    }
    /* User-driven show/hide (the TweaksPanel toggle) slides instead of
       popping. Transitions are gated on :host([data-rail-anim]) — set only
       for the 200ms around the toggle — so window-resize and rail-width
       drag (which also call _fit) don't lag behind the cursor. */
    .rail[data-user-hidden] { transform: translateX(-100%); }
    :host([data-rail-anim]) .rail { transition: transform 200ms cubic-bezier(.3,.7,.4,1); }
    :host([data-rail-anim]) .stage { transition: left 200ms cubic-bezier(.3,.7,.4,1); }
    :host([data-rail-anim]) .canvas { transition: transform 200ms cubic-bezier(.3,.7,.4,1); }
    /* transition shorthand replaces rather than merges — repeat the base
       .overlay opacity/transform/filter transitions so visibility changes
       during the 200ms toggle window still fade instead of popping. */
    :host([data-rail-anim]) .overlay {
      transition: margin-left 200ms cubic-bezier(.3,.7,.4,1),
                  opacity 260ms ease,
                  transform 260ms cubic-bezier(.2,.8,.2,1),
                  filter 260ms ease;
    }

    .thumb {
      position: relative;
      display: flex;
      align-items: flex-start;
      gap: 8px;
      cursor: pointer;
      user-select: none;
    }
    .thumb .num {
      width: 16px;
      flex-shrink: 0;
      font-size: 11px;
      font-weight: 500;
      text-align: right;
      color: rgba(255,255,255,0.55);
      padding-top: 2px;
      font-variant-numeric: tabular-nums;
    }
    .thumb .frame {
      position: relative;
      flex: 1;
      min-width: 0;
      aspect-ratio: var(--deck-aspect);
      background: #fff;
      border-radius: 4px;
      outline: 2px solid transparent;
      outline-offset: 0;
      overflow: hidden;
      transition: outline-color 120ms ease;
    }
    .thumb:hover .frame { outline-color: rgba(255,255,255,0.25); }
    .thumb { outline: none; }
    .thumb:focus-visible .frame { outline-color: rgba(255,255,255,0.5); }
    .thumb[data-current] .num { color: #fff; }
    .thumb[data-current] .frame { outline-color: #D97757; }
    .thumb[data-dragging] { opacity: 0.35; }
    .thumb::before {
      content: '';
      position: absolute;
      left: 24px;
      right: 0;
      height: 3px;
      border-radius: 2px;
      background: #D97757;
      opacity: 0;
      pointer-events: none;
    }
    .thumb[data-drop="before"]::before { top: -8px; opacity: 1; }
    .thumb[data-drop="after"]::before { bottom: -8px; opacity: 1; }
    .thumb[data-skip] .frame { opacity: 0.35; }
    .thumb[data-skip] .frame::after {
      content: 'Skipped';
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0,0,0,0.45);
      color: #fff;
      font-size: 10px;
      font-weight: 500;
      letter-spacing: 0.04em;
    }

    .ctxmenu {
      position: fixed;
      min-width: 150px;
      padding: 4px;
      background: #242424;
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 7px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.45);
      z-index: 2147483100;
      display: none;
      font-size: 12px;
    }
    .ctxmenu[data-open] { display: block; }
    .ctxmenu button {
      display: block;
      width: 100%;
      appearance: none;
      border: 0;
      background: transparent;
      color: #e8e8e8;
      font: inherit;
      text-align: left;
      padding: 6px 10px;
      border-radius: 4px;
      cursor: pointer;
    }
    .ctxmenu button:hover:not(:disabled) { background: rgba(255,255,255,0.08); }
    .ctxmenu button:disabled { opacity: 0.35; cursor: default; }
    .ctxmenu hr {
      border: 0;
      border-top: 1px solid rgba(255,255,255,0.1);
      margin: 4px 2px;
    }

    .rail-resize {
      position: fixed;
      left: calc(var(--deck-rail-w, 188px) - 3px);
      top: 0;
      bottom: 0;
      width: 6px;
      cursor: col-resize;
      z-index: 2147482600;
      touch-action: none;
    }
    .rail-resize:hover,
    .rail-resize[data-dragging] { background: rgba(255,255,255,0.12); }
    :host([no-rail]) .rail-resize,
    :host([noscale]) .rail-resize,
    .rail[data-presenting] + .rail-resize,
    .rail[data-user-hidden] + .rail-resize { display: none; }

    /* Delete-confirm popup — matches the SPA's ConfirmDialog layout
       (title + message body, depressed footer with Cancel / Delete). */
    .confirm-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.45);
      z-index: 2147483200;
      display: none;
      align-items: center;
      justify-content: center;
    }
    .confirm-backdrop[data-open] { display: flex; }
    .confirm {
      width: 320px;
      max-width: calc(100vw - 32px);
      background: #2a2a2a;
      color: #e8e8e8;
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 12px;
      box-shadow: 0 12px 32px rgba(0,0,0,0.5);
      overflow: hidden;
      font-family: inherit;
      animation: deck-confirm-in 0.18s ease;
    }
    @keyframes deck-confirm-in {
      from { opacity: 0; transform: scale(0.96); }
      to { opacity: 1; transform: scale(1); }
    }
    .confirm .body { padding: 20px 20px 16px; }
    .confirm .title { font-size: 14px; font-weight: 600; margin-bottom: 4px; }
    .confirm .msg { font-size: 13px; line-height: 1.5; color: rgba(255,255,255,0.65); }
    .confirm .footer {
      padding: 14px 20px;
      background: #1f1f1f;
      border-top: 1px solid rgba(255,255,255,0.08);
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }
    .confirm button {
      appearance: none;
      font: inherit;
      font-size: 13px;
      font-weight: 500;
      padding: 8px 16px;
      border-radius: 8px;
      cursor: pointer;
    }
    .confirm .cancel {
      background: transparent;
      border: 0;
      color: rgba(255,255,255,0.8);
    }
    .confirm .cancel:hover { background: rgba(255,255,255,0.08); }
    .confirm .danger {
      background: #c96442;
      border: 1px solid rgba(0,0,0,0.15);
      color: #fff;
      box-shadow: 0 1px 3px rgba(166,50,68,0.3), 0 2px 6px rgba(166,50,68,0.18);
    }
    .confirm .danger:hover { background: #b5563a; }

    /* ── Print: one page per slide, no chrome ────────────────────────────
       The screen layout stacks every slide at inset:0 inside a scaled
       canvas; for print we want them in document flow at the authored
       design size so the browser paginates one slide per sheet. The
       @page size is set from the width/height attributes via the inline
       <style id="deck-stage-print-page"> that connectedCallback injects
       into <head> (the @page at-rule has no effect inside shadow DOM). */
    @media print {
      :host {
        position: static;
        inset: auto;
        background: none;
        overflow: visible;
        color: inherit;
      }
      .stage { position: static; display: block; }
      .canvas {
        transform: none !important;
        width: auto !important;
        height: auto !important;
        background: none;
        will-change: auto;
      }
      ::slotted(*) {
        position: relative !important;
        inset: auto !important;
        width: var(--deck-design-w) !important;
        height: var(--deck-design-h) !important;
        box-sizing: border-box !important;
        opacity: 1 !important;
        visibility: visible !important;
        pointer-events: auto;
        break-after: page;
        page-break-after: always;
        break-inside: avoid;
        overflow: hidden;
      }
      /* :last-child alone isn't enough once data-deck-skip hides the
         trailing slide(s) — the last *visible* slide still carries
         break-after:page and prints a blank sheet. _markLastVisible()
         maintains data-deck-last-visible on the last non-skipped slide. */
      ::slotted(*:last-child),
      ::slotted([data-deck-last-visible]) {
        break-after: auto;
        page-break-after: auto;
      }
      ::slotted([data-deck-skip]) { display: none !important; }
      .overlay, .rail, .rail-resize, .ctxmenu, .confirm-backdrop { display: none !important; }
    }
  `;
  class DeckStage extends HTMLElement {
    static get observedAttributes() {
      return ['width', 'height', 'noscale', 'no-rail'];
    }
    constructor() {
      super();
      this._root = this.attachShadow({
        mode: 'open'
      });
      this._index = 0;
      this._slides = [];
      this._notes = [];
      this._hideTimer = null;
      this._mouseIdleTimer = null;
      this._menuIndex = -1;
      this._onKey = this._onKey.bind(this);
      this._onResize = this._onResize.bind(this);
      this._onSlotChange = this._onSlotChange.bind(this);
      this._onMouseMove = this._onMouseMove.bind(this);
      this._onTap = this._onTap.bind(this);
      this._onMessage = this._onMessage.bind(this);
      // Capture-phase close so a click anywhere dismisses the menu, but
      // ignore clicks that land inside the menu itself — otherwise the
      // capture handler runs before the menu's own (bubble) handler and
      // clears _menuIndex out from under it.
      this._onDocClick = e => {
        if (this._menu && e.composedPath && e.composedPath().includes(this._menu)) return;
        this._closeMenu();
      };
    }
    get designWidth() {
      return parseInt(this.getAttribute('width'), 10) || DESIGN_W_DEFAULT;
    }
    get designHeight() {
      return parseInt(this.getAttribute('height'), 10) || DESIGN_H_DEFAULT;
    }
    connectedCallback() {
      // Presenter-view popup loads deckUrl?_snthumb=...#N for its prev/cur/
      // next thumbnails — the rail has no business rendering inside those
      // (wrong scale, and it offsets the stage so the thumb shows a gutter).
      if (/[?&]_snthumb=/.test(location.search)) this.setAttribute('no-rail', '');
      this._render();
      this._loadNotes();
      this._syncPrintPageRule();
      window.addEventListener('keydown', this._onKey);
      window.addEventListener('resize', this._onResize);
      window.addEventListener('mousemove', this._onMouseMove, {
        passive: true
      });
      window.addEventListener('message', this._onMessage);
      window.addEventListener('click', this._onDocClick, true);
      this.addEventListener('click', this._onTap);
      // Print lays every slide out as its own page, so [data-deck-active]-
      // gated entrance styles need the attribute on every slide (not just
      // the current one) or their content prints at the hidden base style.
      // The transient freeze style lands BEFORE the attributes so any
      // attribute-keyed transition fires at 0s (changing transition-
      // duration after a transition has started doesn't affect it).
      this._onBeforePrint = () => {
        if (this._freezeStyle) this._freezeStyle.remove();
        this._freezeStyle = document.createElement('style');
        this._freezeStyle.textContent = '*,*::before,*::after{transition-duration:0s !important}';
        document.head.appendChild(this._freezeStyle);
        this._slides.forEach(s => s.setAttribute('data-deck-active', ''));
      };
      this._onAfterPrint = () => {
        this._applyIndex({
          showOverlay: false,
          broadcast: false
        });
        if (this._freezeStyle) {
          this._freezeStyle.remove();
          this._freezeStyle = null;
        }
      };
      window.addEventListener('beforeprint', this._onBeforePrint);
      window.addEventListener('afterprint', this._onAfterPrint);
      // Initial collection + layout happens via slotchange, which fires on mount.
      this._enableRail();
      // Hold the stage hidden until webfonts are ready so the first visible
      // paint has the deck's real typography — the :not(:defined) guard in
      // the page HTML only covers custom-element upgrade, not font load.
      // Capped so a 404'd font URL can't blank the deck indefinitely.
      this.setAttribute('data-fonts-pending', '');
      const reveal = () => this.removeAttribute('data-fonts-pending');
      // rAF first: fonts.ready is a pre-resolved promise until layout has
      // resolved the slotted text's font-family and pushed a FontFace into
      // 'loading'. Reading it here in connectedCallback (parse-time) would
      // settle the race in a microtask before any font fetch starts.
      requestAnimationFrame(() => {
        Promise.race([document.fonts ? document.fonts.ready : Promise.resolve(), new Promise(r => setTimeout(r, 2000))]).then(reveal, reveal);
      });
    }
    _enableRail() {
      // Idempotent — older host builds still post __omelette_rail_enabled.
      // no-rail guard keeps the observers/stylesheet walk off the cheap path
      // for presenter-popup thumbnail iframes (up to 9 per view).
      if (this._railEnabled || this.hasAttribute('no-rail')) return;
      this._railEnabled = true;
      // Per-viewer preference — restored alongside rail width. Default on;
      // only a stored '0' (from the TweaksPanel toggle) hides it.
      this._railVisible = true;
      try {
        if (localStorage.getItem('deck-stage.railVisible') === '0') this._railVisible = false;
      } catch (e) {}
      // Live thumbnail updates: watch the light-DOM slides for content
      // edits and re-clone just the affected thumb(s), debounced. Ignore
      // the data-deck-* / data-screen-label / data-om-validate attributes
      // this component itself writes so nav and skip don't trigger
      // spurious refreshes.
      const OWN_ATTRS = /^data-(deck-|screen-label$|om-validate$)/;
      this._liveDirty = new Set();
      this._liveObserver = new MutationObserver(records => {
        for (const r of records) {
          if (r.type === 'attributes' && OWN_ATTRS.test(r.attributeName || '')) continue;
          let n = r.target;
          while (n && n.parentElement !== this) n = n.parentElement;
          if (n && this._slideSet && this._slideSet.has(n)) this._liveDirty.add(n);
        }
        if (this._liveDirty.size && !this._liveTimer) {
          this._liveTimer = setTimeout(() => {
            this._liveTimer = null;
            this._liveDirty.forEach(s => this._refreshThumb(s));
            this._liveDirty.clear();
          }, 200);
        }
      });
      this._liveObserver.observe(this, {
        subtree: true,
        childList: true,
        characterData: true,
        attributes: true
      });
      // Lazy thumbnail materialization — clone the slide only when its
      // frame scrolls into (or near) the rail viewport. rootMargin gives
      // ~4 thumbs of pre-load so fast scrolling doesn't flash blanks.
      this._railObserver = new IntersectionObserver(entries => {
        entries.forEach(e => {
          if (e.isIntersecting && e.target.__deckThumb) {
            this._materialize(e.target.__deckThumb);
          }
        });
      }, {
        root: this._rail,
        rootMargin: '400px 0px'
      });
      // Tweaks typically change CSS vars / attrs OUTSIDE <deck-stage>
      // (on <html>, <body>, a wrapper div, or a <style> tag), which
      // _liveObserver can't see. Re-snapshot author CSS (constructable
      // sheet is shared by reference, so one replaceSync updates every
      // thumb shadow root) and re-sync each thumb host's attrs + custom
      // properties. In-slide DOM mutations are _liveObserver's job.
      // Debounced so slider drags don't thrash.
      this._onTweakChange = () => {
        clearTimeout(this._tweakTimer);
        this._tweakTimer = setTimeout(() => {
          this._snapshotAuthorCss();
          // One getComputedStyle for the whole batch — each
          // getPropertyValue read below reuses the same computed style
          // as long as nothing invalidates layout between thumbs.
          const cs = getComputedStyle(this);
          (this._thumbs || []).forEach(t => {
            if (t.host) this._syncThumbHostAttrs(t.host, cs);
          });
        }, 120);
      };
      window.addEventListener('tweakchange', this._onTweakChange);
      this._snapshotAuthorCss();
      // Build the rail now that it's enabled — slotchange already fired,
      // so _renderRail's early-return skipped the initial build.
      this._syncRailHidden();
      this._renderRail();
      this._fit();
    }

    /** Snapshot document stylesheets into a constructable sheet that each
     *  thumbnail's nested shadow root adopts — so author CSS styles the
     *  cloned slide content without touching this component's chrome.
     *  Cross-origin sheets throw on .cssRules — skip them. Re-callable:
     *  the existing constructable sheet is reused via replaceSync so every
     *  already-adopted shadow root picks up the fresh CSS without re-adopt. */
    _snapshotAuthorCss() {
      // :root in an adopted sheet inside a shadow root matches nothing
      // (only the document root qualifies), so author rules like
      // `:root[data-voice="modern"] .serif` never reach the clones.
      // Rewrite :root → :host and mirror <html>'s data-*/class/lang onto
      // each thumb host (see _syncThumbHostAttrs) so the same selectors
      // match inside the thumbnail's shadow tree.
      const authorCss = Array.from(document.styleSheets).map(sh => {
        try {
          return Array.from(sh.cssRules).map(r => r.cssText).join('\n');
        } catch (e) {
          return '';
        }
      }).join('\n')
      // The shadow host is featureless outside the functional :host(...)
      // form, so any compound on :root — [attr], .class, #id, :pseudo —
      // must become :host(<compound>) not :host<compound>. Same for the
      // html type selector (Tailwind class-strategy dark mode emits
      // html.dark; Pico uses html[data-theme]), which has nothing to
      // match inside the thumb's shadow tree.
      .replace(/:root((?:\[[^\]]*\]|[.#][-\w]+|:[-\w]+(?:\([^)]*\))?)+)/g, ':host($1)').replace(/:root\b/g, ':host').replace(/(^|[\s,>~+(}])html((?:\[[^\]]*\]|[.#][-\w]+|:[-\w]+(?:\([^)]*\))?)+)(?![-\w])/g, '$1:host($2)').replace(/(^|[\s,>~+(}])html(?![-\w])/g, '$1:host');
      // Every custom property the author references. _syncThumbHostAttrs
      // mirrors each one's *computed* value at <deck-stage> onto the
      // thumb host so the live value wins over the :host default above
      // regardless of which ancestor the tweak wrote to (<html>, <body>,
      // a wrapper div, or the deck-stage element itself all inherit
      // down to getComputedStyle(this)).
      this._authorVars = new Set(authorCss.match(/--[\w-]+/g) || []);
      try {
        if (!this._adoptedSheet) this._adoptedSheet = new CSSStyleSheet();
        this._adoptedSheet.replaceSync(authorCss);
      } catch (e) {
        this._adoptedSheet = null;
        this._authorCss = authorCss;
      }
    }
    _syncThumbHostAttrs(host, cs) {
      const de = document.documentElement;
      // setAttribute overwrites but can't delete — an attr removed from
      // <html> (toggleAttribute off, classList emptied) would linger on
      // the host and :host([data-*]) / :host(.foo) rules would keep
      // matching. Remove stale mirrored attrs first; iterate backward
      // because removeAttribute mutates the live NamedNodeMap.
      for (let i = host.attributes.length - 1; i >= 0; i--) {
        const n = host.attributes[i].name;
        if ((n.startsWith('data-') || n === 'class' || n === 'lang') && !de.hasAttribute(n)) {
          host.removeAttribute(n);
        }
      }
      for (const a of de.attributes) {
        if (a.name.startsWith('data-') || a.name === 'class' || a.name === 'lang') {
          host.setAttribute(a.name, a.value);
        }
      }
      // The :root→:host rewrite in _snapshotAuthorCss pins each custom
      // property to its stylesheet default on the thumb host, shadowing
      // the live value that would otherwise inherit. Tweaks can write the
      // live value on any ancestor — <html>, <body>, a wrapper div, the
      // deck-stage element — so read it as the *computed* value at
      // <deck-stage> (which sees the whole inheritance chain) rather than
      // trying to guess which element the author wrote to. Inline on the
      // host beats the :host{} rule. remove-stale covers vars dropped
      // from the stylesheet between snapshots.
      const vars = this._authorVars || new Set();
      for (let i = host.style.length - 1; i >= 0; i--) {
        const p = host.style[i];
        if (p.startsWith('--') && !vars.has(p)) host.style.removeProperty(p);
      }
      const live = cs || getComputedStyle(this);
      vars.forEach(p => {
        const v = live.getPropertyValue(p);
        if (v) host.style.setProperty(p, v.trim());else host.style.removeProperty(p);
      });
    }
    disconnectedCallback() {
      window.removeEventListener('keydown', this._onKey);
      window.removeEventListener('resize', this._onResize);
      window.removeEventListener('mousemove', this._onMouseMove);
      window.removeEventListener('message', this._onMessage);
      window.removeEventListener('click', this._onDocClick, true);
      window.removeEventListener('beforeprint', this._onBeforePrint);
      window.removeEventListener('afterprint', this._onAfterPrint);
      if (this._freezeStyle) {
        this._freezeStyle.remove();
        this._freezeStyle = null;
      }
      this.removeEventListener('click', this._onTap);
      if (this._hideTimer) clearTimeout(this._hideTimer);
      if (this._mouseIdleTimer) clearTimeout(this._mouseIdleTimer);
      if (this._liveTimer) clearTimeout(this._liveTimer);
      if (this._tweakTimer) clearTimeout(this._tweakTimer);
      if (this._railAnimTimer) clearTimeout(this._railAnimTimer);
      if (this._scaleRaf) cancelAnimationFrame(this._scaleRaf);
      if (this._liveObserver) this._liveObserver.disconnect();
      if (this._railObserver) this._railObserver.disconnect();
      if (this._onTweakChange) window.removeEventListener('tweakchange', this._onTweakChange);
    }
    attributeChangedCallback() {
      if (this._canvas) {
        this._canvas.style.width = this.designWidth + 'px';
        this._canvas.style.height = this.designHeight + 'px';
        this._canvas.style.setProperty('--deck-design-w', this.designWidth + 'px');
        this._canvas.style.setProperty('--deck-design-h', this.designHeight + 'px');
        if (this._rail) {
          this._rail.style.setProperty('--deck-aspect', this.designWidth + '/' + this.designHeight);
        }
        this._fit();
        this._scaleThumbs();
        this._syncPrintPageRule();
      }
    }
    _render() {
      const style = document.createElement('style');
      style.textContent = stylesheet;
      const stage = document.createElement('div');
      stage.className = 'stage';
      const canvas = document.createElement('div');
      canvas.className = 'canvas';
      canvas.style.width = this.designWidth + 'px';
      canvas.style.height = this.designHeight + 'px';
      canvas.style.setProperty('--deck-design-w', this.designWidth + 'px');
      canvas.style.setProperty('--deck-design-h', this.designHeight + 'px');
      const slot = document.createElement('slot');
      slot.addEventListener('slotchange', this._onSlotChange);
      canvas.appendChild(slot);
      stage.appendChild(canvas);

      // Overlay: compact, solid black, with clickable controls.
      const overlay = document.createElement('div');
      overlay.className = 'overlay export-hidden';
      overlay.setAttribute('role', 'toolbar');
      overlay.setAttribute('aria-label', 'Deck controls');
      overlay.setAttribute('data-omelette-chrome', '');
      overlay.innerHTML = `
        <button class="btn prev" type="button" aria-label="Previous slide" title="Previous (←)">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 3L5 8l5 5"/></svg>
        </button>
        <span class="count" aria-live="polite"><span class="current">1</span><span class="sep">/</span><span class="total">1</span></span>
        <button class="btn next" type="button" aria-label="Next slide" title="Next (→)">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 3l5 5-5 5"/></svg>
        </button>
        <span class="divider"></span>
        <button class="btn reset" type="button" aria-label="Reset to first slide" title="Reset (R)">Reset<span class="kbd">R</span></button>
      `;
      overlay.querySelector('.prev').addEventListener('click', () => this._advance(-1, 'click'));
      overlay.querySelector('.next').addEventListener('click', () => this._advance(1, 'click'));
      overlay.querySelector('.reset').addEventListener('click', () => this._go(0, 'click'));

      // Thumbnail rail + context menu. Thumbnails are populated in
      // _renderRail() after _collectSlides().
      const rail = document.createElement('div');
      rail.className = 'rail export-hidden';
      rail.setAttribute('data-omelette-chrome', '');
      rail.style.setProperty('--deck-aspect', this.designWidth + '/' + this.designHeight);
      // Edge auto-scroll while dragging a thumb near the rail's top/bottom
      // so off-screen drop targets are reachable. Native dragover fires
      // continuously while the pointer is stationary, so a per-event nudge
      // (ramped by edge proximity) is enough — no rAF loop needed.
      rail.addEventListener('dragover', e => {
        if (this._dragFrom == null) return;
        const r = rail.getBoundingClientRect();
        const EDGE = 40;
        const dt = e.clientY - r.top;
        const db = r.bottom - e.clientY;
        if (dt < EDGE) rail.scrollTop -= Math.ceil((EDGE - dt) / 3);else if (db < EDGE) rail.scrollTop += Math.ceil((EDGE - db) / 3);
      });
      const menu = document.createElement('div');
      menu.className = 'ctxmenu export-hidden';
      menu.setAttribute('data-omelette-chrome', '');
      menu.innerHTML = `
        <button type="button" data-act="skip">Skip slide</button>
        <button type="button" data-act="up">Move up</button>
        <button type="button" data-act="down">Move down</button>
        <button type="button" data-act="duplicate">Duplicate slide</button>
        <hr>
        <button type="button" data-act="delete">Delete slide</button>
      `;
      menu.addEventListener('click', e => {
        const act = e.target && e.target.getAttribute && e.target.getAttribute('data-act');
        if (!act) return;
        const i = this._menuIndex;
        this._closeMenu();
        if (act === 'skip') this._toggleSkip(i);else if (act === 'up') this._moveSlide(i, i - 1);else if (act === 'down') this._moveSlide(i, i + 1);else if (act === 'duplicate') this._duplicateSlide(i);else if (act === 'delete') this._openConfirm(i);
      });
      menu.addEventListener('contextmenu', e => e.preventDefault());

      // Rail resize handle — drag to set --deck-rail-w, persisted to
      // localStorage so the width survives reloads.
      const resize = document.createElement('div');
      resize.className = 'rail-resize export-hidden';
      resize.setAttribute('data-omelette-chrome', '');
      resize.addEventListener('pointerdown', e => {
        e.preventDefault();
        resize.setPointerCapture(e.pointerId);
        resize.setAttribute('data-dragging', '');
        const move = ev => this._setRailWidth(ev.clientX);
        const up = () => {
          resize.removeEventListener('pointermove', move);
          resize.removeEventListener('pointerup', up);
          resize.removeEventListener('pointercancel', up);
          resize.removeAttribute('data-dragging');
          try {
            localStorage.setItem('deck-stage.railWidth', String(this._railPx));
          } catch (err) {}
        };
        resize.addEventListener('pointermove', move);
        resize.addEventListener('pointerup', up);
        resize.addEventListener('pointercancel', up);
      });

      // Delete-confirm dialog — mirrors the SPA's ConfirmDialog layout.
      const confirm = document.createElement('div');
      confirm.className = 'confirm-backdrop export-hidden';
      confirm.setAttribute('data-omelette-chrome', '');
      confirm.innerHTML = `
        <div class="confirm" role="dialog" aria-modal="true">
          <div class="body">
            <div class="title">Delete slide?</div>
            <div class="msg">This slide will be removed from the deck.</div>
          </div>
          <div class="footer">
            <button type="button" class="cancel">Cancel</button>
            <button type="button" class="danger">Delete</button>
          </div>
        </div>
      `;
      confirm.addEventListener('click', e => {
        if (e.target === confirm) this._closeConfirm();
      });
      confirm.querySelector('.cancel').addEventListener('click', () => this._closeConfirm());
      confirm.querySelector('.danger').addEventListener('click', () => {
        const i = this._confirmIndex;
        this._closeConfirm();
        this._deleteSlide(i);
      });
      this._root.append(style, rail, resize, stage, overlay, menu, confirm);
      this._canvas = canvas;
      this._stage = stage;
      this._slot = slot;
      this._overlay = overlay;
      this._rail = rail;
      this._resize = resize;
      this._menu = menu;
      this._confirm = confirm;
      this._countEl = overlay.querySelector('.current');
      this._totalEl = overlay.querySelector('.total');

      // Restore persisted rail width.
      let rw = 188;
      try {
        const s = localStorage.getItem('deck-stage.railWidth');
        if (s) rw = parseInt(s, 10) || rw;
      } catch (err) {}
      this._setRailWidth(rw);
      this._syncRailHidden();
    }
    _setRailWidth(px) {
      const w = Math.max(120, Math.min(360, Math.round(px)));
      this._railPx = w;
      this.style.setProperty('--deck-rail-w', w + 'px');
      this._fit();
      // _scaleThumbs forces a sync layout (frame.offsetWidth) then writes
      // N transforms. During a resize drag this runs per-pointermove;
      // coalesce to one per frame.
      if (!this._scaleRaf) {
        this._scaleRaf = requestAnimationFrame(() => {
          this._scaleRaf = null;
          this._scaleThumbs();
        });
      }
    }

    /** @page must live in the document stylesheet — it's a no-op inside
     *  shadow DOM. Inject/update a single <head> style tag so the print
     *  sheet matches the design size and Save-as-PDF yields one slide per
     *  page with no margins. */
    _syncPrintPageRule() {
      const id = 'deck-stage-print-page';
      let tag = document.getElementById(id);
      if (!tag) {
        tag = document.createElement('style');
        tag.id = id;
        document.head.appendChild(tag);
      }
      tag.textContent = '@page { size: ' + this.designWidth + 'px ' + this.designHeight + 'px; margin: 0; } ' + '@media print { html, body { margin: 0 !important; padding: 0 !important; background: none !important; overflow: visible !important; height: auto !important; } ' + '* { -webkit-print-color-adjust: exact; print-color-adjust: exact; } ' +
      // Jump authored animations/transitions to their end state so print
      // never captures mid-entrance — pairs with the beforeprint handler
      // in connectedCallback that sets data-deck-active on every slide.
      '*, *::before, *::after { animation-delay: -99s !important; animation-duration: .001s !important; ' + 'animation-iteration-count: 1 !important; animation-fill-mode: both !important; ' + 'animation-play-state: running !important; transition-duration: 0s !important; } }';
    }
    _onSlotChange() {
      // Rail mutations (delete/move/duplicate) already reconcile synchronously and
      // emit slidechange with reason 'api'; skip the async slotchange that
      // would otherwise re-broadcast with reason 'init'.
      if (this._squelchSlotChange) {
        this._squelchSlotChange = false;
        return;
      }
      this._collectSlides();
      this._restoreIndex();
      this._applyIndex({
        showOverlay: false,
        broadcast: true,
        reason: 'init'
      });
      this._fit();
    }
    _collectSlides() {
      const assigned = this._slot.assignedElements({
        flatten: true
      });
      this._slides = assigned.filter(el => {
        // Skip template/style/script nodes even if someone slots them.
        const tag = el.tagName;
        return tag !== 'TEMPLATE' && tag !== 'SCRIPT' && tag !== 'STYLE';
      });
      this._slideSet = new Set(this._slides);
      this._slides.forEach((slide, i) => {
        const n = i + 1;
        slide.setAttribute('data-screen-label', `${pad2(n)} ${getSlideLabel(slide)}`);

        // Validation attribute for comment flow / auto-checks.
        if (!slide.hasAttribute('data-om-validate')) {
          slide.setAttribute('data-om-validate', VALIDATE_ATTR);
        }
        slide.setAttribute('data-deck-slide', String(i));
      });
      if (this._totalEl) this._totalEl.textContent = String(this._slides.length || 1);
      if (this._index >= this._slides.length) this._index = Math.max(0, this._slides.length - 1);
      this._markLastVisible();
      this._renderRail();
    }

    /** Tag the last non-skipped slide so print CSS can drop its
     *  break-after (see the @media print comment above — :last-child
     *  alone matches a hidden skipped slide). */
    _markLastVisible() {
      let last = null;
      this._slides.forEach(s => {
        s.removeAttribute('data-deck-last-visible');
        if (!s.hasAttribute('data-deck-skip')) last = s;
      });
      if (last) last.setAttribute('data-deck-last-visible', '');
    }
    _loadNotes() {
      const tag = document.getElementById('speaker-notes');
      if (!tag) {
        this._notes = [];
        return;
      }
      try {
        const parsed = JSON.parse(tag.textContent || '[]');
        if (Array.isArray(parsed)) this._notes = parsed;
      } catch (e) {
        console.warn('[deck-stage] Failed to parse #speaker-notes JSON:', e);
        this._notes = [];
      }
    }
    _restoreIndex() {
      // The host's ?slide= param is delivered as a #<int> hash (1-indexed) on
      // the iframe src. No hash → slide 1; the deck itself keeps no position
      // state across loads.
      const h = (location.hash || '').match(/^#(\d+)$/);
      if (h) {
        const n = parseInt(h[1], 10) - 1;
        if (n >= 0 && n < this._slides.length) this._index = n;
      }
    }
    _applyIndex({
      showOverlay = true,
      broadcast = true,
      reason = 'init'
    } = {}) {
      if (!this._slides.length) return;
      const prev = this._prevIndex == null ? -1 : this._prevIndex;
      const curr = this._index;
      // Keep the iframe's own hash in sync so an in-iframe location.reload()
      // (reload banner path in viewer-handle.ts) lands on the current slide,
      // not the stale deep-link hash from initial load.
      try {
        history.replaceState(null, '', '#' + (curr + 1));
      } catch (e) {}
      this._slides.forEach((s, i) => {
        if (i === curr) s.setAttribute('data-deck-active', '');else s.removeAttribute('data-deck-active');
      });
      if (this._countEl) this._countEl.textContent = String(curr + 1);
      // Follow-scroll on every navigation (init deep-link, keyboard, click,
      // tap, external goTo) — the only time we *don't* want the rail to
      // track current is after a rail-internal mutation, where _renderRail
      // has already restored the user's scroll position and yanking back to
      // current would undo it.
      this._syncRail(reason !== 'mutation');
      if (broadcast) {
        // (1) Legacy: host-window postMessage for speaker-notes renderers.
        try {
          window.postMessage({
            slideIndexChanged: curr,
            deckTotal: this._slides.length,
            deckSkipped: this._skippedIndices()
          }, '*');
        } catch (e) {}

        // (2) In-page CustomEvent on the <deck-stage> element itself.
        //     Bubbles and composes out of shadow DOM so slide code can listen:
        //       document.querySelector('deck-stage').addEventListener('slidechange', e => {
        //         e.detail.index, e.detail.previousIndex, e.detail.total, e.detail.slide, e.detail.reason
        //       });
        const detail = {
          index: curr,
          previousIndex: prev,
          total: this._slides.length,
          slide: this._slides[curr] || null,
          previousSlide: prev >= 0 ? this._slides[prev] || null : null,
          reason: reason // 'init' | 'keyboard' | 'click' | 'tap' | 'api'
        };
        this.dispatchEvent(new CustomEvent('slidechange', {
          detail,
          bubbles: true,
          composed: true
        }));
      }
      this._prevIndex = curr;
      if (showOverlay) this._flashOverlay();
    }
    _flashOverlay() {
      // Host posts __omelette_presenting while in fullscreen/tab presentation
      // mode — suppress the nav footer entirely (both hover and slide-change
      // flash) so the audience sees clean slides.
      if (!this._overlay || this._presenting) return;
      this._overlay.setAttribute('data-visible', '');
      if (this._hideTimer) clearTimeout(this._hideTimer);
      this._hideTimer = setTimeout(() => {
        this._overlay.removeAttribute('data-visible');
      }, OVERLAY_HIDE_MS);
    }
    _railWidth() {
      // State-based, no offsetWidth: the first _fit() can run before the
      // rail has had layout on some load paths, and a 0 there paints the
      // slide full-width for one frame before the post-slotchange _fit()
      // corrects it.
      if (!this._railEnabled || !this._railVisible || this.hasAttribute('no-rail') || this.hasAttribute('noscale') || this._presenting || this._previewMode || NARROW_MQ.matches) return 0;
      return this._railPx || 0;
    }
    _fit() {
      if (!this._canvas) return;
      const stage = this._canvas.parentElement;
      // PPTX export sets noscale so the DOM capture sees authored-size
      // geometry — the scaled canvas is in shadow DOM, so the exporter's
      // resetTransformSelector can't reach .canvas.style.transform directly.
      if (this.hasAttribute('noscale')) {
        this._canvas.style.transform = 'none';
        if (stage) stage.style.left = '0';
        if (this._overlay) this._overlay.style.marginLeft = '0';
        return;
      }
      const rw = this._railWidth();
      if (stage) stage.style.left = rw + 'px';
      // Overlay is centred on the viewport via left:50% + translate(-50%);
      // marginLeft shifts the centre by rw/2 so it lands in the middle of
      // the [rw, innerWidth] stage region.
      if (this._overlay) this._overlay.style.marginLeft = rw / 2 + 'px';
      const vw = window.innerWidth - rw;
      const vh = window.innerHeight;
      const s = Math.min(vw / this.designWidth, vh / this.designHeight);
      this._canvas.style.transform = `scale(${s})`;
    }
    _onResize() {
      this._fit();
      // Crossing the narrow-viewport breakpoint reveals the rail — rerun the
      // thumbnail scale the same way _setRailWidth does.
      if (!this._scaleRaf) {
        this._scaleRaf = requestAnimationFrame(() => {
          this._scaleRaf = null;
          this._scaleThumbs();
        });
      }
    }
    _onMouseMove() {
      // Keep overlay visible while mouse moves; hide after idle.
      this._flashOverlay();
    }
    _onMessage(e) {
      const d = e.data;
      if (d && typeof d.__omelette_presenting === 'boolean') {
        this._presenting = d.__omelette_presenting;
        if (this._presenting && this._overlay) {
          this._overlay.removeAttribute('data-visible');
          if (this._hideTimer) clearTimeout(this._hideTimer);
        }
        this._syncRailHidden();
        this._closeMenu();
        this._closeConfirm();
        this._fit();
        this._scaleThumbs();
      }
      // Host's Preview segment (ViewerMode='none'): the rail's drag-reorder /
      // right-click skip-delete affordances are editing chrome, so hide it
      // while the user is just looking at the deck. Same hard-hide path as
      // presenting; independent of the user's _railVisible preference so
      // returning to Edit restores whatever they had.
      if (d && typeof d.__omelette_preview_mode === 'boolean') {
        if (d.__omelette_preview_mode === this._previewMode) return;
        this._previewMode = d.__omelette_preview_mode;
        this._syncRailHidden();
        this._closeMenu();
        this._closeConfirm();
        this._fit();
        this._scaleThumbs();
      }
      // Per-viewer show/hide, driven by the TweaksPanel's auto-injected
      // "Thumbnail rail" toggle (or any author script). Independent of
      // whether the Tweaks panel itself is open — closing the panel
      // doesn't change rail visibility. Persists alongside rail width.
      if (d && d.type === '__deck_rail_visible' && typeof d.on === 'boolean') {
        if (d.on === this._railVisible) return;
        this._railVisible = d.on;
        try {
          localStorage.setItem('deck-stage.railVisible', d.on ? '1' : '0');
        } catch (e) {}
        // Arm the transition, commit it, then flip state — otherwise the
        // browser coalesces both writes and nothing animates on show.
        this.setAttribute('data-rail-anim', '');
        void (this._rail && this._rail.offsetHeight);
        this._syncRailHidden();
        this._fit();
        this._scaleThumbs();
        clearTimeout(this._railAnimTimer);
        this._railAnimTimer = setTimeout(() => this.removeAttribute('data-rail-anim'), 220);
      }
      if (d && d.type === '__omelette_rail_enabled') this._enableRail();
    }
    _syncRailHidden() {
      if (!this._rail) return;
      // data-presenting is the hard hide (display:none) for flag-off,
      // presentation mode, and the host's Preview segment — instant, no
      // transition. data-user-hidden is the soft hide (translateX(-100%))
      // for the viewer's rail toggle, so show/hide slides under
      // :host([data-rail-anim]).
      const hard = !this._railEnabled || this._presenting || this._previewMode;
      if (hard) this._rail.setAttribute('data-presenting', '');else this._rail.removeAttribute('data-presenting');
      if (!this._railVisible) this._rail.setAttribute('data-user-hidden', '');else this._rail.removeAttribute('data-user-hidden');
      // translateX hide leaves thumbs (tabIndex=0) in the tab order —
      // inert keeps them unfocusable while the rail is off-screen.
      this._rail.inert = hard || !this._railVisible;
    }
    _onTap(e) {
      // Touch-only — keyboard + the overlay toolbar cover nav on desktop.
      if (FINE_POINTER_MQ.matches) return;
      // Only taps that land on the stage (slide content or letterbox); the
      // overlay / rail / menus are siblings with their own click handlers.
      const path = e.composedPath();
      if (!this._stage || !path.includes(this._stage)) return;
      // Let interactive slide content keep the tap. composedPath (not
      // e.target.closest) so we see through open shadow roots — a <button>
      // inside a slide-authored custom element retargets e.target to the
      // host but still appears in the composed path.
      if (e.defaultPrevented) return;
      for (const n of path) {
        if (n === this._stage) break;
        if (n.matches && n.matches(INTERACTIVE_SEL)) return;
      }
      e.preventDefault();
      const rw = this._railWidth();
      const mid = rw + (window.innerWidth - rw) / 2;
      this._advance(e.clientX < mid ? -1 : 1, 'tap');
    }
    _onKey(e) {
      // Ignore when the user is typing.
      const t = e.target;
      if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
      // Confirm dialog swallows nav keys while open; Escape cancels. Enter
      // is left to the focused button's native activation so Tab→Cancel
      // →Enter activates Cancel, not the window-level confirm path.
      if (this._confirm && this._confirm.hasAttribute('data-open')) {
        if (e.key === 'Escape') {
          this._closeConfirm();
          e.preventDefault();
        }
        return;
      }
      if (e.key === 'Escape' && this._menu && this._menu.hasAttribute('data-open')) {
        this._closeMenu();
        e.preventDefault();
        return;
      }
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const key = e.key;
      let handled = true;
      if (key === 'ArrowRight' || key === 'PageDown' || key === ' ' || key === 'Spacebar') {
        this._advance(1, 'keyboard');
      } else if (key === 'ArrowLeft' || key === 'PageUp') {
        this._advance(-1, 'keyboard');
      } else if (key === 'Home') {
        this._go(0, 'keyboard');
      } else if (key === 'End') {
        this._go(this._slides.length - 1, 'keyboard');
      } else if (key === 'r' || key === 'R') {
        this._go(0, 'keyboard');
      } else if (/^[0-9]$/.test(key)) {
        // 1..9 jump to that slide; 0 jumps to 10.
        const n = key === '0' ? 9 : parseInt(key, 10) - 1;
        if (n < this._slides.length) this._go(n, 'keyboard');
      } else {
        handled = false;
      }
      if (handled) {
        e.preventDefault();
        this._flashOverlay();
      }
    }
    _go(i, reason = 'api') {
      if (!this._slides.length) return;
      const clamped = Math.max(0, Math.min(this._slides.length - 1, i));
      if (clamped === this._index) {
        this._flashOverlay();
        return;
      }
      this._index = clamped;
      this._applyIndex({
        showOverlay: true,
        broadcast: true,
        reason
      });
    }

    /** Step forward/back skipping any slide marked data-deck-skip. Falls
     *  back to _go's clamp-at-ends behaviour (flash overlay) when there's
     *  nothing further in that direction. */
    _advance(dir, reason) {
      if (!this._slides.length) return;
      let i = this._index + dir;
      while (i >= 0 && i < this._slides.length && this._slides[i].hasAttribute('data-deck-skip')) {
        i += dir;
      }
      if (i < 0 || i >= this._slides.length) {
        this._flashOverlay();
        return;
      }
      this._go(i, reason);
    }

    // ── Thumbnail rail ────────────────────────────────────────────────────
    //
    // Thumbs are keyed by slide element and reused across _renderRail()
    // calls, so a reorder/delete is an O(changed) DOM shuffle instead of an
    // O(N) teardown-and-re-clone. Each thumb starts as a lightweight shell
    // (num + empty frame); the clone is materialized lazily by an
    // IntersectionObserver when the frame scrolls into (or near) view, so
    // only visible-ish slides pay the clone + image-decode cost.

    _renderRail() {
      if (!this._rail || !this._railEnabled) {
        this._thumbs = [];
        return;
      }
      // FLIP: record each *materialized* thumb's top before the reconcile.
      // Off-screen (non-materialized) thumbs don't need the animation and
      // skipping their getBoundingClientRect saves a forced layout per
      // off-screen thumb on large decks.
      const prevTops = new Map();
      (this._thumbs || []).forEach(({
        thumb,
        slide,
        host
      }) => {
        if (host) prevTops.set(slide, thumb.getBoundingClientRect().top);
      });
      const st = this._rail.scrollTop;

      // Reconcile: reuse thumbs that already exist for a slide, create
      // shells for new slides, drop thumbs for removed slides.
      const bySlide = new Map();
      (this._thumbs || []).forEach(t => bySlide.set(t.slide, t));
      const next = [];
      this._slides.forEach(slide => {
        let t = bySlide.get(slide);
        if (t) bySlide.delete(slide);else t = this._makeThumb(slide);
        next.push(t);
      });
      // Orphans — slides removed since last render.
      bySlide.forEach(t => {
        if (this._railObserver) this._railObserver.unobserve(t.frame);
        t.thumb.remove();
      });
      // Put thumbs into document order to match _slides. insertBefore on
      // an already-correctly-placed node is a no-op, so this is cheap
      // when nothing moved.
      next.forEach((t, i) => {
        const want = t.thumb;
        const at = this._rail.children[i];
        if (at !== want) this._rail.insertBefore(want, at || null);
        t.i = i;
        t.num.textContent = String(i + 1);
        if (t.slide.hasAttribute('data-deck-skip')) t.thumb.setAttribute('data-skip', '');else t.thumb.removeAttribute('data-skip');
      });
      this._thumbs = next;
      this._rail.scrollTop = st;
      if (prevTops.size) {
        const moved = [];
        this._thumbs.forEach(({
          thumb,
          slide
        }) => {
          const old = prevTops.get(slide);
          if (old == null) return;
          const dy = old - thumb.getBoundingClientRect().top;
          if (Math.abs(dy) < 1) return;
          thumb.style.transition = 'none';
          thumb.style.transform = `translateY(${dy}px)`;
          moved.push(thumb);
        });
        if (moved.length) {
          // Commit the inverted positions before flipping the transition
          // on — otherwise the browser coalesces both style writes and
          // nothing animates.
          void this._rail.offsetHeight;
          moved.forEach(t => {
            t.style.transition = 'transform 180ms cubic-bezier(.2,.7,.3,1)';
            t.style.transform = '';
          });
          setTimeout(() => moved.forEach(t => {
            t.style.transition = '';
          }), 220);
        }
      }
      requestAnimationFrame(() => this._scaleThumbs());
      this._syncRail(false);
    }

    /** Create a lightweight thumb shell for one slide. The clone is
     *  materialized later by the IntersectionObserver. Event handlers
     *  look up the thumb's *current* index (via _thumbs.indexOf) so the
     *  same element can be reused across reorders. */
    _makeThumb(slide) {
      const thumb = document.createElement('div');
      thumb.className = 'thumb';
      thumb.tabIndex = 0;
      const num = document.createElement('div');
      num.className = 'num';
      const frame = document.createElement('div');
      frame.className = 'frame';
      thumb.append(num, frame);
      const entry = {
        thumb,
        num,
        frame,
        slide,
        clone: null,
        host: null,
        i: -1
      };
      // entry.i is refreshed on every _renderRail reconcile pass, so
      // handlers read the thumb's current position without an O(N) scan.
      const idx = () => entry.i;
      thumb.addEventListener('click', () => this._go(idx(), 'click'));
      // ↑/↓ step through the rail when a thumb has focus. _go clamps at the
      // ends and _applyIndex→_syncRail scrolls the new current thumb into
      // view; we move focus to it (preventScroll — _syncRail already
      // scrolled) so a held key walks the whole list. stopPropagation keeps
      // this out of the window-level _onKey nav handler.
      thumb.addEventListener('keydown', e => {
        if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;
        if (e.metaKey || e.ctrlKey || e.altKey) return;
        e.preventDefault();
        e.stopPropagation();
        this._go(idx() + (e.key === 'ArrowDown' ? 1 : -1), 'keyboard');
        const cur = this._thumbs && this._thumbs[this._index];
        if (cur) cur.thumb.focus({
          preventScroll: true
        });
      });
      thumb.addEventListener('contextmenu', e => {
        e.preventDefault();
        this._openMenu(idx(), e.clientX, e.clientY);
      });
      thumb.draggable = true;
      thumb.addEventListener('dragstart', e => {
        this._dragFrom = idx();
        thumb.setAttribute('data-dragging', '');
        e.dataTransfer.effectAllowed = 'move';
        try {
          e.dataTransfer.setData('text/plain', String(this._dragFrom));
        } catch (err) {}
      });
      thumb.addEventListener('dragend', () => {
        thumb.removeAttribute('data-dragging');
        this._clearDrop();
        this._dragFrom = null;
      });
      thumb.addEventListener('dragover', e => {
        if (this._dragFrom == null) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        const r = thumb.getBoundingClientRect();
        this._setDrop(idx(), e.clientY < r.top + r.height / 2 ? 'before' : 'after');
      });
      thumb.addEventListener('drop', e => {
        if (this._dragFrom == null) return;
        e.preventDefault();
        const i = idx();
        const r = thumb.getBoundingClientRect();
        let to = e.clientY >= r.top + r.height / 2 ? i + 1 : i;
        if (this._dragFrom < to) to--;
        const from = this._dragFrom;
        this._clearDrop();
        this._dragFrom = null;
        if (to !== from) this._moveSlide(from, to);
      });
      if (this._railObserver) this._railObserver.observe(frame);
      frame.__deckThumb = entry;
      return entry;
    }

    /** Lazily build the clone for a thumb that has scrolled into view. */
    _materialize(entry) {
      if (entry.host) return;
      const dw = this.designWidth,
        dh = this.designHeight;
      let clone = entry.slide.cloneNode(true);
      clone.removeAttribute('id');
      clone.removeAttribute('data-deck-active');
      clone.querySelectorAll('[id]').forEach(el => el.removeAttribute('id'));
      // Neuter heavy media; replace <video> with its poster so the box
      // keeps a visual. <iframe>/<audio> become empty placeholders.
      clone.querySelectorAll('iframe, audio, object, embed').forEach(el => {
        el.removeAttribute('src');
        el.removeAttribute('srcdoc');
        el.removeAttribute('data');
        el.innerHTML = '';
      });
      clone.querySelectorAll('video').forEach(el => {
        if (!el.poster) {
          el.removeAttribute('src');
          el.innerHTML = '';
          return;
        }
        const img = document.createElement('img');
        img.src = el.poster;
        img.alt = '';
        img.style.cssText = el.style.cssText + ';object-fit:cover;width:100%;height:100%;';
        img.className = el.className;
        el.replaceWith(img);
      });
      // Images: defer decode and let the browser pick the smallest
      // srcset candidate for the ~140px thumb. Same-URL clones reuse the
      // slide's decoded bitmap (URL-keyed cache), so the remaining cost
      // is paint/composite — lazy+async keeps that off the main thread.
      clone.querySelectorAll('img').forEach(el => {
        el.loading = 'lazy';
        el.decoding = 'async';
        if (el.srcset) el.sizes = (this._railPx || 188) + 'px';
      });
      // Custom elements inside the slide would have their
      // connectedCallback fire when the clone is appended. Replace them
      // with inert boxes so a component-heavy deck doesn't run N copies
      // of each component's mount logic in the rail. Children are
      // preserved so layout-wrapper elements (<my-column><h2>…</h2>)
      // still show their authored content; the querySelectorAll NodeList
      // is static, so nested custom elements in the moved subtree are
      // still visited on later iterations.
      const neuter = el => {
        const box = document.createElement('div');
        box.style.cssText = (el.getAttribute('style') || '') + ';background:rgba(0,0,0,0.06);border:1px dashed rgba(0,0,0,0.15);';
        box.className = el.className;
        // Preserve theming/i18n hooks so [data-*] / :lang() / [dir]
        // descendant selectors still match the neutered root.
        for (const a of el.attributes) {
          const n = a.name;
          if (n.startsWith('data-') || n.startsWith('aria-') || n === 'lang' || n === 'dir' || n === 'role' || n === 'title') {
            box.setAttribute(n, a.value);
          }
        }
        while (el.firstChild) box.appendChild(el.firstChild);
        return box;
      };
      // querySelectorAll('*') returns descendants only — a custom-element
      // slide root (<my-slide>…</my-slide>) would slip through and upgrade
      // on append. Swap the root first.
      if (clone.tagName.includes('-')) clone = neuter(clone);
      clone.querySelectorAll('*').forEach(el => {
        if (el.tagName.includes('-')) el.replaceWith(neuter(el));
      });
      clone.style.cssText += ';position:absolute;top:0;left:0;transform-origin:0 0;' + 'pointer-events:none;width:' + dw + 'px;height:' + dh + 'px;' + 'box-sizing:border-box;overflow:hidden;visibility:visible;opacity:1;';
      const host = document.createElement('div');
      host.style.cssText = 'position:absolute;inset:0;';
      this._syncThumbHostAttrs(host);
      const sr = host.attachShadow({
        mode: 'open'
      });
      if (this._adoptedSheet) sr.adoptedStyleSheets = [this._adoptedSheet];else {
        const st = document.createElement('style');
        st.textContent = this._authorCss || '';
        sr.appendChild(st);
      }
      sr.appendChild(clone);
      entry.frame.appendChild(host);
      entry.host = host;
      entry.clone = clone;
      if (this._thumbScale) clone.style.transform = 'scale(' + this._thumbScale + ')';
      // Once materialized the IO callback is a no-op early-return —
      // unobserve so scroll doesn't keep firing it.
      if (this._railObserver) this._railObserver.unobserve(entry.frame);
    }

    /** Re-clone a single thumb (live-update path). No-op if the thumb
     *  hasn't been materialized yet — it'll pick up current content when
     *  it scrolls into view. */
    _refreshThumb(slide) {
      const entry = (this._thumbs || []).find(t => t.slide === slide);
      if (!entry || !entry.host) return;
      entry.host.remove();
      entry.host = entry.clone = null;
      this._materialize(entry);
    }
    _scaleThumbs() {
      if (!this._thumbs || !this._thumbs.length) return;
      // Every frame is the same width; if it reads 0 the rail is
      // display:none (noscale / no-rail / presenting / print) — leave the
      // clones as-is and re-run when the rail is revealed.
      const fw = this._thumbs[0].frame.offsetWidth;
      if (!fw) return;
      this._thumbScale = fw / this.designWidth;
      this._thumbs.forEach(({
        clone
      }) => {
        if (clone) clone.style.transform = 'scale(' + this._thumbScale + ')';
      });
    }
    _setDrop(i, where) {
      // dragover fires at pointer-event rate; touch only the previous
      // and new target rather than sweeping all N thumbs.
      const t = this._thumbs && this._thumbs[i];
      if (this._dropOn && this._dropOn !== t) {
        this._dropOn.thumb.removeAttribute('data-drop');
      }
      if (t) t.thumb.setAttribute('data-drop', where);
      this._dropOn = t || null;
    }
    _clearDrop() {
      if (this._dropOn) this._dropOn.thumb.removeAttribute('data-drop');
      this._dropOn = null;
    }
    _syncRail(follow) {
      if (!this._thumbs) return;
      this._thumbs.forEach(({
        thumb
      }, i) => {
        if (i === this._index) {
          thumb.setAttribute('data-current', '');
          if (follow && typeof thumb.scrollIntoView === 'function') {
            thumb.scrollIntoView({
              block: 'nearest'
            });
          }
        } else {
          thumb.removeAttribute('data-current');
        }
      });
    }
    _openMenu(i, x, y) {
      if (!this._menu) return;
      this._menuIndex = i;
      const slide = this._slides[i];
      const skip = slide && slide.hasAttribute('data-deck-skip');
      this._menu.querySelector('[data-act="skip"]').textContent = skip ? 'Unskip slide' : 'Skip slide';
      this._menu.querySelector('[data-act="up"]').disabled = i <= 0;
      this._menu.querySelector('[data-act="down"]').disabled = i >= this._slides.length - 1;
      this._menu.querySelector('[data-act="delete"]').disabled = this._slides.length <= 1;
      // Place, then clamp to viewport after it's measurable.
      this._menu.style.left = x + 'px';
      this._menu.style.top = y + 'px';
      this._menu.setAttribute('data-open', '');
      const r = this._menu.getBoundingClientRect();
      const nx = Math.min(x, window.innerWidth - r.width - 4);
      const ny = Math.min(y, window.innerHeight - r.height - 4);
      this._menu.style.left = Math.max(4, nx) + 'px';
      this._menu.style.top = Math.max(4, ny) + 'px';
    }
    _closeMenu() {
      if (this._menu) this._menu.removeAttribute('data-open');
      this._menuIndex = -1;
    }
    _openConfirm(i) {
      if (!this._confirm) return;
      this._confirmIndex = i;
      this._confirm.querySelector('.title').textContent = 'Delete slide ' + (i + 1) + '?';
      this._confirm.setAttribute('data-open', '');
      const btn = this._confirm.querySelector('.danger');
      if (btn && btn.focus) btn.focus();
    }
    _closeConfirm() {
      if (this._confirm) this._confirm.removeAttribute('data-open');
      this._confirmIndex = -1;
    }
    _emitDeckChange(detail) {
      this.dispatchEvent(new CustomEvent('deckchange', {
        detail,
        bubbles: true,
        composed: true
      }));
    }
    _deleteSlide(i) {
      const slide = this._slides[i];
      if (!slide || this._slides.length <= 1) return;
      const wasCurrent = i === this._index;
      if (i < this._index || wasCurrent && i === this._slides.length - 1) this._index--;
      this._squelchSlotChange = true;
      slide.remove();
      this._emitDeckChange({
        action: 'delete',
        from: i,
        slide
      });
      this._collectSlides();
      this._applyIndex({
        showOverlay: true,
        broadcast: true,
        reason: 'mutation'
      });
    }
    _duplicateSlide(i) {
      const slide = this._slides[i];
      if (!slide) return;
      const copy = slide.cloneNode(true);
      // Strip ids so the document stays valid (no duplicate-id collisions
      // with the original). Same treatment _materialize gives rail clones.
      copy.removeAttribute('id');
      copy.querySelectorAll('[id]').forEach(el => el.removeAttribute('id'));
      // Insert after the original and make the copy active so it's the one
      // on screen. _collectSlides re-derives data-screen-label / data-deck-*
      // attrs, so the cloned values are overwritten.
      this._index = i + 1;
      this._squelchSlotChange = true;
      this.insertBefore(copy, slide.nextSibling);
      this._emitDeckChange({
        action: 'duplicate',
        from: i,
        to: i + 1,
        slide: copy
      });
      this._collectSlides();
      this._applyIndex({
        showOverlay: true,
        broadcast: true,
        reason: 'mutation'
      });
    }
    _toggleSkip(i) {
      const slide = this._slides[i];
      if (!slide) return;
      const on = !slide.hasAttribute('data-deck-skip');
      if (on) slide.setAttribute('data-deck-skip', '');else slide.removeAttribute('data-deck-skip');
      if (this._thumbs && this._thumbs[i]) {
        if (on) this._thumbs[i].thumb.setAttribute('data-skip', '');else this._thumbs[i].thumb.removeAttribute('data-skip');
      }
      this._markLastVisible();
      this._emitDeckChange({
        action: on ? 'skip' : 'unskip',
        from: i,
        slide
      });
      // Re-broadcast so the presenter popup's prev/next thumbnails re-pick
      // the nearest non-skipped slide without waiting for a nav event.
      try {
        window.postMessage({
          slideIndexChanged: this._index,
          deckTotal: this._slides.length,
          deckSkipped: this._skippedIndices()
        }, '*');
      } catch (e) {}
    }
    _skippedIndices() {
      const out = [];
      for (let i = 0; i < this._slides.length; i++) {
        if (this._slides[i].hasAttribute('data-deck-skip')) out.push(i);
      }
      return out;
    }
    _moveSlide(i, j) {
      if (j < 0 || j >= this._slides.length || j === i) return;
      const slide = this._slides[i];
      const ref = j < i ? this._slides[j] : this._slides[j].nextSibling;
      // Track the active slide across the reorder so the same content
      // stays on screen.
      const cur = this._index;
      if (cur === i) this._index = j;else if (i < cur && j >= cur) this._index = cur - 1;else if (i > cur && j <= cur) this._index = cur + 1;
      this._squelchSlotChange = true;
      this.insertBefore(slide, ref);
      this._emitDeckChange({
        action: 'move',
        from: i,
        to: j,
        slide
      });
      this._collectSlides();
      this._applyIndex({
        showOverlay: false,
        broadcast: true,
        reason: 'mutation'
      });
    }

    // Public API ------------------------------------------------------------

    /** Current slide index (0-based). */
    get index() {
      return this._index;
    }
    /** Total slide count. */
    get length() {
      return this._slides.length;
    }
    /** Programmatically navigate. */
    goTo(i) {
      this._go(i, 'api');
    }
    next() {
      this._advance(1, 'api');
    }
    prev() {
      this._advance(-1, 'api');
    }
    reset() {
      this._go(0, 'api');
    }
  }
  if (!customElements.get('deck-stage')) {
    customElements.define('deck-stage', DeckStage);
  }
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "deck-stage.js", error: String((e && e.message) || e) }); }

// export/src/animations.jsx
try { (() => {
// @ds-adherence-ignore -- omelette starter scaffold (raw elements/hex/px by design)

/* BEGIN USAGE */
// animations.jsx
// Reusable animation starter: Stage, Timeline, Sprite, easing helpers.
// Exports (to window): Stage, Sprite, PlaybackBar, TextSprite, ImageSprite, RectSprite,
//   useTime, useTimeline, useSprite, Easing, interpolate, animate, clamp.
//
// Usage (in an HTML file that loads React + Babel):
//
//   <Stage width={1280} height={720} duration={10} background="#f6f4ef">
//     <MyScene />
//   </Stage>
//
// <Stage> auto-scales to the viewport and provides the scrubber, play/pause,
// ←/→ seek, space, and 0-to-reset controls, and persists the playhead.
// Inside <Stage>, any child can call useTime() to read the current
// playhead (seconds). Or wrap content in <Sprite start={1} end={4}>...</Sprite>
// to only render during that window -- children receive a `localTime` and
// `progress` via the useSprite() hook. Use Easing + interpolate()/animate()
// for tweens; TextSprite / ImageSprite / RectSprite have built-in entry/exit.
// Build YOUR scenes by composing Sprites inside a Stage.
/* END USAGE */
// ─────────────────────────────────────────────────────────────────────────────

// ── Easing functions (hand-rolled, Popmotion-style) ─────────────────────────
// All easings take t ∈ [0,1] and return eased t ∈ [0,1] (may overshoot for back/elastic).
const Easing = {
  linear: t => t,
  // Quad
  easeInQuad: t => t * t,
  easeOutQuad: t => t * (2 - t),
  easeInOutQuad: t => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,
  // Cubic
  easeInCubic: t => t * t * t,
  easeOutCubic: t => --t * t * t + 1,
  easeInOutCubic: t => t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1,
  // Quart
  easeInQuart: t => t * t * t * t,
  easeOutQuart: t => 1 - --t * t * t * t,
  easeInOutQuart: t => t < 0.5 ? 8 * t * t * t * t : 1 - 8 * --t * t * t * t,
  // Expo
  easeInExpo: t => t === 0 ? 0 : Math.pow(2, 10 * (t - 1)),
  easeOutExpo: t => t === 1 ? 1 : 1 - Math.pow(2, -10 * t),
  easeInOutExpo: t => {
    if (t === 0) return 0;
    if (t === 1) return 1;
    if (t < 0.5) return 0.5 * Math.pow(2, 20 * t - 10);
    return 1 - 0.5 * Math.pow(2, -20 * t + 10);
  },
  // Sine
  easeInSine: t => 1 - Math.cos(t * Math.PI / 2),
  easeOutSine: t => Math.sin(t * Math.PI / 2),
  easeInOutSine: t => -(Math.cos(Math.PI * t) - 1) / 2,
  // Back (overshoot)
  easeOutBack: t => {
    const c1 = 1.70158,
      c3 = c1 + 1;
    return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
  },
  easeInBack: t => {
    const c1 = 1.70158,
      c3 = c1 + 1;
    return c3 * t * t * t - c1 * t * t;
  },
  easeInOutBack: t => {
    const c1 = 1.70158,
      c2 = c1 * 1.525;
    return t < 0.5 ? Math.pow(2 * t, 2) * ((c2 + 1) * 2 * t - c2) / 2 : (Math.pow(2 * t - 2, 2) * ((c2 + 1) * (t * 2 - 2) + c2) + 2) / 2;
  },
  // Elastic
  easeOutElastic: t => {
    const c4 = 2 * Math.PI / 3;
    if (t === 0) return 0;
    if (t === 1) return 1;
    return Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1;
  }
};

// ── Core interpolation helpers ──────────────────────────────────────────────

// Clamp a value to [min, max]
const clamp = (v, min, max) => Math.max(min, Math.min(max, v));

// interpolate([0, 0.5, 1], [0, 100, 50], ease?) -> fn(t)
// Popmotion-style: linearly maps t across input keyframes to output values,
// with optional easing per segment (single fn or array of fns).
function interpolate(input, output, ease = Easing.linear) {
  return t => {
    if (t <= input[0]) return output[0];
    if (t >= input[input.length - 1]) return output[output.length - 1];
    for (let i = 0; i < input.length - 1; i++) {
      if (t >= input[i] && t <= input[i + 1]) {
        const span = input[i + 1] - input[i];
        const local = span === 0 ? 0 : (t - input[i]) / span;
        const easeFn = Array.isArray(ease) ? ease[i] || Easing.linear : ease;
        const eased = easeFn(local);
        return output[i] + (output[i + 1] - output[i]) * eased;
      }
    }
    return output[output.length - 1];
  };
}

// animate({from, to, start, end, ease})(t) — simpler single-segment tween.
// Returns `from` before `start`, `to` after `end`.
function animate({
  from = 0,
  to = 1,
  start = 0,
  end = 1,
  ease = Easing.easeInOutCubic
}) {
  return t => {
    if (t <= start) return from;
    if (t >= end) return to;
    const local = (t - start) / (end - start);
    return from + (to - from) * ease(local);
  };
}

// ── Timeline context ────────────────────────────────────────────────────────

const TimelineContext = React.createContext({
  time: 0,
  duration: 10,
  playing: false
});
const useTime = () => React.useContext(TimelineContext).time;
const useTimeline = () => React.useContext(TimelineContext);

// ── Sprite ──────────────────────────────────────────────────────────────────
// Renders children only when the playhead is inside [start, end]. Provides
// a sub-context with `localTime` (seconds since start) and `progress` (0..1).
//
//   <Sprite start={2} end={5}>
//     {({ localTime, progress }) => <Thing x={progress * 100} />}
//   </Sprite>
//
// Or as a plain wrapper — children can call useSprite() themselves.

const SpriteContext = React.createContext({
  localTime: 0,
  progress: 0,
  duration: 0
});
const useSprite = () => React.useContext(SpriteContext);
function Sprite({
  start = 0,
  end = Infinity,
  children,
  keepMounted = false
}) {
  const {
    time
  } = useTimeline();
  const visible = time >= start && time <= end;
  if (!visible && !keepMounted) return null;
  const duration = end - start;
  const localTime = Math.max(0, time - start);
  const progress = duration > 0 && isFinite(duration) ? clamp(localTime / duration, 0, 1) : 0;
  const value = {
    localTime,
    progress,
    duration,
    visible
  };
  return /*#__PURE__*/React.createElement(SpriteContext.Provider, {
    value: value
  }, typeof children === 'function' ? children(value) : children);
}

// ── Sample sprite components ────────────────────────────────────────────────

// TextSprite: fades/slides text in on entry, holds, then fades out on exit.
// Props: text, x, y, size, color, font, entryDur, exitDur, align
function TextSprite({
  text,
  x = 0,
  y = 0,
  size = 48,
  color = '#111',
  font = 'Inter, system-ui, sans-serif',
  weight = 600,
  entryDur = 0.45,
  exitDur = 0.35,
  entryEase = Easing.easeOutBack,
  exitEase = Easing.easeInCubic,
  align = 'left',
  letterSpacing = '-0.01em'
}) {
  const {
    localTime,
    duration
  } = useSprite();
  const exitStart = Math.max(0, duration - exitDur);
  let opacity = 1;
  let ty = 0;
  if (localTime < entryDur) {
    const t = entryEase(clamp(localTime / entryDur, 0, 1));
    opacity = t;
    ty = (1 - t) * 16;
  } else if (localTime > exitStart) {
    const t = exitEase(clamp((localTime - exitStart) / exitDur, 0, 1));
    opacity = 1 - t;
    ty = -t * 8;
  }
  const translateX = align === 'center' ? '-50%' : align === 'right' ? '-100%' : '0';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x,
      top: y,
      transform: `translate(${translateX}, ${ty}px)`,
      opacity,
      fontFamily: font,
      fontSize: size,
      fontWeight: weight,
      color,
      letterSpacing,
      whiteSpace: 'pre',
      lineHeight: 1.1,
      willChange: 'transform, opacity'
    }
  }, text);
}

// ImageSprite: scales + fades in; optional Ken Burns drift during hold.
function ImageSprite({
  src,
  x = 0,
  y = 0,
  width = 400,
  height = 300,
  entryDur = 0.6,
  exitDur = 0.4,
  kenBurns = false,
  kenBurnsScale = 1.08,
  radius = 12,
  fit = 'cover',
  placeholder = null // {label: string} for striped placeholder
}) {
  const {
    localTime,
    duration
  } = useSprite();
  const exitStart = Math.max(0, duration - exitDur);
  let opacity = 1;
  let scale = 1;
  if (localTime < entryDur) {
    const t = Easing.easeOutCubic(clamp(localTime / entryDur, 0, 1));
    opacity = t;
    scale = 0.96 + 0.04 * t;
  } else if (localTime > exitStart) {
    const t = Easing.easeInCubic(clamp((localTime - exitStart) / exitDur, 0, 1));
    opacity = 1 - t;
    scale = (kenBurns ? kenBurnsScale : 1) + 0.02 * t;
  } else if (kenBurns) {
    const holdSpan = exitStart - entryDur;
    const holdT = holdSpan > 0 ? (localTime - entryDur) / holdSpan : 0;
    scale = 1 + (kenBurnsScale - 1) * holdT;
  }
  const content = placeholder ? /*#__PURE__*/React.createElement("div", {
    style: {
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'repeating-linear-gradient(135deg, #e9e6df 0 10px, #dcd8cf 10px 20px)',
      color: '#6b6458',
      fontFamily: 'JetBrains Mono, ui-monospace, monospace',
      fontSize: 13,
      letterSpacing: '0.04em',
      textTransform: 'uppercase'
    }
  }, placeholder.label || 'image') : /*#__PURE__*/React.createElement("img", {
    src: src,
    alt: "",
    style: {
      width: '100%',
      height: '100%',
      objectFit: fit,
      display: 'block'
    }
  });
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x,
      top: y,
      width,
      height,
      opacity,
      transform: `scale(${scale})`,
      transformOrigin: 'center',
      borderRadius: radius,
      overflow: 'hidden',
      willChange: 'transform, opacity'
    }
  }, content);
}

// RectSprite: simple rectangle that animates position/size/color via props.
// Useful demo primitive — takes a `render` fn for per-frame customization.
function RectSprite({
  x = 0,
  y = 0,
  width = 100,
  height = 100,
  color = '#111',
  radius = 8,
  entryDur = 0.4,
  exitDur = 0.3,
  render // optional: (ctx) => style overrides
}) {
  const spriteCtx = useSprite();
  const {
    localTime,
    duration
  } = spriteCtx;
  const exitStart = Math.max(0, duration - exitDur);
  let opacity = 1;
  let scale = 1;
  if (localTime < entryDur) {
    const t = Easing.easeOutBack(clamp(localTime / entryDur, 0, 1));
    opacity = clamp(localTime / entryDur, 0, 1);
    scale = 0.4 + 0.6 * t;
  } else if (localTime > exitStart) {
    const t = Easing.easeInQuad(clamp((localTime - exitStart) / exitDur, 0, 1));
    opacity = 1 - t;
    scale = 1 - 0.15 * t;
  }
  const overrides = render ? render(spriteCtx) : {};
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x,
      top: y,
      width,
      height,
      background: color,
      borderRadius: radius,
      opacity,
      transform: `scale(${scale})`,
      transformOrigin: 'center',
      willChange: 'transform, opacity',
      ...overrides
    }
  });
}
function Stage({
  width = 1280,
  height = 720,
  duration = 10,
  background = '#f6f4ef',
  fps = 60,
  loop = true,
  autoplay = true,
  persistKey = 'animstage',
  children
}) {
  const [time, setTime] = React.useState(() => {
    try {
      const v = parseFloat(localStorage.getItem(persistKey + ':t') || '0');
      return isFinite(v) ? clamp(v, 0, duration) : 0;
    } catch {
      return 0;
    }
  });
  const [playing, setPlaying] = React.useState(autoplay);
  const [hoverTime, setHoverTime] = React.useState(null);
  const [scale, setScale] = React.useState(1);
  const stageRef = React.useRef(null);
  const canvasRef = React.useRef(null);
  const rafRef = React.useRef(null);
  const lastTsRef = React.useRef(null);

  // Persist playhead
  React.useEffect(() => {
    try {
      localStorage.setItem(persistKey + ':t', String(time));
    } catch {}
  }, [time, persistKey]);

  // Auto-scale to fit viewport
  React.useEffect(() => {
    if (!stageRef.current) return;
    const el = stageRef.current;
    const measure = () => {
      const barH = 44; // playback bar height
      const s = Math.min(el.clientWidth / width, (el.clientHeight - barH) / height);
      setScale(Math.max(0.05, s));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    window.addEventListener('resize', measure);
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, [width, height]);

  // Animation loop
  React.useEffect(() => {
    if (!playing) {
      lastTsRef.current = null;
      return;
    }
    const step = ts => {
      if (lastTsRef.current == null) lastTsRef.current = ts;
      const dt = (ts - lastTsRef.current) / 1000;
      lastTsRef.current = ts;
      setTime(t => {
        let next = t + dt;
        if (next >= duration) {
          if (loop) next = next % duration;else {
            next = duration;
            setPlaying(false);
          }
        }
        return next;
      });
      rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      lastTsRef.current = null;
    };
  }, [playing, duration, loop]);

  // Keyboard: space = play/pause, ← → = seek
  React.useEffect(() => {
    const onKey = e => {
      if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
      if (e.code === 'Space') {
        e.preventDefault();
        setPlaying(p => !p);
      } else if (e.code === 'ArrowLeft') {
        setTime(t => clamp(t - (e.shiftKey ? 1 : 0.1), 0, duration));
      } else if (e.code === 'ArrowRight') {
        setTime(t => clamp(t + (e.shiftKey ? 1 : 0.1), 0, duration));
      } else if (e.key === '0' || e.code === 'Home') {
        setTime(0);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [duration]);
  const displayTime = hoverTime != null ? hoverTime : time;
  const ctxValue = React.useMemo(() => ({
    time: displayTime,
    duration,
    playing,
    setTime,
    setPlaying
  }), [displayTime, duration, playing]);
  return /*#__PURE__*/React.createElement("div", {
    ref: stageRef,
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      background: '#0a0a0a',
      fontFamily: 'Inter, system-ui, sans-serif'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      width: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      overflow: 'hidden',
      minHeight: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    ref: canvasRef,
    style: {
      width,
      height,
      background,
      position: 'relative',
      transform: `scale(${scale})`,
      transformOrigin: 'center',
      flexShrink: 0,
      boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement(TimelineContext.Provider, {
    value: ctxValue
  }, children))), /*#__PURE__*/React.createElement(PlaybackBar, {
    time: displayTime,
    actualTime: time,
    duration: duration,
    playing: playing,
    onPlayPause: () => setPlaying(p => !p),
    onReset: () => {
      setTime(0);
    },
    onSeek: t => setTime(t),
    onHover: t => setHoverTime(t)
  }));
}

// ── Playback bar ────────────────────────────────────────────────────────────
// Play/pause, return-to-begin, scrub track, time display.
// Uses fixed-width time fields so layout doesn't thrash.

function PlaybackBar({
  time,
  duration,
  playing,
  onPlayPause,
  onReset,
  onSeek,
  onHover
}) {
  const trackRef = React.useRef(null);
  const [dragging, setDragging] = React.useState(false);
  const timeFromEvent = React.useCallback(e => {
    const rect = trackRef.current.getBoundingClientRect();
    const x = clamp((e.clientX - rect.left) / rect.width, 0, 1);
    return x * duration;
  }, [duration]);
  const onTrackMove = e => {
    if (!trackRef.current) return;
    const t = timeFromEvent(e);
    if (dragging) {
      onSeek(t);
    } else {
      onHover(t);
    }
  };
  const onTrackLeave = () => {
    if (!dragging) onHover(null);
  };
  const onTrackDown = e => {
    setDragging(true);
    const t = timeFromEvent(e);
    onSeek(t);
    onHover(null);
  };
  React.useEffect(() => {
    if (!dragging) return;
    const onUp = () => setDragging(false);
    const onMove = e => {
      if (!trackRef.current) return;
      const t = timeFromEvent(e);
      onSeek(t);
    };
    window.addEventListener('mouseup', onUp);
    window.addEventListener('mousemove', onMove);
    return () => {
      window.removeEventListener('mouseup', onUp);
      window.removeEventListener('mousemove', onMove);
    };
  }, [dragging, timeFromEvent, onSeek]);
  const pct = duration > 0 ? time / duration * 100 : 0;
  const fmt = t => {
    const total = Math.max(0, t);
    const m = Math.floor(total / 60);
    const s = Math.floor(total % 60);
    const cs = Math.floor(total * 100 % 100);
    return `${String(m).padStart(1, '0')}:${String(s).padStart(2, '0')}.${String(cs).padStart(2, '0')}`;
  };
  const mono = 'JetBrains Mono, ui-monospace, SFMono-Regular, monospace';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      padding: '8px 16px',
      background: 'rgba(20,20,20,0.92)',
      borderTop: '1px solid rgba(255,255,255,0.08)',
      width: '100%',
      maxWidth: 680,
      alignSelf: 'center',
      borderRadius: 8,
      color: '#f6f4ef',
      fontFamily: 'Inter, system-ui, sans-serif',
      userSelect: 'none',
      flexShrink: 0
    }
  }, /*#__PURE__*/React.createElement(IconButton, {
    onClick: onReset,
    title: "Return to start (0)"
  }, /*#__PURE__*/React.createElement("svg", {
    width: "14",
    height: "14",
    viewBox: "0 0 14 14",
    fill: "none"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M3 2v10M12 2L5 7l7 5V2z",
    stroke: "currentColor",
    strokeWidth: "1.5",
    strokeLinejoin: "round",
    strokeLinecap: "round"
  }))), /*#__PURE__*/React.createElement(IconButton, {
    onClick: onPlayPause,
    title: "Play/pause (space)"
  }, playing ? /*#__PURE__*/React.createElement("svg", {
    width: "14",
    height: "14",
    viewBox: "0 0 14 14",
    fill: "none"
  }, /*#__PURE__*/React.createElement("rect", {
    x: "3",
    y: "2",
    width: "3",
    height: "10",
    fill: "currentColor"
  }), /*#__PURE__*/React.createElement("rect", {
    x: "8",
    y: "2",
    width: "3",
    height: "10",
    fill: "currentColor"
  })) : /*#__PURE__*/React.createElement("svg", {
    width: "14",
    height: "14",
    viewBox: "0 0 14 14",
    fill: "none"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M3 2l9 5-9 5V2z",
    fill: "currentColor"
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: mono,
      fontSize: 12,
      fontVariantNumeric: 'tabular-nums',
      width: 64,
      textAlign: 'right',
      color: '#f6f4ef'
    }
  }, fmt(time)), /*#__PURE__*/React.createElement("div", {
    ref: trackRef,
    onMouseMove: onTrackMove,
    onMouseLeave: onTrackLeave,
    onMouseDown: onTrackDown,
    style: {
      flex: 1,
      height: 22,
      position: 'relative',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      right: 0,
      height: 4,
      background: 'rgba(255,255,255,0.12)',
      borderRadius: 2
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      width: `${pct}%`,
      height: 4,
      background: 'oklch(72% 0.12 250)',
      borderRadius: 2
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: `${pct}%`,
      top: '50%',
      width: 12,
      height: 12,
      marginLeft: -6,
      marginTop: -6,
      background: '#fff',
      borderRadius: 6,
      boxShadow: '0 2px 4px rgba(0,0,0,0.4)'
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: mono,
      fontSize: 12,
      fontVariantNumeric: 'tabular-nums',
      width: 64,
      textAlign: 'left',
      color: 'rgba(246,244,239,0.55)'
    }
  }, fmt(duration)));
}
function IconButton({
  children,
  onClick,
  title
}) {
  const [hover, setHover] = React.useState(false);
  return /*#__PURE__*/React.createElement("button", {
    onClick: onClick,
    title: title,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      width: 28,
      height: 28,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: hover ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.04)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 6,
      color: '#f6f4ef',
      cursor: 'pointer',
      padding: 0,
      transition: 'background 120ms'
    }
  }, children);
}
Object.assign(window, {
  Easing,
  interpolate,
  animate,
  clamp,
  TimelineContext,
  useTime,
  useTimeline,
  Sprite,
  SpriteContext,
  useSprite,
  TextSprite,
  ImageSprite,
  RectSprite,
  Stage,
  PlaybackBar
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "export/src/animations.jsx", error: String((e && e.message) || e) }); }

// export/src/parts.jsx
try { (() => {
/* cdr-kit explainer — shared parts. Brand tokens (light + indigo). */
const COL = {
  paper: '#fcfbf8',
  paper2: '#f6f3ee',
  paper3: '#efebe4',
  card: '#ffffff',
  ink: '#2b2724',
  ink2: '#6f6a63',
  ink3: '#948f87',
  line: '#e7e4df',
  line2: '#dcd9d2',
  primary: '#3a5adb',
  primarySoft: 'rgba(58,90,219,0.10)',
  primaryLine: 'rgba(58,90,219,0.34)',
  signal: '#1e9c66',
  signalSoft: 'rgba(30,156,102,0.12)',
  signalLine: 'rgba(30,156,102,0.40)',
  warn: '#b9852f',
  warnSoft: 'rgba(185,133,47,0.12)',
  warnLine: 'rgba(185,133,47,0.40)'
};
const FONT = {
  disp: "'Bricolage Grotesque', sans-serif",
  sans: "'Hanken Grotesk', system-ui, sans-serif",
  mono: "'JetBrains Mono', ui-monospace, monospace"
};

// scramble: resolves `target` left-to-right as p:0->1, random hex glyphs elsewhere
const GLYPHS = '0123456789abcdef?{}":,./';
function scramble(target, p) {
  const n = Math.floor(clamp(p, 0, 1) * target.length);
  let s = '';
  for (let i = 0; i < target.length; i++) {
    const ch = target[i];
    if (i < n || ch === ' ') s += ch;else s += GLYPHS[Math.random() * GLYPHS.length | 0];
  }
  return s;
}

// The Vault-Rail brand mark. `draw` (0..1) strokes it on; dotP (0..1) pops the payload dot.
function Mark({
  size = 64,
  color = COL.ink,
  dot = COL.primary,
  draw = 1,
  dotP = 1
}) {
  const railLen = 29,
    rectLen = 84;
  return /*#__PURE__*/React.createElement("svg", {
    width: size,
    height: size,
    viewBox: "0 0 32 32",
    fill: "none",
    style: {
      display: 'block'
    }
  }, /*#__PURE__*/React.createElement("line", {
    x1: "1.5",
    y1: "16",
    x2: "30.5",
    y2: "16",
    stroke: color,
    strokeWidth: "2.6",
    strokeLinecap: "round",
    strokeDasharray: railLen,
    strokeDashoffset: railLen * (1 - clamp(draw, 0, 1))
  }), /*#__PURE__*/React.createElement("rect", {
    x: "7",
    y: "7",
    width: "18",
    height: "18",
    rx: "5.2",
    stroke: color,
    strokeWidth: "2.6",
    strokeDasharray: rectLen,
    strokeDashoffset: rectLen * (1 - clamp(draw, 0, 1))
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "16",
    cy: "16",
    r: 2.8 * clamp(dotP, 0, 1),
    fill: dot
  }));
}

// Subtle hairline grid with radial fade. opacity prop fades the whole thing.
function Grid({
  opacity = 1,
  cx = '50%',
  cy = '30%'
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      opacity,
      pointerEvents: 'none',
      backgroundImage: `linear-gradient(${COL.line} 1px, transparent 1px), linear-gradient(90deg, ${COL.line} 1px, transparent 1px)`,
      backgroundSize: '48px 48px',
      WebkitMaskImage: `radial-gradient(ellipse 75% 75% at ${cx} ${cy}, #000 0%, transparent 72%)`,
      maskImage: `radial-gradient(ellipse 75% 75% at ${cx} ${cy}, #000 0%, transparent 72%)`
    }
  });
}

// Brand wordmark lockup
function Lockup({
  size = 1,
  color = COL.ink
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 14 * size
    }
  }, /*#__PURE__*/React.createElement(Mark, {
    size: 42 * size,
    color: color
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontWeight: 700,
      fontSize: 34 * size,
      letterSpacing: '-0.04em',
      color,
      whiteSpace: 'nowrap'
    }
  }, "cdr", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "-"), "kit"));
}

// Window-chrome card (the vault card shell)
function WinCard({
  x,
  y,
  w,
  title,
  children,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x,
      top: y,
      width: w,
      background: COL.card,
      border: `1px solid ${COL.line}`,
      borderRadius: 16,
      boxShadow: '0 18px 50px -20px rgba(43,39,36,0.28)',
      overflow: 'hidden',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '11px 16px',
      borderBottom: `1px solid ${COL.line}`,
      background: COL.paper2
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'flex',
      gap: 6
    }
  }, [0, 1, 2].map(i => /*#__PURE__*/React.createElement("i", {
    key: i,
    style: {
      width: 10,
      height: 10,
      borderRadius: '50%',
      background: COL.line2,
      display: 'block'
    }
  }))), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 13,
      color: COL.ink3
    }
  }, title)), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '18px 20px'
    }
  }, children));
}
function Pill({
  tone = 'primary',
  children,
  style
}) {
  const map = {
    primary: [COL.primary, COL.primarySoft, COL.primaryLine],
    signal: [COL.signal, COL.signalSoft, COL.signalLine],
    warn: [COL.warn, COL.warnSoft, COL.warnLine]
  };
  const [c, bg, bd] = map[tone];
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 7,
      fontFamily: FONT.mono,
      fontSize: 13,
      color: c,
      background: bg,
      border: `1px solid ${bd}`,
      borderRadius: 999,
      padding: '5px 12px',
      whiteSpace: 'nowrap',
      ...style
    }
  }, children);
}

// lock glyph (open/closed) for status
function Lock({
  open,
  color,
  size = 15
}) {
  return /*#__PURE__*/React.createElement("svg", {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: color,
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("rect", {
    x: "5",
    y: "11",
    width: "14",
    height: "10",
    rx: "2"
  }), open ? /*#__PURE__*/React.createElement("path", {
    d: "M8 11V7a4 4 0 0 1 8 0"
  }) : /*#__PURE__*/React.createElement("path", {
    d: "M8 11V7a4 4 0 0 1 8 0v4"
  }));
}
Object.assign(window, {
  COL,
  FONT,
  scramble,
  Mark,
  Grid,
  Lockup,
  WinCard,
  Pill,
  Lock
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "export/src/parts.jsx", error: String((e && e.message) || e) }); }

// export/src/scenes.jsx
try { (() => {
/* cdr-kit explainer — scenes. Each reads useSprite() for scene-local time. */
const {
  useSprite: uS
} = window;
const A = o => animate(o);
const typed = (str, p) => str.slice(0, Math.max(0, Math.floor(clamp(p, 0, 1) * str.length)));
const CIPHER = '7b 22 73 69 67 9f a3 2e c1 04 7d e8 11 b6 6a 0c 3f d1';
const PLAIN1 = '{ "signal": "BUY",';
const PLAIN2 = '  "pair": "ETH/USD", "confidence": 0.86 }';
const CIPHER2 = 'a1 9c 04 e8 7d 22 6e 61 6c b6 2e c1 ?? 9f 11 0c 6a d1 3f';
function fade(lt, inEnd, outStart, outEnd) {
  if (lt < inEnd) return clamp(lt / inEnd, 0, 1);
  if (outStart != null && lt > outStart) return 1 - clamp((lt - outStart) / (outEnd - outStart), 0, 1);
  return 1;
}

// ── S1 · Hook ────────────────────────────────────────────────────────────
function SceneHook() {
  const {
    localTime: lt
  } = uS();
  const draw = A({
    from: 0,
    to: 1,
    start: 0.5,
    end: 2.0,
    ease: Easing.easeInOutCubic
  })(lt);
  const dotP = A({
    from: 0,
    to: 1,
    start: 2.0,
    end: 2.4,
    ease: Easing.easeOutBack
  })(lt);
  const drift = A({
    from: 1,
    to: 1.05,
    start: 0,
    end: 5,
    ease: Easing.linear
  })(lt);
  const gridO = A({
    from: 0,
    to: 1,
    start: 0,
    end: 1,
    ease: Easing.easeOutQuad
  })(lt);
  const wordO = fade(lt, 0.5, 4.4, 5);
  const wordIn = A({
    from: 0,
    to: 1,
    start: 1.7,
    end: 2.3,
    ease: Easing.easeOutCubic
  })(lt);
  const tagIn = A({
    from: 0,
    to: 1,
    start: 2.7,
    end: 3.3,
    ease: Easing.easeOutCubic
  })(lt);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: gridO * 0.85,
    cx: "50%",
    cy: "42%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      transform: `scale(${drift})`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 18,
      opacity: fade(lt, 0.4, 4.4, 5)
    }
  }, /*#__PURE__*/React.createElement(Mark, {
    size: 86,
    draw: draw,
    dotP: dotP
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontWeight: 700,
      fontSize: 72,
      letterSpacing: '-0.05em',
      color: COL.ink,
      whiteSpace: 'nowrap',
      opacity: wordIn,
      transform: `translateX(${(1 - wordIn) * -12}px)`
    }
  }, "cdr", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "-"), "kit")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 26,
      fontFamily: FONT.disp,
      fontWeight: 700,
      fontSize: 30,
      letterSpacing: '-0.02em',
      color: COL.ink2,
      textAlign: 'center',
      opacity: tagIn,
      transform: `translateY(${(1 - tagIn) * 10}px)`
    }
  }, "Confidential Data Rails, ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink
    }
  }, "made shippable."))));
}

// ── S2 · The primitive (encrypt) ─────────────────────────────────────────
function ScenePrimitive() {
  const {
    localTime: lt
  } = uS();
  const encP = A({
    from: 0,
    to: 1,
    start: 1.3,
    end: 3.2,
    ease: Easing.easeInOutQuad
  })(lt);
  // encrypt = reverse-resolve: at p=0 plaintext, p=1 cipher. scramble cipher with (1-?) trick:
  const l1 = lt < 1.3 ? PLAIN1 : scramble(CIPHER, encP);
  const l2 = lt < 1.3 ? PLAIN2 : scramble(CIPHER2, encP);
  const sealP = A({
    from: 0,
    to: 1,
    start: 3.1,
    end: 4.3,
    ease: Easing.easeInOutCubic
  })(lt);
  const zoom = A({
    from: 1,
    to: 1.06,
    start: 0,
    end: 6,
    ease: Easing.linear
  })(lt);
  const sealLen = 320;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.5,
    cx: "50%",
    cy: "34%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 96,
      left: 0,
      right: 0,
      textAlign: 'center',
      opacity: fade(lt, 0.5, 5.2, 6)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      letterSpacing: '0.16em',
      color: COL.ink3
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "\u259A"), "\xA0\xA0THE PRIMITIVE"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 800,
      fontSize: 46,
      letterSpacing: '-0.03em',
      color: COL.ink,
      marginTop: 14
    }
  }, "Write ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "encrypted"), " data on-chain.")), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 300,
      left: '50%',
      transform: `translateX(-50%) scale(${zoom})`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      width: 560
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: COL.card,
      border: `1px solid ${COL.line}`,
      borderRadius: 12,
      padding: '24px 26px',
      fontFamily: FONT.mono,
      fontSize: 19,
      lineHeight: 1.7,
      color: COL.ink,
      boxShadow: '0 18px 50px -22px rgba(43,39,36,0.3)',
      wordBreak: 'break-all'
    }
  }, /*#__PURE__*/React.createElement("div", null, l1), /*#__PURE__*/React.createElement("div", {
    style: {
      color: lt < 1.3 ? COL.ink : COL.ink2
    }
  }, l2)), /*#__PURE__*/React.createElement("svg", {
    width: "560",
    height: "150",
    viewBox: "0 0 560 150",
    style: {
      position: 'absolute',
      inset: 0,
      pointerEvents: 'none',
      overflow: 'visible'
    }
  }, /*#__PURE__*/React.createElement("rect", {
    x: "2",
    y: "2",
    width: "556",
    height: "146",
    rx: "12",
    fill: "none",
    stroke: COL.primary,
    strokeWidth: "2.5",
    strokeDasharray: sealLen,
    strokeDashoffset: sealLen * 2 * (1 - sealP),
    opacity: sealP > 0 ? 0.9 : 0
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 22,
      textAlign: 'center',
      fontFamily: FONT.sans,
      fontSize: 18,
      color: COL.ink2,
      opacity: A({
        from: 0,
        to: 1,
        start: 3.6,
        end: 4.4,
        ease: Easing.easeOutCubic
      })(lt)
    }
  }, "Sealed in a vault \u2014 readable only if you satisfy a ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink,
      fontFamily: FONT.mono,
      fontSize: 16
    }
  }, "condition"), ".")));
}

// ── S3 · The gate (money shot: decrypt) ──────────────────────────────────
function SceneGate() {
  const {
    localTime: lt
  } = uS();
  const locked = lt < 3.4;
  const decP = A({
    from: 0,
    to: 1,
    start: 3.6,
    end: 5.4,
    ease: Easing.easeInOutQuad
  })(lt);
  const pay = lt >= 2.0 && lt < 3.6;
  const cardZoom = A({
    from: 0.94,
    to: 1.04,
    start: 0,
    end: 7,
    ease: Easing.easeOutCubic
  })(lt);
  const payRow = A({
    from: 0,
    to: 1,
    start: 1.8,
    end: 2.4,
    ease: Easing.easeOutBack
  })(lt);
  const statusOpen = lt >= 3.4;
  // payload lines
  let p1, p2, pcol;
  if (lt < 3.6) {
    p1 = CIPHER;
    p2 = CIPHER2;
    pcol = COL.ink3;
  } else {
    p1 = scramble(PLAIN1, decP);
    p2 = scramble(PLAIN2, decP);
    pcol = decP > 0.98 ? COL.signal : COL.ink;
  }
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper2
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.4,
    cx: "50%",
    cy: "50%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 54,
      left: 0,
      right: 0,
      textAlign: 'center',
      opacity: fade(lt, 0.5, 6.2, 7)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 800,
      fontSize: 38,
      letterSpacing: '-0.03em',
      color: COL.ink
    }
  }, "Satisfy the condition \u2192 ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.signal
    }
  }, "it decrypts."))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 150,
      left: '50%',
      transform: `translateX(-50%) scale(${cardZoom})`,
      transformOrigin: 'top center'
    }
  }, /*#__PURE__*/React.createElement(WinCard, {
    x: 0,
    y: 0,
    w: 520,
    title: "<VaultGate uuid={4200} />",
    style: {
      position: 'relative'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 11,
      paddingBottom: 14,
      borderBottom: `1px solid ${COL.line}`,
      marginBottom: 14
    }
  }, [['vault.uuid', '4200', COL.ink], ['read.condition', 'Subscription', COL.primary], ['price.period', '5 $IP / 30d', COL.ink]].map(([k, v, c]) => /*#__PURE__*/React.createElement("div", {
    key: k,
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      fontFamily: FONT.mono,
      fontSize: 15,
      whiteSpace: 'nowrap'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink3,
      fontSize: 13
    }
  }, k), /*#__PURE__*/React.createElement("span", {
    style: {
      color: c
    }
  }, v)))), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 15.5,
      lineHeight: 1.7,
      background: COL.paper2,
      border: `1px solid ${COL.line}`,
      borderRadius: 8,
      padding: '14px 16px',
      minHeight: 76,
      color: pcol,
      wordBreak: 'break-all',
      transition: 'color .3s'
    }
  }, /*#__PURE__*/React.createElement("div", null, p1), /*#__PURE__*/React.createElement("div", null, p2)), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginTop: 14
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      fontFamily: FONT.mono,
      fontSize: 14,
      color: statusOpen ? COL.signal : COL.warn
    }
  }, /*#__PURE__*/React.createElement(Lock, {
    open: statusOpen,
    color: statusOpen ? COL.signal : COL.warn
  }), statusOpen ? 'condition satisfied · decrypted' : 'condition not met'), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 13,
      color: COL.ink3
    }
  }, "~15s read"))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: -38,
      top: 330,
      opacity: payRow,
      transform: `translateY(${(1 - payRow) * 14}px)`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      background: COL.card,
      border: `1px solid ${COL.line2}`,
      borderRadius: 12,
      padding: '10px 14px',
      boxShadow: '0 14px 36px -16px rgba(43,39,36,0.3)',
      whiteSpace: 'nowrap'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 9,
      height: 9,
      borderRadius: '50%',
      background: pay ? COL.warn : COL.signal,
      transition: 'background .3s'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 13.5,
      color: COL.ink
    }
  }, "agent 0x9f\u2026a3c1"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 13.5,
      color: statusOpen ? COL.signal : COL.primary
    }
  }, statusOpen ? '✓ paid 5 $IP' : 'subscribe()')))));
}

// ── S4 · One install ─────────────────────────────────────────────────────
function SceneInstall() {
  const {
    localTime: lt
  } = uS();
  const cmd = typed('npm create cdr-kit', A({
    from: 0,
    to: 1,
    start: 0.6,
    end: 1.7,
    ease: Easing.linear
  })(lt));
  const codeO = A({
    from: 0,
    to: 1,
    start: 2.0,
    end: 2.7,
    ease: Easing.easeOutCubic
  })(lt);
  const layers = [['Layer 3', 'Framework adapters · MCP · CLI'], ['Layer 2', 'TypeScript SDK · React · agent'], ['Layer 1', '9 Solidity conditions · vault']];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.45,
    cx: "28%",
    cy: "30%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 88,
      left: 96,
      opacity: fade(lt, 0.5, 4.4, 5)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      letterSpacing: '0.16em',
      color: COL.ink3
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "\u259A"), "\xA0\xA0ONE INSTALL"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 800,
      fontSize: 44,
      letterSpacing: '-0.03em',
      color: COL.ink,
      marginTop: 14,
      maxWidth: 480,
      lineHeight: 1.05
    }
  }, "One package.", /*#__PURE__*/React.createElement("br", null), "Real on-chain checks."), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 18,
      fontFamily: FONT.sans,
      fontSize: 17,
      color: COL.ink2,
      maxWidth: 430
    }
  }, "Gate any data behind a payment or license \u2014 in under a minute.")), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 150,
      left: 640,
      width: 540
    }
  }, /*#__PURE__*/React.createElement(WinCard, {
    x: 0,
    y: 0,
    w: 540,
    title: "terminal"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 17,
      color: COL.ink
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "$"), " ", cmd, /*#__PURE__*/React.createElement("span", {
    style: {
      opacity: lt % 1 < 0.5 ? 1 : 0,
      color: COL.ink3
    }
  }, "\u258B")), /*#__PURE__*/React.createElement("div", {
    style: {
      opacity: codeO,
      marginTop: 16,
      paddingTop: 16,
      borderTop: `1px solid ${COL.line}`,
      fontFamily: FONT.mono,
      fontSize: 15.5,
      lineHeight: 1.7
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "import"), " ", '{ VaultGate }', " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "from"), " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.signal
    }
  }, "\"@cdr-kit/react\""), ";"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 8
    }
  }, '<', /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#b5532f'
    }
  }, "VaultGate"), " uuid=", '{', /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.warn
    }
  }, "4200"), '}', " auto", '>'), /*#__PURE__*/React.createElement("div", null, '  {(data) => <pre>{decode(data)}</pre>}'), /*#__PURE__*/React.createElement("div", null, '</', /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#b5532f'
    }
  }, "VaultGate"), '>'))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 10,
      marginTop: 18,
      opacity: A({
        from: 0,
        to: 1,
        start: 3.0,
        end: 3.7,
        ease: Easing.easeOutCubic
      })(lt)
    }
  }, layers.map(([a, b], i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      flex: 1,
      background: COL.card,
      border: `1px solid ${COL.line}`,
      borderRadius: 10,
      padding: '11px 13px',
      transform: `translateY(${(1 - A({
        from: 0,
        to: 1,
        start: 3.0 + i * 0.12,
        end: 3.7 + i * 0.12,
        ease: Easing.easeOutBack
      })(lt)) * 12}px)`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 11.5,
      color: COL.primary,
      fontWeight: 700
    }
  }, a), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.sans,
      fontSize: 12.5,
      color: COL.ink2,
      marginTop: 4
    }
  }, b))))));
}

// ── S5 · The agent ───────────────────────────────────────────────────────
function SceneAgent() {
  const {
    localTime: lt
  } = uS();
  const lines = [['$ ', 'agent run --intent "trading signal"', COL.ink, 0.4], ['⚙ ', 'discover → matched vault 4200', COL.primary, 1.1], ['⚙ ', 'subscribe & access → paid 5 $IP', COL.primary, 1.8], ['✓ ', 'threshold met · decrypted locally', COL.signal, 2.5], ['→ ', 'decide: BUY ETH/USD (0.86)', COL.ink, 3.1]];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.4,
    cx: "70%",
    cy: "32%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 92,
      left: 0,
      right: 0,
      textAlign: 'center',
      opacity: fade(lt, 0.5, 3.6, 4)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 800,
      fontSize: 42,
      letterSpacing: '-0.03em',
      color: COL.ink
    }
  }, "An agent that buys its ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "own data.")), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.sans,
      fontSize: 18,
      color: COL.ink2,
      marginTop: 10
    }
  }, "Discover \u2192 pay \u2192 decrypt \u2192 decide. No human in the loop.")), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 226,
      left: '50%',
      transform: 'translateX(-50%)',
      width: 620
    }
  }, /*#__PURE__*/React.createElement(WinCard, {
    x: 0,
    y: 0,
    w: 620,
    title: "cdr-kit-example \xB7 vercel-ai"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 16,
      lineHeight: 1.85,
      minHeight: 170
    }
  }, lines.map(([pre, txt, col, t], i) => {
    const o = A({
      from: 0,
      to: 1,
      start: t,
      end: t + 0.35,
      ease: Easing.easeOutCubic
    })(lt);
    const shown = typed(txt, A({
      from: 0,
      to: 1,
      start: t,
      end: t + 0.5,
      ease: Easing.linear
    })(lt));
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        opacity: o,
        color: col
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        color: pre === '✓ ' ? COL.signal : pre === '→ ' ? COL.primary : COL.ink3
      }
    }, pre), shown);
  })))));
}

// ── S6 · Outro ───────────────────────────────────────────────────────────
function SceneOutro() {
  const {
    localTime: lt
  } = uS();
  const inP = A({
    from: 0,
    to: 1,
    start: 0.2,
    end: 1.0,
    ease: Easing.easeOutBack
  })(lt);
  const sub = A({
    from: 0,
    to: 1,
    start: 0.9,
    end: 1.6,
    ease: Easing.easeOutCubic
  })(lt);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.7,
    cx: "50%",
    cy: "48%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      transform: `scale(${0.9 + 0.1 * inP})`,
      opacity: inP
    }
  }, /*#__PURE__*/React.createElement(Lockup, {
    size: 1.5
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 28,
      fontFamily: FONT.mono,
      fontSize: 16,
      color: COL.ink2,
      opacity: sub,
      letterSpacing: '0.01em',
      whiteSpace: 'nowrap'
    }
  }, "15 packages \xB7 9 conditions \xB7 34 tools \xB7 17 hooks \xB7 ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink
    }
  }, "MIT")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 20,
      display: 'flex',
      alignItems: 'center',
      gap: 14,
      opacity: sub
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 22,
      fontWeight: 700,
      color: COL.primary
    }
  }, "cdrkit.xyz"), /*#__PURE__*/React.createElement(Pill, {
    tone: "signal"
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 7,
      height: 7,
      borderRadius: '50%',
      background: COL.signal,
      display: 'inline-block'
    }
  }), "Live on Aeneid"))));
}
Object.assign(window, {
  SceneHook,
  ScenePrimitive,
  SceneGate,
  SceneInstall,
  SceneAgent,
  SceneOutro
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "export/src/scenes.jsx", error: String((e && e.message) || e) }); }

// export/src/scenes2.jsx
try { (() => {
/* cdr-kit explainer — additional scenes (breadth): React surface, conditions,
   agents-everywhere, Story IP. Loaded after parts.jsx + scenes.jsx. */
const {
  useSprite: uS2
} = window;
const A2 = o => animate(o);
const typed2 = (str, p) => str.slice(0, Math.max(0, Math.floor(clamp(p, 0, 1) * str.length)));
function fade2(lt, inEnd, outStart, outEnd) {
  if (lt < inEnd) return clamp(lt / inEnd, 0, 1);
  if (outStart != null && lt > outStart) return 1 - clamp((lt - outStart) / (outEnd - outStart), 0, 1);
  return 1;
}
function Chip2({
  children,
  tone,
  style
}) {
  const key = tone === 'primary';
  return /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      color: key ? COL.primary : COL.ink2,
      background: key ? COL.primarySoft : COL.paper2,
      border: `1px solid ${key ? COL.primaryLine : COL.line}`,
      borderRadius: 8,
      padding: '7px 12px',
      whiteSpace: 'nowrap',
      display: 'inline-block',
      ...style
    }
  }, children);
}
function SceneHead({
  lt,
  kick,
  title,
  accent,
  dur
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 62,
      left: 0,
      right: 0,
      textAlign: 'center',
      opacity: fade2(lt, 0.5, dur - 0.8, dur)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 13.5,
      letterSpacing: '0.16em',
      color: COL.ink3
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "\u259A"), "\xA0\xA0", kick), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 800,
      fontSize: 42,
      letterSpacing: '-0.03em',
      color: COL.ink,
      marginTop: 13
    }
  }, title, " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, accent)));
}

// ── React surface ────────────────────────────────────────────────────────
function SceneReact() {
  const {
    localTime: lt
  } = uS2();
  const comps = ['<VaultGate>', '<SubscribeButton>', '<UnlockablePill>', '<VaultCard>', '<HeartbeatTimer>', '<TimeWindowBadge>', '<MultiSigSigner>', '<EscrowDeliveryConfirm>', '<ConditionBadge>', '<IpPrice>'];
  const hooks = ['useAccessVault()', 'useSubscribeAndAccess()', 'useDeadManTimer()', 'useMultiSigStatus()', 'useEscrowState()', 'usePublish()'];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.4,
    cx: "50%",
    cy: "28%"
  }), /*#__PURE__*/React.createElement(SceneHead, {
    lt: lt,
    kick: "REACT LAYER",
    title: "Drop it into",
    accent: "your UI.",
    dur: 6
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 168,
      left: 96,
      width: 660
    }
  }, /*#__PURE__*/React.createElement(WinCard, {
    x: 0,
    y: 0,
    w: 660,
    title: "@cdr-kit/react \xB7 components"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: 10
    }
  }, comps.map((c, i) => {
    const p = A2({
      from: 0,
      to: 1,
      start: 0.3 + i * 0.12,
      end: 0.8 + i * 0.12,
      ease: Easing.easeOutBack
    })(lt);
    return /*#__PURE__*/React.createElement("span", {
      key: c,
      style: {
        opacity: p,
        transform: `translateY(${(1 - p) * 10}px)`
      }
    }, /*#__PURE__*/React.createElement(Chip2, {
      tone: i === 0 ? 'primary' : undefined
    }, c));
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 14,
      paddingTop: 13,
      borderTop: `1px solid ${COL.line}`,
      fontFamily: FONT.sans,
      fontSize: 13.5,
      color: COL.ink3,
      opacity: A2({
        from: 0,
        to: 1,
        start: 1.8,
        end: 2.4
      })(lt)
    }
  }, "headless ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink2
    }
  }, "@cdr-kit/react"), " \xB7 styled ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink2
    }
  }, "@cdr-kit/react-ui"), " \xB7 mock mode, no wallet needed"))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 168,
      left: 792,
      width: 392
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: COL.card,
      border: `1px solid ${COL.line}`,
      borderRadius: 14,
      padding: '16px 18px',
      boxShadow: '0 14px 40px -22px rgba(43,39,36,0.25)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 12,
      letterSpacing: '0.1em',
      color: COL.ink3,
      marginBottom: 10
    }
  }, "17 HOOKS"), hooks.map((h, i) => /*#__PURE__*/React.createElement("div", {
    key: h,
    style: {
      fontFamily: FONT.mono,
      fontSize: 14.5,
      color: COL.ink,
      marginBottom: 7,
      opacity: A2({
        from: 0,
        to: 1,
        start: 1.0 + i * 0.14,
        end: 1.5 + i * 0.14
      })(lt)
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "\u203A"), " ", h))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 14,
      background: COL.primarySoft,
      border: `1px solid ${COL.primaryLine}`,
      borderRadius: 14,
      padding: '14px 18px',
      opacity: A2({
        from: 0,
        to: 1,
        start: 2.6,
        end: 3.3
      })(lt)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      color: COL.primary,
      fontWeight: 700
    }
  }, "@cdr-kit/forms"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.sans,
      fontSize: 13.5,
      color: COL.ink2,
      marginTop: 4
    }
  }, "Encrypted, on-chain forms & surveys \u2014 the Confide pattern."))));
}

// ── Condition library ──────────────────────────────────────────────────────
function SceneConditions() {
  const {
    localTime: lt
  } = uS2();
  const conds = [['Subscription', 'recurring paid access'], ['TierGate', 'Story license tier'], ['Composable', 'AND / OR, 8 deep'], ['Open', 'public fallback'], ['CreatorWrite', 'gate writes'], ['TimeWindow', '[start, end] window'], ['DeadManSwitch', 'poke() or unlock'], ['ConditionalEscrow', 'pay → confirm → read'], ['MultiSig', 'N-of-M · dual-path'], ['CdrKitVault', 'factory · one tx']];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper2
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.35,
    cx: "50%",
    cy: "30%"
  }), /*#__PURE__*/React.createElement(SceneHead, {
    lt: lt,
    kick: "CONDITION STANDARD LIBRARY",
    title: "Nine conditions \u2014",
    accent: "deployed & tested.",
    dur: 5
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 180,
      left: '50%',
      transform: 'translateX(-50%)',
      width: 980,
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: 12
    }
  }, conds.map((c, i) => {
    const factory = c[0] === 'CdrKitVault';
    const p = A2({
      from: 0,
      to: 1,
      start: 0.4 + i * 0.11,
      end: 0.95 + i * 0.11,
      ease: Easing.easeOutBack
    })(lt);
    return /*#__PURE__*/React.createElement("div", {
      key: c[0],
      style: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 14,
        background: factory ? COL.primarySoft : COL.card,
        border: `1px solid ${factory ? COL.primaryLine : COL.line}`,
        borderRadius: 11,
        padding: '13px 18px',
        opacity: p,
        transform: `translateY(${(1 - p) * 12}px)`,
        boxShadow: '0 6px 18px -12px rgba(43,39,36,0.2)'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: FONT.mono,
        fontSize: 16,
        fontWeight: 500,
        color: factory ? COL.primary : COL.ink
      }
    }, c[0]), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: FONT.sans,
        fontSize: 13.5,
        color: COL.ink2
      }
    }, c[1]));
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      bottom: 54,
      left: 0,
      right: 0,
      textAlign: 'center',
      fontFamily: FONT.mono,
      fontSize: 14,
      color: COL.ink3,
      opacity: A2({
        from: 0,
        to: 1,
        start: 2.0,
        end: 2.8
      })(lt)
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink2
    }
  }, "checkReadCondition(uuid, \u2026)"), " \u2014 a view fn the validators call \xB7 ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.signal
    }
  }, "\u25CF live on Aeneid \xB7 1315")));
}

// ── Agents everywhere ──────────────────────────────────────────────────────
function SceneEverywhere() {
  const {
    localTime: lt
  } = uS2();
  const lines = [['⚙ ', 'discover → matched vault 4200', COL.primary, 0.5], ['⚙ ', 'subscribe_and_access → paid 5 $IP', COL.primary, 1.2], ['✓ ', 'decrypted locally · BUY ETH/USD', COL.signal, 1.9]];
  const hosts = ['Claude Desktop', 'Cursor', 'Windsurf', 'OpenClaw'];
  const adapters = ['vercel-ai', 'openai', 'langchain', 'agentkit', 'goat'];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.4,
    cx: "50%",
    cy: "26%"
  }), /*#__PURE__*/React.createElement(SceneHead, {
    lt: lt,
    kick: "AGENT KIT \xB7 MCP \xB7 CLI",
    title: "An agent buys data \u2014",
    accent: "from any host.",
    dur: 6.5
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 176,
      left: 96,
      width: 560
    }
  }, /*#__PURE__*/React.createElement(WinCard, {
    x: 0,
    y: 0,
    w: 560,
    title: "cdr-kit-example \xB7 vercel-ai"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 15.5,
      lineHeight: 1.85,
      minHeight: 108
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      color: COL.ink3
    }
  }, "$ agent run --intent \"trading signal\""), lines.map(([pre, txt, col, t], i) => {
    const o = A2({
      from: 0,
      to: 1,
      start: t,
      end: t + 0.3
    })(lt);
    const shown = typed2(txt, A2({
      from: 0,
      to: 1,
      start: t,
      end: t + 0.5
    })(lt));
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        opacity: o,
        color: col
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        color: pre === '✓ ' ? COL.signal : COL.ink3
      }
    }, pre), shown);
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 8,
      fontFamily: FONT.mono,
      fontSize: 13,
      color: COL.ink3,
      opacity: A2({
        from: 0,
        to: 1,
        start: 2.6,
        end: 3.2
      })(lt)
    }
  }, "the LLM never sees the private key"))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 176,
      left: 700,
      width: 484
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      opacity: A2({
        from: 0,
        to: 1,
        start: 1.0,
        end: 1.6
      })(lt),
      marginBottom: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 12,
      letterSpacing: '0.1em',
      color: COL.ink3,
      marginBottom: 9
    }
  }, "MCP HOSTS"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: 8
    }
  }, hosts.map((h, i) => /*#__PURE__*/React.createElement("span", {
    key: h,
    style: {
      opacity: A2({
        from: 0,
        to: 1,
        start: 1.1 + i * 0.1,
        end: 1.6 + i * 0.1
      })(lt)
    }
  }, /*#__PURE__*/React.createElement(Chip2, null, h))))), /*#__PURE__*/React.createElement("div", {
    style: {
      opacity: A2({
        from: 0,
        to: 1,
        start: 1.8,
        end: 2.4
      })(lt),
      marginBottom: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 12,
      letterSpacing: '0.1em',
      color: COL.ink3,
      marginBottom: 9
    }
  }, "5 FRAMEWORK ADAPTERS"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: 8
    }
  }, adapters.map((h, i) => /*#__PURE__*/React.createElement("span", {
    key: h,
    style: {
      opacity: A2({
        from: 0,
        to: 1,
        start: 1.9 + i * 0.09,
        end: 2.4 + i * 0.09
      })(lt)
    }
  }, /*#__PURE__*/React.createElement(Chip2, null, h))))), /*#__PURE__*/React.createElement("div", {
    style: {
      opacity: A2({
        from: 0,
        to: 1,
        start: 2.7,
        end: 3.3
      })(lt),
      display: 'flex',
      gap: 10
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      background: COL.primarySoft,
      border: `1px solid ${COL.primaryLine}`,
      borderRadius: 11,
      padding: '12px 14px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      color: COL.primary,
      fontWeight: 700
    }
  }, "34 tools"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.sans,
      fontSize: 12.5,
      color: COL.ink2,
      marginTop: 3
    }
  }, "one source of truth")), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      background: COL.card,
      border: `1px solid ${COL.line}`,
      borderRadius: 11,
      padding: '12px 14px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      color: COL.ink,
      fontWeight: 700
    }
  }, "cdr \xB7 CLI"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.sans,
      fontSize: 12.5,
      color: COL.ink2,
      marginTop: 3
    }
  }, "25 commands")))));
}

// ── Story IP one-shot ──────────────────────────────────────────────────────
function SceneStory() {
  const {
    localTime: lt
  } = uS2();
  const steps = [['register IP', 'Story SPG'], ['attach PIL', 'license terms'], ['mint license', 'token'], ['gated vault', 'encrypted + paid']];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.4,
    cx: "50%",
    cy: "30%"
  }), /*#__PURE__*/React.createElement(SceneHead, {
    lt: lt,
    kick: "@cdr-kit/story",
    title: "Gated by real",
    accent: "Story IP.",
    dur: 5
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 212,
      left: '50%',
      transform: 'translateX(-50%)',
      textAlign: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 20,
      color: COL.ink,
      opacity: A2({
        from: 0,
        to: 1,
        start: 0.3,
        end: 0.9
      })(lt)
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "await"), " agent.", /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#b5532f'
    }
  }, "publish"), "(", '{ data, pilTerms }', ")"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 0,
      marginTop: 34,
      justifyContent: 'center'
    }
  }, steps.map((s, i) => {
    const p = A2({
      from: 0,
      to: 1,
      start: 1.0 + i * 0.45,
      end: 1.55 + i * 0.45,
      ease: Easing.easeOutBack
    })(lt);
    const last = i === steps.length - 1;
    return /*#__PURE__*/React.createElement(React.Fragment, {
      key: s[0]
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        width: 184,
        background: last ? COL.primarySoft : COL.card,
        border: `1px solid ${last ? COL.primaryLine : COL.line}`,
        borderRadius: 12,
        padding: '16px 14px',
        opacity: p,
        transform: `scale(${0.85 + 0.15 * p})`,
        boxShadow: '0 10px 28px -16px rgba(43,39,36,0.25)'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: FONT.mono,
        fontSize: 15,
        fontWeight: 700,
        color: last ? COL.primary : COL.ink
      }
    }, s[0]), /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: FONT.sans,
        fontSize: 12.5,
        color: COL.ink2,
        marginTop: 4
      }
    }, s[1])), !last && /*#__PURE__*/React.createElement("div", {
      style: {
        width: 34,
        textAlign: 'center',
        color: COL.ink3,
        fontSize: 20,
        opacity: A2({
          from: 0,
          to: 1,
          start: 1.45 + i * 0.45,
          end: 1.8 + i * 0.45
        })(lt)
      }
    }, "\u2192"));
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 30,
      fontFamily: FONT.sans,
      fontSize: 17,
      color: COL.ink2,
      opacity: A2({
        from: 0,
        to: 1,
        start: 3.1,
        end: 3.7
      })(lt)
    }
  }, "One call \u2014 IP + license + encrypted vault. PIL flavors: ", /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      color: COL.ink
    }
  }, "commercialUse \xB7 commercialRemix \xB7 nonCommercial"))));
}

// ── Scaffolder / templates (blog · paywall · forms · data-marketplace · mcp · agents) ──
function SceneTemplates() {
  const {
    localTime: lt
  } = uS2();
  const tpls = [['starter', 0], ['blog', 1], ['paywall', 1], ['data-marketplace', 1], ['forms', 1], ['mcp-server', 0], ['agent-vercel-ai', 0], ['agent-openai', 0], ['agent-langchain', 0], ['agent-agentkit', 0], ['agent-goat', 0]];
  const unlock = A2({
    from: 0,
    to: 1,
    start: 2.4,
    end: 3.0,
    ease: Easing.easeOutBack
  })(lt);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper2
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.38,
    cx: "30%",
    cy: "28%"
  }), /*#__PURE__*/React.createElement(SceneHead, {
    lt: lt,
    kick: "create-cdr-kit-app",
    title: "Scaffold any",
    accent: "pattern.",
    dur: 5.5
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 172,
      left: 96,
      width: 600
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: COL.card,
      border: `1px solid ${COL.line}`,
      borderRadius: 12,
      padding: '14px 18px',
      fontFamily: FONT.mono,
      fontSize: 16,
      color: COL.ink,
      boxShadow: '0 12px 32px -20px rgba(43,39,36,0.25)',
      opacity: A2({
        from: 0,
        to: 1,
        start: 0.3,
        end: 0.9
      })(lt)
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "$"), " npm create cdr-kit my-blog ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink3
    }
  }, "--"), " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.signal
    }
  }, "--template blog")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: 9,
      marginTop: 18
    }
  }, tpls.map((t, i) => {
    const p = A2({
      from: 0,
      to: 1,
      start: 0.8 + i * 0.1,
      end: 1.3 + i * 0.1,
      ease: Easing.easeOutBack
    })(lt);
    return /*#__PURE__*/React.createElement("span", {
      key: t[0],
      style: {
        opacity: p,
        transform: `translateY(${(1 - p) * 10}px)`
      }
    }, /*#__PURE__*/React.createElement(Chip2, {
      tone: t[1] ? 'primary' : undefined
    }, t[0]));
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 18,
      fontFamily: FONT.sans,
      fontSize: 14,
      color: COL.ink3,
      opacity: A2({
        from: 0,
        to: 1,
        start: 2.4,
        end: 3.0
      })(lt)
    }
  }, "Working app in under a minute \u2014 mock CDR out of the box, one swap to go live.")), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 172,
      left: 740,
      width: 444
    }
  }, /*#__PURE__*/React.createElement(WinCard, {
    x: 0,
    y: 0,
    w: 444,
    title: "my-blog \xB7 onscroll pattern"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 700,
      fontSize: 21,
      letterSpacing: '-0.02em',
      color: COL.ink
    }
  }, "The alpha leak, Q3"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.sans,
      fontSize: 13.5,
      color: COL.ink2,
      marginTop: 8,
      lineHeight: 1.55
    }
  }, "The signal held through the quarter. Here's the full breakdown of where the flow went and why it\u2026"), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      marginTop: 12,
      borderRadius: 10,
      overflow: 'hidden',
      border: `1px solid ${COL.line}`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '16px 14px',
      filter: 'blur(3px)',
      opacity: 0.6
    }
  }, [92, 80, 86, 72].map((w, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      height: 9,
      width: `${w}%`,
      background: COL.line2,
      borderRadius: 5,
      marginBottom: 9
    }
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(180deg, rgba(252,251,248,0.2), rgba(252,251,248,0.85))'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 9,
      whiteSpace: 'nowrap',
      background: COL.primary,
      color: '#fff',
      fontFamily: FONT.mono,
      fontSize: 14,
      fontWeight: 600,
      padding: '10px 16px',
      borderRadius: 999,
      boxShadow: '0 8px 22px -8px rgba(58,90,219,0.6)',
      transform: `scale(${0.85 + 0.15 * unlock})`,
      opacity: unlock
    }
  }, /*#__PURE__*/React.createElement(Lock, {
    open: false,
    color: "#fff",
    size: 15
  }), " Unlock to read \xB7 2 $IP"))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 11,
      fontFamily: FONT.mono,
      fontSize: 11.5,
      color: COL.ink3,
      opacity: A2({
        from: 0,
        to: 1,
        start: 3.0,
        end: 3.6
      })(lt)
    }
  }, "<UnlockablePill /> \xB7 pay inline, decrypt in place"))));
}
Object.assign(window, {
  SceneReact,
  SceneConditions,
  SceneEverywhere,
  SceneStory,
  SceneTemplates
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "export/src/scenes2.jsx", error: String((e && e.message) || e) }); }

// export/src/sound.jsx
try { (() => {
// sound.jsx — procedural Web Audio score for the cdr-kit explainer (v2).
// Warm, musical bed: I–V–vi–IV progression in C, sub-bass pulse, soft kick +
// hat groove, plucked melody through a tape-echo, slow swelling pads, and
// in-key mallet cues synced to each scene. Renders only a mute toggle.
// Place <SoundTrack/> inside <Stage> so it can read the timeline.

const mtof = m => 440 * Math.pow(2, (m - 69) / 12);

// I–V–vi–IV in C major. Each chord = one bar.
// triad notes (mid octave) + bass root (low).
const PROG = [{
  name: 'C',
  bass: 36,
  triad: [48, 52, 55],
  color: [55, 60, 64]
},
// C  E  G
{
  name: 'G',
  bass: 31,
  triad: [47, 50, 55],
  color: [50, 55, 62]
},
// G  B  D
{
  name: 'Am',
  bass: 33,
  triad: [45, 48, 52],
  color: [52, 57, 60]
},
// A  C  E
{
  name: 'F',
  bass: 29,
  triad: [45, 48, 53],
  color: [53, 57, 60]
} // F  A  C
];

// Melody pattern over 16 sixteenth-steps. Values index into the chord's
// "color" notes (transposed up an octave); null = rest. Gives a gentle,
// syncopated pluck line that always sits inside the current chord.
const MEL = [0, null, 2, null, 1, null, null, 2, 0, null, 1, null, 2, null, 1, null];
const BPM = 84;
const STEP = 60 / BPM / 4; // sixteenth-note duration (s)

function buildReverbIR(ctx, seconds = 2.2, decay = 3.2) {
  const rate = ctx.sampleRate;
  const len = Math.floor(rate * seconds);
  const ir = ctx.createBuffer(2, len, rate);
  for (let ch = 0; ch < 2; ch++) {
    const d = ir.getChannelData(ch);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay);
  }
  return ir;
}
function SoundTrack() {
  const {
    time,
    playing
  } = useTimeline();
  const [enabled, setEnabled] = React.useState(true);
  const [ready, setReady] = React.useState(false);
  const ref = React.useRef({
    ctx: null,
    master: null,
    music: null,
    cue: null,
    reverb: null,
    delay: null,
    pad: [],
    schedulerId: null,
    nextNote: 0,
    step: 0,
    lastTime: 0,
    started: false
  });
  const ensureAudio = React.useCallback(() => {
    const S = ref.current;
    if (S.ctx) {
      if (S.ctx.state === 'suspended') S.ctx.resume();
      return S;
    }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    const ctx = new AC();
    const master = ctx.createGain();
    master.gain.value = enabled ? 0.85 : 0.0001;
    const limiter = ctx.createDynamicsCompressor();
    limiter.threshold.value = -8;
    limiter.knee.value = 8;
    limiter.ratio.value = 14;
    limiter.attack.value = 0.003;
    limiter.release.value = 0.25;
    master.connect(limiter);
    limiter.connect(ctx.destination);
    const reverb = ctx.createConvolver();
    reverb.buffer = buildReverbIR(ctx);
    const revGain = ctx.createGain();
    revGain.gain.value = 0.32;
    reverb.connect(revGain);
    revGain.connect(master);

    // tape-style feedback delay (for melody sparkle)
    const delay = ctx.createDelay(1.0);
    delay.delayTime.value = STEP * 3; // dotted-ish echo
    const fb = ctx.createGain();
    fb.gain.value = 0.34;
    const delayTone = ctx.createBiquadFilter();
    delayTone.type = 'lowpass';
    delayTone.frequency.value = 2200;
    const delayWet = ctx.createGain();
    delayWet.gain.value = 0.45;
    delay.connect(delayTone);
    delayTone.connect(fb);
    fb.connect(delay);
    delay.connect(delayWet);
    delayWet.connect(master);
    delayWet.connect(reverb);
    const music = ctx.createGain();
    music.gain.value = 0.0001;
    music.connect(master);
    music.connect(reverb);
    const cue = ctx.createGain();
    cue.gain.value = 0.6;
    cue.connect(master);
    cue.connect(reverb);
    Object.assign(S, {
      ctx,
      master,
      music,
      cue,
      reverb,
      delay
    });
    setReady(true);
    return S;
  }, [enabled]);
  React.useEffect(() => {
    const kick = () => ensureAudio();
    window.addEventListener('pointerdown', kick);
    window.addEventListener('keydown', kick);
    return () => {
      window.removeEventListener('pointerdown', kick);
      window.removeEventListener('keydown', kick);
    };
  }, [ensureAudio]);

  // ── voice helpers ──────────────────────────────────────────────
  const voice = React.useCallback((midi, at, dur, opt = {}) => {
    const S = ref.current;
    if (!S.ctx) return;
    const {
      type = 'triangle',
      peak = 0.1,
      cutoff = 2600,
      dest = S.music,
      send
    } = opt;
    const osc = S.ctx.createOscillator();
    osc.type = type;
    osc.frequency.value = mtof(midi);
    if (opt.detune) osc.detune.value = opt.detune;
    const lp = S.ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = cutoff;
    const g = S.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(peak, at + (opt.attack || 0.008));
    g.gain.exponentialRampToValueAtTime(0.0001, at + dur);
    osc.connect(lp);
    lp.connect(g);
    g.connect(dest);
    if (send) g.connect(send);
    osc.start(at);
    osc.stop(at + dur + 0.05);
  }, []);
  const kickHit = React.useCallback(at => {
    const S = ref.current;
    if (!S.ctx) return;
    const osc = S.ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(140, at);
    osc.frequency.exponentialRampToValueAtTime(45, at + 0.12);
    const g = S.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(0.55, at + 0.006);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 0.22);
    osc.connect(g);
    g.connect(S.master);
    osc.start(at);
    osc.stop(at + 0.28);
  }, []);
  const hatHit = React.useCallback((at, vel = 0.05) => {
    const S = ref.current;
    if (!S.ctx) return;
    const len = Math.floor(S.ctx.sampleRate * 0.04);
    const buf = S.ctx.createBuffer(1, len, S.ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len);
    const src = S.ctx.createBufferSource();
    src.buffer = buf;
    const hp = S.ctx.createBiquadFilter();
    hp.type = 'highpass';
    hp.frequency.value = 7500;
    const g = S.ctx.createGain();
    g.gain.setValueAtTime(vel, at);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 0.04);
    src.connect(hp);
    hp.connect(g);
    g.connect(S.master);
    src.start(at);
    src.stop(at + 0.06);
  }, []);

  // ── pad: swell the current chord, retrigger each bar ──
  const swellPad = React.useCallback((chord, at) => {
    const S = ref.current;
    if (!S.ctx) return;
    // fade out previous pad
    S.pad.forEach(({
      g,
      osc
    }) => {
      try {
        g.gain.cancelScheduledValues(at);
        g.gain.setValueAtTime(g.gain.value, at);
        g.gain.exponentialRampToValueAtTime(0.0001, at + 1.4);
        osc.stop(at + 1.5);
      } catch (e) {}
    });
    S.pad = chord.color.map((m, i) => {
      const osc = S.ctx.createOscillator();
      osc.type = i % 2 ? 'triangle' : 'sine';
      osc.frequency.value = mtof(m);
      osc.detune.value = (i - 1) * 5;
      const lp = S.ctx.createBiquadFilter();
      lp.type = 'lowpass';
      lp.frequency.value = 1500;
      const g = S.ctx.createGain();
      g.gain.setValueAtTime(0.0001, at);
      g.gain.exponentialRampToValueAtTime(0.045, at + 1.2); // slow swell
      osc.connect(lp);
      lp.connect(g);
      g.connect(S.music);
      osc.start(at);
      return {
        osc,
        g
      };
    });
  }, []);

  // ── scheduler ──
  React.useEffect(() => {
    const S = ref.current;
    if (!ready) return;
    if (playing) {
      if (S.ctx.state === 'suspended') S.ctx.resume();
      const now = S.ctx.currentTime;
      S.music.gain.cancelScheduledValues(now);
      S.music.gain.setValueAtTime(Math.max(0.0001, S.music.gain.value), now);
      S.music.gain.exponentialRampToValueAtTime(0.55, now + 1.0);
      if (!S.started) {
        S.nextNote = S.ctx.currentTime + 0.1;
        S.step = 0;
        S.started = true;
      }
      const tick = () => {
        const ahead = S.ctx.currentTime + 0.14;
        while (S.nextNote < ahead) {
          const at = S.nextNote;
          const s16 = S.step % 16;
          const bar = Math.floor(S.step / 16);
          const chord = PROG[bar % PROG.length];
          if (s16 === 0) swellPad(chord, at); // new chord swell
          if (s16 % 8 === 0) kickHit(at); // kick on beats 1 & 3
          if (s16 % 4 === 0) voice(chord.bass, at, 0.5,
          // sub bass on each beat
          {
            type: 'sine',
            peak: 0.22,
            cutoff: 600,
            attack: 0.012
          });
          if (s16 % 2 === 1) hatHit(at, s16 === 7 ? 0.07 : 0.04); // offbeat hats

          const mi = MEL[s16];
          if (mi != null) {
            // plucked melody (8va) w/ echo
            const note = chord.color[mi] + 12;
            voice(note, at, 0.4, {
              type: 'triangle',
              peak: 0.085,
              cutoff: 3200,
              send: S.delay
            });
          }
          S.step++;
          S.nextNote += STEP;
        }
      };
      tick();
      S.schedulerId = setInterval(tick, 25);
      return () => {
        clearInterval(S.schedulerId);
        S.schedulerId = null;
      };
    } else {
      if (S.ctx) {
        const now = S.ctx.currentTime;
        S.music.gain.cancelScheduledValues(now);
        S.music.gain.setValueAtTime(Math.max(0.0001, S.music.gain.value), now);
        S.music.gain.exponentialRampToValueAtTime(0.0001, now + 0.35);
        S.pad.forEach(({
          g,
          osc
        }) => {
          try {
            g.gain.cancelScheduledValues(now);
            g.gain.setValueAtTime(g.gain.value, now);
            g.gain.exponentialRampToValueAtTime(0.0001, now + 0.35);
            osc.stop(now + 0.4);
          } catch (e) {}
        });
        S.pad = [];
      }
      S.started = false;
    }
  }, [playing, ready, swellPad, voice, kickHit, hatHit]);

  // ── scene cues: in-key mallet motifs synced to the visuals ──
  const fireCue = React.useCallback(kind => {
    const S = ref.current;
    if (!S.ctx) return;
    const now = S.ctx.currentTime;
    const mallet = (m, off, dur = 0.7, peak = 0.5) => voice(m, now + off, dur, {
      type: 'sine',
      peak,
      cutoff: 3400,
      dest: S.cue,
      send: S.delay
    });
    if (kind === 'blip') {
      mallet(84, 0, 0.5, 0.4);
      mallet(79, 0.05, 0.55, 0.22); // soft bell, C/G
    } else if (kind === 'intro') {
      [60, 64, 67, 72, 79].forEach((m, i) => mallet(m, i * 0.085, 0.9, 0.42)); // rising Cmaj
    } else if (kind === 'sweep') {
      const len = Math.floor(S.ctx.sampleRate * 0.7);
      const buf = S.ctx.createBuffer(1, len, S.ctx.sampleRate);
      const d = buf.getChannelData(0);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (i / len);
      const src = S.ctx.createBufferSource();
      src.buffer = buf;
      const bp = S.ctx.createBiquadFilter();
      bp.type = 'bandpass';
      bp.Q.value = 1.3;
      bp.frequency.setValueAtTime(450, now);
      bp.frequency.exponentialRampToValueAtTime(4500, now + 0.6);
      const g = S.ctx.createGain();
      g.gain.setValueAtTime(0.0001, now);
      g.gain.exponentialRampToValueAtTime(0.22, now + 0.1);
      g.gain.exponentialRampToValueAtTime(0.0001, now + 0.7);
      src.connect(bp);
      bp.connect(g);
      g.connect(S.cue);
      g.connect(S.reverb);
      src.start(now);
      src.stop(now + 0.72);
      mallet(83, 0.12, 0.6, 0.3);
    } else if (kind === 'outro') {
      [48, 55, 60, 64, 67, 72].forEach((m, i) => mallet(m, i * 0.05, 2.0, 0.4)); // full Cmaj resolve
    }
  }, [voice]);
  React.useEffect(() => {
    const S = ref.current;
    const prev = S.lastTime;
    S.lastTime = time;
    if (!ready || !playing) return;
    if (time >= prev) {
      for (const c of SCENE_CUES) if (prev < c.t && time >= c.t) fireCue(c.kind);
    }
  }, [time, ready, playing, fireCue]);
  React.useEffect(() => {
    const S = ref.current;
    if (!S.ctx) return;
    const now = S.ctx.currentTime;
    S.master.gain.cancelScheduledValues(now);
    S.master.gain.setValueAtTime(Math.max(0.0001, S.master.gain.value), now);
    S.master.gain.exponentialRampToValueAtTime(enabled ? 0.85 : 0.0001, now + 0.15);
  }, [enabled]);
  const toggle = () => {
    ensureAudio();
    setEnabled(e => !e);
  };
  return /*#__PURE__*/React.createElement("button", {
    onClick: toggle,
    title: enabled ? 'Mute sound' : 'Unmute sound',
    style: {
      position: 'absolute',
      top: 16,
      right: 16,
      zIndex: 50,
      width: 40,
      height: 40,
      borderRadius: 10,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'rgba(20,20,20,0.55)',
      border: '1px solid rgba(255,255,255,0.18)',
      color: '#f6f4ef',
      cursor: 'pointer',
      backdropFilter: 'blur(6px)',
      padding: 0
    }
  }, enabled ? /*#__PURE__*/React.createElement("svg", {
    width: "20",
    height: "20",
    viewBox: "0 0 24 24",
    fill: "none"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M4 9v6h4l5 4V5L8 9H4z",
    fill: "currentColor"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M16 8.5a4 4 0 010 7M18.5 6a7.5 7.5 0 010 12",
    stroke: "currentColor",
    strokeWidth: "1.6",
    strokeLinecap: "round"
  })) : /*#__PURE__*/React.createElement("svg", {
    width: "20",
    height: "20",
    viewBox: "0 0 24 24",
    fill: "none"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M4 9v6h4l5 4V5L8 9H4z",
    fill: "currentColor"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M17 9.5l4 5M21 9.5l-4 5",
    stroke: "currentColor",
    strokeWidth: "1.6",
    strokeLinecap: "round"
  })));
}

// scene start times -> cue type
const SCENE_CUES = [{
  t: 0.05,
  kind: 'intro'
}, {
  t: 4.5,
  kind: 'blip'
}, {
  t: 9.5,
  kind: 'blip'
}, {
  t: 15.5,
  kind: 'blip'
}, {
  t: 19.5,
  kind: 'blip'
}, {
  t: 25.0,
  kind: 'blip'
}, {
  t: 30.5,
  kind: 'blip'
}, {
  t: 35.0,
  kind: 'sweep'
}, {
  t: 41.0,
  kind: 'blip'
}, {
  t: 46.0,
  kind: 'outro'
}];
Object.assign(window, {
  SoundTrack
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "export/src/sound.jsx", error: String((e && e.message) || e) }); }

// logo/concepts.jsx
try { (() => {
/* cdr-kit logo concepts — original geometric glyphs.
   Each built on the brief: "containment + something flowing through it."
   Colors come from CSS vars (--c-ink / --c-acc) set by the context wrapper,
   so one markup renders 2-tone (ink+amber), mono-white, or mono-black. */

function Glyph({
  type,
  size = 88
}) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 32 32",
    fill: "none"
  };
  const ink = "var(--c-ink)";
  const acc = "var(--c-acc)";
  if (type === "vault") {
    // Rounded-square containment with a rail passing through + amber payload node.
    return /*#__PURE__*/React.createElement("svg", common, /*#__PURE__*/React.createElement("line", {
      x1: "1.5",
      y1: "16",
      x2: "30.5",
      y2: "16",
      stroke: ink,
      strokeWidth: "2.6",
      strokeLinecap: "round"
    }), /*#__PURE__*/React.createElement("rect", {
      x: "7",
      y: "7",
      width: "18",
      height: "18",
      rx: "5.2",
      stroke: ink,
      strokeWidth: "2.6"
    }), /*#__PURE__*/React.createElement("circle", {
      cx: "16",
      cy: "16",
      r: "2.8",
      fill: acc
    }));
  }
  if (type === "rails") {
    // Two parallel data rails crossing a single condition gate (amber checkpoint).
    return /*#__PURE__*/React.createElement("svg", common, /*#__PURE__*/React.createElement("line", {
      x1: "3",
      y1: "11",
      x2: "29",
      y2: "11",
      stroke: ink,
      strokeWidth: "2.5",
      strokeLinecap: "round"
    }), /*#__PURE__*/React.createElement("line", {
      x1: "3",
      y1: "21",
      x2: "29",
      y2: "21",
      stroke: ink,
      strokeWidth: "2.5",
      strokeLinecap: "round"
    }), /*#__PURE__*/React.createElement("rect", {
      x: "14.2",
      y: "5.5",
      width: "3.6",
      height: "21",
      rx: "1.8",
      fill: acc
    }));
  }
  if (type === "key") {
    // Turned key: ring bow + shaft + amber teeth. Matches the kit's KeyRound icon language.
    return /*#__PURE__*/React.createElement("svg", common, /*#__PURE__*/React.createElement("circle", {
      cx: "9",
      cy: "16",
      r: "5.2",
      stroke: ink,
      strokeWidth: "2.6"
    }), /*#__PURE__*/React.createElement("line", {
      x1: "13.6",
      y1: "16",
      x2: "28",
      y2: "16",
      stroke: ink,
      strokeWidth: "2.6",
      strokeLinecap: "round"
    }), /*#__PURE__*/React.createElement("line", {
      x1: "23",
      y1: "16",
      x2: "23",
      y2: "21.6",
      stroke: acc,
      strokeWidth: "2.6",
      strokeLinecap: "round"
    }), /*#__PURE__*/React.createElement("line", {
      x1: "27.6",
      y1: "16",
      x2: "27.6",
      y2: "20",
      stroke: acc,
      strokeWidth: "2.6",
      strokeLinecap: "round"
    }));
  }
  if (type === "bracket") {
    // Code brackets [ ] as containment, amber payload node on the track between them.
    return /*#__PURE__*/React.createElement("svg", common, /*#__PURE__*/React.createElement("path", {
      d: "M11 7.5 H6.5 V24.5 H11",
      stroke: ink,
      strokeWidth: "2.5",
      strokeLinecap: "round",
      strokeLinejoin: "round"
    }), /*#__PURE__*/React.createElement("path", {
      d: "M21 7.5 H25.5 V24.5 H21",
      stroke: ink,
      strokeWidth: "2.5",
      strokeLinecap: "round",
      strokeLinejoin: "round"
    }), /*#__PURE__*/React.createElement("circle", {
      cx: "16",
      cy: "16",
      r: "3.2",
      fill: acc
    }));
  }
  return null;
}
function Wordmark({
  glyphType,
  size = 30,
  mono = false
}) {
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: size * 0.34
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: mono ? "ctx mono-ink" : "ctx on-light",
    style: {
      display: "inline-flex"
    }
  }, /*#__PURE__*/React.createElement(Glyph, {
    type: glyphType,
    size: size * 1.15
  })), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: "'JetBrains Mono', monospace",
      fontWeight: 700,
      fontSize: size,
      letterSpacing: "-0.03em",
      color: mono ? "#0a0a0a" : "#1d1b19"
    }
  }, "cdr", /*#__PURE__*/React.createElement("b", {
    style: {
      color: mono ? "#0a0a0a" : "#3a5adb"
    }
  }, "-"), "kit"));
}
Object.assign(window, {
  Glyph,
  Wordmark
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "logo/concepts.jsx", error: String((e && e.message) || e) }); }

// logo/design-canvas.jsx
try { (() => {
// @ds-adherence-ignore -- omelette starter scaffold (raw elements/hex/px by design)

/* BEGIN USAGE */
// DesignCanvas.jsx — Figma-ish design canvas wrapper
// Warm gray grid bg + Sections + Artboards + PostIt notes.
// Exports (to window): DesignCanvas, DCSection, DCArtboard, DCPostIt.
// Artboards are reorderable (grip-drag), deletable, labels/titles are
// inline-editable, and any artboard can be opened in a fullscreen focus
// overlay (←/→/Esc). State persists to a .design-canvas.state.json sidecar
// via the host bridge. No assets, no deps.
//
// Usage:
//   <DesignCanvas>
//     <DCSection id="onboarding" title="Onboarding" subtitle="First-run variants">
//       <DCArtboard id="a" label="A · Dusk" width={260} height={480}>…</DCArtboard>
//       <DCArtboard id="b" label="B · Minimal" width={260} height={480}>…</DCArtboard>
//     </DCSection>
//   </DesignCanvas>
//
// Artboards are static design frames, not scroll regions — never use
// height: 100% + overflow: auto/scroll on inner elements; size each artboard
// to fit its content (explicit pixel height, or let it grow).
/* END USAGE */

const DC = {
  bg: '#f0eee9',
  grid: 'rgba(0,0,0,0.06)',
  label: 'rgba(60,50,40,0.7)',
  title: 'rgba(40,30,20,0.85)',
  subtitle: 'rgba(60,50,40,0.6)',
  postitBg: '#fef4a8',
  postitText: '#5a4a2a',
  font: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif'
};

// One-time CSS injection (classes are dc-prefixed so they don't collide with
// the hosted design's own styles).
if (typeof document !== 'undefined' && !document.getElementById('dc-styles')) {
  const s = document.createElement('style');
  s.id = 'dc-styles';
  s.textContent = ['.dc-editable{cursor:text;outline:none;white-space:nowrap;border-radius:3px;padding:0 2px;margin:0 -2px}', '.dc-editable:focus{background:#fff;box-shadow:0 0 0 1.5px #c96442}', '[data-dc-slot]{transition:transform .18s cubic-bezier(.2,.7,.3,1)}', '[data-dc-slot].dc-dragging{transition:none;z-index:10;pointer-events:none}', '[data-dc-slot].dc-dragging .dc-card{box-shadow:0 12px 40px rgba(0,0,0,.25),0 0 0 2px #c96442;transform:scale(1.02)}',
  // isolation:isolate contains artboard content's z-indexes so a
  // z-indexed child (sticky navbar etc.) can't paint over .dc-header or
  // the .dc-menu popover that drops into the top of the card.
  '.dc-card{isolation:isolate;transition:box-shadow .15s,transform .15s}', '.dc-card *{scrollbar-width:none}', '.dc-card *::-webkit-scrollbar{display:none}',
  // Per-artboard header: grip + label on the left, delete/expand on the
  // right. Single flex row; when the artboard's on-screen width is too
  // narrow for both the label yields (ellipsis, then hidden entirely below
  // ~4ch via the container query) and the buttons stay on the row.
  '.dc-header{position:absolute;bottom:100%;left:-4px;margin-bottom:calc(4px * var(--dc-inv-zoom,1));z-index:2;', '  display:flex;align-items:center;container-type:inline-size}', '.dc-labelrow{display:flex;align-items:center;gap:4px;height:24px;flex:1 1 auto;min-width:0}', '.dc-grip{flex:0 0 auto;cursor:grab;display:flex;align-items:center;padding:5px 4px;border-radius:4px;transition:background .12s,opacity .12s}', '.dc-grip:hover{background:rgba(0,0,0,.08)}', '.dc-grip:active{cursor:grabbing}', '.dc-labeltext{flex:1 1 auto;min-width:0;cursor:pointer;border-radius:4px;padding:3px 6px;', '  display:flex;align-items:center;transition:background .12s;overflow:hidden}',
  // Below ~4ch of label room: hide the label entirely, and drop the grip to
  // hover-only (same reveal rule as .dc-btns) so a narrow header is clean
  // until the card is moused.
  '@container (max-width: 110px){', '  .dc-labeltext{display:none}', '  .dc-grip{opacity:0}', '  [data-dc-slot]:hover .dc-grip{opacity:1}', '}', '.dc-labeltext:hover{background:rgba(0,0,0,.05)}', '.dc-labeltext .dc-editable{overflow:hidden;text-overflow:ellipsis;max-width:100%}', '.dc-labeltext .dc-editable:focus{overflow:visible;text-overflow:clip}', '.dc-btns{flex:0 0 auto;margin-left:auto;display:flex;gap:2px;opacity:0;transition:opacity .12s}', '[data-dc-slot]:hover .dc-btns,.dc-btns:has(.dc-menu){opacity:1}', '.dc-expand,.dc-kebab{width:22px;height:22px;border-radius:5px;border:none;cursor:pointer;padding:0;', '  background:transparent;color:rgba(60,50,40,.7);display:flex;align-items:center;justify-content:center;', '  font:inherit;transition:background .12s,color .12s}', '.dc-expand:hover,.dc-kebab:hover{background:rgba(0,0,0,.06);color:#2a251f}',
  // Slot hosting an open menu floats above later siblings (which otherwise
  // paint on top — same z-index:auto, later DOM order) so the popup isn't
  // clipped by the next card.
  '[data-dc-slot]:has(.dc-menu){z-index:10}', '.dc-menu{position:absolute;top:100%;right:0;margin-top:4px;background:#fff;border-radius:8px;', '  box-shadow:0 8px 28px rgba(0,0,0,.18),0 0 0 1px rgba(0,0,0,.05);padding:4px;min-width:160px;z-index:10}', '.dc-menu button{display:block;width:100%;padding:7px 10px;border:0;background:transparent;', '  border-radius:5px;font-family:inherit;font-size:13px;font-weight:500;line-height:1.2;', '  color:#29261b;cursor:pointer;text-align:left;transition:background .12s;white-space:nowrap}', '.dc-menu button:hover{background:rgba(0,0,0,.05)}', '.dc-menu hr{border:0;border-top:1px solid rgba(0,0,0,.08);margin:4px 2px}', '.dc-menu .dc-danger{color:#c96442}', '.dc-menu .dc-danger:hover{background:rgba(201,100,66,.1)}',
  // Chrome (titles / labels / buttons) counter-scales against the viewport
  // zoom so it stays a constant on-screen size. --dc-inv-zoom is set by
  // DCViewport on every transform update and inherits to all descendants —
  // any overlay inside the world (e.g. a TweaksPanel on an artboard) can use
  // it the same way.
  //
  // The header uses transform:scale (out-of-flow, so layout impact doesn't
  // matter) with its world-space width set to card-width / inv-zoom so that
  // after counter-scaling its on-screen width exactly matches the card's —
  // that's what lets the container query + text-overflow behave against the
  // card's visible edge at every zoom level.
  //
  // The section head uses CSS zoom instead of transform so its layout box
  // grows with the counter-scale, pushing the card row down — otherwise the
  // constant-screen-size title would overflow into the (shrinking) world-
  // space gap and overlap the artboard headers at low zoom.
  '.dc-header{width:calc((100% + 4px) / var(--dc-inv-zoom,1));', '  transform:scale(var(--dc-inv-zoom,1));transform-origin:bottom left}', '.dc-sectionhead{zoom:var(--dc-inv-zoom,1)}'].join('\n');
  document.head.appendChild(s);
}
const DCCtx = React.createContext(null);

// Recursively unwrap React.Fragment so <>…</> grouping doesn't hide
// DCSection/DCArtboard children from the type-based walks below.
function dcFlatten(children) {
  const out = [];
  React.Children.forEach(children, c => {
    if (c && c.type === React.Fragment) out.push(...dcFlatten(c.props.children));else out.push(c);
  });
  return out;
}

// ─────────────────────────────────────────────────────────────
// DesignCanvas — stateful wrapper around the pan/zoom viewport.
// Owns runtime state (per-section order, renamed titles/labels, hidden
// artboards, focused artboard). Order/titles/labels/hidden persist to a
// .design-canvas.state.json
// sidecar next to the HTML. Reads go via plain fetch() so the saved
// arrangement is visible anywhere the HTML + sidecar are served together
// (omelette preview, direct link, downloaded zip). Writes go through the
// host's window.omelette bridge — editing requires the omelette runtime.
// Focus is ephemeral.
// ─────────────────────────────────────────────────────────────
const DC_STATE_FILE = '.design-canvas.state.json';
function DesignCanvas({
  children,
  minScale,
  maxScale,
  style
}) {
  const [state, setState] = React.useState({
    sections: {},
    focus: null
  });
  // Hold rendering until the sidecar read settles so the saved order/titles
  // appear on first paint (no source-order flash). didRead gates writes until
  // the read settles so the empty initial state can't clobber a slow read;
  // skipNextWrite suppresses the one echo-write that would otherwise follow
  // hydration.
  const [ready, setReady] = React.useState(false);
  const didRead = React.useRef(false);
  const skipNextWrite = React.useRef(false);
  React.useEffect(() => {
    let off = false;
    fetch('./' + DC_STATE_FILE).then(r => r.ok ? r.json() : null).then(saved => {
      if (off || !saved || !saved.sections) return;
      skipNextWrite.current = true;
      setState(s => ({
        ...s,
        sections: saved.sections
      }));
    }).catch(() => {}).finally(() => {
      didRead.current = true;
      if (!off) setReady(true);
    });
    const t = setTimeout(() => {
      if (!off) setReady(true);
    }, 150);
    return () => {
      off = true;
      clearTimeout(t);
    };
  }, []);
  React.useEffect(() => {
    if (!didRead.current) return;
    if (skipNextWrite.current) {
      skipNextWrite.current = false;
      return;
    }
    const t = setTimeout(() => {
      window.omelette?.writeFile(DC_STATE_FILE, JSON.stringify({
        sections: state.sections
      })).catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [state.sections]);

  // Build registries synchronously from children so FocusOverlay can read
  // them in the same render. Fragments are flattened; wrapping in other
  // elements still opts out of focus/reorder.
  const registry = {}; // slotId -> { sectionId, artboard }
  const sectionMeta = {}; // sectionId -> { title, subtitle, slotIds[] }
  const sectionOrder = [];
  dcFlatten(children).forEach(sec => {
    if (!sec || sec.type !== DCSection) return;
    const sid = sec.props.id ?? sec.props.title;
    if (!sid) return;
    sectionOrder.push(sid);
    const persisted = state.sections[sid] || {};
    const abs = [];
    dcFlatten(sec.props.children).forEach(ab => {
      if (!ab || ab.type !== DCArtboard) return;
      const aid = ab.props.id ?? ab.props.label;
      if (aid) abs.push([aid, ab]);
    });
    // hidden is scoped to one source revision — when the agent regenerates
    // (artboard-ID set changes), prior deletes don't apply to new content.
    const srcKey = abs.map(([k]) => k).join('\x1f');
    const hidden = persisted.srcKey === srcKey ? persisted.hidden || [] : [];
    const srcIds = [];
    abs.forEach(([aid, ab]) => {
      if (hidden.includes(aid)) return;
      registry[`${sid}/${aid}`] = {
        sectionId: sid,
        artboard: ab
      };
      srcIds.push(aid);
    });
    const kept = (persisted.order || []).filter(k => srcIds.includes(k));
    sectionMeta[sid] = {
      title: persisted.title ?? sec.props.title,
      subtitle: sec.props.subtitle,
      slotIds: [...kept, ...srcIds.filter(k => !kept.includes(k))]
    };
  });
  const api = React.useMemo(() => ({
    state,
    section: id => state.sections[id] || {},
    patchSection: (id, p) => setState(s => ({
      ...s,
      sections: {
        ...s.sections,
        [id]: {
          ...s.sections[id],
          ...(typeof p === 'function' ? p(s.sections[id] || {}) : p)
        }
      }
    })),
    setFocus: slotId => setState(s => ({
      ...s,
      focus: slotId
    }))
  }), [state]);

  // Esc exits focus; any outside pointerdown commits an in-progress rename.
  React.useEffect(() => {
    const onKey = e => {
      if (e.key === 'Escape') api.setFocus(null);
    };
    const onPd = e => {
      const ae = document.activeElement;
      if (ae && ae.isContentEditable && !ae.contains(e.target)) ae.blur();
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onPd, true);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onPd, true);
    };
  }, [api]);
  return /*#__PURE__*/React.createElement(DCCtx.Provider, {
    value: api
  }, /*#__PURE__*/React.createElement(DCViewport, {
    minScale: minScale,
    maxScale: maxScale,
    style: style
  }, ready && children), state.focus && registry[state.focus] && /*#__PURE__*/React.createElement(DCFocusOverlay, {
    entry: registry[state.focus],
    sectionMeta: sectionMeta,
    sectionOrder: sectionOrder
  }));
}

// ─────────────────────────────────────────────────────────────
// DCViewport — transform-based pan/zoom (internal)
//
// Input mapping (Figma-style):
//   • trackpad pinch  → zoom   (ctrlKey wheel; Safari gesture* events)
//   • trackpad scroll → pan    (two-finger)
//   • mouse wheel     → zoom   (notched; distinguished from trackpad scroll)
//   • middle-drag / primary-drag-on-bg → pan
//
// Transform state lives in a ref and is written straight to the DOM
// (translate3d + will-change) so wheel ticks don't go through React —
// keeps pans at 60fps on dense canvases.
// ─────────────────────────────────────────────────────────────
function DCViewport({
  children,
  minScale = 0.1,
  maxScale = 8,
  style = {}
}) {
  const vpRef = React.useRef(null);
  const worldRef = React.useRef(null);
  const tf = React.useRef({
    x: 0,
    y: 0,
    scale: 1
  });
  // Persist viewport across reloads so the user lands back where they were
  // after an agent edit or browser refresh. The sandbox origin is already
  // per-project; pathname keeps multiple canvas files in one project apart.
  const tfKey = 'dc-viewport:' + location.pathname;
  const saveT = React.useRef(0);
  const lastPostedScale = React.useRef();
  const apply = React.useCallback(() => {
    const {
      x,
      y,
      scale
    } = tf.current;
    const el = worldRef.current;
    if (!el) return;
    el.style.transform = `translate3d(${x}px, ${y}px, 0) scale(${scale})`;
    // Exposed for zoom-invariant chrome (labels, buttons, TweaksPanel).
    el.style.setProperty('--dc-inv-zoom', String(1 / scale));
    // Keep the host toolbar's % readout in sync with the canvas scale. Pan
    // ticks leave scale unchanged — skip the cross-frame post for those.
    if (lastPostedScale.current !== scale) {
      lastPostedScale.current = scale;
      window.parent.postMessage({
        type: '__dc_zoom',
        scale
      }, '*');
    }
    clearTimeout(saveT.current);
    saveT.current = setTimeout(() => {
      try {
        localStorage.setItem(tfKey, JSON.stringify(tf.current));
      } catch {}
    }, 200);
  }, [tfKey]);
  React.useLayoutEffect(() => {
    const flush = () => {
      clearTimeout(saveT.current);
      try {
        localStorage.setItem(tfKey, JSON.stringify(tf.current));
      } catch {}
    };
    try {
      const s = JSON.parse(localStorage.getItem(tfKey) || 'null');
      if (s && Number.isFinite(s.x) && Number.isFinite(s.y) && Number.isFinite(s.scale)) {
        tf.current = {
          x: s.x,
          y: s.y,
          scale: Math.min(maxScale, Math.max(minScale, s.scale))
        };
        apply();
      }
    } catch {}
    // Flush on pagehide and unmount so a reload within the 200ms debounce
    // window doesn't drop the last pan/zoom.
    window.addEventListener('pagehide', flush);
    return () => {
      window.removeEventListener('pagehide', flush);
      flush();
    };
  }, []);
  React.useEffect(() => {
    const vp = vpRef.current;
    if (!vp) return;
    const zoomAt = (cx, cy, factor) => {
      const r = vp.getBoundingClientRect();
      const px = cx - r.left,
        py = cy - r.top;
      const t = tf.current;
      const next = Math.min(maxScale, Math.max(minScale, t.scale * factor));
      const k = next / t.scale;
      // --dc-inv-zoom consumers (.dc-sectionhead's CSS zoom, each section's
      // marginBottom) reflow on every scale change, vertically shifting the
      // world layout — so a world point mathematically pinned under the cursor
      // drifts as you zoom (content creeps up on zoom-in, down on zoom-out).
      // Anchor the DOM element under the cursor instead: record its screen Y,
      // apply the transform + --dc-inv-zoom, then cancel whatever vertical
      // drift the reflow introduced so it stays put on screen.
      let marker = null,
        markerY0 = 0;
      if (k !== 1) {
        const hit = document.elementFromPoint(cx, cy);
        marker = hit && hit.closest ? hit.closest('[data-dc-slot],[data-dc-section]') : null;
        if (marker) markerY0 = marker.getBoundingClientRect().top;
      }
      // keep the world point under the cursor fixed
      t.x = px - (px - t.x) * k;
      t.y = py - (py - t.y) * k;
      t.scale = next;
      apply();
      if (marker) {
        // A pure zoom around (cx, cy) maps screen Y → cy + (Y - cy) * k. Any
        // departure after the --dc-inv-zoom reflow is the layout drift.
        const drift = marker.getBoundingClientRect().top - (cy + (markerY0 - cy) * k);
        if (Math.abs(drift) > 0.1) {
          t.y -= drift;
          apply();
        }
      }
    };

    // Mouse-wheel vs trackpad-scroll heuristic. A physical wheel sends
    // line-mode deltas (Firefox) or large integer pixel deltas with no X
    // component (Chrome/Safari, typically multiples of 100/120). Trackpad
    // two-finger scroll sends small/fractional pixel deltas, often with
    // non-zero deltaX. ctrlKey is set by the browser for trackpad pinch.
    const isMouseWheel = e => e.deltaMode !== 0 || e.deltaX === 0 && Number.isInteger(e.deltaY) && Math.abs(e.deltaY) >= 40;
    const onWheel = e => {
      e.preventDefault();
      if (isGesturing) return; // Safari: gesture* owns the pinch — discard concurrent wheels
      if ((e.ctrlKey || e.metaKey) && !isMouseWheel(e)) {
        // trackpad pinch, or ctrl/cmd + smooth-scroll mouse. Notched
        // wheels fall through to the fixed-step branch below.
        zoomAt(e.clientX, e.clientY, Math.exp(-e.deltaY * 0.01));
      } else if (isMouseWheel(e)) {
        // notched mouse wheel — fixed-ratio step per click
        zoomAt(e.clientX, e.clientY, Math.exp(-Math.sign(e.deltaY) * 0.18));
      } else {
        // trackpad two-finger scroll — pan
        tf.current.x -= e.deltaX;
        tf.current.y -= e.deltaY;
        apply();
      }
    };

    // Safari sends native gesture* events for trackpad pinch with a smooth
    // e.scale; preferring these over the ctrl+wheel fallback gives a much
    // better feel there. No-ops on other browsers. Safari also fires
    // ctrlKey wheel events during the same pinch — isGesturing makes
    // onWheel drop those entirely so they neither zoom nor pan.
    let gsBase = 1;
    let isGesturing = false;
    const onGestureStart = e => {
      e.preventDefault();
      isGesturing = true;
      gsBase = tf.current.scale;
    };
    const onGestureChange = e => {
      e.preventDefault();
      zoomAt(e.clientX, e.clientY, gsBase * e.scale / tf.current.scale);
    };
    const onGestureEnd = e => {
      e.preventDefault();
      isGesturing = false;
    };

    // Drag-pan: middle button anywhere, or primary button on canvas
    // background (anything that isn't an artboard or an inline editor).
    let drag = null;
    const onPointerDown = e => {
      const onBg = !e.target.closest('[data-dc-slot], .dc-editable');
      if (!(e.button === 1 || e.button === 0 && onBg)) return;
      e.preventDefault();
      vp.setPointerCapture(e.pointerId);
      drag = {
        id: e.pointerId,
        lx: e.clientX,
        ly: e.clientY
      };
      vp.style.cursor = 'grabbing';
    };
    const onPointerMove = e => {
      if (!drag || e.pointerId !== drag.id) return;
      tf.current.x += e.clientX - drag.lx;
      tf.current.y += e.clientY - drag.ly;
      drag.lx = e.clientX;
      drag.ly = e.clientY;
      apply();
    };
    const onPointerUp = e => {
      if (!drag || e.pointerId !== drag.id) return;
      vp.releasePointerCapture(e.pointerId);
      drag = null;
      vp.style.cursor = '';
    };

    // Host-driven zoom (toolbar % menu). Zooms around viewport centre so the
    // visible midpoint stays fixed — matching the host's iframe-zoom feel.
    const onHostMsg = e => {
      const d = e.data;
      if (d && d.type === '__dc_set_zoom' && typeof d.scale === 'number') {
        const r = vp.getBoundingClientRect();
        zoomAt(r.left + r.width / 2, r.top + r.height / 2, d.scale / tf.current.scale);
      } else if (d && d.type === '__dc_probe') {
        // Host's [readyGen] reset asks whether a canvas is present; it
        // fires on the iframe's native 'load', which for canvases with
        // images/fonts is after our mount-time announce, so re-announce.
        // Clear the pan-tick guard so apply() re-posts the current scale
        // even if it's unchanged — the host just reset dcScale to 1.
        window.parent.postMessage({
          type: '__dc_present'
        }, '*');
        lastPostedScale.current = undefined;
        apply();
      }
    };
    window.addEventListener('message', onHostMsg);
    // Announce canvas mode so the host toolbar proxies its % control here
    // instead of scaling the iframe element (which would just shrink the
    // viewport window of an infinite canvas). The apply() that follows emits
    // the initial __dc_zoom so the toolbar % is correct before first pinch.
    // lastPostedScale reset mirrors the __dc_probe handler: the layout
    // effect's restore-path apply() may already have posted the restored
    // scale (before __dc_present), so clear the guard to re-post it in order.
    window.parent.postMessage({
      type: '__dc_present'
    }, '*');
    lastPostedScale.current = undefined;
    apply();
    vp.addEventListener('wheel', onWheel, {
      passive: false
    });
    vp.addEventListener('gesturestart', onGestureStart, {
      passive: false
    });
    vp.addEventListener('gesturechange', onGestureChange, {
      passive: false
    });
    vp.addEventListener('gestureend', onGestureEnd, {
      passive: false
    });
    vp.addEventListener('pointerdown', onPointerDown);
    vp.addEventListener('pointermove', onPointerMove);
    vp.addEventListener('pointerup', onPointerUp);
    vp.addEventListener('pointercancel', onPointerUp);
    return () => {
      window.removeEventListener('message', onHostMsg);
      vp.removeEventListener('wheel', onWheel);
      vp.removeEventListener('gesturestart', onGestureStart);
      vp.removeEventListener('gesturechange', onGestureChange);
      vp.removeEventListener('gestureend', onGestureEnd);
      vp.removeEventListener('pointerdown', onPointerDown);
      vp.removeEventListener('pointermove', onPointerMove);
      vp.removeEventListener('pointerup', onPointerUp);
      vp.removeEventListener('pointercancel', onPointerUp);
    };
  }, [apply, minScale, maxScale]);
  const gridSvg = `url("data:image/svg+xml,%3Csvg width='120' height='120' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M120 0H0v120' fill='none' stroke='${encodeURIComponent(DC.grid)}' stroke-width='1'/%3E%3C/svg%3E")`;
  return /*#__PURE__*/React.createElement("div", {
    ref: vpRef,
    className: "design-canvas",
    style: {
      height: '100vh',
      width: '100vw',
      background: DC.bg,
      overflow: 'hidden',
      overscrollBehavior: 'none',
      touchAction: 'none',
      position: 'relative',
      fontFamily: DC.font,
      boxSizing: 'border-box',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    ref: worldRef,
    style: {
      position: 'absolute',
      top: 0,
      left: 0,
      transformOrigin: '0 0',
      willChange: 'transform',
      width: 'max-content',
      minWidth: '100%',
      minHeight: '100%',
      padding: '60px 0 80px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: -6000,
      backgroundImage: gridSvg,
      backgroundSize: '120px 120px',
      pointerEvents: 'none',
      zIndex: -1
    }
  }), children));
}

// ─────────────────────────────────────────────────────────────
// DCSection — editable title + h-row of artboards in persisted order
// ─────────────────────────────────────────────────────────────
function DCSection({
  id,
  title,
  subtitle,
  children,
  gap = 48
}) {
  const ctx = React.useContext(DCCtx);
  const sid = id ?? title;
  const all = React.Children.toArray(dcFlatten(children));
  const artboards = all.filter(c => c && c.type === DCArtboard);
  const rest = all.filter(c => !(c && c.type === DCArtboard));
  const sec = ctx && sid && ctx.section(sid) || {};
  // Must match DesignCanvas's srcKey computation exactly (it filters falsy
  // IDs), or onDelete persists a srcKey that DesignCanvas never recognizes.
  const allIds = artboards.map(a => a.props.id ?? a.props.label).filter(Boolean);
  const srcKey = allIds.join('\x1f');
  const hidden = sec.srcKey === srcKey ? sec.hidden || [] : [];
  const srcOrder = allIds.filter(k => !hidden.includes(k));
  const order = React.useMemo(() => {
    const kept = (sec.order || []).filter(k => srcOrder.includes(k));
    return [...kept, ...srcOrder.filter(k => !kept.includes(k))];
  }, [sec.order, srcOrder.join('|')]);
  const byId = Object.fromEntries(artboards.map(a => [a.props.id ?? a.props.label, a]));

  // marginBottom counter-scales so the on-screen gap between sections stays
  // constant — otherwise at low zoom the (world-space) gap collapses while
  // the screen-constant sectionhead below it doesn't, and the title reads as
  // belonging to the section above. paddingBottom below is just enough for
  // the 24px artboard-header (abs-positioned above each card) plus ~8px, so
  // the title sits tight against its own row at every zoom.
  return /*#__PURE__*/React.createElement("div", {
    "data-dc-section": sid,
    style: {
      marginBottom: 'calc(80px * var(--dc-inv-zoom, 1))',
      position: 'relative'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '0 60px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "dc-sectionhead",
    style: {
      paddingBottom: 36
    }
  }, /*#__PURE__*/React.createElement(DCEditable, {
    tag: "div",
    value: sec.title ?? title,
    onChange: v => ctx && sid && ctx.patchSection(sid, {
      title: v
    }),
    style: {
      fontSize: 28,
      fontWeight: 600,
      color: DC.title,
      letterSpacing: -0.4,
      marginBottom: 6,
      display: 'inline-block'
    }
  }), subtitle && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 16,
      color: DC.subtitle
    }
  }, subtitle))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap,
      padding: '0 60px',
      alignItems: 'flex-start',
      width: 'max-content'
    }
  }, order.map(k => /*#__PURE__*/React.createElement(DCArtboardFrame, {
    key: k,
    sectionId: sid,
    artboard: byId[k],
    order: order,
    label: (sec.labels || {})[k] ?? byId[k].props.label,
    onRename: v => ctx && ctx.patchSection(sid, x => ({
      labels: {
        ...x.labels,
        [k]: v
      }
    })),
    onReorder: next => ctx && ctx.patchSection(sid, {
      order: next
    }),
    onDelete: () => ctx && ctx.patchSection(sid, x => ({
      hidden: [...(x.srcKey === srcKey ? x.hidden || [] : []), k],
      srcKey
    })),
    onFocus: () => ctx && ctx.setFocus(`${sid}/${k}`)
  }))), rest);
}

// DCArtboard — marker; rendered by DCArtboardFrame via DCSection.
function DCArtboard() {
  return null;
}

// Per-artboard export (kind: 'png' | 'html'). Both paths share the same
// self-contained clone: computed styles baked in, @font-face / <img> /
// inline-style background-image urls inlined as data URIs. PNG wraps the
// clone in foreignObject→canvas at 3× the artboard's natural width×height
// (same pipeline the host uses for page captures); HTML wraps it in a
// minimal standalone document. Both are independent of viewport zoom.
async function dcExport(node, w, h, name, kind) {
  try {
    await document.fonts.ready;
  } catch {}
  const toDataURL = url => fetch(url).then(r => r.blob()).then(b => new Promise(res => {
    const fr = new FileReader();
    fr.onload = () => res(fr.result);
    fr.onerror = () => res(url);
    fr.readAsDataURL(b);
  })).catch(() => url);

  // Collect @font-face rules. ss.cssRules throws SecurityError on
  // cross-origin sheets (e.g. fonts.googleapis.com) — in that case fetch
  // the CSS text directly (those endpoints send ACAO:*) and regex-extract
  // the blocks. @import and @media/@supports are walked so nested
  // @font-face rules aren't missed.
  const fontRules = [],
    pending = [],
    seen = new Set();
  const scrapeCss = href => {
    if (seen.has(href)) return;
    seen.add(href);
    pending.push(fetch(href).then(r => r.text()).then(css => {
      for (const m of css.match(/@font-face\s*{[^}]*}/g) || []) fontRules.push({
        css: m,
        base: href
      });
      for (const m of css.matchAll(/@import\s+(?:url\()?['"]?([^'")\s;]+)/g)) scrapeCss(new URL(m[1], href).href);
    }).catch(() => {}));
  };
  const walk = (rules, base) => {
    for (const r of rules) {
      if (r.type === CSSRule.FONT_FACE_RULE) fontRules.push({
        css: r.cssText,
        base
      });else if (r.type === CSSRule.IMPORT_RULE && r.styleSheet) {
        const ibase = r.styleSheet.href || base;
        try {
          walk(r.styleSheet.cssRules, ibase);
        } catch {
          scrapeCss(ibase);
        }
      } else if (r.cssRules) walk(r.cssRules, base);
    }
  };
  for (const ss of document.styleSheets) {
    const base = ss.href || location.href;
    try {
      walk(ss.cssRules, base);
    } catch {
      if (ss.href) scrapeCss(ss.href);
    }
  }
  while (pending.length) await pending.shift();
  const fontCss = (await Promise.all(fontRules.map(async rule => {
    let out = rule.css,
      m;
    const re = /url\((['"]?)([^'")]+)\1\)/g;
    while (m = re.exec(rule.css)) {
      if (m[2].indexOf('data:') === 0) continue;
      let abs;
      try {
        abs = new URL(m[2], rule.base).href;
      } catch {
        continue;
      }
      out = out.split(m[0]).join('url("' + (await toDataURL(abs)) + '")');
    }
    return out;
  }))).join('\n');
  const cloneStyled = src => {
    if (src.nodeType === 8 || src.nodeType === 1 && src.tagName === 'SCRIPT') return document.createTextNode('');
    const dst = src.cloneNode(false);
    if (src.nodeType === 1) {
      const cs = getComputedStyle(src);
      let txt = '';
      for (let i = 0; i < cs.length; i++) txt += cs[i] + ':' + cs.getPropertyValue(cs[i]) + ';';
      dst.setAttribute('style', txt + 'animation:none;transition:none;');
      if (src.tagName === 'CANVAS') try {
        const im = document.createElement('img');
        im.src = src.toDataURL();
        im.setAttribute('style', txt);
        return im;
      } catch {}
    }
    for (let c = src.firstChild; c; c = c.nextSibling) dst.appendChild(cloneStyled(c));
    return dst;
  };
  const clone = cloneStyled(node);
  clone.setAttribute('xmlns', 'http://www.w3.org/1999/xhtml');
  // Drop the card's own shadow/radius so the export is a flush w×h rect;
  // the artboard's own background (if any) is already in the computed style.
  clone.style.boxShadow = 'none';
  clone.style.borderRadius = '0';
  const jobs = [];
  clone.querySelectorAll('img').forEach(el => {
    const s = el.getAttribute('src');
    if (s && s.indexOf('data:') !== 0) jobs.push(toDataURL(el.src).then(d => el.setAttribute('src', d)));
  });
  [clone, ...clone.querySelectorAll('*')].forEach(el => {
    const bg = el.style.backgroundImage;
    if (!bg) return;
    let m;
    const re = /url\(["']?([^"')]+)["']?\)/g;
    while (m = re.exec(bg)) {
      const tok = m[0],
        url = m[1];
      if (url.indexOf('data:') === 0) continue;
      jobs.push(toDataURL(url).then(d => {
        el.style.backgroundImage = el.style.backgroundImage.split(tok).join('url("' + d + '")');
      }));
    }
  });
  await Promise.all(jobs);
  const xml = new XMLSerializer().serializeToString(clone);
  const save = (blob, ext) => {
    if (!blob) return;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name + '.' + ext;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  if (kind === 'html') {
    const html = '<!doctype html><html><head><meta charset="utf-8"><title>' + name + '</title>' + (fontCss ? '<style>' + fontCss + '</style>' : '') + '</head><body style="margin:0">' + xml + '</body></html>';
    return save(new Blob([html], {
      type: 'text/html'
    }), 'html');
  }

  // PNG: the SVG's own width/height must be the output resolution — an
  // <img>-loaded SVG rasterizes at its intrinsic size, so sizing it at 1×
  // and ctx.scale()-ing up would just upscale a 1× bitmap. viewBox maps the
  // w×h foreignObject onto the px·w × px·h SVG canvas so the browser renders
  // the HTML at full resolution.
  const px = 3;
  const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + w * px + '" height="' + h * px + '" viewBox="0 0 ' + w + ' ' + h + '"><foreignObject width="' + w + '" height="' + h + '">' + (fontCss ? '<style><![CDATA[' + fontCss + ']]></style>' : '') + xml + '</foreignObject></svg>';
  const img = new Image();
  await new Promise((res, rej) => {
    img.onload = res;
    img.onerror = () => rej(new Error('svg load failed'));
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  });
  const cv = document.createElement('canvas');
  cv.width = w * px;
  cv.height = h * px;
  cv.getContext('2d').drawImage(img, 0, 0);
  cv.toBlob(blob => save(blob, 'png'), 'image/png');
}
function DCArtboardFrame({
  sectionId,
  artboard,
  label,
  order,
  onRename,
  onReorder,
  onFocus,
  onDelete
}) {
  const {
    id: rawId,
    label: rawLabel,
    width = 260,
    height = 480,
    children,
    style = {}
  } = artboard.props;
  const id = rawId ?? rawLabel;
  const ref = React.useRef(null);
  const cardRef = React.useRef(null);
  const menuRef = React.useRef(null);
  const [menuOpen, setMenuOpen] = React.useState(false);
  const [confirming, setConfirming] = React.useState(false);

  // ⋯ menu: close on any outside pointerdown. Two-click delete lives inside
  // the menu — first click arms the row, second commits; closing disarms.
  React.useEffect(() => {
    if (!menuOpen) {
      setConfirming(false);
      return;
    }
    const off = e => {
      if (!menuRef.current || !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener('pointerdown', off, true);
    return () => document.removeEventListener('pointerdown', off, true);
  }, [menuOpen]);
  const doExport = kind => {
    setMenuOpen(false);
    if (!cardRef.current) return;
    const name = String(label || id || 'artboard').replace(/[^\w\s.-]+/g, '_');
    dcExport(cardRef.current, width, height, name, kind).catch(e => console.error('[design-canvas] export failed:', e));
  };

  // Live drag-reorder: dragged card sticks to cursor; siblings slide into
  // their would-be slots in real time via transforms. DOM order only
  // changes on drop.
  const onGripDown = e => {
    e.preventDefault();
    e.stopPropagation();
    const me = ref.current;
    // translateX is applied in local (pre-scale) space but pointer deltas and
    // getBoundingClientRect().left are screen-space — divide by the viewport's
    // current scale so the dragged card tracks the cursor at any zoom level.
    const scale = me.getBoundingClientRect().width / me.offsetWidth || 1;
    const peers = Array.from(document.querySelectorAll(`[data-dc-section="${sectionId}"] [data-dc-slot]`));
    const homes = peers.map(el => ({
      el,
      id: el.dataset.dcSlot,
      x: el.getBoundingClientRect().left
    }));
    const slotXs = homes.map(h => h.x);
    const startIdx = order.indexOf(id);
    const startX = e.clientX;
    let liveOrder = order.slice();
    me.classList.add('dc-dragging');
    const layout = () => {
      for (const h of homes) {
        if (h.id === id) continue;
        const slot = liveOrder.indexOf(h.id);
        h.el.style.transform = `translateX(${(slotXs[slot] - h.x) / scale}px)`;
      }
    };
    const move = ev => {
      const dx = ev.clientX - startX;
      me.style.transform = `translateX(${dx / scale}px)`;
      const cur = homes[startIdx].x + dx;
      let nearest = 0,
        best = Infinity;
      for (let i = 0; i < slotXs.length; i++) {
        const d = Math.abs(slotXs[i] - cur);
        if (d < best) {
          best = d;
          nearest = i;
        }
      }
      if (liveOrder.indexOf(id) !== nearest) {
        liveOrder = order.filter(k => k !== id);
        liveOrder.splice(nearest, 0, id);
        layout();
      }
    };
    const up = () => {
      document.removeEventListener('pointermove', move);
      document.removeEventListener('pointerup', up);
      const finalSlot = liveOrder.indexOf(id);
      me.classList.remove('dc-dragging');
      me.style.transform = `translateX(${(slotXs[finalSlot] - homes[startIdx].x) / scale}px)`;
      // After the settle transition, kill transitions + clear transforms +
      // commit the reorder in the same frame so there's no visual snap-back.
      setTimeout(() => {
        for (const h of homes) {
          h.el.style.transition = 'none';
          h.el.style.transform = '';
        }
        if (liveOrder.join('|') !== order.join('|')) onReorder(liveOrder);
        requestAnimationFrame(() => requestAnimationFrame(() => {
          for (const h of homes) h.el.style.transition = '';
        }));
      }, 180);
    };
    document.addEventListener('pointermove', move);
    document.addEventListener('pointerup', up);
  };
  return /*#__PURE__*/React.createElement("div", {
    ref: ref,
    "data-dc-slot": id,
    style: {
      position: 'relative',
      flexShrink: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "dc-header",
    "data-omelette-chrome": "",
    style: {
      color: DC.label
    },
    onPointerDown: e => e.stopPropagation()
  }, /*#__PURE__*/React.createElement("div", {
    className: "dc-labelrow"
  }, /*#__PURE__*/React.createElement("div", {
    className: "dc-grip",
    onPointerDown: onGripDown,
    title: "Drag to reorder"
  }, /*#__PURE__*/React.createElement("svg", {
    width: "9",
    height: "13",
    viewBox: "0 0 9 13",
    fill: "currentColor"
  }, /*#__PURE__*/React.createElement("circle", {
    cx: "2",
    cy: "2",
    r: "1.1"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "7",
    cy: "2",
    r: "1.1"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "2",
    cy: "6.5",
    r: "1.1"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "7",
    cy: "6.5",
    r: "1.1"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "2",
    cy: "11",
    r: "1.1"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "7",
    cy: "11",
    r: "1.1"
  }))), /*#__PURE__*/React.createElement("div", {
    className: "dc-labeltext",
    onClick: onFocus,
    title: "Click to focus"
  }, /*#__PURE__*/React.createElement(DCEditable, {
    value: label,
    onChange: onRename,
    onClick: e => e.stopPropagation(),
    style: {
      fontSize: 15,
      fontWeight: 500,
      color: DC.label,
      lineHeight: 1
    }
  }))), /*#__PURE__*/React.createElement("div", {
    className: "dc-btns"
  }, /*#__PURE__*/React.createElement("div", {
    ref: menuRef,
    style: {
      position: 'relative'
    }
  }, /*#__PURE__*/React.createElement("button", {
    className: "dc-kebab",
    title: "More",
    onClick: () => setMenuOpen(o => !o)
  }, /*#__PURE__*/React.createElement("svg", {
    width: "12",
    height: "12",
    viewBox: "0 0 12 12",
    fill: "currentColor"
  }, /*#__PURE__*/React.createElement("circle", {
    cx: "2.5",
    cy: "6",
    r: "1.1"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "6",
    cy: "6",
    r: "1.1"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "9.5",
    cy: "6",
    r: "1.1"
  }))), menuOpen && /*#__PURE__*/React.createElement("div", {
    className: "dc-menu",
    onPointerDown: e => e.stopPropagation()
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => doExport('png')
  }, "Download PNG"), /*#__PURE__*/React.createElement("button", {
    onClick: () => doExport('html')
  }, "Download HTML"), /*#__PURE__*/React.createElement("hr", null), /*#__PURE__*/React.createElement("button", {
    className: "dc-danger",
    onClick: () => {
      if (confirming) {
        setMenuOpen(false);
        onDelete();
      } else setConfirming(true);
    }
  }, confirming ? 'Click again to delete' : 'Delete'))), /*#__PURE__*/React.createElement("button", {
    className: "dc-expand",
    onClick: onFocus,
    title: "Focus"
  }, /*#__PURE__*/React.createElement("svg", {
    width: "12",
    height: "12",
    viewBox: "0 0 12 12",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "1.6",
    strokeLinecap: "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M7 1h4v4M5 11H1V7M11 1L7.5 4.5M1 11l3.5-3.5"
  }))))), /*#__PURE__*/React.createElement("div", {
    ref: cardRef,
    className: "dc-card",
    style: {
      borderRadius: 2,
      boxShadow: '0 1px 3px rgba(0,0,0,.08),0 4px 16px rgba(0,0,0,.06)',
      overflow: 'hidden',
      width,
      height,
      background: '#fff',
      ...style
    }
  }, children || /*#__PURE__*/React.createElement("div", {
    style: {
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#bbb',
      fontSize: 13,
      fontFamily: DC.font
    }
  }, id)));
}

// Inline rename — commits on blur or Enter.
function DCEditable({
  value,
  onChange,
  style,
  tag = 'span',
  onClick
}) {
  const T = tag;
  return /*#__PURE__*/React.createElement(T, {
    className: "dc-editable",
    contentEditable: true,
    suppressContentEditableWarning: true,
    onClick: onClick,
    onPointerDown: e => e.stopPropagation(),
    onBlur: e => onChange && onChange(e.currentTarget.textContent),
    onKeyDown: e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        e.currentTarget.blur();
      }
    },
    style: style
  }, value);
}

// ─────────────────────────────────────────────────────────────
// Focus mode — overlay one artboard; ←/→ within section, ↑/↓ across
// sections, Esc or backdrop click to exit.
// ─────────────────────────────────────────────────────────────
function DCFocusOverlay({
  entry,
  sectionMeta,
  sectionOrder
}) {
  const ctx = React.useContext(DCCtx);
  const {
    sectionId,
    artboard
  } = entry;
  const sec = ctx.section(sectionId);
  const meta = sectionMeta[sectionId];
  const peers = meta.slotIds;
  const aid = artboard.props.id ?? artboard.props.label;
  const idx = peers.indexOf(aid);
  const secIdx = sectionOrder.indexOf(sectionId);
  const go = d => {
    const n = peers[(idx + d + peers.length) % peers.length];
    if (n) ctx.setFocus(`${sectionId}/${n}`);
  };
  const goSection = d => {
    // Sections whose artboards are all deleted have slotIds:[] — step past
    // them to the next non-empty section so ↑/↓ doesn't dead-end.
    const n = sectionOrder.length;
    for (let i = 1; i < n; i++) {
      const ns = sectionOrder[((secIdx + d * i) % n + n) % n];
      const first = sectionMeta[ns] && sectionMeta[ns].slotIds[0];
      if (first) {
        ctx.setFocus(`${ns}/${first}`);
        return;
      }
    }
  };
  React.useEffect(() => {
    const k = e => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        go(-1);
      }
      if (e.key === 'ArrowRight') {
        e.preventDefault();
        go(1);
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        goSection(-1);
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        goSection(1);
      }
    };
    document.addEventListener('keydown', k);
    return () => document.removeEventListener('keydown', k);
  });
  const {
    width = 260,
    height = 480,
    children
  } = artboard.props;
  const [vp, setVp] = React.useState({
    w: window.innerWidth,
    h: window.innerHeight
  });
  React.useEffect(() => {
    const r = () => setVp({
      w: window.innerWidth,
      h: window.innerHeight
    });
    window.addEventListener('resize', r);
    return () => window.removeEventListener('resize', r);
  }, []);
  const scale = Math.max(0.1, Math.min((vp.w - 200) / width, (vp.h - 260) / height, 2));
  const [ddOpen, setDd] = React.useState(false);
  const Arrow = ({
    dir,
    onClick
  }) => /*#__PURE__*/React.createElement("button", {
    onClick: e => {
      e.stopPropagation();
      onClick();
    },
    style: {
      position: 'absolute',
      top: '50%',
      [dir]: 28,
      transform: 'translateY(-50%)',
      border: 'none',
      background: 'rgba(255,255,255,.08)',
      color: 'rgba(255,255,255,.9)',
      width: 44,
      height: 44,
      borderRadius: 22,
      fontSize: 18,
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'background .15s'
    },
    onMouseEnter: e => e.currentTarget.style.background = 'rgba(255,255,255,.18)',
    onMouseLeave: e => e.currentTarget.style.background = 'rgba(255,255,255,.08)'
  }, /*#__PURE__*/React.createElement("svg", {
    width: "18",
    height: "18",
    viewBox: "0 0 18 18",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: dir === 'left' ? 'M11 3L5 9l6 6' : 'M7 3l6 6-6 6'
  })));

  // Portal to body so position:fixed is the real viewport regardless of any
  // transform on DesignCanvas's ancestors (including the canvas zoom itself).
  return ReactDOM.createPortal(/*#__PURE__*/React.createElement("div", {
    onClick: () => ctx.setFocus(null),
    onWheel: e => e.preventDefault(),
    style: {
      position: 'fixed',
      inset: 0,
      zIndex: 100,
      background: 'rgba(24,20,16,.6)',
      backdropFilter: 'blur(14px)',
      fontFamily: DC.font,
      color: '#fff'
    }
  }, /*#__PURE__*/React.createElement("div", {
    onClick: e => e.stopPropagation(),
    style: {
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      height: 72,
      display: 'flex',
      alignItems: 'flex-start',
      padding: '16px 20px 0',
      gap: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative'
    }
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => setDd(o => !o),
    style: {
      border: 'none',
      background: 'transparent',
      color: '#fff',
      cursor: 'pointer',
      padding: '6px 8px',
      borderRadius: 6,
      textAlign: 'left',
      fontFamily: 'inherit'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 18,
      fontWeight: 600,
      letterSpacing: -0.3
    }
  }, meta.title), /*#__PURE__*/React.createElement("svg", {
    width: "11",
    height: "11",
    viewBox: "0 0 11 11",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "1.8",
    strokeLinecap: "round",
    style: {
      opacity: .7
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "M2 4l3.5 3.5L9 4"
  }))), meta.subtitle && /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'block',
      fontSize: 13,
      opacity: .6,
      fontWeight: 400,
      marginTop: 2
    }
  }, meta.subtitle)), ddOpen && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: '100%',
      left: 0,
      marginTop: 4,
      background: '#2a251f',
      borderRadius: 8,
      boxShadow: '0 8px 32px rgba(0,0,0,.4)',
      padding: 4,
      minWidth: 200,
      zIndex: 10
    }
  }, sectionOrder.filter(sid => sectionMeta[sid].slotIds.length).map(sid => /*#__PURE__*/React.createElement("button", {
    key: sid,
    onClick: () => {
      setDd(false);
      const f = sectionMeta[sid].slotIds[0];
      if (f) ctx.setFocus(`${sid}/${f}`);
    },
    style: {
      display: 'block',
      width: '100%',
      textAlign: 'left',
      border: 'none',
      cursor: 'pointer',
      background: sid === sectionId ? 'rgba(255,255,255,.1)' : 'transparent',
      color: '#fff',
      padding: '8px 12px',
      borderRadius: 5,
      fontSize: 14,
      fontWeight: sid === sectionId ? 600 : 400,
      fontFamily: 'inherit'
    }
  }, sectionMeta[sid].title)))), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), /*#__PURE__*/React.createElement("button", {
    onClick: () => ctx.setFocus(null),
    onMouseEnter: e => e.currentTarget.style.background = 'rgba(255,255,255,.12)',
    onMouseLeave: e => e.currentTarget.style.background = 'transparent',
    style: {
      border: 'none',
      background: 'transparent',
      color: 'rgba(255,255,255,.7)',
      width: 32,
      height: 32,
      borderRadius: 16,
      fontSize: 20,
      cursor: 'pointer',
      lineHeight: 1,
      transition: 'background .12s'
    }
  }, "\xD7")), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 64,
      bottom: 56,
      left: 100,
      right: 100,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    onClick: e => e.stopPropagation(),
    style: {
      width: width * scale,
      height: height * scale,
      position: 'relative'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width,
      height,
      transform: `scale(${scale})`,
      transformOrigin: 'top left',
      background: '#fff',
      borderRadius: 2,
      overflow: 'hidden',
      boxShadow: '0 20px 80px rgba(0,0,0,.4)'
    }
  }, children || /*#__PURE__*/React.createElement("div", {
    style: {
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#bbb'
    }
  }, aid))), /*#__PURE__*/React.createElement("div", {
    onClick: e => e.stopPropagation(),
    style: {
      fontSize: 14,
      fontWeight: 500,
      opacity: .85,
      textAlign: 'center'
    }
  }, (sec.labels || {})[aid] ?? artboard.props.label, /*#__PURE__*/React.createElement("span", {
    style: {
      opacity: .5,
      marginLeft: 10,
      fontVariantNumeric: 'tabular-nums'
    }
  }, idx + 1, " / ", peers.length))), /*#__PURE__*/React.createElement(Arrow, {
    dir: "left",
    onClick: () => go(-1)
  }), /*#__PURE__*/React.createElement(Arrow, {
    dir: "right",
    onClick: () => go(1)
  }), /*#__PURE__*/React.createElement("div", {
    onClick: e => e.stopPropagation(),
    style: {
      position: 'absolute',
      bottom: 20,
      left: '50%',
      transform: 'translateX(-50%)',
      display: 'flex',
      gap: 8
    }
  }, peers.map((p, i) => /*#__PURE__*/React.createElement("button", {
    key: p,
    onClick: () => ctx.setFocus(`${sectionId}/${p}`),
    style: {
      border: 'none',
      padding: 0,
      cursor: 'pointer',
      width: 6,
      height: 6,
      borderRadius: 3,
      background: i === idx ? '#fff' : 'rgba(255,255,255,.3)'
    }
  })))), document.body);
}

// ─────────────────────────────────────────────────────────────
// Post-it — absolute-positioned sticky note
// ─────────────────────────────────────────────────────────────
function DCPostIt({
  children,
  top,
  left,
  right,
  bottom,
  rotate = -2,
  width = 180
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top,
      left,
      right,
      bottom,
      width,
      background: DC.postitBg,
      padding: '14px 16px',
      fontFamily: '"Comic Sans MS", "Marker Felt", "Segoe Print", cursive',
      fontSize: 14,
      lineHeight: 1.4,
      color: DC.postitText,
      boxShadow: '0 2px 8px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08)',
      transform: `rotate(${rotate}deg)`,
      zIndex: 5
    }
  }, children);
}
Object.assign(window, {
  DesignCanvas,
  DCSection,
  DCArtboard,
  DCPostIt
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "logo/design-canvas.jsx", error: String((e && e.message) || e) }); }

// ui_kits/cdrkit-site/Chrome.jsx
try { (() => {
/* cdr-kit site chrome — Nav, Footer, ThemeToggle, Badge, CopyButton, Brand.
   Faithful to apps/site/components/{nav,footer,theme-toggle,primitives}. */
const {
  useState,
  useEffect,
  useRef
} = React;
function Brand() {
  return /*#__PURE__*/React.createElement("a", {
    className: "brand",
    href: "#top",
    "aria-label": "cdr-kit home"
  }, /*#__PURE__*/React.createElement("span", {
    className: "brand-mark",
    "aria-hidden": "true"
  }, /*#__PURE__*/React.createElement(CdrMark, {
    width: "24",
    height: "24"
  })), /*#__PURE__*/React.createElement("span", {
    className: "word"
  }, "cdr", /*#__PURE__*/React.createElement("b", null, "-"), "kit"));
}
function Badge({
  tone = "default",
  dot = true,
  children
}) {
  const cls = {
    default: "badge",
    primary: "badge badge-primary",
    live: "badge badge-live",
    warn: "badge badge-warn"
  }[tone];
  return /*#__PURE__*/React.createElement("span", {
    className: cls
  }, dot && /*#__PURE__*/React.createElement("span", {
    className: "dot"
  }), children);
}
function CopyButton({
  value,
  label = "Copy"
}) {
  const [copied, setCopied] = useState(false);
  const onClick = () => {
    try {
      navigator.clipboard?.writeText(value);
    } catch (e) {}
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  };
  return /*#__PURE__*/React.createElement("button", {
    className: copied ? "copybtn copied" : "copybtn",
    onClick: onClick,
    type: "button"
  }, copied ? /*#__PURE__*/React.createElement(Check, null) : /*#__PURE__*/React.createElement(Copy, null), " ", copied ? "Copied" : label);
}
function CopyLine({
  command,
  minWidth
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "copyline",
    style: minWidth ? {
      minWidth
    } : undefined
  }, /*#__PURE__*/React.createElement("span", {
    className: "cmd"
  }, /*#__PURE__*/React.createElement("span", {
    className: "pfx"
  }, "$"), " ", command), /*#__PURE__*/React.createElement(CopyButton, {
    value: command
  }));
}
function ThemeToggle() {
  const toggle = () => {
    const el = document.documentElement;
    const next = el.getAttribute("data-theme") === "dark" ? "light" : "dark";
    el.setAttribute("data-theme", next);
    try {
      localStorage.setItem("cdr-theme", next);
    } catch (e) {}
  };
  return /*#__PURE__*/React.createElement("button", {
    className: "icon-btn theme-toggle",
    onClick: toggle,
    "aria-label": "Toggle theme",
    type: "button"
  }, /*#__PURE__*/React.createElement("span", {
    className: "sun"
  }, /*#__PURE__*/React.createElement(Sun, null)), /*#__PURE__*/React.createElement("span", {
    className: "moon"
  }, /*#__PURE__*/React.createElement(Moon, null)));
}
const PRIMARY_LINKS = [{
  href: "#quickstart",
  label: "Docs"
}, {
  href: "#pillars",
  label: "Components"
}, {
  href: "#quickstart",
  label: "Hooks"
}, {
  href: "#agent",
  label: "Agent Kit"
}];
const MORE_GROUP = [{
  href: "#conditions",
  label: "Contracts",
  desc: "Standard library of CDR conditions."
}, {
  href: "#agent",
  label: "MCP server",
  desc: "Drop-in stdio server for Claude / Cursor."
}, {
  href: "#quickstart",
  label: "Scaffolder",
  desc: "npm create cdr-kit — start in seconds."
}, {
  href: "#live",
  label: "Live on Aeneid",
  desc: "Deployed condition addresses."
}];
function Nav() {
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef(null);
  useEffect(() => {
    if (!moreOpen) return;
    const onClick = e => {
      if (!moreRef.current?.contains(e.target)) setMoreOpen(false);
    };
    window.addEventListener("mousedown", onClick);
    return () => window.removeEventListener("mousedown", onClick);
  }, [moreOpen]);
  return /*#__PURE__*/React.createElement("header", {
    className: "nav",
    id: "top"
  }, /*#__PURE__*/React.createElement("div", {
    className: "nav-inner"
  }, /*#__PURE__*/React.createElement(Brand, null), /*#__PURE__*/React.createElement("nav", {
    className: "nav-links"
  }, PRIMARY_LINKS.map((l, i) => /*#__PURE__*/React.createElement("a", {
    key: i,
    href: l.href
  }, l.label)), /*#__PURE__*/React.createElement("div", {
    className: "nav-more",
    ref: moreRef
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: moreOpen ? "nav-more-btn is-open" : "nav-more-btn",
    "aria-expanded": moreOpen,
    onClick: () => setMoreOpen(v => !v)
  }, "More ", /*#__PURE__*/React.createElement(ChevDown, {
    width: "10",
    height: "10"
  })), moreOpen && /*#__PURE__*/React.createElement("div", {
    className: "nav-more-menu",
    role: "menu"
  }, MORE_GROUP.map((m, i) => /*#__PURE__*/React.createElement("a", {
    key: i,
    href: m.href,
    className: "nav-more-item",
    onClick: () => setMoreOpen(false)
  }, /*#__PURE__*/React.createElement("span", {
    className: "nm-label"
  }, m.label), /*#__PURE__*/React.createElement("span", {
    className: "nm-desc"
  }, m.desc)))))), /*#__PURE__*/React.createElement("div", {
    className: "nav-right"
  }, /*#__PURE__*/React.createElement("button", {
    className: "nav-search-trigger",
    type: "button"
  }, /*#__PURE__*/React.createElement(Search, null), /*#__PURE__*/React.createElement("span", {
    className: "nav-search-placeholder"
  }, "Search docs\u2026"), /*#__PURE__*/React.createElement("span", {
    className: "nav-search-kbd"
  }, "\u2318K")), /*#__PURE__*/React.createElement("a", {
    className: "icon-btn",
    href: "https://www.npmjs.com/org/cdr-kit",
    target: "_blank",
    rel: "noreferrer",
    title: "npm"
  }, /*#__PURE__*/React.createElement(Npm, null)), /*#__PURE__*/React.createElement("a", {
    className: "icon-btn",
    href: "https://github.com/Blockchain-Oracle/cdr-kit",
    target: "_blank",
    rel: "noreferrer",
    title: "GitHub"
  }, /*#__PURE__*/React.createElement(Github, null)), /*#__PURE__*/React.createElement(ThemeToggle, null), /*#__PURE__*/React.createElement("a", {
    className: "btn btn-primary btn-sm",
    href: "#quickstart"
  }, "Get started"))));
}
const FOOTER_COLUMNS = [{
  heading: "Docs",
  links: [["Quickstart", "#quickstart"], ["Components", "#pillars"], ["Hooks", "#quickstart"], ["Contracts", "#conditions"]]
}, {
  heading: "Agent kit",
  links: [["CdrAgent", "#agent"], ["MCP server", "#agent"], ["Framework adapters", "#agent"], ["Examples", "#quickstart"]]
}, {
  heading: "Project",
  links: [["GitHub", "https://github.com/Blockchain-Oracle/cdr-kit"], ["npm org", "https://www.npmjs.com/org/cdr-kit"], ["Story Protocol", "https://www.story.foundation"], ["Hackathon", "https://build.usecdr.dev"]]
}];
function Footer() {
  return /*#__PURE__*/React.createElement("footer", {
    className: "footer"
  }, /*#__PURE__*/React.createElement("div", {
    className: "container"
  }, /*#__PURE__*/React.createElement("div", {
    className: "footer-inner"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Brand, null), /*#__PURE__*/React.createElement("p", {
    className: "muted",
    style: {
      marginTop: 12,
      fontSize: "0.9rem",
      maxWidth: 320
    }
  }, "The developer toolkit for Story Protocol's Confidential Data Rails. MIT licensed."), /*#__PURE__*/React.createElement("span", {
    className: "badge badge-live",
    style: {
      marginTop: 14
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "dot"
  }), "Live on Aeneid")), FOOTER_COLUMNS.map(col => /*#__PURE__*/React.createElement("div", {
    key: col.heading
  }, /*#__PURE__*/React.createElement("h4", null, col.heading), /*#__PURE__*/React.createElement("ul", null, col.links.map(([label, href]) => /*#__PURE__*/React.createElement("li", {
    key: label
  }, /*#__PURE__*/React.createElement("a", {
    href: href,
    target: href.startsWith("http") ? "_blank" : undefined,
    rel: "noreferrer"
  }, label))))))), /*#__PURE__*/React.createElement("div", {
    className: "footer-bottom"
  }, /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "\xA9 2026 cdr-kit \xB7 MIT \xB7 built on Story Protocol"), /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "v0.7.1"))));
}
Object.assign(window, {
  Brand,
  Badge,
  CopyButton,
  CopyLine,
  ThemeToggle,
  Nav,
  Footer
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/cdrkit-site/Chrome.jsx", error: String((e && e.message) || e) }); }

// ui_kits/cdrkit-site/Hero.jsx
try { (() => {
/* Hero + VaultCycle + PackageStrip — ported from apps/site/components/landing.
   VaultCycle cycles the payload locked → decrypted → relocked on a 9.6s loop. */
const {
  useState: _useState,
  useEffect: _useEffect,
  useRef: _useRef
} = React;
const CIPHER = "7b 22 73 69 67 6e 61 6c 22 3a 22 ?? ?? ?? 9f a3 2e c1 04 7d e8 11 b6 ?? ?? ?? 6a 0c";
const PLAIN = '{ "signal": "BUY", "pair": "ETH/USD", "confidence": 0.86, "ttl": "30d" }';
const GLYPHS = '0123456789abcdef ?{}":,./';
const FRAMES = 30,
  FRAME_MS = 36,
  DECRYPT_DELAY = 1600,
  RELOCK_DELAY = 7200,
  CYCLE = 9600;
function EncryptedScramble({
  final,
  className
}) {
  const [txt, setTxt] = _useState(final);
  _useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;
    let frame = 0;
    const iv = setInterval(() => {
      frame++;
      const resolved = Math.floor(frame / 22 * final.length);
      let out = "";
      for (let i = 0; i < final.length; i++) {
        out += i < resolved ? final[i] : GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
      }
      setTxt(out);
      if (frame >= 22) {
        setTxt(final);
        clearInterval(iv);
      }
    }, 40);
    return () => clearInterval(iv);
  }, [final]);
  return /*#__PURE__*/React.createElement("span", {
    className: className
  }, txt);
}
function VaultCycle() {
  const [phase, setPhase] = _useState("locked");
  const [payload, setPayload] = _useState(CIPHER);
  const ref = _useRef(null);
  _useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timers = [];
    let cycleIv;
    const decrypt = () => {
      setPhase("open");
      let frame = 0;
      const iv = setInterval(() => {
        frame++;
        const resolved = Math.floor(frame / FRAMES * PLAIN.length);
        let out = "";
        for (let i = 0; i < PLAIN.length; i++) {
          const ch = PLAIN[i] ?? "";
          out += i < resolved ? ch : ch === " " ? " " : GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
        }
        setPayload(out);
        if (frame >= FRAMES) {
          setPayload(PLAIN);
          clearInterval(iv);
        }
      }, FRAME_MS);
      timers.push(iv);
    };
    const lock = () => {
      setPhase("locked");
      setPayload(CIPHER);
    };
    const cycle = () => {
      timers.push(setTimeout(decrypt, DECRYPT_DELAY));
      timers.push(setTimeout(lock, RELOCK_DELAY));
    };
    lock();
    cycle();
    cycleIv = setInterval(cycle, CYCLE);
    return () => {
      timers.forEach(clearTimeout);
      clearInterval(cycleIv);
    };
  }, []);
  return /*#__PURE__*/React.createElement("div", {
    className: "hero-right reveal"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vault-card win"
  }, /*#__PURE__*/React.createElement("div", {
    className: "win-bar"
  }, /*#__PURE__*/React.createElement("span", {
    className: "lights"
  }, /*#__PURE__*/React.createElement("i", null), /*#__PURE__*/React.createElement("i", null), /*#__PURE__*/React.createElement("i", null)), /*#__PURE__*/React.createElement("span", {
    className: "win-title"
  }, "<VaultGate uuid={4200} />")), /*#__PURE__*/React.createElement("div", {
    className: "vault-meta"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vault-row"
  }, /*#__PURE__*/React.createElement("span", {
    className: "k"
  }, "vault.uuid"), /*#__PURE__*/React.createElement("span", {
    className: "v"
  }, "4200")), /*#__PURE__*/React.createElement("div", {
    className: "vault-row"
  }, /*#__PURE__*/React.createElement("span", {
    className: "k"
  }, "read.condition"), /*#__PURE__*/React.createElement("span", {
    className: "v",
    style: {
      color: "var(--primary)"
    }
  }, "Subscription")), /*#__PURE__*/React.createElement("div", {
    className: "vault-row"
  }, /*#__PURE__*/React.createElement("span", {
    className: "k"
  }, "price.period"), /*#__PURE__*/React.createElement("span", {
    className: "v"
  }, "5 $IP / 30d"))), /*#__PURE__*/React.createElement("div", {
    className: "vault-body"
  }, /*#__PURE__*/React.createElement("div", {
    ref: ref,
    className: phase === "locked" ? "vault-payload locked" : "vault-payload"
  }, payload), /*#__PURE__*/React.createElement("div", {
    className: "vault-foot"
  }, /*#__PURE__*/React.createElement("span", {
    className: phase === "locked" ? "vault-status is-locked" : "vault-status is-open"
  }, phase === "locked" ? /*#__PURE__*/React.createElement(LockClosed, {
    className: "ic"
  }) : /*#__PURE__*/React.createElement(LockOpen, {
    className: "ic"
  }), /*#__PURE__*/React.createElement("span", null, phase === "locked" ? "condition not met" : "condition satisfied · decrypted")), /*#__PURE__*/React.createElement("span", {
    className: "lat"
  }, "~15s threshold read")))), /*#__PURE__*/React.createElement("div", {
    className: "vault-chip"
  }, /*#__PURE__*/React.createElement("span", {
    className: "ck"
  }, "condition()"), /*#__PURE__*/React.createElement("span", {
    style: {
      color: "var(--ink-2)"
    }
  }, "\u2192"), /*#__PURE__*/React.createElement("span", null, "checkReadCondition(uuid, \u2026)")));
}
function Hero() {
  return /*#__PURE__*/React.createElement("section", {
    className: "hero"
  }, /*#__PURE__*/React.createElement("div", {
    className: "container"
  }, /*#__PURE__*/React.createElement("div", {
    className: "hero-grid"
  }, /*#__PURE__*/React.createElement("div", {
    className: "hero-left"
  }, /*#__PURE__*/React.createElement("div", {
    className: "hero-eyebrows reveal"
  }, /*#__PURE__*/React.createElement(Badge, {
    tone: "primary"
  }, "Story Protocol \xB7 Confidential Data Rails"), /*#__PURE__*/React.createElement(Badge, {
    tone: "live"
  }, "Live on Aeneid")), /*#__PURE__*/React.createElement("h1", {
    className: "display reveal"
  }, "Ship ", /*#__PURE__*/React.createElement(EncryptedScramble, {
    final: "encrypted",
    className: "enc"
  }), ", paid,", /*#__PURE__*/React.createElement("br", null), "license-gated data."), /*#__PURE__*/React.createElement("p", {
    className: "lede hero-lede reveal"
  }, "The ", /*#__PURE__*/React.createElement("span", {
    className: "mono",
    style: {
      color: "var(--ink)"
    }
  }, "wagmi"), "-style toolkit for CDR. Install one package and gate encrypted data behind a real on-chain payment or license check \u2014 in under a minute."), /*#__PURE__*/React.createElement("div", {
    className: "hero-cta reveal"
  }, /*#__PURE__*/React.createElement(CopyLine, {
    command: "npm create cdr-kit",
    minWidth: 280
  }), /*#__PURE__*/React.createElement("a", {
    className: "btn btn-ghost",
    href: "#quickstart"
  }, "Read the docs")), /*#__PURE__*/React.createElement("div", {
    className: "hero-proof reveal"
  }, /*#__PURE__*/React.createElement("span", {
    className: "proof-item"
  }, /*#__PURE__*/React.createElement("span", {
    className: "mk"
  }, "\u2726"), /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "15"), " packages on npm"), /*#__PURE__*/React.createElement("span", {
    className: "proof-item"
  }, /*#__PURE__*/React.createElement("span", {
    className: "mk"
  }, "\u2726"), /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "99 + 7"), " Solidity tests"), /*#__PURE__*/React.createElement("span", {
    className: "proof-item"
  }, /*#__PURE__*/React.createElement("span", {
    className: "mk"
  }, "\u2726"), "MIT licensed"), /*#__PURE__*/React.createElement("span", {
    className: "proof-item"
  }, /*#__PURE__*/React.createElement("span", {
    className: "mk"
  }, "\u2726"), "CI green on ", /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "main")))), /*#__PURE__*/React.createElement(VaultCycle, null))));
}
const PACKAGES = ["@cdr-kit/react", "@cdr-kit/react-ui", "@cdr-kit/core", "@cdr-kit/agent", "@cdr-kit/story", "@cdr-kit/tools", "@cdr-kit/mcp", "@cdr-kit/cli", "@cdr-kit/contracts", "@cdr-kit/vercel-ai", "@cdr-kit/openai", "@cdr-kit/langchain", "@cdr-kit/agentkit", "@cdr-kit/goat", "create-cdr-kit-app"];
function PackageStrip() {
  return /*#__PURE__*/React.createElement("section", {
    className: "strip"
  }, /*#__PURE__*/React.createElement("div", {
    className: "container strip-inner"
  }, /*#__PURE__*/React.createElement("span", {
    className: "strip-label"
  }, "@cdr-kit \xB7 15 packages, v0.7.1"), /*#__PURE__*/React.createElement("div", {
    className: "strip-pkgs"
  }, PACKAGES.map(pkg => /*#__PURE__*/React.createElement("a", {
    key: pkg,
    className: "pkg-pill",
    href: `https://www.npmjs.com/package/${pkg}`,
    target: "_blank",
    rel: "noreferrer"
  }, pkg)))));
}
Object.assign(window, {
  Hero,
  VaultCycle,
  EncryptedScramble,
  PackageStrip
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/cdrkit-site/Hero.jsx", error: String((e && e.message) || e) }); }

// ui_kits/cdrkit-site/Icons.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* cdr-kit icon set — ported verbatim from apps/site/components/icons.tsx.
   All consume currentColor. Exported to window for cross-file use. */
const _s = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round"
};
function LockboxGlyph(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, {
    strokeWidth: 2.1
  }, p), /*#__PURE__*/React.createElement("rect", {
    x: "4",
    y: "10.5",
    width: "16",
    height: "10",
    rx: "2"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M8 10.5V7a4 4 0 0 1 8 0v3.5"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "15",
    r: "1.3",
    fill: "currentColor",
    stroke: "none"
  }));
}
function LockClosed(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("rect", {
    x: "5",
    y: "11",
    width: "14",
    height: "10",
    rx: "2"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M8 11V7a4 4 0 0 1 8 0v4"
  }));
}
function LockOpen(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("rect", {
    x: "5",
    y: "11",
    width: "14",
    height: "10",
    rx: "2"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M8 11V7a4 4 0 0 1 8 0"
  }));
}
function Npm(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24",
    fill: "currentColor"
  }, p), /*#__PURE__*/React.createElement("path", {
    d: "M2 5h20v13H12v2H7v-2H2V5zm2 2v9h3V9h2v7h2V7H4zm9 0v9h3V9h2v7h1V7h-6z"
  }));
}
function Github(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24",
    fill: "currentColor"
  }, p), /*#__PURE__*/React.createElement("path", {
    d: "M12 1.5A10.5 10.5 0 0 0 8.7 22c.5.1.7-.2.7-.5v-1.8c-2.9.6-3.5-1.4-3.5-1.4-.5-1.2-1.2-1.5-1.2-1.5-.9-.6.1-.6.1-.6 1 .1 1.6 1 1.6 1 .9 1.6 2.4 1.1 3 .9.1-.7.4-1.1.6-1.4-2.3-.3-4.7-1.2-4.7-5.1 0-1.1.4-2 1-2.7-.1-.3-.5-1.3.1-2.7 0 0 .9-.3 2.8 1a9.6 9.6 0 0 1 5 0c1.9-1.3 2.8-1 2.8-1 .6 1.4.2 2.4.1 2.7.7.7 1 1.6 1 2.7 0 3.9-2.4 4.8-4.7 5.1.4.3.7.9.7 1.9v2.8c0 .3.2.6.7.5A10.5 10.5 0 0 0 12 1.5z"
  }));
}
function Sun(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "12",
    r: "4.2"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
  }));
}
function Moon(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("path", {
    d: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"
  }));
}
function Copy(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("rect", {
    x: "9",
    y: "9",
    width: "11",
    height: "11",
    rx: "2"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M5 15V5a2 2 0 0 1 2-2h10"
  }));
}
function ExternalLink(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("path", {
    d: "M14 4h6v6"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M10 14L20 4"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M20 14v6H4V4h6"
  }));
}
function Check(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("path", {
    d: "M4 12l5 5 11-11"
  }));
}
function ArrowRight(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("path", {
    d: "M5 12h14M13 6l6 6-6 6"
  }));
}
function KeyRound(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("circle", {
    cx: "8",
    cy: "15",
    r: "4"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M11 12l9-9 3 3-3 3 2 2-3 3"
  }));
}
function Search(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 24 24"
  }, _s, p), /*#__PURE__*/React.createElement("circle", {
    cx: "11",
    cy: "11",
    r: "7"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M21 21l-4-4"
  }));
}
function ChevDown(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 12 12",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, p), /*#__PURE__*/React.createElement("path", {
    d: "M3 5l3 3 3-3"
  }));
}
/* cdr-kit brand mark — "Vault-Rail". Strokes use currentColor (ink/cream per
   theme); the payload dot is always brand amber. */
function CdrMark(p) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    viewBox: "0 0 32 32",
    fill: "none"
  }, p), /*#__PURE__*/React.createElement("line", {
    x1: "1.5",
    y1: "16",
    x2: "30.5",
    y2: "16",
    stroke: "currentColor",
    strokeWidth: "2.6",
    strokeLinecap: "round"
  }), /*#__PURE__*/React.createElement("rect", {
    x: "7",
    y: "7",
    width: "18",
    height: "18",
    rx: "5.2",
    stroke: "currentColor",
    strokeWidth: "2.6"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "16",
    cy: "16",
    r: "2.8",
    fill: "var(--primary)"
  }));
}
Object.assign(window, {
  LockboxGlyph,
  LockClosed,
  LockOpen,
  Npm,
  Github,
  Sun,
  Moon,
  Copy,
  ExternalLink,
  Check,
  ArrowRight,
  KeyRound,
  Search,
  ChevDown,
  CdrMark
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/cdrkit-site/Icons.jsx", error: String((e && e.message) || e) }); }

// ui_kits/cdrkit-site/Interactive.jsx
try { (() => {
/* Interactive landing sections — Quickstart (InstallTabs) + AgentTerminal.
   AgentTerminal types a scripted autonomous-agent run, ported from
   apps/site/components/landing/agent-terminal.tsx. */
const {
  useState: useS,
  useEffect: useE,
  useRef: useR
} = React;
const PM_COMMANDS = {
  npm: "npm i @cdr-kit/react @cdr-kit/core wagmi viem",
  pnpm: "pnpm add @cdr-kit/react @cdr-kit/core wagmi viem",
  bun: "bun add @cdr-kit/react @cdr-kit/core wagmi viem"
};
function InstallTabs() {
  const [pm, setPm] = useS("pnpm");
  const parts = PM_COMMANDS[pm].split(" ");
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    className: "qs-tabbar"
  }, /*#__PURE__*/React.createElement("div", {
    className: "tabs",
    role: "tablist"
  }, Object.keys(PM_COMMANDS).map(k => /*#__PURE__*/React.createElement("button", {
    key: k,
    type: "button",
    role: "tab",
    "aria-selected": pm === k,
    className: "tab",
    onClick: () => setPm(k)
  }, k))), /*#__PURE__*/React.createElement(CopyButton, {
    value: PM_COMMANDS[pm]
  })), /*#__PURE__*/React.createElement("div", {
    className: "code"
  }, /*#__PURE__*/React.createElement("pre", null, /*#__PURE__*/React.createElement("code", null, /*#__PURE__*/React.createElement("span", {
    className: "tok-punc"
  }, "$"), " ", parts[0], " ", parts[1], " ", /*#__PURE__*/React.createElement("span", {
    className: "tok-str"
  }, "@cdr-kit/react @cdr-kit/core"), " wagmi viem"))));
}
function Quickstart() {
  return /*#__PURE__*/React.createElement("section", {
    className: "section",
    id: "quickstart",
    style: {
      borderTop: "1px solid var(--line)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "container"
  }, /*#__PURE__*/React.createElement("div", {
    className: "qs-grid"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "sec-head reveal",
    style: {
      marginBottom: 32
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "eyebrow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "tick"
  }, "\u259A"), "Quickstart"), /*#__PURE__*/React.createElement("h2", {
    className: "h-sec"
  }, "Gated encrypted data", /*#__PURE__*/React.createElement("br", null), "in under 60 seconds.")), /*#__PURE__*/React.createElement("ol", {
    className: "qs-steps reveal"
  }, /*#__PURE__*/React.createElement("li", {
    className: "qs-step"
  }, /*#__PURE__*/React.createElement("span", {
    className: "n"
  }, "1"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h4", null, "Install the React layer"), /*#__PURE__*/React.createElement("p", null, "One package pulls in the typed core SDK and the provider."))), /*#__PURE__*/React.createElement("li", {
    className: "qs-step"
  }, /*#__PURE__*/React.createElement("span", {
    className: "n"
  }, "2"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h4", null, "Wrap your app in ", /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "<CdrProvider>")), /*#__PURE__*/React.createElement("p", null, "Pass a wagmi config + API URL to go live, or a mock kit for local dev."))), /*#__PURE__*/React.createElement("li", {
    className: "qs-step"
  }, /*#__PURE__*/React.createElement("span", {
    className: "n"
  }, "3"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h4", null, "Drop in ", /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "<VaultGate>")), /*#__PURE__*/React.createElement("p", null, "It checks the on-chain condition, releases key shares, and hands you the decrypted bytes."))))), /*#__PURE__*/React.createElement("div", {
    className: "qs-panel reveal"
  }, /*#__PURE__*/React.createElement("div", {
    className: "win"
  }, /*#__PURE__*/React.createElement(InstallTabs, null), /*#__PURE__*/React.createElement("hr", {
    className: "rule"
  }), /*#__PURE__*/React.createElement("div", {
    className: "code"
  }, /*#__PURE__*/React.createElement("pre", null, /*#__PURE__*/React.createElement("code", null, /*#__PURE__*/React.createElement("span", {
    className: "tok-key"
  }, "import"), " ", "{ CdrProvider, VaultGate }", " ", /*#__PURE__*/React.createElement("span", {
    className: "tok-key"
  }, "from"), " ", /*#__PURE__*/React.createElement("span", {
    className: "tok-str"
  }, "\"@cdr-kit/react\""), ";", "\n\n", /*#__PURE__*/React.createElement("span", {
    className: "tok-punc"
  }, "<"), /*#__PURE__*/React.createElement("span", {
    className: "tok-fn"
  }, "CdrProvider"), " config=", "{wagmiConfig}", " apiUrl=", "{apiUrl}", /*#__PURE__*/React.createElement("span", {
    className: "tok-punc"
  }, ">"), "\n  ", /*#__PURE__*/React.createElement("span", {
    className: "tok-punc"
  }, "<"), /*#__PURE__*/React.createElement("span", {
    className: "tok-fn"
  }, "VaultGate"), " uuid=", "{", /*#__PURE__*/React.createElement("span", {
    className: "tok-num"
  }, "4200"), "}", " auto", "\n    ", "fallback=", "{", /*#__PURE__*/React.createElement("span", {
    className: "tok-punc"
  }, "<"), /*#__PURE__*/React.createElement("span", {
    className: "tok-fn"
  }, "SubscribeButton"), " /", /*#__PURE__*/React.createElement("span", {
    className: "tok-punc"
  }, ">"), "}", /*#__PURE__*/React.createElement("span", {
    className: "tok-punc"
  }, ">"), "\n    ", "{(data) => ", /*#__PURE__*/React.createElement("span", {
    className: "tok-punc"
  }, "<"), "pre", /*#__PURE__*/React.createElement("span", {
    className: "tok-punc"
  }, ">"), "{", /*#__PURE__*/React.createElement("span", {
    className: "tok-key"
  }, "new"), " ", /*#__PURE__*/React.createElement("span", {
    className: "tok-fn"
  }, "TextDecoder"), "().", /*#__PURE__*/React.createElement("span", {
    className: "tok-fn"
  }, "decode"), "(data)", "}", /*#__PURE__*/React.createElement("span", {
    className: "tok-punc"
  }, "</"), "pre", /*#__PURE__*/React.createElement("span", {
    className: "tok-punc"
  }, ">"), "}", "\n  ", /*#__PURE__*/React.createElement("span", {
    className: "tok-punc"
  }, "</"), /*#__PURE__*/React.createElement("span", {
    className: "tok-fn"
  }, "VaultGate"), /*#__PURE__*/React.createElement("span", {
    className: "tok-punc"
  }, ">"), "\n", /*#__PURE__*/React.createElement("span", {
    className: "tok-punc"
  }, "</"), /*#__PURE__*/React.createElement("span", {
    className: "tok-fn"
  }, "CdrProvider"), /*#__PURE__*/React.createElement("span", {
    className: "tok-punc"
  }, ">"), "\n", /*#__PURE__*/React.createElement("span", {
    className: "tok-com"
  }, "// → renders the decrypted payload once the condition is satisfied")))))))));
}
const SCRIPT = [{
  html: '<span class="pmt">›</span> <span class="cmd">pnpm --filter cdr-kit-example-vercel-ai-chatbot start</span>',
  delay: 60
}, {
  html: "agent online · model=claude · wallet=0x9f…a3c1 · chain=aeneid",
  delay: 320
}, {
  html: '⚙ <span class="tool">cdr_discover_vaults</span> { intent: "trading signal" }',
  delay: 460
}, {
  html: "  → 3 vaults · matched uuid 4200  (Subscription · 5 $IP/30d)",
  delay: 320
}, {
  html: '⚙ <span class="tool">cdr_subscribe_and_access</span> { uuid: 4200, periods: 1 }',
  delay: 460
}, {
  html: "  → tx 0x4e…b1 confirmed · paid 5 $IP · collecting key shares…",
  delay: 460
}, {
  html: '  ✓ threshold met (7/10 shares) · payload decrypted locally',
  delay: 380,
  cls: "ok"
}, {
  html: '  signal: { "BUY": "ETH/USD", confidence: 0.86 }',
  delay: 340,
  cls: "acc"
}, {
  html: "&nbsp;",
  delay: 80,
  spacer: true
}, {
  html: '<span class="pmt">›</span> <span class="cmd">Decision:</span> <span class="ok">BUY ETH/USD</span> — confidence 0.86, acting on signal.',
  delay: 60
}, {
  html: '<span class="ok">●</span> <span class="dim">loop complete · no human in the loop · 28.4s</span>',
  delay: 0
}];
const TYPE_MS = 13,
  RESTART_MS = 5200;
const stripTags = h => h.replace(/<[^>]+>/g, "");
const wait = ms => new Promise(r => setTimeout(r, ms));
function AgentTerminal() {
  const [lines, setLines] = useS([]);
  const ref = useR(null);
  const [inView, setInView] = useS(false);
  useE(() => {
    const node = ref.current;
    if (!node) return;
    const io = new IntersectionObserver(es => es.forEach(e => e.isIntersecting && setInView(true)), {
      threshold: 0.3
    });
    io.observe(node);
    return () => io.disconnect();
  }, []);
  useE(() => {
    if (!inView) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let cancelled = false;
    (async () => {
      while (!cancelled) {
        setLines([]);
        for (const item of SCRIPT) {
          if (cancelled) return;
          if (item.spacer) {
            setLines(p => [...p, {
              html: item.html
            }]);
            await wait(item.delay);
            continue;
          }
          if (reduce) {
            setLines(p => [...p, {
              html: item.html
            }]);
          } else {
            const plain = stripTags(item.html);
            setLines(p => [...p, {
              partial: ""
            }]);
            for (let n = 1; n <= plain.length; n++) {
              if (cancelled) return;
              await wait(TYPE_MS);
              setLines(p => {
                const nx = p.slice();
                nx[nx.length - 1] = {
                  partial: plain.slice(0, n)
                };
                return nx;
              });
            }
            setLines(p => {
              const nx = p.slice();
              nx[nx.length - 1] = {
                html: item.html
              };
              return nx;
            });
          }
          await wait(item.delay);
        }
        await wait(RESTART_MS);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [inView]);
  return /*#__PURE__*/React.createElement("div", {
    className: "term",
    ref: ref
  }, /*#__PURE__*/React.createElement("div", {
    className: "term-bar"
  }, /*#__PURE__*/React.createElement("span", {
    className: "lights"
  }, /*#__PURE__*/React.createElement("i", null), /*#__PURE__*/React.createElement("i", null), /*#__PURE__*/React.createElement("i", null)), /*#__PURE__*/React.createElement("span", {
    className: "tt"
  }, "cdr-kit-example-vercel-ai-chatbot"), /*#__PURE__*/React.createElement("span", {
    className: "runtag"
  }, /*#__PURE__*/React.createElement("span", {
    className: "dot"
  }), "live \xB7 aeneid")), /*#__PURE__*/React.createElement("div", {
    className: "term-body"
  }, lines.map((line, i) => {
    const isLast = i === lines.length - 1;
    if (line.partial !== undefined) return /*#__PURE__*/React.createElement("div", {
      key: i,
      className: "term-line"
    }, line.partial, isLast && /*#__PURE__*/React.createElement("span", {
      className: "term-cursor"
    }));
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      className: "term-line",
      dangerouslySetInnerHTML: {
        __html: line.html + (isLast ? '<span class="term-cursor"></span>' : "")
      }
    });
  })));
}
function AgentSection() {
  return /*#__PURE__*/React.createElement("section", {
    className: "section agent",
    id: "agent"
  }, /*#__PURE__*/React.createElement("div", {
    className: "container"
  }, /*#__PURE__*/React.createElement("div", {
    className: "agent-grid"
  }, /*#__PURE__*/React.createElement("div", {
    className: "reveal"
  }, /*#__PURE__*/React.createElement("span", {
    className: "eyebrow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "tick"
  }, "\u259A"), "Autonomous agents"), /*#__PURE__*/React.createElement("h2", {
    className: "h-sec",
    style: {
      marginTop: 16
    }
  }, "An agent that pays", /*#__PURE__*/React.createElement("br", null), "for its own data."), /*#__PURE__*/React.createElement("ul", {
    className: "agent-points"
  }, /*#__PURE__*/React.createElement("li", null, /*#__PURE__*/React.createElement("span", {
    className: "mk"
  }, "\u2726"), /*#__PURE__*/React.createElement("span", null, /*#__PURE__*/React.createElement("b", null, "Discover"), " vaults by intent, then ", /*#__PURE__*/React.createElement("b", null, "subscribe + access"), " \u2014 the agent signs and pays from its own wallet.")), /*#__PURE__*/React.createElement("li", null, /*#__PURE__*/React.createElement("span", {
    className: "mk"
  }, "\u2726"), /*#__PURE__*/React.createElement("span", null, /*#__PURE__*/React.createElement("b", null, "34 tools"), " wired through one source into MCP and all five framework adapters.")), /*#__PURE__*/React.createElement("li", null, /*#__PURE__*/React.createElement("span", {
    className: "mk"
  }, "\u2726"), /*#__PURE__*/React.createElement("span", null, "Decrypts locally once the threshold is met \u2014 ", /*#__PURE__*/React.createElement("b", null, "no human in the loop"), ".")))), /*#__PURE__*/React.createElement("div", {
    className: "reveal"
  }, /*#__PURE__*/React.createElement(AgentTerminal, null)))));
}
Object.assign(window, {
  Quickstart,
  InstallTabs,
  AgentTerminal,
  AgentSection
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/cdrkit-site/Interactive.jsx", error: String((e && e.message) || e) }); }

// ui_kits/cdrkit-site/Sections.jsx
try { (() => {
/* Landing sections — Pillars, Conditions, Proof, Why, CtaBand.
   Addresses are the real verified Aeneid (chain 1315) deployments. */

const AENEID = {
  cdrKitVault: "0xac592f165D8dD1f27A087bdB39c0b2f619FF6C8C",
  subscriptionCondition: "0xB75Cc6571ac7E0ee30A519192740fc471e187458",
  tierGateCondition: "0xdA704Faf61b2FFB37205d7Eb8C1D26BD3090455f",
  composableCondition: "0x74F2f94e7867b07ECDFbcc667050CBec1dE2800B",
  creatorWriteCondition: "0x85CEB332445ca1d3D1975d6929cA6BED25195b2F",
  openCondition: "0x36fB2e2d10efd1E905b7779A684F34B9c775b62B",
  timeWindowCondition: "0x67911435F262e7e4EC4F7FEB4e868a67b9dd90b1",
  deadManSwitchCondition: "0x37226f97e184843aB0b8d4f08A55969801B97766",
  conditionalEscrowCondition: "0x7fcDe02DB7c14fD3587aB2fED064a1D8355b7584",
  multiSigCondition: "0x3A0Cf72f167A2c1f5a7A5025eb36219f28C20FCd"
};
const trunc = a => `${a.slice(0, 8)}…${a.slice(-6)}`;
const PILLARS = [{
  no: "01",
  tag: "@cdr-kit/react",
  title: "React layer",
  desc: /*#__PURE__*/React.createElement(React.Fragment, null, "Drop a ", /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "<VaultGate>"), " around encrypted data. Hooks, a Clerk-style ", /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "<Vault>"), " compound, and a mock mode so you can build UI with no wallet or chain."),
  mini: /*#__PURE__*/React.createElement(React.Fragment, null, "useAccessVault()", /*#__PURE__*/React.createElement("br", null), "useSubscribeAndAccess()", /*#__PURE__*/React.createElement("br", null), "<VaultGate /> \xB7 <Vault.Unlocked />"),
  cta: "Component showcase"
}, {
  no: "02",
  tag: "@cdr-kit/agent",
  title: "Autonomous agent kit",
  desc: /*#__PURE__*/React.createElement(React.Fragment, null, "An LLM agent that buys data with its own wallet \u2014 discover, pay, decrypt, decide. Five framework adapters plus an MCP server."),
  mini: /*#__PURE__*/React.createElement(React.Fragment, null, "agent.discover()", /*#__PURE__*/React.createElement("br", null), "agent.subscribeAndAccess()", /*#__PURE__*/React.createElement("br", null), "vercel-ai \xB7 openai \xB7 langchain \xB7 goat"),
  cta: "See the agent loop"
}, {
  no: "03",
  tag: "contracts/",
  title: "Condition library",
  desc: /*#__PURE__*/React.createElement(React.Fragment, null, "A standard library of tested Solidity conditions \u2014 Subscription, TierGate, Composable \u2014 plus the ", /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "CdrKitVault"), " factory that mints, registers IP, and gates in one tx."),
  mini: /*#__PURE__*/React.createElement(React.Fragment, null, "SubscriptionCondition", /*#__PURE__*/React.createElement("br", null), "TierGateCondition \xB7 Composable", /*#__PURE__*/React.createElement("br", null), "CdrKitVault.create()"),
  cta: "Browse conditions"
}];
function Pillars() {
  return /*#__PURE__*/React.createElement("section", {
    className: "section",
    id: "pillars"
  }, /*#__PURE__*/React.createElement("div", {
    className: "container"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-head reveal"
  }, /*#__PURE__*/React.createElement("span", {
    className: "eyebrow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "tick"
  }, "\u259A"), "Three pillars, one kit"), /*#__PURE__*/React.createElement("h2", {
    className: "h-sec"
  }, "Not one feature \u2014 a toolkit over CDR."), /*#__PURE__*/React.createElement("p", {
    className: "lede"
  }, "Encryption stays in CDR. Payments stay in Story's IP layer. cdr-kit wires them together ergonomically across React, autonomous agents, and Solidity.")), /*#__PURE__*/React.createElement("div", {
    className: "pillars"
  }, PILLARS.map(p => /*#__PURE__*/React.createElement("article", {
    key: p.no,
    className: "pillar card reveal"
  }, /*#__PURE__*/React.createElement("div", {
    className: "pillar-no"
  }, /*#__PURE__*/React.createElement("span", null, p.no), /*#__PURE__*/React.createElement("span", {
    className: "tag"
  }, p.tag)), /*#__PURE__*/React.createElement("h3", {
    className: "h-card"
  }, p.title), /*#__PURE__*/React.createElement("p", {
    className: "p-desc"
  }, p.desc), /*#__PURE__*/React.createElement("div", {
    className: "mini-code"
  }, p.mini), /*#__PURE__*/React.createElement("a", {
    className: "p-link",
    href: "#quickstart"
  }, p.cta, " ", /*#__PURE__*/React.createElement(ArrowRight, null)))))));
}
function CondRow({
  name,
  highlight,
  badge,
  badgeTone = "live",
  address,
  children
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "cond"
  }, /*#__PURE__*/React.createElement("div", {
    className: "cond-top"
  }, /*#__PURE__*/React.createElement("span", {
    className: "cond-name",
    style: highlight ? {
      color: "var(--primary)"
    } : undefined
  }, name), badge ? /*#__PURE__*/React.createElement(Badge, {
    tone: badgeTone
  }, badge) : null), /*#__PURE__*/React.createElement("p", null, children), /*#__PURE__*/React.createElement("span", {
    className: "addr"
  }, address));
}
function Conditions() {
  return /*#__PURE__*/React.createElement("section", {
    className: "section",
    id: "conditions"
  }, /*#__PURE__*/React.createElement("div", {
    className: "container"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-head reveal"
  }, /*#__PURE__*/React.createElement("span", {
    className: "eyebrow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "tick"
  }, "\u259A"), "Condition standard library"), /*#__PURE__*/React.createElement("h2", {
    className: "h-sec"
  }, "Composable access rules,", /*#__PURE__*/React.createElement("br", null), "deployed and tested."), /*#__PURE__*/React.createElement("p", {
    className: "lede"
  }, "Every vault's read & write access is a ", /*#__PURE__*/React.createElement("span", {
    className: "mono",
    style: {
      color: "var(--ink)"
    }
  }, "view"), " function the validator network calls. cdr-kit ships a standard library \u2014 typed, tested, and addressed in ", /*#__PURE__*/React.createElement("span", {
    className: "mono",
    style: {
      color: "var(--ink)"
    }
  }, "@cdr-kit/contracts"), ".")), /*#__PURE__*/React.createElement("div", {
    className: "cond-list reveal"
  }, /*#__PURE__*/React.createElement(CondRow, {
    name: "SubscriptionCondition",
    highlight: true,
    badge: "deployed",
    address: AENEID.subscriptionCondition
  }, "Recurring paid access \u2014 price per period, period length, payee, native-IP or WIP-royalty mode."), /*#__PURE__*/React.createElement(CondRow, {
    name: "TierGateCondition",
    badge: "deployed",
    address: AENEID.tierGateCondition
  }, "Gate by a held Story IP license-token tier. License-aware access, natively on chain."), /*#__PURE__*/React.createElement(CondRow, {
    name: "ComposableCondition",
    badge: "deployed",
    address: AENEID.composableCondition
  }, "Boolean AND / OR over child conditions, up to 8 deep. Subscription ", /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "OR"), " tier, royalty ", /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "AND"), " license."), /*#__PURE__*/React.createElement(CondRow, {
    name: "CreatorWrite / Open",
    badge: "deployed",
    address: `${trunc(AENEID.creatorWriteCondition)} · ${trunc(AENEID.openCondition)}`
  }, "Gate writes to the vault creator, or open access as a sanity / fallback condition."), /*#__PURE__*/React.createElement(CondRow, {
    name: "CdrKitVault",
    highlight: true,
    badge: "factory",
    badgeTone: "primary",
    address: AENEID.cdrKitVault
  }, "One tx: mint the vault NFT, register it as Story IP, allocate the CDR slot, set the read condition, attach PIL terms."), /*#__PURE__*/React.createElement(CondRow, {
    name: "TimeWindowCondition",
    address: AENEID.timeWindowCondition
  }, "Reads gated to an absolute ", /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "[startTs, endTs]"), " window. Release-on-date drops, embargoes, time-bound previews."), /*#__PURE__*/React.createElement(CondRow, {
    name: "DeadManSwitchCondition",
    address: AENEID.deadManSwitchCondition
  }, "Auto-unlock to heirs (or public) if the creator stops ", /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "poke()"), "-ing within ", /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "duration"), "."), /*#__PURE__*/React.createElement(CondRow, {
    name: "ConditionalEscrowCondition",
    address: AENEID.conditionalEscrowCondition
  }, "Buyer pays \u2192 confirms delivery \u2192 seller is paid + buyer reads. Optional arbiter for disputes."), /*#__PURE__*/React.createElement(CondRow, {
    name: "MultiSigCondition",
    highlight: true,
    address: AENEID.multiSigCondition
  }, "N-of-M with ", /*#__PURE__*/React.createElement("b", null, "two parallel approval paths"), ": off-chain EIP-712 sigs (gas-free) OR on-chain ", /*#__PURE__*/React.createElement("span", {
    className: "mono"
  }, "approve(uuid, epoch)"), ". First-of-kind in the CDR ecosystem."))));
}
function Stat({
  number,
  unit,
  label
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "stat card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num"
  }, number, unit && /*#__PURE__*/React.createElement("span", {
    className: "u"
  }, unit)), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, label));
}
const DEPLOY_ROWS = [["CdrKitVault", AENEID.cdrKitVault], ["SubscriptionCondition", AENEID.subscriptionCondition], ["TierGateCondition", AENEID.tierGateCondition], ["ComposableCondition", AENEID.composableCondition]];
function Proof() {
  return /*#__PURE__*/React.createElement("section", {
    className: "section proof",
    id: "live"
  }, /*#__PURE__*/React.createElement("div", {
    className: "container"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-head reveal"
  }, /*#__PURE__*/React.createElement("span", {
    className: "eyebrow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "tick"
  }, "\u259A"), "Proof, not a slide deck"), /*#__PURE__*/React.createElement("h2", {
    className: "h-sec"
  }, "Live on Aeneid."), /*#__PURE__*/React.createElement("p", {
    className: "lede"
  }, "Story's testnet \u2014 chain id ", /*#__PURE__*/React.createElement("span", {
    className: "mono",
    style: {
      color: "var(--ink)"
    }
  }, "1315"), ". Contracts verified; end-to-end encrypt\u2192write\u2192read\u2192decrypt round-trips confirmed on real chain.")), /*#__PURE__*/React.createElement("div", {
    className: "stat-grid reveal",
    style: {
      marginBottom: 34
    }
  }, /*#__PURE__*/React.createElement(Stat, {
    number: "15",
    label: "packages published to npm"
  }), /*#__PURE__*/React.createElement(Stat, {
    number: "9",
    label: "condition contracts deployed"
  }), /*#__PURE__*/React.createElement(Stat, {
    number: "~15",
    unit: "s",
    label: "typical threshold read latency"
  }), /*#__PURE__*/React.createElement(Stat, {
    number: "99+7",
    label: "Solidity tests passing"
  })), /*#__PURE__*/React.createElement("div", {
    className: "deploy-table reveal"
  }, /*#__PURE__*/React.createElement("div", {
    className: "deploy-row",
    style: {
      background: "var(--paper-2)"
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "dn",
    style: {
      color: "var(--ink-3)"
    }
  }, "contract"), /*#__PURE__*/React.createElement("span", {
    className: "da",
    style: {
      color: "var(--ink-3)"
    }
  }, "address (aeneid \xB7 1315)"), /*#__PURE__*/React.createElement("span", {
    className: "dx",
    style: {
      color: "var(--ink-3)"
    }
  }, "explorer")), DEPLOY_ROWS.map(([name, address]) => /*#__PURE__*/React.createElement("div", {
    className: "deploy-row",
    key: name
  }, /*#__PURE__*/React.createElement("span", {
    className: "dn"
  }, name), /*#__PURE__*/React.createElement("span", {
    className: "da"
  }, address), /*#__PURE__*/React.createElement("a", {
    className: "dx",
    href: `https://aeneid.storyscan.xyz/address/${address}`,
    target: "_blank",
    rel: "noreferrer"
  }, "view ", /*#__PURE__*/React.createElement(ExternalLink, null)))))));
}
function Why() {
  return /*#__PURE__*/React.createElement("section", {
    className: "section",
    id: "why"
  }, /*#__PURE__*/React.createElement("div", {
    className: "container"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-head reveal"
  }, /*#__PURE__*/React.createElement("span", {
    className: "eyebrow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "tick"
  }, "\u259A"), "Why cdr-kit"), /*#__PURE__*/React.createElement("h2", {
    className: "h-sec"
  }, "Honest about the wedge.")), /*#__PURE__*/React.createElement("div", {
    className: "why-grid"
  }, /*#__PURE__*/React.createElement("article", {
    className: "why-card card reveal"
  }, /*#__PURE__*/React.createElement("div", {
    className: "wk"
  }, "vs. Lit / TACo"), /*#__PURE__*/React.createElement("h3", null, "The Story IP coupling"), /*#__PURE__*/React.createElement("p", null, "CDR's threshold encryption is commodity. The edge is what it composes with \u2014 a read condition can require a license tier, a subscription, or a royalty payment, natively, on the same chain.")), /*#__PURE__*/React.createElement("article", {
    className: "why-card card reveal"
  }, /*#__PURE__*/React.createElement("div", {
    className: "wk"
  }, "vs. Story's cdr-demo"), /*#__PURE__*/React.createElement("h3", null, "Productization, not a demo"), /*#__PURE__*/React.createElement("p", null, "Story's reference ships ~9 app-internal demo contracts. cdr-kit turns them into a standard, installable, tested, typed library \u2014 and adds advanced conditions (", /*#__PURE__*/React.createElement("code", null, "Subscription"), ", ", /*#__PURE__*/React.createElement("code", null, "TierGate"), ", ", /*#__PURE__*/React.createElement("code", null, "Composable"), ") that exist nowhere else.")), /*#__PURE__*/React.createElement("article", {
    className: "why-card card reveal"
  }, /*#__PURE__*/React.createElement("div", {
    className: "wk"
  }, "what it is not"), /*#__PURE__*/React.createElement("h3", null, "A library, not a SaaS"), /*#__PURE__*/React.createElement("p", null, "No account, no hosted dashboard, no \"sign up.\" You install npm packages and own your stack. cdr-kit sits ", /*#__PURE__*/React.createElement("em", null, "on top of"), " Story Protocol and CDR \u2014 it doesn't replace them.")))));
}
function CtaBand() {
  return /*#__PURE__*/React.createElement("section", {
    className: "section"
  }, /*#__PURE__*/React.createElement("div", {
    className: "container"
  }, /*#__PURE__*/React.createElement("div", {
    className: "cta-band reveal"
  }, /*#__PURE__*/React.createElement("h2", {
    className: "display"
  }, "Gate your first vault."), /*#__PURE__*/React.createElement("p", {
    className: "lede",
    style: {
      maxWidth: 460,
      margin: "0 auto"
    }
  }, "One command scaffolds a Next.js app wired to a live Aeneid vault. No billing infra, no key management."), /*#__PURE__*/React.createElement(CopyLine, {
    command: "npm create cdr-kit"
  }))));
}
Object.assign(window, {
  Pillars,
  Conditions,
  Proof,
  Why,
  CtaBand
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/cdrkit-site/Sections.jsx", error: String((e && e.message) || e) }); }

// video/animations.jsx
try { (() => {
// @ds-adherence-ignore -- omelette starter scaffold (raw elements/hex/px by design)

/* BEGIN USAGE */
// animations.jsx
// Reusable animation starter: Stage, Timeline, Sprite, easing helpers.
// Exports (to window): Stage, Sprite, PlaybackBar, TextSprite, ImageSprite, RectSprite,
//   useTime, useTimeline, useSprite, Easing, interpolate, animate, clamp.
//
// Usage (in an HTML file that loads React + Babel):
//
//   <Stage width={1280} height={720} duration={10} background="#f6f4ef">
//     <MyScene />
//   </Stage>
//
// <Stage> auto-scales to the viewport and provides the scrubber, play/pause,
// ←/→ seek, space, and 0-to-reset controls, and persists the playhead.
// Inside <Stage>, any child can call useTime() to read the current
// playhead (seconds). Or wrap content in <Sprite start={1} end={4}>...</Sprite>
// to only render during that window -- children receive a `localTime` and
// `progress` via the useSprite() hook. Use Easing + interpolate()/animate()
// for tweens; TextSprite / ImageSprite / RectSprite have built-in entry/exit.
// Build YOUR scenes by composing Sprites inside a Stage.
/* END USAGE */
// ─────────────────────────────────────────────────────────────────────────────

// ── Easing functions (hand-rolled, Popmotion-style) ─────────────────────────
// All easings take t ∈ [0,1] and return eased t ∈ [0,1] (may overshoot for back/elastic).
const Easing = {
  linear: t => t,
  // Quad
  easeInQuad: t => t * t,
  easeOutQuad: t => t * (2 - t),
  easeInOutQuad: t => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,
  // Cubic
  easeInCubic: t => t * t * t,
  easeOutCubic: t => --t * t * t + 1,
  easeInOutCubic: t => t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1,
  // Quart
  easeInQuart: t => t * t * t * t,
  easeOutQuart: t => 1 - --t * t * t * t,
  easeInOutQuart: t => t < 0.5 ? 8 * t * t * t * t : 1 - 8 * --t * t * t * t,
  // Expo
  easeInExpo: t => t === 0 ? 0 : Math.pow(2, 10 * (t - 1)),
  easeOutExpo: t => t === 1 ? 1 : 1 - Math.pow(2, -10 * t),
  easeInOutExpo: t => {
    if (t === 0) return 0;
    if (t === 1) return 1;
    if (t < 0.5) return 0.5 * Math.pow(2, 20 * t - 10);
    return 1 - 0.5 * Math.pow(2, -20 * t + 10);
  },
  // Sine
  easeInSine: t => 1 - Math.cos(t * Math.PI / 2),
  easeOutSine: t => Math.sin(t * Math.PI / 2),
  easeInOutSine: t => -(Math.cos(Math.PI * t) - 1) / 2,
  // Back (overshoot)
  easeOutBack: t => {
    const c1 = 1.70158,
      c3 = c1 + 1;
    return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
  },
  easeInBack: t => {
    const c1 = 1.70158,
      c3 = c1 + 1;
    return c3 * t * t * t - c1 * t * t;
  },
  easeInOutBack: t => {
    const c1 = 1.70158,
      c2 = c1 * 1.525;
    return t < 0.5 ? Math.pow(2 * t, 2) * ((c2 + 1) * 2 * t - c2) / 2 : (Math.pow(2 * t - 2, 2) * ((c2 + 1) * (t * 2 - 2) + c2) + 2) / 2;
  },
  // Elastic
  easeOutElastic: t => {
    const c4 = 2 * Math.PI / 3;
    if (t === 0) return 0;
    if (t === 1) return 1;
    return Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1;
  }
};

// ── Core interpolation helpers ──────────────────────────────────────────────

// Clamp a value to [min, max]
const clamp = (v, min, max) => Math.max(min, Math.min(max, v));

// interpolate([0, 0.5, 1], [0, 100, 50], ease?) -> fn(t)
// Popmotion-style: linearly maps t across input keyframes to output values,
// with optional easing per segment (single fn or array of fns).
function interpolate(input, output, ease = Easing.linear) {
  return t => {
    if (t <= input[0]) return output[0];
    if (t >= input[input.length - 1]) return output[output.length - 1];
    for (let i = 0; i < input.length - 1; i++) {
      if (t >= input[i] && t <= input[i + 1]) {
        const span = input[i + 1] - input[i];
        const local = span === 0 ? 0 : (t - input[i]) / span;
        const easeFn = Array.isArray(ease) ? ease[i] || Easing.linear : ease;
        const eased = easeFn(local);
        return output[i] + (output[i + 1] - output[i]) * eased;
      }
    }
    return output[output.length - 1];
  };
}

// animate({from, to, start, end, ease})(t) — simpler single-segment tween.
// Returns `from` before `start`, `to` after `end`.
function animate({
  from = 0,
  to = 1,
  start = 0,
  end = 1,
  ease = Easing.easeInOutCubic
}) {
  return t => {
    if (t <= start) return from;
    if (t >= end) return to;
    const local = (t - start) / (end - start);
    return from + (to - from) * ease(local);
  };
}

// ── Timeline context ────────────────────────────────────────────────────────

const TimelineContext = React.createContext({
  time: 0,
  duration: 10,
  playing: false
});
const useTime = () => React.useContext(TimelineContext).time;
const useTimeline = () => React.useContext(TimelineContext);

// ── Sprite ──────────────────────────────────────────────────────────────────
// Renders children only when the playhead is inside [start, end]. Provides
// a sub-context with `localTime` (seconds since start) and `progress` (0..1).
//
//   <Sprite start={2} end={5}>
//     {({ localTime, progress }) => <Thing x={progress * 100} />}
//   </Sprite>
//
// Or as a plain wrapper — children can call useSprite() themselves.

const SpriteContext = React.createContext({
  localTime: 0,
  progress: 0,
  duration: 0
});
const useSprite = () => React.useContext(SpriteContext);
function Sprite({
  start = 0,
  end = Infinity,
  children,
  keepMounted = false
}) {
  const {
    time
  } = useTimeline();
  const visible = time >= start && time <= end;
  if (!visible && !keepMounted) return null;
  const duration = end - start;
  const localTime = Math.max(0, time - start);
  const progress = duration > 0 && isFinite(duration) ? clamp(localTime / duration, 0, 1) : 0;
  const value = {
    localTime,
    progress,
    duration,
    visible
  };
  return /*#__PURE__*/React.createElement(SpriteContext.Provider, {
    value: value
  }, typeof children === 'function' ? children(value) : children);
}

// ── Sample sprite components ────────────────────────────────────────────────

// TextSprite: fades/slides text in on entry, holds, then fades out on exit.
// Props: text, x, y, size, color, font, entryDur, exitDur, align
function TextSprite({
  text,
  x = 0,
  y = 0,
  size = 48,
  color = '#111',
  font = 'Inter, system-ui, sans-serif',
  weight = 600,
  entryDur = 0.45,
  exitDur = 0.35,
  entryEase = Easing.easeOutBack,
  exitEase = Easing.easeInCubic,
  align = 'left',
  letterSpacing = '-0.01em'
}) {
  const {
    localTime,
    duration
  } = useSprite();
  const exitStart = Math.max(0, duration - exitDur);
  let opacity = 1;
  let ty = 0;
  if (localTime < entryDur) {
    const t = entryEase(clamp(localTime / entryDur, 0, 1));
    opacity = t;
    ty = (1 - t) * 16;
  } else if (localTime > exitStart) {
    const t = exitEase(clamp((localTime - exitStart) / exitDur, 0, 1));
    opacity = 1 - t;
    ty = -t * 8;
  }
  const translateX = align === 'center' ? '-50%' : align === 'right' ? '-100%' : '0';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x,
      top: y,
      transform: `translate(${translateX}, ${ty}px)`,
      opacity,
      fontFamily: font,
      fontSize: size,
      fontWeight: weight,
      color,
      letterSpacing,
      whiteSpace: 'pre',
      lineHeight: 1.1,
      willChange: 'transform, opacity'
    }
  }, text);
}

// ImageSprite: scales + fades in; optional Ken Burns drift during hold.
function ImageSprite({
  src,
  x = 0,
  y = 0,
  width = 400,
  height = 300,
  entryDur = 0.6,
  exitDur = 0.4,
  kenBurns = false,
  kenBurnsScale = 1.08,
  radius = 12,
  fit = 'cover',
  placeholder = null // {label: string} for striped placeholder
}) {
  const {
    localTime,
    duration
  } = useSprite();
  const exitStart = Math.max(0, duration - exitDur);
  let opacity = 1;
  let scale = 1;
  if (localTime < entryDur) {
    const t = Easing.easeOutCubic(clamp(localTime / entryDur, 0, 1));
    opacity = t;
    scale = 0.96 + 0.04 * t;
  } else if (localTime > exitStart) {
    const t = Easing.easeInCubic(clamp((localTime - exitStart) / exitDur, 0, 1));
    opacity = 1 - t;
    scale = (kenBurns ? kenBurnsScale : 1) + 0.02 * t;
  } else if (kenBurns) {
    const holdSpan = exitStart - entryDur;
    const holdT = holdSpan > 0 ? (localTime - entryDur) / holdSpan : 0;
    scale = 1 + (kenBurnsScale - 1) * holdT;
  }
  const content = placeholder ? /*#__PURE__*/React.createElement("div", {
    style: {
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'repeating-linear-gradient(135deg, #e9e6df 0 10px, #dcd8cf 10px 20px)',
      color: '#6b6458',
      fontFamily: 'JetBrains Mono, ui-monospace, monospace',
      fontSize: 13,
      letterSpacing: '0.04em',
      textTransform: 'uppercase'
    }
  }, placeholder.label || 'image') : /*#__PURE__*/React.createElement("img", {
    src: src,
    alt: "",
    style: {
      width: '100%',
      height: '100%',
      objectFit: fit,
      display: 'block'
    }
  });
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x,
      top: y,
      width,
      height,
      opacity,
      transform: `scale(${scale})`,
      transformOrigin: 'center',
      borderRadius: radius,
      overflow: 'hidden',
      willChange: 'transform, opacity'
    }
  }, content);
}

// RectSprite: simple rectangle that animates position/size/color via props.
// Useful demo primitive — takes a `render` fn for per-frame customization.
function RectSprite({
  x = 0,
  y = 0,
  width = 100,
  height = 100,
  color = '#111',
  radius = 8,
  entryDur = 0.4,
  exitDur = 0.3,
  render // optional: (ctx) => style overrides
}) {
  const spriteCtx = useSprite();
  const {
    localTime,
    duration
  } = spriteCtx;
  const exitStart = Math.max(0, duration - exitDur);
  let opacity = 1;
  let scale = 1;
  if (localTime < entryDur) {
    const t = Easing.easeOutBack(clamp(localTime / entryDur, 0, 1));
    opacity = clamp(localTime / entryDur, 0, 1);
    scale = 0.4 + 0.6 * t;
  } else if (localTime > exitStart) {
    const t = Easing.easeInQuad(clamp((localTime - exitStart) / exitDur, 0, 1));
    opacity = 1 - t;
    scale = 1 - 0.15 * t;
  }
  const overrides = render ? render(spriteCtx) : {};
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x,
      top: y,
      width,
      height,
      background: color,
      borderRadius: radius,
      opacity,
      transform: `scale(${scale})`,
      transformOrigin: 'center',
      willChange: 'transform, opacity',
      ...overrides
    }
  });
}
function Stage({
  width = 1280,
  height = 720,
  duration = 10,
  background = '#f6f4ef',
  fps = 60,
  loop = true,
  autoplay = true,
  persistKey = 'animstage',
  children
}) {
  const [time, setTime] = React.useState(() => {
    try {
      const v = parseFloat(localStorage.getItem(persistKey + ':t') || '0');
      return isFinite(v) ? clamp(v, 0, duration) : 0;
    } catch {
      return 0;
    }
  });
  const [playing, setPlaying] = React.useState(autoplay);
  const [hoverTime, setHoverTime] = React.useState(null);
  const [scale, setScale] = React.useState(1);
  const stageRef = React.useRef(null);
  const canvasRef = React.useRef(null);
  const rafRef = React.useRef(null);
  const lastTsRef = React.useRef(null);

  // Persist playhead
  React.useEffect(() => {
    try {
      localStorage.setItem(persistKey + ':t', String(time));
    } catch {}
  }, [time, persistKey]);

  // Auto-scale to fit viewport
  React.useEffect(() => {
    if (!stageRef.current) return;
    const el = stageRef.current;
    const measure = () => {
      const barH = 44; // playback bar height
      const s = Math.min(el.clientWidth / width, (el.clientHeight - barH) / height);
      setScale(Math.max(0.05, s));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    window.addEventListener('resize', measure);
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, [width, height]);

  // Animation loop
  React.useEffect(() => {
    if (!playing) {
      lastTsRef.current = null;
      return;
    }
    const step = ts => {
      if (lastTsRef.current == null) lastTsRef.current = ts;
      const dt = (ts - lastTsRef.current) / 1000;
      lastTsRef.current = ts;
      setTime(t => {
        let next = t + dt;
        if (next >= duration) {
          if (loop) next = next % duration;else {
            next = duration;
            setPlaying(false);
          }
        }
        return next;
      });
      rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      lastTsRef.current = null;
    };
  }, [playing, duration, loop]);

  // Keyboard: space = play/pause, ← → = seek
  React.useEffect(() => {
    const onKey = e => {
      if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
      if (e.code === 'Space') {
        e.preventDefault();
        setPlaying(p => !p);
      } else if (e.code === 'ArrowLeft') {
        setTime(t => clamp(t - (e.shiftKey ? 1 : 0.1), 0, duration));
      } else if (e.code === 'ArrowRight') {
        setTime(t => clamp(t + (e.shiftKey ? 1 : 0.1), 0, duration));
      } else if (e.key === '0' || e.code === 'Home') {
        setTime(0);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [duration]);
  const displayTime = hoverTime != null ? hoverTime : time;
  const ctxValue = React.useMemo(() => ({
    time: displayTime,
    duration,
    playing,
    setTime,
    setPlaying
  }), [displayTime, duration, playing]);
  return /*#__PURE__*/React.createElement("div", {
    ref: stageRef,
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      background: '#0a0a0a',
      fontFamily: 'Inter, system-ui, sans-serif'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      width: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      overflow: 'hidden',
      minHeight: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    ref: canvasRef,
    style: {
      width,
      height,
      background,
      position: 'relative',
      transform: `scale(${scale})`,
      transformOrigin: 'center',
      flexShrink: 0,
      boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement(TimelineContext.Provider, {
    value: ctxValue
  }, children))), /*#__PURE__*/React.createElement(PlaybackBar, {
    time: displayTime,
    actualTime: time,
    duration: duration,
    playing: playing,
    onPlayPause: () => setPlaying(p => !p),
    onReset: () => {
      setTime(0);
    },
    onSeek: t => setTime(t),
    onHover: t => setHoverTime(t)
  }));
}

// ── Playback bar ────────────────────────────────────────────────────────────
// Play/pause, return-to-begin, scrub track, time display.
// Uses fixed-width time fields so layout doesn't thrash.

function PlaybackBar({
  time,
  duration,
  playing,
  onPlayPause,
  onReset,
  onSeek,
  onHover
}) {
  const trackRef = React.useRef(null);
  const [dragging, setDragging] = React.useState(false);
  const timeFromEvent = React.useCallback(e => {
    const rect = trackRef.current.getBoundingClientRect();
    const x = clamp((e.clientX - rect.left) / rect.width, 0, 1);
    return x * duration;
  }, [duration]);
  const onTrackMove = e => {
    if (!trackRef.current) return;
    const t = timeFromEvent(e);
    if (dragging) {
      onSeek(t);
    } else {
      onHover(t);
    }
  };
  const onTrackLeave = () => {
    if (!dragging) onHover(null);
  };
  const onTrackDown = e => {
    setDragging(true);
    const t = timeFromEvent(e);
    onSeek(t);
    onHover(null);
  };
  React.useEffect(() => {
    if (!dragging) return;
    const onUp = () => setDragging(false);
    const onMove = e => {
      if (!trackRef.current) return;
      const t = timeFromEvent(e);
      onSeek(t);
    };
    window.addEventListener('mouseup', onUp);
    window.addEventListener('mousemove', onMove);
    return () => {
      window.removeEventListener('mouseup', onUp);
      window.removeEventListener('mousemove', onMove);
    };
  }, [dragging, timeFromEvent, onSeek]);
  const pct = duration > 0 ? time / duration * 100 : 0;
  const fmt = t => {
    const total = Math.max(0, t);
    const m = Math.floor(total / 60);
    const s = Math.floor(total % 60);
    const cs = Math.floor(total * 100 % 100);
    return `${String(m).padStart(1, '0')}:${String(s).padStart(2, '0')}.${String(cs).padStart(2, '0')}`;
  };
  const mono = 'JetBrains Mono, ui-monospace, SFMono-Regular, monospace';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      padding: '8px 16px',
      background: 'rgba(20,20,20,0.92)',
      borderTop: '1px solid rgba(255,255,255,0.08)',
      width: '100%',
      maxWidth: 680,
      alignSelf: 'center',
      borderRadius: 8,
      color: '#f6f4ef',
      fontFamily: 'Inter, system-ui, sans-serif',
      userSelect: 'none',
      flexShrink: 0
    }
  }, /*#__PURE__*/React.createElement(IconButton, {
    onClick: onReset,
    title: "Return to start (0)"
  }, /*#__PURE__*/React.createElement("svg", {
    width: "14",
    height: "14",
    viewBox: "0 0 14 14",
    fill: "none"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M3 2v10M12 2L5 7l7 5V2z",
    stroke: "currentColor",
    strokeWidth: "1.5",
    strokeLinejoin: "round",
    strokeLinecap: "round"
  }))), /*#__PURE__*/React.createElement(IconButton, {
    onClick: onPlayPause,
    title: "Play/pause (space)"
  }, playing ? /*#__PURE__*/React.createElement("svg", {
    width: "14",
    height: "14",
    viewBox: "0 0 14 14",
    fill: "none"
  }, /*#__PURE__*/React.createElement("rect", {
    x: "3",
    y: "2",
    width: "3",
    height: "10",
    fill: "currentColor"
  }), /*#__PURE__*/React.createElement("rect", {
    x: "8",
    y: "2",
    width: "3",
    height: "10",
    fill: "currentColor"
  })) : /*#__PURE__*/React.createElement("svg", {
    width: "14",
    height: "14",
    viewBox: "0 0 14 14",
    fill: "none"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M3 2l9 5-9 5V2z",
    fill: "currentColor"
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: mono,
      fontSize: 12,
      fontVariantNumeric: 'tabular-nums',
      width: 64,
      textAlign: 'right',
      color: '#f6f4ef'
    }
  }, fmt(time)), /*#__PURE__*/React.createElement("div", {
    ref: trackRef,
    onMouseMove: onTrackMove,
    onMouseLeave: onTrackLeave,
    onMouseDown: onTrackDown,
    style: {
      flex: 1,
      height: 22,
      position: 'relative',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      right: 0,
      height: 4,
      background: 'rgba(255,255,255,0.12)',
      borderRadius: 2
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      width: `${pct}%`,
      height: 4,
      background: 'oklch(72% 0.12 250)',
      borderRadius: 2
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: `${pct}%`,
      top: '50%',
      width: 12,
      height: 12,
      marginLeft: -6,
      marginTop: -6,
      background: '#fff',
      borderRadius: 6,
      boxShadow: '0 2px 4px rgba(0,0,0,0.4)'
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: mono,
      fontSize: 12,
      fontVariantNumeric: 'tabular-nums',
      width: 64,
      textAlign: 'left',
      color: 'rgba(246,244,239,0.55)'
    }
  }, fmt(duration)));
}
function IconButton({
  children,
  onClick,
  title
}) {
  const [hover, setHover] = React.useState(false);
  return /*#__PURE__*/React.createElement("button", {
    onClick: onClick,
    title: title,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      width: 28,
      height: 28,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: hover ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.04)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 6,
      color: '#f6f4ef',
      cursor: 'pointer',
      padding: 0,
      transition: 'background 120ms'
    }
  }, children);
}
Object.assign(window, {
  Easing,
  interpolate,
  animate,
  clamp,
  TimelineContext,
  useTime,
  useTimeline,
  Sprite,
  SpriteContext,
  useSprite,
  TextSprite,
  ImageSprite,
  RectSprite,
  Stage,
  PlaybackBar
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "video/animations.jsx", error: String((e && e.message) || e) }); }

// video/parts.jsx
try { (() => {
/* cdr-kit explainer — shared parts. Brand tokens (light + indigo). */
const COL = {
  paper: '#fcfbf8',
  paper2: '#f6f3ee',
  paper3: '#efebe4',
  card: '#ffffff',
  ink: '#2b2724',
  ink2: '#6f6a63',
  ink3: '#948f87',
  line: '#e7e4df',
  line2: '#dcd9d2',
  primary: '#3a5adb',
  primarySoft: 'rgba(58,90,219,0.10)',
  primaryLine: 'rgba(58,90,219,0.34)',
  signal: '#1e9c66',
  signalSoft: 'rgba(30,156,102,0.12)',
  signalLine: 'rgba(30,156,102,0.40)',
  warn: '#b9852f',
  warnSoft: 'rgba(185,133,47,0.12)',
  warnLine: 'rgba(185,133,47,0.40)'
};
const FONT = {
  disp: "'Bricolage Grotesque', sans-serif",
  sans: "'Hanken Grotesk', system-ui, sans-serif",
  mono: "'JetBrains Mono', ui-monospace, monospace"
};

// scramble: resolves `target` left-to-right as p:0->1, random hex glyphs elsewhere
const GLYPHS = '0123456789abcdef?{}":,./';
function scramble(target, p) {
  const n = Math.floor(clamp(p, 0, 1) * target.length);
  let s = '';
  for (let i = 0; i < target.length; i++) {
    const ch = target[i];
    if (i < n || ch === ' ') s += ch;else s += GLYPHS[Math.random() * GLYPHS.length | 0];
  }
  return s;
}

// The Vault-Rail brand mark. `draw` (0..1) strokes it on; dotP (0..1) pops the payload dot.
function Mark({
  size = 64,
  color = COL.ink,
  dot = COL.primary,
  draw = 1,
  dotP = 1
}) {
  const railLen = 29,
    rectLen = 84;
  return /*#__PURE__*/React.createElement("svg", {
    width: size,
    height: size,
    viewBox: "0 0 32 32",
    fill: "none",
    style: {
      display: 'block'
    }
  }, /*#__PURE__*/React.createElement("line", {
    x1: "1.5",
    y1: "16",
    x2: "30.5",
    y2: "16",
    stroke: color,
    strokeWidth: "2.6",
    strokeLinecap: "round",
    strokeDasharray: railLen,
    strokeDashoffset: railLen * (1 - clamp(draw, 0, 1))
  }), /*#__PURE__*/React.createElement("rect", {
    x: "7",
    y: "7",
    width: "18",
    height: "18",
    rx: "5.2",
    stroke: color,
    strokeWidth: "2.6",
    strokeDasharray: rectLen,
    strokeDashoffset: rectLen * (1 - clamp(draw, 0, 1))
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "16",
    cy: "16",
    r: 2.8 * clamp(dotP, 0, 1),
    fill: dot
  }));
}

// Subtle hairline grid with radial fade. opacity prop fades the whole thing.
function Grid({
  opacity = 1,
  cx = '50%',
  cy = '30%'
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      opacity,
      pointerEvents: 'none',
      backgroundImage: `linear-gradient(${COL.line} 1px, transparent 1px), linear-gradient(90deg, ${COL.line} 1px, transparent 1px)`,
      backgroundSize: '48px 48px',
      WebkitMaskImage: `radial-gradient(ellipse 75% 75% at ${cx} ${cy}, #000 0%, transparent 72%)`,
      maskImage: `radial-gradient(ellipse 75% 75% at ${cx} ${cy}, #000 0%, transparent 72%)`
    }
  });
}

// Brand wordmark lockup
function Lockup({
  size = 1,
  color = COL.ink
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 14 * size
    }
  }, /*#__PURE__*/React.createElement(Mark, {
    size: 42 * size,
    color: color
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontWeight: 700,
      fontSize: 34 * size,
      letterSpacing: '-0.04em',
      color,
      whiteSpace: 'nowrap'
    }
  }, "cdr", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "-"), "kit"));
}

// Window-chrome card (the vault card shell)
function WinCard({
  x,
  y,
  w,
  title,
  children,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x,
      top: y,
      width: w,
      background: COL.card,
      border: `1px solid ${COL.line}`,
      borderRadius: 16,
      boxShadow: '0 18px 50px -20px rgba(43,39,36,0.28)',
      overflow: 'hidden',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '11px 16px',
      borderBottom: `1px solid ${COL.line}`,
      background: COL.paper2
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'flex',
      gap: 6
    }
  }, [0, 1, 2].map(i => /*#__PURE__*/React.createElement("i", {
    key: i,
    style: {
      width: 10,
      height: 10,
      borderRadius: '50%',
      background: COL.line2,
      display: 'block'
    }
  }))), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 13,
      color: COL.ink3
    }
  }, title)), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '18px 20px'
    }
  }, children));
}
function Pill({
  tone = 'primary',
  children,
  style
}) {
  const map = {
    primary: [COL.primary, COL.primarySoft, COL.primaryLine],
    signal: [COL.signal, COL.signalSoft, COL.signalLine],
    warn: [COL.warn, COL.warnSoft, COL.warnLine]
  };
  const [c, bg, bd] = map[tone];
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 7,
      fontFamily: FONT.mono,
      fontSize: 13,
      color: c,
      background: bg,
      border: `1px solid ${bd}`,
      borderRadius: 999,
      padding: '5px 12px',
      whiteSpace: 'nowrap',
      ...style
    }
  }, children);
}

// lock glyph (open/closed) for status
function Lock({
  open,
  color,
  size = 15
}) {
  return /*#__PURE__*/React.createElement("svg", {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: color,
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("rect", {
    x: "5",
    y: "11",
    width: "14",
    height: "10",
    rx: "2"
  }), open ? /*#__PURE__*/React.createElement("path", {
    d: "M8 11V7a4 4 0 0 1 8 0"
  }) : /*#__PURE__*/React.createElement("path", {
    d: "M8 11V7a4 4 0 0 1 8 0v4"
  }));
}
Object.assign(window, {
  COL,
  FONT,
  scramble,
  Mark,
  Grid,
  Lockup,
  WinCard,
  Pill,
  Lock
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "video/parts.jsx", error: String((e && e.message) || e) }); }

// video/scenes.jsx
try { (() => {
/* cdr-kit explainer — scenes. Each reads useSprite() for scene-local time. */
const {
  useSprite: uS
} = window;
const A = o => animate(o);
const typed = (str, p) => str.slice(0, Math.max(0, Math.floor(clamp(p, 0, 1) * str.length)));
const CIPHER = '7b 22 73 69 67 9f a3 2e c1 04 7d e8 11 b6 6a 0c 3f d1';
const PLAIN1 = '{ "signal": "BUY",';
const PLAIN2 = '  "pair": "ETH/USD", "confidence": 0.86 }';
const CIPHER2 = 'a1 9c 04 e8 7d 22 6e 61 6c b6 2e c1 ?? 9f 11 0c 6a d1 3f';
function fade(lt, inEnd, outStart, outEnd) {
  if (lt < inEnd) return clamp(lt / inEnd, 0, 1);
  if (outStart != null && lt > outStart) return 1 - clamp((lt - outStart) / (outEnd - outStart), 0, 1);
  return 1;
}

// ── S1 · Hook ────────────────────────────────────────────────────────────
function SceneHook() {
  const {
    localTime: lt
  } = uS();
  const draw = A({
    from: 0,
    to: 1,
    start: 0.5,
    end: 2.0,
    ease: Easing.easeInOutCubic
  })(lt);
  const dotP = A({
    from: 0,
    to: 1,
    start: 2.0,
    end: 2.4,
    ease: Easing.easeOutBack
  })(lt);
  const drift = A({
    from: 1,
    to: 1.05,
    start: 0,
    end: 5,
    ease: Easing.linear
  })(lt);
  const gridO = A({
    from: 0,
    to: 1,
    start: 0,
    end: 1,
    ease: Easing.easeOutQuad
  })(lt);
  const wordO = fade(lt, 0.5, 4.4, 5);
  const wordIn = A({
    from: 0,
    to: 1,
    start: 1.7,
    end: 2.3,
    ease: Easing.easeOutCubic
  })(lt);
  const tagIn = A({
    from: 0,
    to: 1,
    start: 2.7,
    end: 3.3,
    ease: Easing.easeOutCubic
  })(lt);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: gridO * 0.85,
    cx: "50%",
    cy: "42%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      transform: `scale(${drift})`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 18,
      opacity: fade(lt, 0.4, 4.4, 5)
    }
  }, /*#__PURE__*/React.createElement(Mark, {
    size: 86,
    draw: draw,
    dotP: dotP
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontWeight: 700,
      fontSize: 72,
      letterSpacing: '-0.05em',
      color: COL.ink,
      whiteSpace: 'nowrap',
      opacity: wordIn,
      transform: `translateX(${(1 - wordIn) * -12}px)`
    }
  }, "cdr", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "-"), "kit")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 26,
      fontFamily: FONT.disp,
      fontWeight: 700,
      fontSize: 30,
      letterSpacing: '-0.02em',
      color: COL.ink2,
      textAlign: 'center',
      opacity: tagIn,
      transform: `translateY(${(1 - tagIn) * 10}px)`
    }
  }, "Confidential Data Rails, ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink
    }
  }, "made shippable."))));
}

// ── S2 · The primitive (encrypt) ─────────────────────────────────────────
function ScenePrimitive() {
  const {
    localTime: lt
  } = uS();
  const encP = A({
    from: 0,
    to: 1,
    start: 1.3,
    end: 3.2,
    ease: Easing.easeInOutQuad
  })(lt);
  // encrypt = reverse-resolve: at p=0 plaintext, p=1 cipher. scramble cipher with (1-?) trick:
  const l1 = lt < 1.3 ? PLAIN1 : scramble(CIPHER, encP);
  const l2 = lt < 1.3 ? PLAIN2 : scramble(CIPHER2, encP);
  const sealP = A({
    from: 0,
    to: 1,
    start: 3.1,
    end: 4.3,
    ease: Easing.easeInOutCubic
  })(lt);
  const zoom = A({
    from: 1,
    to: 1.06,
    start: 0,
    end: 6,
    ease: Easing.linear
  })(lt);
  const sealLen = 320;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.5,
    cx: "50%",
    cy: "34%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 96,
      left: 0,
      right: 0,
      textAlign: 'center',
      opacity: fade(lt, 0.5, 5.2, 6)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      letterSpacing: '0.16em',
      color: COL.ink3
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "\u259A"), "\xA0\xA0THE PRIMITIVE"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 800,
      fontSize: 46,
      letterSpacing: '-0.03em',
      color: COL.ink,
      marginTop: 14
    }
  }, "Write ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "encrypted"), " data on-chain.")), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 300,
      left: '50%',
      transform: `translateX(-50%) scale(${zoom})`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      width: 560
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: COL.card,
      border: `1px solid ${COL.line}`,
      borderRadius: 12,
      padding: '24px 26px',
      fontFamily: FONT.mono,
      fontSize: 19,
      lineHeight: 1.7,
      color: COL.ink,
      boxShadow: '0 18px 50px -22px rgba(43,39,36,0.3)',
      wordBreak: 'break-all'
    }
  }, /*#__PURE__*/React.createElement("div", null, l1), /*#__PURE__*/React.createElement("div", {
    style: {
      color: lt < 1.3 ? COL.ink : COL.ink2
    }
  }, l2)), /*#__PURE__*/React.createElement("svg", {
    width: "560",
    height: "150",
    viewBox: "0 0 560 150",
    style: {
      position: 'absolute',
      inset: 0,
      pointerEvents: 'none',
      overflow: 'visible'
    }
  }, /*#__PURE__*/React.createElement("rect", {
    x: "2",
    y: "2",
    width: "556",
    height: "146",
    rx: "12",
    fill: "none",
    stroke: COL.primary,
    strokeWidth: "2.5",
    strokeDasharray: sealLen,
    strokeDashoffset: sealLen * 2 * (1 - sealP),
    opacity: sealP > 0 ? 0.9 : 0
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 22,
      textAlign: 'center',
      fontFamily: FONT.sans,
      fontSize: 18,
      color: COL.ink2,
      opacity: A({
        from: 0,
        to: 1,
        start: 3.6,
        end: 4.4,
        ease: Easing.easeOutCubic
      })(lt)
    }
  }, "Sealed in a vault \u2014 readable only if you satisfy a ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink,
      fontFamily: FONT.mono,
      fontSize: 16
    }
  }, "condition"), ".")));
}

// ── S3 · The gate (money shot: decrypt) ──────────────────────────────────
function SceneGate() {
  const {
    localTime: lt
  } = uS();
  const locked = lt < 3.4;
  const decP = A({
    from: 0,
    to: 1,
    start: 3.6,
    end: 5.4,
    ease: Easing.easeInOutQuad
  })(lt);
  const pay = lt >= 2.0 && lt < 3.6;
  const cardZoom = A({
    from: 0.94,
    to: 1.04,
    start: 0,
    end: 7,
    ease: Easing.easeOutCubic
  })(lt);
  const payRow = A({
    from: 0,
    to: 1,
    start: 1.8,
    end: 2.4,
    ease: Easing.easeOutBack
  })(lt);
  const statusOpen = lt >= 3.4;
  // payload lines
  let p1, p2, pcol;
  if (lt < 3.6) {
    p1 = CIPHER;
    p2 = CIPHER2;
    pcol = COL.ink3;
  } else {
    p1 = scramble(PLAIN1, decP);
    p2 = scramble(PLAIN2, decP);
    pcol = decP > 0.98 ? COL.signal : COL.ink;
  }
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper2
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.4,
    cx: "50%",
    cy: "50%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 54,
      left: 0,
      right: 0,
      textAlign: 'center',
      opacity: fade(lt, 0.5, 6.2, 7)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 800,
      fontSize: 38,
      letterSpacing: '-0.03em',
      color: COL.ink
    }
  }, "Satisfy the condition \u2192 ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.signal
    }
  }, "it decrypts."))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 150,
      left: '50%',
      transform: `translateX(-50%) scale(${cardZoom})`,
      transformOrigin: 'top center'
    }
  }, /*#__PURE__*/React.createElement(WinCard, {
    x: 0,
    y: 0,
    w: 520,
    title: "<VaultGate uuid={4200} />",
    style: {
      position: 'relative'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 11,
      paddingBottom: 14,
      borderBottom: `1px solid ${COL.line}`,
      marginBottom: 14
    }
  }, [['vault.uuid', '4200', COL.ink], ['read.condition', 'Subscription', COL.primary], ['price.period', '5 $IP / 30d', COL.ink]].map(([k, v, c]) => /*#__PURE__*/React.createElement("div", {
    key: k,
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      fontFamily: FONT.mono,
      fontSize: 15,
      whiteSpace: 'nowrap'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink3,
      fontSize: 13
    }
  }, k), /*#__PURE__*/React.createElement("span", {
    style: {
      color: c
    }
  }, v)))), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 15.5,
      lineHeight: 1.7,
      background: COL.paper2,
      border: `1px solid ${COL.line}`,
      borderRadius: 8,
      padding: '14px 16px',
      minHeight: 76,
      color: pcol,
      wordBreak: 'break-all',
      transition: 'color .3s'
    }
  }, /*#__PURE__*/React.createElement("div", null, p1), /*#__PURE__*/React.createElement("div", null, p2)), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginTop: 14
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      fontFamily: FONT.mono,
      fontSize: 14,
      color: statusOpen ? COL.signal : COL.warn
    }
  }, /*#__PURE__*/React.createElement(Lock, {
    open: statusOpen,
    color: statusOpen ? COL.signal : COL.warn
  }), statusOpen ? 'condition satisfied · decrypted' : 'condition not met'), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 13,
      color: COL.ink3
    }
  }, "~15s read"))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: -38,
      top: 330,
      opacity: payRow,
      transform: `translateY(${(1 - payRow) * 14}px)`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      background: COL.card,
      border: `1px solid ${COL.line2}`,
      borderRadius: 12,
      padding: '10px 14px',
      boxShadow: '0 14px 36px -16px rgba(43,39,36,0.3)',
      whiteSpace: 'nowrap'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 9,
      height: 9,
      borderRadius: '50%',
      background: pay ? COL.warn : COL.signal,
      transition: 'background .3s'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 13.5,
      color: COL.ink
    }
  }, "agent 0x9f\u2026a3c1"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 13.5,
      color: statusOpen ? COL.signal : COL.primary
    }
  }, statusOpen ? '✓ paid 5 $IP' : 'subscribe()')))));
}

// ── S4 · One install ─────────────────────────────────────────────────────
function SceneInstall() {
  const {
    localTime: lt
  } = uS();
  const cmd = typed('npm create cdr-kit', A({
    from: 0,
    to: 1,
    start: 0.6,
    end: 1.7,
    ease: Easing.linear
  })(lt));
  const codeO = A({
    from: 0,
    to: 1,
    start: 2.0,
    end: 2.7,
    ease: Easing.easeOutCubic
  })(lt);
  const layers = [['Layer 3', 'Framework adapters · MCP · CLI'], ['Layer 2', 'TypeScript SDK · React · agent'], ['Layer 1', '9 Solidity conditions · vault']];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.45,
    cx: "28%",
    cy: "30%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 88,
      left: 96,
      opacity: fade(lt, 0.5, 4.4, 5)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      letterSpacing: '0.16em',
      color: COL.ink3
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "\u259A"), "\xA0\xA0ONE INSTALL"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 800,
      fontSize: 44,
      letterSpacing: '-0.03em',
      color: COL.ink,
      marginTop: 14,
      maxWidth: 480,
      lineHeight: 1.05
    }
  }, "One package.", /*#__PURE__*/React.createElement("br", null), "Real on-chain checks."), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 18,
      fontFamily: FONT.sans,
      fontSize: 17,
      color: COL.ink2,
      maxWidth: 430
    }
  }, "Gate any data behind a payment or license \u2014 in under a minute.")), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 150,
      left: 640,
      width: 540
    }
  }, /*#__PURE__*/React.createElement(WinCard, {
    x: 0,
    y: 0,
    w: 540,
    title: "terminal"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 17,
      color: COL.ink
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "$"), " ", cmd, /*#__PURE__*/React.createElement("span", {
    style: {
      opacity: lt % 1 < 0.5 ? 1 : 0,
      color: COL.ink3
    }
  }, "\u258B")), /*#__PURE__*/React.createElement("div", {
    style: {
      opacity: codeO,
      marginTop: 16,
      paddingTop: 16,
      borderTop: `1px solid ${COL.line}`,
      fontFamily: FONT.mono,
      fontSize: 15.5,
      lineHeight: 1.7
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "import"), " ", '{ VaultGate }', " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "from"), " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.signal
    }
  }, "\"@cdr-kit/react\""), ";"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 8
    }
  }, '<', /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#b5532f'
    }
  }, "VaultGate"), " uuid=", '{', /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.warn
    }
  }, "4200"), '}', " auto", '>'), /*#__PURE__*/React.createElement("div", null, '  {(data) => <pre>{decode(data)}</pre>}'), /*#__PURE__*/React.createElement("div", null, '</', /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#b5532f'
    }
  }, "VaultGate"), '>'))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 10,
      marginTop: 18,
      opacity: A({
        from: 0,
        to: 1,
        start: 3.0,
        end: 3.7,
        ease: Easing.easeOutCubic
      })(lt)
    }
  }, layers.map(([a, b], i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      flex: 1,
      background: COL.card,
      border: `1px solid ${COL.line}`,
      borderRadius: 10,
      padding: '11px 13px',
      transform: `translateY(${(1 - A({
        from: 0,
        to: 1,
        start: 3.0 + i * 0.12,
        end: 3.7 + i * 0.12,
        ease: Easing.easeOutBack
      })(lt)) * 12}px)`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 11.5,
      color: COL.primary,
      fontWeight: 700
    }
  }, a), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.sans,
      fontSize: 12.5,
      color: COL.ink2,
      marginTop: 4
    }
  }, b))))));
}

// ── S5 · The agent ───────────────────────────────────────────────────────
function SceneAgent() {
  const {
    localTime: lt
  } = uS();
  const lines = [['$ ', 'agent run --intent "trading signal"', COL.ink, 0.4], ['⚙ ', 'discover → matched vault 4200', COL.primary, 1.1], ['⚙ ', 'subscribe & access → paid 5 $IP', COL.primary, 1.8], ['✓ ', 'threshold met · decrypted locally', COL.signal, 2.5], ['→ ', 'decide: BUY ETH/USD (0.86)', COL.ink, 3.1]];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.4,
    cx: "70%",
    cy: "32%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 92,
      left: 0,
      right: 0,
      textAlign: 'center',
      opacity: fade(lt, 0.5, 3.6, 4)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 800,
      fontSize: 42,
      letterSpacing: '-0.03em',
      color: COL.ink
    }
  }, "An agent that buys its ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "own data.")), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.sans,
      fontSize: 18,
      color: COL.ink2,
      marginTop: 10
    }
  }, "Discover \u2192 pay \u2192 decrypt \u2192 decide. No human in the loop.")), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 226,
      left: '50%',
      transform: 'translateX(-50%)',
      width: 620
    }
  }, /*#__PURE__*/React.createElement(WinCard, {
    x: 0,
    y: 0,
    w: 620,
    title: "cdr-kit-example \xB7 vercel-ai"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 16,
      lineHeight: 1.85,
      minHeight: 170
    }
  }, lines.map(([pre, txt, col, t], i) => {
    const o = A({
      from: 0,
      to: 1,
      start: t,
      end: t + 0.35,
      ease: Easing.easeOutCubic
    })(lt);
    const shown = typed(txt, A({
      from: 0,
      to: 1,
      start: t,
      end: t + 0.5,
      ease: Easing.linear
    })(lt));
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        opacity: o,
        color: col
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        color: pre === '✓ ' ? COL.signal : pre === '→ ' ? COL.primary : COL.ink3
      }
    }, pre), shown);
  })))));
}

// ── S6 · Outro ───────────────────────────────────────────────────────────
function SceneOutro() {
  const {
    localTime: lt
  } = uS();
  const inP = A({
    from: 0,
    to: 1,
    start: 0.2,
    end: 1.0,
    ease: Easing.easeOutBack
  })(lt);
  const sub = A({
    from: 0,
    to: 1,
    start: 0.9,
    end: 1.6,
    ease: Easing.easeOutCubic
  })(lt);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.7,
    cx: "50%",
    cy: "48%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      transform: `scale(${0.9 + 0.1 * inP})`,
      opacity: inP
    }
  }, /*#__PURE__*/React.createElement(Lockup, {
    size: 1.5
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 28,
      fontFamily: FONT.mono,
      fontSize: 16,
      color: COL.ink2,
      opacity: sub,
      letterSpacing: '0.01em',
      whiteSpace: 'nowrap'
    }
  }, "15 packages \xB7 9 conditions \xB7 34 tools \xB7 17 hooks \xB7 ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink
    }
  }, "MIT")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 20,
      display: 'flex',
      alignItems: 'center',
      gap: 14,
      opacity: sub
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 22,
      fontWeight: 700,
      color: COL.primary
    }
  }, "cdrkit.xyz"), /*#__PURE__*/React.createElement(Pill, {
    tone: "signal"
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 7,
      height: 7,
      borderRadius: '50%',
      background: COL.signal,
      display: 'inline-block'
    }
  }), "Live on Aeneid"))));
}
Object.assign(window, {
  SceneHook,
  ScenePrimitive,
  SceneGate,
  SceneInstall,
  SceneAgent,
  SceneOutro
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "video/scenes.jsx", error: String((e && e.message) || e) }); }

// video/scenes2.jsx
try { (() => {
/* cdr-kit explainer — additional scenes (breadth): React surface, conditions,
   agents-everywhere, Story IP. Loaded after parts.jsx + scenes.jsx. */
const {
  useSprite: uS2
} = window;
const A2 = o => animate(o);
const typed2 = (str, p) => str.slice(0, Math.max(0, Math.floor(clamp(p, 0, 1) * str.length)));
function fade2(lt, inEnd, outStart, outEnd) {
  if (lt < inEnd) return clamp(lt / inEnd, 0, 1);
  if (outStart != null && lt > outStart) return 1 - clamp((lt - outStart) / (outEnd - outStart), 0, 1);
  return 1;
}
function Chip2({
  children,
  tone,
  style
}) {
  const key = tone === 'primary';
  return /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      color: key ? COL.primary : COL.ink2,
      background: key ? COL.primarySoft : COL.paper2,
      border: `1px solid ${key ? COL.primaryLine : COL.line}`,
      borderRadius: 8,
      padding: '7px 12px',
      whiteSpace: 'nowrap',
      display: 'inline-block',
      ...style
    }
  }, children);
}
function SceneHead({
  lt,
  kick,
  title,
  accent,
  dur
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 62,
      left: 0,
      right: 0,
      textAlign: 'center',
      opacity: fade2(lt, 0.5, dur - 0.8, dur)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 13.5,
      letterSpacing: '0.16em',
      color: COL.ink3
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "\u259A"), "\xA0\xA0", kick), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 800,
      fontSize: 42,
      letterSpacing: '-0.03em',
      color: COL.ink,
      marginTop: 13
    }
  }, title, " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, accent)));
}

// ── React surface ────────────────────────────────────────────────────────
function SceneReact() {
  const {
    localTime: lt
  } = uS2();
  const comps = ['<VaultGate>', '<SubscribeButton>', '<UnlockablePill>', '<VaultCard>', '<HeartbeatTimer>', '<TimeWindowBadge>', '<MultiSigSigner>', '<EscrowDeliveryConfirm>', '<ConditionBadge>', '<IpPrice>'];
  const hooks = ['useAccessVault()', 'useSubscribeAndAccess()', 'useDeadManTimer()', 'useMultiSigStatus()', 'useEscrowState()', 'usePublish()'];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.4,
    cx: "50%",
    cy: "28%"
  }), /*#__PURE__*/React.createElement(SceneHead, {
    lt: lt,
    kick: "REACT LAYER",
    title: "Drop it into",
    accent: "your UI.",
    dur: 6
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 168,
      left: 96,
      width: 660
    }
  }, /*#__PURE__*/React.createElement(WinCard, {
    x: 0,
    y: 0,
    w: 660,
    title: "@cdr-kit/react \xB7 components"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: 10
    }
  }, comps.map((c, i) => {
    const p = A2({
      from: 0,
      to: 1,
      start: 0.3 + i * 0.12,
      end: 0.8 + i * 0.12,
      ease: Easing.easeOutBack
    })(lt);
    return /*#__PURE__*/React.createElement("span", {
      key: c,
      style: {
        opacity: p,
        transform: `translateY(${(1 - p) * 10}px)`
      }
    }, /*#__PURE__*/React.createElement(Chip2, {
      tone: i === 0 ? 'primary' : undefined
    }, c));
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 14,
      paddingTop: 13,
      borderTop: `1px solid ${COL.line}`,
      fontFamily: FONT.sans,
      fontSize: 13.5,
      color: COL.ink3,
      opacity: A2({
        from: 0,
        to: 1,
        start: 1.8,
        end: 2.4
      })(lt)
    }
  }, "headless ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink2
    }
  }, "@cdr-kit/react"), " \xB7 styled ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink2
    }
  }, "@cdr-kit/react-ui"), " \xB7 mock mode, no wallet needed"))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 168,
      left: 792,
      width: 392
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: COL.card,
      border: `1px solid ${COL.line}`,
      borderRadius: 14,
      padding: '16px 18px',
      boxShadow: '0 14px 40px -22px rgba(43,39,36,0.25)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 12,
      letterSpacing: '0.1em',
      color: COL.ink3,
      marginBottom: 10
    }
  }, "17 HOOKS"), hooks.map((h, i) => /*#__PURE__*/React.createElement("div", {
    key: h,
    style: {
      fontFamily: FONT.mono,
      fontSize: 14.5,
      color: COL.ink,
      marginBottom: 7,
      opacity: A2({
        from: 0,
        to: 1,
        start: 1.0 + i * 0.14,
        end: 1.5 + i * 0.14
      })(lt)
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "\u203A"), " ", h))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 14,
      background: COL.primarySoft,
      border: `1px solid ${COL.primaryLine}`,
      borderRadius: 14,
      padding: '14px 18px',
      opacity: A2({
        from: 0,
        to: 1,
        start: 2.6,
        end: 3.3
      })(lt)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      color: COL.primary,
      fontWeight: 700
    }
  }, "@cdr-kit/forms"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.sans,
      fontSize: 13.5,
      color: COL.ink2,
      marginTop: 4
    }
  }, "Encrypted, on-chain forms & surveys \u2014 the Confide pattern."))));
}

// ── Condition library ──────────────────────────────────────────────────────
function SceneConditions() {
  const {
    localTime: lt
  } = uS2();
  const conds = [['Subscription', 'recurring paid access'], ['TierGate', 'Story license tier'], ['Composable', 'AND / OR, 8 deep'], ['Open', 'public fallback'], ['CreatorWrite', 'gate writes'], ['TimeWindow', '[start, end] window'], ['DeadManSwitch', 'poke() or unlock'], ['ConditionalEscrow', 'pay → confirm → read'], ['MultiSig', 'N-of-M · dual-path'], ['CdrKitVault', 'factory · one tx']];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper2
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.35,
    cx: "50%",
    cy: "30%"
  }), /*#__PURE__*/React.createElement(SceneHead, {
    lt: lt,
    kick: "CONDITION STANDARD LIBRARY",
    title: "Nine conditions \u2014",
    accent: "deployed & tested.",
    dur: 5
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 180,
      left: '50%',
      transform: 'translateX(-50%)',
      width: 980,
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: 12
    }
  }, conds.map((c, i) => {
    const factory = c[0] === 'CdrKitVault';
    const p = A2({
      from: 0,
      to: 1,
      start: 0.4 + i * 0.11,
      end: 0.95 + i * 0.11,
      ease: Easing.easeOutBack
    })(lt);
    return /*#__PURE__*/React.createElement("div", {
      key: c[0],
      style: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 14,
        background: factory ? COL.primarySoft : COL.card,
        border: `1px solid ${factory ? COL.primaryLine : COL.line}`,
        borderRadius: 11,
        padding: '13px 18px',
        opacity: p,
        transform: `translateY(${(1 - p) * 12}px)`,
        boxShadow: '0 6px 18px -12px rgba(43,39,36,0.2)'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: FONT.mono,
        fontSize: 16,
        fontWeight: 500,
        color: factory ? COL.primary : COL.ink
      }
    }, c[0]), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: FONT.sans,
        fontSize: 13.5,
        color: COL.ink2
      }
    }, c[1]));
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      bottom: 54,
      left: 0,
      right: 0,
      textAlign: 'center',
      fontFamily: FONT.mono,
      fontSize: 14,
      color: COL.ink3,
      opacity: A2({
        from: 0,
        to: 1,
        start: 2.0,
        end: 2.8
      })(lt)
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink2
    }
  }, "checkReadCondition(uuid, \u2026)"), " \u2014 a view fn the validators call \xB7 ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.signal
    }
  }, "\u25CF live on Aeneid \xB7 1315")));
}

// ── Agents everywhere ──────────────────────────────────────────────────────
function SceneEverywhere() {
  const {
    localTime: lt
  } = uS2();
  const lines = [['⚙ ', 'discover → matched vault 4200', COL.primary, 0.5], ['⚙ ', 'subscribe_and_access → paid 5 $IP', COL.primary, 1.2], ['✓ ', 'decrypted locally · BUY ETH/USD', COL.signal, 1.9]];
  const hosts = ['Claude Desktop', 'Cursor', 'Windsurf', 'OpenClaw'];
  const adapters = ['vercel-ai', 'openai', 'langchain', 'agentkit', 'goat'];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.4,
    cx: "50%",
    cy: "26%"
  }), /*#__PURE__*/React.createElement(SceneHead, {
    lt: lt,
    kick: "AGENT KIT \xB7 MCP \xB7 CLI",
    title: "An agent buys data \u2014",
    accent: "from any host.",
    dur: 6.5
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 176,
      left: 96,
      width: 560
    }
  }, /*#__PURE__*/React.createElement(WinCard, {
    x: 0,
    y: 0,
    w: 560,
    title: "cdr-kit-example \xB7 vercel-ai"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 15.5,
      lineHeight: 1.85,
      minHeight: 108
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      color: COL.ink3
    }
  }, "$ agent run --intent \"trading signal\""), lines.map(([pre, txt, col, t], i) => {
    const o = A2({
      from: 0,
      to: 1,
      start: t,
      end: t + 0.3
    })(lt);
    const shown = typed2(txt, A2({
      from: 0,
      to: 1,
      start: t,
      end: t + 0.5
    })(lt));
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        opacity: o,
        color: col
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        color: pre === '✓ ' ? COL.signal : COL.ink3
      }
    }, pre), shown);
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 8,
      fontFamily: FONT.mono,
      fontSize: 13,
      color: COL.ink3,
      opacity: A2({
        from: 0,
        to: 1,
        start: 2.6,
        end: 3.2
      })(lt)
    }
  }, "the LLM never sees the private key"))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 176,
      left: 700,
      width: 484
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      opacity: A2({
        from: 0,
        to: 1,
        start: 1.0,
        end: 1.6
      })(lt),
      marginBottom: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 12,
      letterSpacing: '0.1em',
      color: COL.ink3,
      marginBottom: 9
    }
  }, "MCP HOSTS"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: 8
    }
  }, hosts.map((h, i) => /*#__PURE__*/React.createElement("span", {
    key: h,
    style: {
      opacity: A2({
        from: 0,
        to: 1,
        start: 1.1 + i * 0.1,
        end: 1.6 + i * 0.1
      })(lt)
    }
  }, /*#__PURE__*/React.createElement(Chip2, null, h))))), /*#__PURE__*/React.createElement("div", {
    style: {
      opacity: A2({
        from: 0,
        to: 1,
        start: 1.8,
        end: 2.4
      })(lt),
      marginBottom: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 12,
      letterSpacing: '0.1em',
      color: COL.ink3,
      marginBottom: 9
    }
  }, "5 FRAMEWORK ADAPTERS"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: 8
    }
  }, adapters.map((h, i) => /*#__PURE__*/React.createElement("span", {
    key: h,
    style: {
      opacity: A2({
        from: 0,
        to: 1,
        start: 1.9 + i * 0.09,
        end: 2.4 + i * 0.09
      })(lt)
    }
  }, /*#__PURE__*/React.createElement(Chip2, null, h))))), /*#__PURE__*/React.createElement("div", {
    style: {
      opacity: A2({
        from: 0,
        to: 1,
        start: 2.7,
        end: 3.3
      })(lt),
      display: 'flex',
      gap: 10
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      background: COL.primarySoft,
      border: `1px solid ${COL.primaryLine}`,
      borderRadius: 11,
      padding: '12px 14px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      color: COL.primary,
      fontWeight: 700
    }
  }, "34 tools"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.sans,
      fontSize: 12.5,
      color: COL.ink2,
      marginTop: 3
    }
  }, "one source of truth")), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      background: COL.card,
      border: `1px solid ${COL.line}`,
      borderRadius: 11,
      padding: '12px 14px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      color: COL.ink,
      fontWeight: 700
    }
  }, "cdr \xB7 CLI"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.sans,
      fontSize: 12.5,
      color: COL.ink2,
      marginTop: 3
    }
  }, "25 commands")))));
}

// ── Story IP one-shot ──────────────────────────────────────────────────────
function SceneStory() {
  const {
    localTime: lt
  } = uS2();
  const steps = [['register IP', 'Story SPG'], ['attach PIL', 'license terms'], ['mint license', 'token'], ['gated vault', 'encrypted + paid']];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.4,
    cx: "50%",
    cy: "30%"
  }), /*#__PURE__*/React.createElement(SceneHead, {
    lt: lt,
    kick: "@cdr-kit/story",
    title: "Gated by real",
    accent: "Story IP.",
    dur: 5
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 212,
      left: '50%',
      transform: 'translateX(-50%)',
      textAlign: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 20,
      color: COL.ink,
      opacity: A2({
        from: 0,
        to: 1,
        start: 0.3,
        end: 0.9
      })(lt)
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "await"), " agent.", /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#b5532f'
    }
  }, "publish"), "(", '{ data, pilTerms }', ")"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 0,
      marginTop: 34,
      justifyContent: 'center'
    }
  }, steps.map((s, i) => {
    const p = A2({
      from: 0,
      to: 1,
      start: 1.0 + i * 0.45,
      end: 1.55 + i * 0.45,
      ease: Easing.easeOutBack
    })(lt);
    const last = i === steps.length - 1;
    return /*#__PURE__*/React.createElement(React.Fragment, {
      key: s[0]
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        width: 184,
        background: last ? COL.primarySoft : COL.card,
        border: `1px solid ${last ? COL.primaryLine : COL.line}`,
        borderRadius: 12,
        padding: '16px 14px',
        opacity: p,
        transform: `scale(${0.85 + 0.15 * p})`,
        boxShadow: '0 10px 28px -16px rgba(43,39,36,0.25)'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: FONT.mono,
        fontSize: 15,
        fontWeight: 700,
        color: last ? COL.primary : COL.ink
      }
    }, s[0]), /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: FONT.sans,
        fontSize: 12.5,
        color: COL.ink2,
        marginTop: 4
      }
    }, s[1])), !last && /*#__PURE__*/React.createElement("div", {
      style: {
        width: 34,
        textAlign: 'center',
        color: COL.ink3,
        fontSize: 20,
        opacity: A2({
          from: 0,
          to: 1,
          start: 1.45 + i * 0.45,
          end: 1.8 + i * 0.45
        })(lt)
      }
    }, "\u2192"));
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 30,
      fontFamily: FONT.sans,
      fontSize: 17,
      color: COL.ink2,
      opacity: A2({
        from: 0,
        to: 1,
        start: 3.1,
        end: 3.7
      })(lt)
    }
  }, "One call \u2014 IP + license + encrypted vault. PIL flavors: ", /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      color: COL.ink
    }
  }, "commercialUse \xB7 commercialRemix \xB7 nonCommercial"))));
}

// ── Scaffolder / templates (blog · paywall · forms · data-marketplace · mcp · agents) ──
function SceneTemplates() {
  const {
    localTime: lt
  } = uS2();
  const tpls = [['starter', 0], ['blog', 1], ['paywall', 1], ['data-marketplace', 1], ['forms', 1], ['mcp-server', 0], ['agent-vercel-ai', 0], ['agent-openai', 0], ['agent-langchain', 0], ['agent-agentkit', 0], ['agent-goat', 0]];
  const unlock = A2({
    from: 0,
    to: 1,
    start: 2.4,
    end: 3.0,
    ease: Easing.easeOutBack
  })(lt);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper2
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.38,
    cx: "30%",
    cy: "28%"
  }), /*#__PURE__*/React.createElement(SceneHead, {
    lt: lt,
    kick: "create-cdr-kit-app",
    title: "Scaffold any",
    accent: "pattern.",
    dur: 5.5
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 172,
      left: 96,
      width: 600
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: COL.card,
      border: `1px solid ${COL.line}`,
      borderRadius: 12,
      padding: '14px 18px',
      fontFamily: FONT.mono,
      fontSize: 16,
      color: COL.ink,
      boxShadow: '0 12px 32px -20px rgba(43,39,36,0.25)',
      opacity: A2({
        from: 0,
        to: 1,
        start: 0.3,
        end: 0.9
      })(lt)
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "$"), " npm create cdr-kit my-blog ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink3
    }
  }, "--"), " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.signal
    }
  }, "--template blog")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: 9,
      marginTop: 18
    }
  }, tpls.map((t, i) => {
    const p = A2({
      from: 0,
      to: 1,
      start: 0.8 + i * 0.1,
      end: 1.3 + i * 0.1,
      ease: Easing.easeOutBack
    })(lt);
    return /*#__PURE__*/React.createElement("span", {
      key: t[0],
      style: {
        opacity: p,
        transform: `translateY(${(1 - p) * 10}px)`
      }
    }, /*#__PURE__*/React.createElement(Chip2, {
      tone: t[1] ? 'primary' : undefined
    }, t[0]));
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 18,
      fontFamily: FONT.sans,
      fontSize: 14,
      color: COL.ink3,
      opacity: A2({
        from: 0,
        to: 1,
        start: 2.4,
        end: 3.0
      })(lt)
    }
  }, "Working app in under a minute \u2014 mock CDR out of the box, one swap to go live.")), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 172,
      left: 740,
      width: 444
    }
  }, /*#__PURE__*/React.createElement(WinCard, {
    x: 0,
    y: 0,
    w: 444,
    title: "my-blog \xB7 onscroll pattern"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 700,
      fontSize: 21,
      letterSpacing: '-0.02em',
      color: COL.ink
    }
  }, "The alpha leak, Q3"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.sans,
      fontSize: 13.5,
      color: COL.ink2,
      marginTop: 8,
      lineHeight: 1.55
    }
  }, "The signal held through the quarter. Here's the full breakdown of where the flow went and why it\u2026"), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      marginTop: 12,
      borderRadius: 10,
      overflow: 'hidden',
      border: `1px solid ${COL.line}`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '16px 14px',
      filter: 'blur(3px)',
      opacity: 0.6
    }
  }, [92, 80, 86, 72].map((w, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      height: 9,
      width: `${w}%`,
      background: COL.line2,
      borderRadius: 5,
      marginBottom: 9
    }
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(180deg, rgba(252,251,248,0.2), rgba(252,251,248,0.85))'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 9,
      whiteSpace: 'nowrap',
      background: COL.primary,
      color: '#fff',
      fontFamily: FONT.mono,
      fontSize: 14,
      fontWeight: 600,
      padding: '10px 16px',
      borderRadius: 999,
      boxShadow: '0 8px 22px -8px rgba(58,90,219,0.6)',
      transform: `scale(${0.85 + 0.15 * unlock})`,
      opacity: unlock
    }
  }, /*#__PURE__*/React.createElement(Lock, {
    open: false,
    color: "#fff",
    size: 15
  }), " Unlock to read \xB7 2 $IP"))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 11,
      fontFamily: FONT.mono,
      fontSize: 11.5,
      color: COL.ink3,
      opacity: A2({
        from: 0,
        to: 1,
        start: 3.0,
        end: 3.6
      })(lt)
    }
  }, "<UnlockablePill /> \xB7 pay inline, decrypt in place"))));
}
Object.assign(window, {
  SceneReact,
  SceneConditions,
  SceneEverywhere,
  SceneStory,
  SceneTemplates
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "video/scenes2.jsx", error: String((e && e.message) || e) }); }

// video/sound.jsx
try { (() => {
// sound.jsx — procedural Web Audio score for the cdr-kit explainer (v2).
// Warm, musical bed: I–V–vi–IV progression in C, sub-bass pulse, soft kick +
// hat groove, plucked melody through a tape-echo, slow swelling pads, and
// in-key mallet cues synced to each scene. Renders only a mute toggle.
// Place <SoundTrack/> inside <Stage> so it can read the timeline.

const mtof = m => 440 * Math.pow(2, (m - 69) / 12);

// I–V–vi–IV in C major. Each chord = one bar.
// triad notes (mid octave) + bass root (low).
const PROG = [{
  name: 'C',
  bass: 36,
  triad: [48, 52, 55],
  color: [55, 60, 64]
},
// C  E  G
{
  name: 'G',
  bass: 31,
  triad: [47, 50, 55],
  color: [50, 55, 62]
},
// G  B  D
{
  name: 'Am',
  bass: 33,
  triad: [45, 48, 52],
  color: [52, 57, 60]
},
// A  C  E
{
  name: 'F',
  bass: 29,
  triad: [45, 48, 53],
  color: [53, 57, 60]
} // F  A  C
];

// Melody pattern over 16 sixteenth-steps. Values index into the chord's
// "color" notes (transposed up an octave); null = rest. Gives a gentle,
// syncopated pluck line that always sits inside the current chord.
const MEL = [0, null, 2, null, 1, null, null, 2, 0, null, 1, null, 2, null, 1, null];
const BPM = 84;
const STEP = 60 / BPM / 4; // sixteenth-note duration (s)

function buildReverbIR(ctx, seconds = 2.2, decay = 3.2) {
  const rate = ctx.sampleRate;
  const len = Math.floor(rate * seconds);
  const ir = ctx.createBuffer(2, len, rate);
  for (let ch = 0; ch < 2; ch++) {
    const d = ir.getChannelData(ch);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay);
  }
  return ir;
}
function SoundTrack() {
  const {
    time,
    playing
  } = useTimeline();
  const [enabled, setEnabled] = React.useState(true);
  const [ready, setReady] = React.useState(false);
  const ref = React.useRef({
    ctx: null,
    master: null,
    music: null,
    cue: null,
    reverb: null,
    delay: null,
    pad: [],
    schedulerId: null,
    nextNote: 0,
    step: 0,
    lastTime: 0,
    started: false
  });
  const ensureAudio = React.useCallback(() => {
    const S = ref.current;
    if (S.ctx) {
      if (S.ctx.state === 'suspended') S.ctx.resume();
      return S;
    }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    const ctx = new AC();
    const master = ctx.createGain();
    master.gain.value = enabled ? 0.85 : 0.0001;
    const limiter = ctx.createDynamicsCompressor();
    limiter.threshold.value = -8;
    limiter.knee.value = 8;
    limiter.ratio.value = 14;
    limiter.attack.value = 0.003;
    limiter.release.value = 0.25;
    master.connect(limiter);
    limiter.connect(ctx.destination);
    const reverb = ctx.createConvolver();
    reverb.buffer = buildReverbIR(ctx);
    const revGain = ctx.createGain();
    revGain.gain.value = 0.32;
    reverb.connect(revGain);
    revGain.connect(master);

    // tape-style feedback delay (for melody sparkle)
    const delay = ctx.createDelay(1.0);
    delay.delayTime.value = STEP * 3; // dotted-ish echo
    const fb = ctx.createGain();
    fb.gain.value = 0.34;
    const delayTone = ctx.createBiquadFilter();
    delayTone.type = 'lowpass';
    delayTone.frequency.value = 2200;
    const delayWet = ctx.createGain();
    delayWet.gain.value = 0.45;
    delay.connect(delayTone);
    delayTone.connect(fb);
    fb.connect(delay);
    delay.connect(delayWet);
    delayWet.connect(master);
    delayWet.connect(reverb);
    const music = ctx.createGain();
    music.gain.value = 0.0001;
    music.connect(master);
    music.connect(reverb);
    const cue = ctx.createGain();
    cue.gain.value = 0.6;
    cue.connect(master);
    cue.connect(reverb);
    Object.assign(S, {
      ctx,
      master,
      music,
      cue,
      reverb,
      delay
    });
    setReady(true);
    return S;
  }, [enabled]);
  React.useEffect(() => {
    const kick = () => ensureAudio();
    window.addEventListener('pointerdown', kick);
    window.addEventListener('keydown', kick);
    return () => {
      window.removeEventListener('pointerdown', kick);
      window.removeEventListener('keydown', kick);
    };
  }, [ensureAudio]);

  // ── voice helpers ──────────────────────────────────────────────
  const voice = React.useCallback((midi, at, dur, opt = {}) => {
    const S = ref.current;
    if (!S.ctx) return;
    const {
      type = 'triangle',
      peak = 0.1,
      cutoff = 2600,
      dest = S.music,
      send
    } = opt;
    const osc = S.ctx.createOscillator();
    osc.type = type;
    osc.frequency.value = mtof(midi);
    if (opt.detune) osc.detune.value = opt.detune;
    const lp = S.ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = cutoff;
    const g = S.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(peak, at + (opt.attack || 0.008));
    g.gain.exponentialRampToValueAtTime(0.0001, at + dur);
    osc.connect(lp);
    lp.connect(g);
    g.connect(dest);
    if (send) g.connect(send);
    osc.start(at);
    osc.stop(at + dur + 0.05);
  }, []);
  const kickHit = React.useCallback(at => {
    const S = ref.current;
    if (!S.ctx) return;
    const osc = S.ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(140, at);
    osc.frequency.exponentialRampToValueAtTime(45, at + 0.12);
    const g = S.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(0.55, at + 0.006);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 0.22);
    osc.connect(g);
    g.connect(S.master);
    osc.start(at);
    osc.stop(at + 0.28);
  }, []);
  const hatHit = React.useCallback((at, vel = 0.05) => {
    const S = ref.current;
    if (!S.ctx) return;
    const len = Math.floor(S.ctx.sampleRate * 0.04);
    const buf = S.ctx.createBuffer(1, len, S.ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len);
    const src = S.ctx.createBufferSource();
    src.buffer = buf;
    const hp = S.ctx.createBiquadFilter();
    hp.type = 'highpass';
    hp.frequency.value = 7500;
    const g = S.ctx.createGain();
    g.gain.setValueAtTime(vel, at);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 0.04);
    src.connect(hp);
    hp.connect(g);
    g.connect(S.master);
    src.start(at);
    src.stop(at + 0.06);
  }, []);

  // ── pad: swell the current chord, retrigger each bar ──
  const swellPad = React.useCallback((chord, at) => {
    const S = ref.current;
    if (!S.ctx) return;
    // fade out previous pad
    S.pad.forEach(({
      g,
      osc
    }) => {
      try {
        g.gain.cancelScheduledValues(at);
        g.gain.setValueAtTime(g.gain.value, at);
        g.gain.exponentialRampToValueAtTime(0.0001, at + 1.4);
        osc.stop(at + 1.5);
      } catch (e) {}
    });
    S.pad = chord.color.map((m, i) => {
      const osc = S.ctx.createOscillator();
      osc.type = i % 2 ? 'triangle' : 'sine';
      osc.frequency.value = mtof(m);
      osc.detune.value = (i - 1) * 5;
      const lp = S.ctx.createBiquadFilter();
      lp.type = 'lowpass';
      lp.frequency.value = 1500;
      const g = S.ctx.createGain();
      g.gain.setValueAtTime(0.0001, at);
      g.gain.exponentialRampToValueAtTime(0.045, at + 1.2); // slow swell
      osc.connect(lp);
      lp.connect(g);
      g.connect(S.music);
      osc.start(at);
      return {
        osc,
        g
      };
    });
  }, []);

  // ── scheduler ──
  React.useEffect(() => {
    const S = ref.current;
    if (!ready) return;
    if (playing) {
      if (S.ctx.state === 'suspended') S.ctx.resume();
      const now = S.ctx.currentTime;
      S.music.gain.cancelScheduledValues(now);
      S.music.gain.setValueAtTime(Math.max(0.0001, S.music.gain.value), now);
      S.music.gain.exponentialRampToValueAtTime(0.55, now + 1.0);
      if (!S.started) {
        S.nextNote = S.ctx.currentTime + 0.1;
        S.step = 0;
        S.started = true;
      }
      const tick = () => {
        const ahead = S.ctx.currentTime + 0.14;
        while (S.nextNote < ahead) {
          const at = S.nextNote;
          const s16 = S.step % 16;
          const bar = Math.floor(S.step / 16);
          const chord = PROG[bar % PROG.length];
          if (s16 === 0) swellPad(chord, at); // new chord swell
          if (s16 % 8 === 0) kickHit(at); // kick on beats 1 & 3
          if (s16 % 4 === 0) voice(chord.bass, at, 0.5,
          // sub bass on each beat
          {
            type: 'sine',
            peak: 0.22,
            cutoff: 600,
            attack: 0.012
          });
          if (s16 % 2 === 1) hatHit(at, s16 === 7 ? 0.07 : 0.04); // offbeat hats

          const mi = MEL[s16];
          if (mi != null) {
            // plucked melody (8va) w/ echo
            const note = chord.color[mi] + 12;
            voice(note, at, 0.4, {
              type: 'triangle',
              peak: 0.085,
              cutoff: 3200,
              send: S.delay
            });
          }
          S.step++;
          S.nextNote += STEP;
        }
      };
      tick();
      S.schedulerId = setInterval(tick, 25);
      return () => {
        clearInterval(S.schedulerId);
        S.schedulerId = null;
      };
    } else {
      if (S.ctx) {
        const now = S.ctx.currentTime;
        S.music.gain.cancelScheduledValues(now);
        S.music.gain.setValueAtTime(Math.max(0.0001, S.music.gain.value), now);
        S.music.gain.exponentialRampToValueAtTime(0.0001, now + 0.35);
        S.pad.forEach(({
          g,
          osc
        }) => {
          try {
            g.gain.cancelScheduledValues(now);
            g.gain.setValueAtTime(g.gain.value, now);
            g.gain.exponentialRampToValueAtTime(0.0001, now + 0.35);
            osc.stop(now + 0.4);
          } catch (e) {}
        });
        S.pad = [];
      }
      S.started = false;
    }
  }, [playing, ready, swellPad, voice, kickHit, hatHit]);

  // ── scene cues: in-key mallet motifs synced to the visuals ──
  const fireCue = React.useCallback(kind => {
    const S = ref.current;
    if (!S.ctx) return;
    const now = S.ctx.currentTime;
    const mallet = (m, off, dur = 0.7, peak = 0.5) => voice(m, now + off, dur, {
      type: 'sine',
      peak,
      cutoff: 3400,
      dest: S.cue,
      send: S.delay
    });
    if (kind === 'blip') {
      mallet(84, 0, 0.5, 0.4);
      mallet(79, 0.05, 0.55, 0.22); // soft bell, C/G
    } else if (kind === 'intro') {
      [60, 64, 67, 72, 79].forEach((m, i) => mallet(m, i * 0.085, 0.9, 0.42)); // rising Cmaj
    } else if (kind === 'sweep') {
      const len = Math.floor(S.ctx.sampleRate * 0.7);
      const buf = S.ctx.createBuffer(1, len, S.ctx.sampleRate);
      const d = buf.getChannelData(0);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (i / len);
      const src = S.ctx.createBufferSource();
      src.buffer = buf;
      const bp = S.ctx.createBiquadFilter();
      bp.type = 'bandpass';
      bp.Q.value = 1.3;
      bp.frequency.setValueAtTime(450, now);
      bp.frequency.exponentialRampToValueAtTime(4500, now + 0.6);
      const g = S.ctx.createGain();
      g.gain.setValueAtTime(0.0001, now);
      g.gain.exponentialRampToValueAtTime(0.22, now + 0.1);
      g.gain.exponentialRampToValueAtTime(0.0001, now + 0.7);
      src.connect(bp);
      bp.connect(g);
      g.connect(S.cue);
      g.connect(S.reverb);
      src.start(now);
      src.stop(now + 0.72);
      mallet(83, 0.12, 0.6, 0.3);
    } else if (kind === 'outro') {
      [48, 55, 60, 64, 67, 72].forEach((m, i) => mallet(m, i * 0.05, 2.0, 0.4)); // full Cmaj resolve
    }
  }, [voice]);
  React.useEffect(() => {
    const S = ref.current;
    const prev = S.lastTime;
    S.lastTime = time;
    if (!ready || !playing) return;
    if (time >= prev) {
      for (const c of SCENE_CUES) if (prev < c.t && time >= c.t) fireCue(c.kind);
    }
  }, [time, ready, playing, fireCue]);
  React.useEffect(() => {
    const S = ref.current;
    if (!S.ctx) return;
    const now = S.ctx.currentTime;
    S.master.gain.cancelScheduledValues(now);
    S.master.gain.setValueAtTime(Math.max(0.0001, S.master.gain.value), now);
    S.master.gain.exponentialRampToValueAtTime(enabled ? 0.85 : 0.0001, now + 0.15);
  }, [enabled]);
  const toggle = () => {
    ensureAudio();
    setEnabled(e => !e);
  };
  return /*#__PURE__*/React.createElement("button", {
    onClick: toggle,
    title: enabled ? 'Mute sound' : 'Unmute sound',
    style: {
      position: 'absolute',
      top: 16,
      right: 16,
      zIndex: 50,
      width: 40,
      height: 40,
      borderRadius: 10,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'rgba(20,20,20,0.55)',
      border: '1px solid rgba(255,255,255,0.18)',
      color: '#f6f4ef',
      cursor: 'pointer',
      backdropFilter: 'blur(6px)',
      padding: 0
    }
  }, enabled ? /*#__PURE__*/React.createElement("svg", {
    width: "20",
    height: "20",
    viewBox: "0 0 24 24",
    fill: "none"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M4 9v6h4l5 4V5L8 9H4z",
    fill: "currentColor"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M16 8.5a4 4 0 010 7M18.5 6a7.5 7.5 0 010 12",
    stroke: "currentColor",
    strokeWidth: "1.6",
    strokeLinecap: "round"
  })) : /*#__PURE__*/React.createElement("svg", {
    width: "20",
    height: "20",
    viewBox: "0 0 24 24",
    fill: "none"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M4 9v6h4l5 4V5L8 9H4z",
    fill: "currentColor"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M17 9.5l4 5M21 9.5l-4 5",
    stroke: "currentColor",
    strokeWidth: "1.6",
    strokeLinecap: "round"
  })));
}

// scene start times -> cue type
const SCENE_CUES = [{
  t: 0.05,
  kind: 'intro'
}, {
  t: 4.5,
  kind: 'blip'
}, {
  t: 9.5,
  kind: 'blip'
}, {
  t: 15.5,
  kind: 'blip'
}, {
  t: 19.5,
  kind: 'blip'
}, {
  t: 25.0,
  kind: 'blip'
}, {
  t: 30.5,
  kind: 'blip'
}, {
  t: 35.0,
  kind: 'sweep'
}, {
  t: 41.0,
  kind: 'blip'
}, {
  t: 46.0,
  kind: 'outro'
}];
Object.assign(window, {
  SoundTrack
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "video/sound.jsx", error: String((e && e.message) || e) }); }

// video/v1-explainer/animations.jsx
try { (() => {
// @ds-adherence-ignore -- omelette starter scaffold (raw elements/hex/px by design)

/* BEGIN USAGE */
// animations.jsx
// Reusable animation starter: Stage, Timeline, Sprite, easing helpers.
// Exports (to window): Stage, Sprite, PlaybackBar, TextSprite, ImageSprite, RectSprite,
//   useTime, useTimeline, useSprite, Easing, interpolate, animate, clamp.
//
// Usage (in an HTML file that loads React + Babel):
//
//   <Stage width={1280} height={720} duration={10} background="#f6f4ef">
//     <MyScene />
//   </Stage>
//
// <Stage> auto-scales to the viewport and provides the scrubber, play/pause,
// ←/→ seek, space, and 0-to-reset controls, and persists the playhead.
// Inside <Stage>, any child can call useTime() to read the current
// playhead (seconds). Or wrap content in <Sprite start={1} end={4}>...</Sprite>
// to only render during that window -- children receive a `localTime` and
// `progress` via the useSprite() hook. Use Easing + interpolate()/animate()
// for tweens; TextSprite / ImageSprite / RectSprite have built-in entry/exit.
// Build YOUR scenes by composing Sprites inside a Stage.
/* END USAGE */
// ─────────────────────────────────────────────────────────────────────────────

// ── Easing functions (hand-rolled, Popmotion-style) ─────────────────────────
// All easings take t ∈ [0,1] and return eased t ∈ [0,1] (may overshoot for back/elastic).
const Easing = {
  linear: t => t,
  // Quad
  easeInQuad: t => t * t,
  easeOutQuad: t => t * (2 - t),
  easeInOutQuad: t => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,
  // Cubic
  easeInCubic: t => t * t * t,
  easeOutCubic: t => --t * t * t + 1,
  easeInOutCubic: t => t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1,
  // Quart
  easeInQuart: t => t * t * t * t,
  easeOutQuart: t => 1 - --t * t * t * t,
  easeInOutQuart: t => t < 0.5 ? 8 * t * t * t * t : 1 - 8 * --t * t * t * t,
  // Expo
  easeInExpo: t => t === 0 ? 0 : Math.pow(2, 10 * (t - 1)),
  easeOutExpo: t => t === 1 ? 1 : 1 - Math.pow(2, -10 * t),
  easeInOutExpo: t => {
    if (t === 0) return 0;
    if (t === 1) return 1;
    if (t < 0.5) return 0.5 * Math.pow(2, 20 * t - 10);
    return 1 - 0.5 * Math.pow(2, -20 * t + 10);
  },
  // Sine
  easeInSine: t => 1 - Math.cos(t * Math.PI / 2),
  easeOutSine: t => Math.sin(t * Math.PI / 2),
  easeInOutSine: t => -(Math.cos(Math.PI * t) - 1) / 2,
  // Back (overshoot)
  easeOutBack: t => {
    const c1 = 1.70158,
      c3 = c1 + 1;
    return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
  },
  easeInBack: t => {
    const c1 = 1.70158,
      c3 = c1 + 1;
    return c3 * t * t * t - c1 * t * t;
  },
  easeInOutBack: t => {
    const c1 = 1.70158,
      c2 = c1 * 1.525;
    return t < 0.5 ? Math.pow(2 * t, 2) * ((c2 + 1) * 2 * t - c2) / 2 : (Math.pow(2 * t - 2, 2) * ((c2 + 1) * (t * 2 - 2) + c2) + 2) / 2;
  },
  // Elastic
  easeOutElastic: t => {
    const c4 = 2 * Math.PI / 3;
    if (t === 0) return 0;
    if (t === 1) return 1;
    return Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1;
  }
};

// ── Core interpolation helpers ──────────────────────────────────────────────

// Clamp a value to [min, max]
const clamp = (v, min, max) => Math.max(min, Math.min(max, v));

// interpolate([0, 0.5, 1], [0, 100, 50], ease?) -> fn(t)
// Popmotion-style: linearly maps t across input keyframes to output values,
// with optional easing per segment (single fn or array of fns).
function interpolate(input, output, ease = Easing.linear) {
  return t => {
    if (t <= input[0]) return output[0];
    if (t >= input[input.length - 1]) return output[output.length - 1];
    for (let i = 0; i < input.length - 1; i++) {
      if (t >= input[i] && t <= input[i + 1]) {
        const span = input[i + 1] - input[i];
        const local = span === 0 ? 0 : (t - input[i]) / span;
        const easeFn = Array.isArray(ease) ? ease[i] || Easing.linear : ease;
        const eased = easeFn(local);
        return output[i] + (output[i + 1] - output[i]) * eased;
      }
    }
    return output[output.length - 1];
  };
}

// animate({from, to, start, end, ease})(t) — simpler single-segment tween.
// Returns `from` before `start`, `to` after `end`.
function animate({
  from = 0,
  to = 1,
  start = 0,
  end = 1,
  ease = Easing.easeInOutCubic
}) {
  return t => {
    if (t <= start) return from;
    if (t >= end) return to;
    const local = (t - start) / (end - start);
    return from + (to - from) * ease(local);
  };
}

// ── Timeline context ────────────────────────────────────────────────────────

const TimelineContext = React.createContext({
  time: 0,
  duration: 10,
  playing: false
});
const useTime = () => React.useContext(TimelineContext).time;
const useTimeline = () => React.useContext(TimelineContext);

// ── Sprite ──────────────────────────────────────────────────────────────────
// Renders children only when the playhead is inside [start, end]. Provides
// a sub-context with `localTime` (seconds since start) and `progress` (0..1).
//
//   <Sprite start={2} end={5}>
//     {({ localTime, progress }) => <Thing x={progress * 100} />}
//   </Sprite>
//
// Or as a plain wrapper — children can call useSprite() themselves.

const SpriteContext = React.createContext({
  localTime: 0,
  progress: 0,
  duration: 0
});
const useSprite = () => React.useContext(SpriteContext);
function Sprite({
  start = 0,
  end = Infinity,
  children,
  keepMounted = false
}) {
  const {
    time
  } = useTimeline();
  const visible = time >= start && time <= end;
  if (!visible && !keepMounted) return null;
  const duration = end - start;
  const localTime = Math.max(0, time - start);
  const progress = duration > 0 && isFinite(duration) ? clamp(localTime / duration, 0, 1) : 0;
  const value = {
    localTime,
    progress,
    duration,
    visible
  };
  return /*#__PURE__*/React.createElement(SpriteContext.Provider, {
    value: value
  }, typeof children === 'function' ? children(value) : children);
}

// ── Sample sprite components ────────────────────────────────────────────────

// TextSprite: fades/slides text in on entry, holds, then fades out on exit.
// Props: text, x, y, size, color, font, entryDur, exitDur, align
function TextSprite({
  text,
  x = 0,
  y = 0,
  size = 48,
  color = '#111',
  font = 'Inter, system-ui, sans-serif',
  weight = 600,
  entryDur = 0.45,
  exitDur = 0.35,
  entryEase = Easing.easeOutBack,
  exitEase = Easing.easeInCubic,
  align = 'left',
  letterSpacing = '-0.01em'
}) {
  const {
    localTime,
    duration
  } = useSprite();
  const exitStart = Math.max(0, duration - exitDur);
  let opacity = 1;
  let ty = 0;
  if (localTime < entryDur) {
    const t = entryEase(clamp(localTime / entryDur, 0, 1));
    opacity = t;
    ty = (1 - t) * 16;
  } else if (localTime > exitStart) {
    const t = exitEase(clamp((localTime - exitStart) / exitDur, 0, 1));
    opacity = 1 - t;
    ty = -t * 8;
  }
  const translateX = align === 'center' ? '-50%' : align === 'right' ? '-100%' : '0';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x,
      top: y,
      transform: `translate(${translateX}, ${ty}px)`,
      opacity,
      fontFamily: font,
      fontSize: size,
      fontWeight: weight,
      color,
      letterSpacing,
      whiteSpace: 'pre',
      lineHeight: 1.1,
      willChange: 'transform, opacity'
    }
  }, text);
}

// ImageSprite: scales + fades in; optional Ken Burns drift during hold.
function ImageSprite({
  src,
  x = 0,
  y = 0,
  width = 400,
  height = 300,
  entryDur = 0.6,
  exitDur = 0.4,
  kenBurns = false,
  kenBurnsScale = 1.08,
  radius = 12,
  fit = 'cover',
  placeholder = null // {label: string} for striped placeholder
}) {
  const {
    localTime,
    duration
  } = useSprite();
  const exitStart = Math.max(0, duration - exitDur);
  let opacity = 1;
  let scale = 1;
  if (localTime < entryDur) {
    const t = Easing.easeOutCubic(clamp(localTime / entryDur, 0, 1));
    opacity = t;
    scale = 0.96 + 0.04 * t;
  } else if (localTime > exitStart) {
    const t = Easing.easeInCubic(clamp((localTime - exitStart) / exitDur, 0, 1));
    opacity = 1 - t;
    scale = (kenBurns ? kenBurnsScale : 1) + 0.02 * t;
  } else if (kenBurns) {
    const holdSpan = exitStart - entryDur;
    const holdT = holdSpan > 0 ? (localTime - entryDur) / holdSpan : 0;
    scale = 1 + (kenBurnsScale - 1) * holdT;
  }
  const content = placeholder ? /*#__PURE__*/React.createElement("div", {
    style: {
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'repeating-linear-gradient(135deg, #e9e6df 0 10px, #dcd8cf 10px 20px)',
      color: '#6b6458',
      fontFamily: 'JetBrains Mono, ui-monospace, monospace',
      fontSize: 13,
      letterSpacing: '0.04em',
      textTransform: 'uppercase'
    }
  }, placeholder.label || 'image') : /*#__PURE__*/React.createElement("img", {
    src: src,
    alt: "",
    style: {
      width: '100%',
      height: '100%',
      objectFit: fit,
      display: 'block'
    }
  });
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x,
      top: y,
      width,
      height,
      opacity,
      transform: `scale(${scale})`,
      transformOrigin: 'center',
      borderRadius: radius,
      overflow: 'hidden',
      willChange: 'transform, opacity'
    }
  }, content);
}

// RectSprite: simple rectangle that animates position/size/color via props.
// Useful demo primitive — takes a `render` fn for per-frame customization.
function RectSprite({
  x = 0,
  y = 0,
  width = 100,
  height = 100,
  color = '#111',
  radius = 8,
  entryDur = 0.4,
  exitDur = 0.3,
  render // optional: (ctx) => style overrides
}) {
  const spriteCtx = useSprite();
  const {
    localTime,
    duration
  } = spriteCtx;
  const exitStart = Math.max(0, duration - exitDur);
  let opacity = 1;
  let scale = 1;
  if (localTime < entryDur) {
    const t = Easing.easeOutBack(clamp(localTime / entryDur, 0, 1));
    opacity = clamp(localTime / entryDur, 0, 1);
    scale = 0.4 + 0.6 * t;
  } else if (localTime > exitStart) {
    const t = Easing.easeInQuad(clamp((localTime - exitStart) / exitDur, 0, 1));
    opacity = 1 - t;
    scale = 1 - 0.15 * t;
  }
  const overrides = render ? render(spriteCtx) : {};
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x,
      top: y,
      width,
      height,
      background: color,
      borderRadius: radius,
      opacity,
      transform: `scale(${scale})`,
      transformOrigin: 'center',
      willChange: 'transform, opacity',
      ...overrides
    }
  });
}
function Stage({
  width = 1280,
  height = 720,
  duration = 10,
  background = '#f6f4ef',
  fps = 60,
  loop = true,
  autoplay = true,
  persistKey = 'animstage',
  children
}) {
  const [time, setTime] = React.useState(() => {
    try {
      const v = parseFloat(localStorage.getItem(persistKey + ':t') || '0');
      return isFinite(v) ? clamp(v, 0, duration) : 0;
    } catch {
      return 0;
    }
  });
  const [playing, setPlaying] = React.useState(autoplay);
  const [hoverTime, setHoverTime] = React.useState(null);
  const [scale, setScale] = React.useState(1);
  const stageRef = React.useRef(null);
  const canvasRef = React.useRef(null);
  const rafRef = React.useRef(null);
  const lastTsRef = React.useRef(null);

  // Persist playhead
  React.useEffect(() => {
    try {
      localStorage.setItem(persistKey + ':t', String(time));
    } catch {}
  }, [time, persistKey]);

  // Auto-scale to fit viewport
  React.useEffect(() => {
    if (!stageRef.current) return;
    const el = stageRef.current;
    const measure = () => {
      const barH = 44; // playback bar height
      const s = Math.min(el.clientWidth / width, (el.clientHeight - barH) / height);
      setScale(Math.max(0.05, s));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    window.addEventListener('resize', measure);
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, [width, height]);

  // Animation loop
  React.useEffect(() => {
    if (!playing) {
      lastTsRef.current = null;
      return;
    }
    const step = ts => {
      if (lastTsRef.current == null) lastTsRef.current = ts;
      const dt = (ts - lastTsRef.current) / 1000;
      lastTsRef.current = ts;
      setTime(t => {
        let next = t + dt;
        if (next >= duration) {
          if (loop) next = next % duration;else {
            next = duration;
            setPlaying(false);
          }
        }
        return next;
      });
      rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      lastTsRef.current = null;
    };
  }, [playing, duration, loop]);

  // Keyboard: space = play/pause, ← → = seek
  React.useEffect(() => {
    const onKey = e => {
      if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
      if (e.code === 'Space') {
        e.preventDefault();
        setPlaying(p => !p);
      } else if (e.code === 'ArrowLeft') {
        setTime(t => clamp(t - (e.shiftKey ? 1 : 0.1), 0, duration));
      } else if (e.code === 'ArrowRight') {
        setTime(t => clamp(t + (e.shiftKey ? 1 : 0.1), 0, duration));
      } else if (e.key === '0' || e.code === 'Home') {
        setTime(0);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [duration]);
  const displayTime = hoverTime != null ? hoverTime : time;
  const ctxValue = React.useMemo(() => ({
    time: displayTime,
    duration,
    playing,
    setTime,
    setPlaying
  }), [displayTime, duration, playing]);
  return /*#__PURE__*/React.createElement("div", {
    ref: stageRef,
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      background: '#0a0a0a',
      fontFamily: 'Inter, system-ui, sans-serif'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      width: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      overflow: 'hidden',
      minHeight: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    ref: canvasRef,
    style: {
      width,
      height,
      background,
      position: 'relative',
      transform: `scale(${scale})`,
      transformOrigin: 'center',
      flexShrink: 0,
      boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement(TimelineContext.Provider, {
    value: ctxValue
  }, children))), /*#__PURE__*/React.createElement(PlaybackBar, {
    time: displayTime,
    actualTime: time,
    duration: duration,
    playing: playing,
    onPlayPause: () => setPlaying(p => !p),
    onReset: () => {
      setTime(0);
    },
    onSeek: t => setTime(t),
    onHover: t => setHoverTime(t)
  }));
}

// ── Playback bar ────────────────────────────────────────────────────────────
// Play/pause, return-to-begin, scrub track, time display.
// Uses fixed-width time fields so layout doesn't thrash.

function PlaybackBar({
  time,
  duration,
  playing,
  onPlayPause,
  onReset,
  onSeek,
  onHover
}) {
  const trackRef = React.useRef(null);
  const [dragging, setDragging] = React.useState(false);
  const timeFromEvent = React.useCallback(e => {
    const rect = trackRef.current.getBoundingClientRect();
    const x = clamp((e.clientX - rect.left) / rect.width, 0, 1);
    return x * duration;
  }, [duration]);
  const onTrackMove = e => {
    if (!trackRef.current) return;
    const t = timeFromEvent(e);
    if (dragging) {
      onSeek(t);
    } else {
      onHover(t);
    }
  };
  const onTrackLeave = () => {
    if (!dragging) onHover(null);
  };
  const onTrackDown = e => {
    setDragging(true);
    const t = timeFromEvent(e);
    onSeek(t);
    onHover(null);
  };
  React.useEffect(() => {
    if (!dragging) return;
    const onUp = () => setDragging(false);
    const onMove = e => {
      if (!trackRef.current) return;
      const t = timeFromEvent(e);
      onSeek(t);
    };
    window.addEventListener('mouseup', onUp);
    window.addEventListener('mousemove', onMove);
    return () => {
      window.removeEventListener('mouseup', onUp);
      window.removeEventListener('mousemove', onMove);
    };
  }, [dragging, timeFromEvent, onSeek]);
  const pct = duration > 0 ? time / duration * 100 : 0;
  const fmt = t => {
    const total = Math.max(0, t);
    const m = Math.floor(total / 60);
    const s = Math.floor(total % 60);
    const cs = Math.floor(total * 100 % 100);
    return `${String(m).padStart(1, '0')}:${String(s).padStart(2, '0')}.${String(cs).padStart(2, '0')}`;
  };
  const mono = 'JetBrains Mono, ui-monospace, SFMono-Regular, monospace';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      padding: '8px 16px',
      background: 'rgba(20,20,20,0.92)',
      borderTop: '1px solid rgba(255,255,255,0.08)',
      width: '100%',
      maxWidth: 680,
      alignSelf: 'center',
      borderRadius: 8,
      color: '#f6f4ef',
      fontFamily: 'Inter, system-ui, sans-serif',
      userSelect: 'none',
      flexShrink: 0
    }
  }, /*#__PURE__*/React.createElement(IconButton, {
    onClick: onReset,
    title: "Return to start (0)"
  }, /*#__PURE__*/React.createElement("svg", {
    width: "14",
    height: "14",
    viewBox: "0 0 14 14",
    fill: "none"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M3 2v10M12 2L5 7l7 5V2z",
    stroke: "currentColor",
    strokeWidth: "1.5",
    strokeLinejoin: "round",
    strokeLinecap: "round"
  }))), /*#__PURE__*/React.createElement(IconButton, {
    onClick: onPlayPause,
    title: "Play/pause (space)"
  }, playing ? /*#__PURE__*/React.createElement("svg", {
    width: "14",
    height: "14",
    viewBox: "0 0 14 14",
    fill: "none"
  }, /*#__PURE__*/React.createElement("rect", {
    x: "3",
    y: "2",
    width: "3",
    height: "10",
    fill: "currentColor"
  }), /*#__PURE__*/React.createElement("rect", {
    x: "8",
    y: "2",
    width: "3",
    height: "10",
    fill: "currentColor"
  })) : /*#__PURE__*/React.createElement("svg", {
    width: "14",
    height: "14",
    viewBox: "0 0 14 14",
    fill: "none"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M3 2l9 5-9 5V2z",
    fill: "currentColor"
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: mono,
      fontSize: 12,
      fontVariantNumeric: 'tabular-nums',
      width: 64,
      textAlign: 'right',
      color: '#f6f4ef'
    }
  }, fmt(time)), /*#__PURE__*/React.createElement("div", {
    ref: trackRef,
    onMouseMove: onTrackMove,
    onMouseLeave: onTrackLeave,
    onMouseDown: onTrackDown,
    style: {
      flex: 1,
      height: 22,
      position: 'relative',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      right: 0,
      height: 4,
      background: 'rgba(255,255,255,0.12)',
      borderRadius: 2
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      width: `${pct}%`,
      height: 4,
      background: 'oklch(72% 0.12 250)',
      borderRadius: 2
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: `${pct}%`,
      top: '50%',
      width: 12,
      height: 12,
      marginLeft: -6,
      marginTop: -6,
      background: '#fff',
      borderRadius: 6,
      boxShadow: '0 2px 4px rgba(0,0,0,0.4)'
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: mono,
      fontSize: 12,
      fontVariantNumeric: 'tabular-nums',
      width: 64,
      textAlign: 'left',
      color: 'rgba(246,244,239,0.55)'
    }
  }, fmt(duration)));
}
function IconButton({
  children,
  onClick,
  title
}) {
  const [hover, setHover] = React.useState(false);
  return /*#__PURE__*/React.createElement("button", {
    onClick: onClick,
    title: title,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      width: 28,
      height: 28,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: hover ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.04)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 6,
      color: '#f6f4ef',
      cursor: 'pointer',
      padding: 0,
      transition: 'background 120ms'
    }
  }, children);
}
Object.assign(window, {
  Easing,
  interpolate,
  animate,
  clamp,
  TimelineContext,
  useTime,
  useTimeline,
  Sprite,
  SpriteContext,
  useSprite,
  TextSprite,
  ImageSprite,
  RectSprite,
  Stage,
  PlaybackBar
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "video/v1-explainer/animations.jsx", error: String((e && e.message) || e) }); }

// video/v1-explainer/parts.jsx
try { (() => {
/* cdr-kit explainer — shared parts. Brand tokens (light + indigo). */
const COL = {
  paper: '#fcfbf8',
  paper2: '#f6f3ee',
  paper3: '#efebe4',
  card: '#ffffff',
  ink: '#2b2724',
  ink2: '#6f6a63',
  ink3: '#948f87',
  line: '#e7e4df',
  line2: '#dcd9d2',
  primary: '#3a5adb',
  primarySoft: 'rgba(58,90,219,0.10)',
  primaryLine: 'rgba(58,90,219,0.34)',
  signal: '#1e9c66',
  signalSoft: 'rgba(30,156,102,0.12)',
  signalLine: 'rgba(30,156,102,0.40)',
  warn: '#b9852f',
  warnSoft: 'rgba(185,133,47,0.12)',
  warnLine: 'rgba(185,133,47,0.40)'
};
const FONT = {
  disp: "'Bricolage Grotesque', sans-serif",
  sans: "'Hanken Grotesk', system-ui, sans-serif",
  mono: "'JetBrains Mono', ui-monospace, monospace"
};

// scramble: resolves `target` left-to-right as p:0->1, random hex glyphs elsewhere
const GLYPHS = '0123456789abcdef?{}":,./';
function scramble(target, p) {
  const n = Math.floor(clamp(p, 0, 1) * target.length);
  let s = '';
  for (let i = 0; i < target.length; i++) {
    const ch = target[i];
    if (i < n || ch === ' ') s += ch;else s += GLYPHS[Math.random() * GLYPHS.length | 0];
  }
  return s;
}

// The Vault-Rail brand mark. `draw` (0..1) strokes it on; dotP (0..1) pops the payload dot.
function Mark({
  size = 64,
  color = COL.ink,
  dot = COL.primary,
  draw = 1,
  dotP = 1
}) {
  const railLen = 29,
    rectLen = 84;
  return /*#__PURE__*/React.createElement("svg", {
    width: size,
    height: size,
    viewBox: "0 0 32 32",
    fill: "none",
    style: {
      display: 'block'
    }
  }, /*#__PURE__*/React.createElement("line", {
    x1: "1.5",
    y1: "16",
    x2: "30.5",
    y2: "16",
    stroke: color,
    strokeWidth: "2.6",
    strokeLinecap: "round",
    strokeDasharray: railLen,
    strokeDashoffset: railLen * (1 - clamp(draw, 0, 1))
  }), /*#__PURE__*/React.createElement("rect", {
    x: "7",
    y: "7",
    width: "18",
    height: "18",
    rx: "5.2",
    stroke: color,
    strokeWidth: "2.6",
    strokeDasharray: rectLen,
    strokeDashoffset: rectLen * (1 - clamp(draw, 0, 1))
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "16",
    cy: "16",
    r: 2.8 * clamp(dotP, 0, 1),
    fill: dot
  }));
}

// Subtle hairline grid with radial fade. opacity prop fades the whole thing.
function Grid({
  opacity = 1,
  cx = '50%',
  cy = '30%'
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      opacity,
      pointerEvents: 'none',
      backgroundImage: `linear-gradient(${COL.line} 1px, transparent 1px), linear-gradient(90deg, ${COL.line} 1px, transparent 1px)`,
      backgroundSize: '48px 48px',
      WebkitMaskImage: `radial-gradient(ellipse 75% 75% at ${cx} ${cy}, #000 0%, transparent 72%)`,
      maskImage: `radial-gradient(ellipse 75% 75% at ${cx} ${cy}, #000 0%, transparent 72%)`
    }
  });
}

// Brand wordmark lockup
function Lockup({
  size = 1,
  color = COL.ink
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 14 * size
    }
  }, /*#__PURE__*/React.createElement(Mark, {
    size: 42 * size,
    color: color
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontWeight: 700,
      fontSize: 34 * size,
      letterSpacing: '-0.04em',
      color,
      whiteSpace: 'nowrap'
    }
  }, "cdr", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "-"), "kit"));
}

// Window-chrome card (the vault card shell)
function WinCard({
  x,
  y,
  w,
  title,
  children,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x,
      top: y,
      width: w,
      background: COL.card,
      border: `1px solid ${COL.line}`,
      borderRadius: 16,
      boxShadow: '0 18px 50px -20px rgba(43,39,36,0.28)',
      overflow: 'hidden',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '11px 16px',
      borderBottom: `1px solid ${COL.line}`,
      background: COL.paper2
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'flex',
      gap: 6
    }
  }, [0, 1, 2].map(i => /*#__PURE__*/React.createElement("i", {
    key: i,
    style: {
      width: 10,
      height: 10,
      borderRadius: '50%',
      background: COL.line2,
      display: 'block'
    }
  }))), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 13,
      color: COL.ink3
    }
  }, title)), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '18px 20px'
    }
  }, children));
}
function Pill({
  tone = 'primary',
  children,
  style
}) {
  const map = {
    primary: [COL.primary, COL.primarySoft, COL.primaryLine],
    signal: [COL.signal, COL.signalSoft, COL.signalLine],
    warn: [COL.warn, COL.warnSoft, COL.warnLine]
  };
  const [c, bg, bd] = map[tone];
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 7,
      fontFamily: FONT.mono,
      fontSize: 13,
      color: c,
      background: bg,
      border: `1px solid ${bd}`,
      borderRadius: 999,
      padding: '5px 12px',
      whiteSpace: 'nowrap',
      ...style
    }
  }, children);
}

// lock glyph (open/closed) for status
function Lock({
  open,
  color,
  size = 15
}) {
  return /*#__PURE__*/React.createElement("svg", {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: color,
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("rect", {
    x: "5",
    y: "11",
    width: "14",
    height: "10",
    rx: "2"
  }), open ? /*#__PURE__*/React.createElement("path", {
    d: "M8 11V7a4 4 0 0 1 8 0"
  }) : /*#__PURE__*/React.createElement("path", {
    d: "M8 11V7a4 4 0 0 1 8 0v4"
  }));
}
Object.assign(window, {
  COL,
  FONT,
  scramble,
  Mark,
  Grid,
  Lockup,
  WinCard,
  Pill,
  Lock
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "video/v1-explainer/parts.jsx", error: String((e && e.message) || e) }); }

// video/v1-explainer/scenes.jsx
try { (() => {
/* cdr-kit explainer — scenes. Each reads useSprite() for scene-local time. */
const {
  useSprite: uS
} = window;
const A = o => animate(o);
const typed = (str, p) => str.slice(0, Math.max(0, Math.floor(clamp(p, 0, 1) * str.length)));
const CIPHER = '7b 22 73 69 67 9f a3 2e c1 04 7d e8 11 b6 6a 0c 3f d1';
const PLAIN1 = '{ "signal": "BUY",';
const PLAIN2 = '  "pair": "ETH/USD", "confidence": 0.86 }';
const CIPHER2 = 'a1 9c 04 e8 7d 22 6e 61 6c b6 2e c1 ?? 9f 11 0c 6a d1 3f';
function fade(lt, inEnd, outStart, outEnd) {
  if (lt < inEnd) return clamp(lt / inEnd, 0, 1);
  if (outStart != null && lt > outStart) return 1 - clamp((lt - outStart) / (outEnd - outStart), 0, 1);
  return 1;
}

// ── S1 · Hook ────────────────────────────────────────────────────────────
function SceneHook() {
  const {
    localTime: lt
  } = uS();
  const draw = A({
    from: 0,
    to: 1,
    start: 0.5,
    end: 2.0,
    ease: Easing.easeInOutCubic
  })(lt);
  const dotP = A({
    from: 0,
    to: 1,
    start: 2.0,
    end: 2.4,
    ease: Easing.easeOutBack
  })(lt);
  const drift = A({
    from: 1,
    to: 1.05,
    start: 0,
    end: 5,
    ease: Easing.linear
  })(lt);
  const gridO = A({
    from: 0,
    to: 1,
    start: 0,
    end: 1,
    ease: Easing.easeOutQuad
  })(lt);
  const wordO = fade(lt, 0.5, 4.4, 5);
  const wordIn = A({
    from: 0,
    to: 1,
    start: 1.7,
    end: 2.3,
    ease: Easing.easeOutCubic
  })(lt);
  const tagIn = A({
    from: 0,
    to: 1,
    start: 2.7,
    end: 3.3,
    ease: Easing.easeOutCubic
  })(lt);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: gridO * 0.85,
    cx: "50%",
    cy: "42%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      transform: `scale(${drift})`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 18,
      opacity: fade(lt, 0.4, 4.4, 5)
    }
  }, /*#__PURE__*/React.createElement(Mark, {
    size: 86,
    draw: draw,
    dotP: dotP
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontWeight: 700,
      fontSize: 72,
      letterSpacing: '-0.05em',
      color: COL.ink,
      whiteSpace: 'nowrap',
      opacity: wordIn,
      transform: `translateX(${(1 - wordIn) * -12}px)`
    }
  }, "cdr", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "-"), "kit")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 26,
      fontFamily: FONT.disp,
      fontWeight: 700,
      fontSize: 30,
      letterSpacing: '-0.02em',
      color: COL.ink2,
      textAlign: 'center',
      opacity: tagIn,
      transform: `translateY(${(1 - tagIn) * 10}px)`
    }
  }, "Confidential Data Rails, ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink
    }
  }, "made shippable."))));
}

// ── S2 · The primitive (encrypt) ─────────────────────────────────────────
function ScenePrimitive() {
  const {
    localTime: lt
  } = uS();
  const encP = A({
    from: 0,
    to: 1,
    start: 1.3,
    end: 3.2,
    ease: Easing.easeInOutQuad
  })(lt);
  // encrypt = reverse-resolve: at p=0 plaintext, p=1 cipher. scramble cipher with (1-?) trick:
  const l1 = lt < 1.3 ? PLAIN1 : scramble(CIPHER, encP);
  const l2 = lt < 1.3 ? PLAIN2 : scramble(CIPHER2, encP);
  const sealP = A({
    from: 0,
    to: 1,
    start: 3.1,
    end: 4.3,
    ease: Easing.easeInOutCubic
  })(lt);
  const zoom = A({
    from: 1,
    to: 1.06,
    start: 0,
    end: 6,
    ease: Easing.linear
  })(lt);
  const sealLen = 320;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.5,
    cx: "50%",
    cy: "34%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 96,
      left: 0,
      right: 0,
      textAlign: 'center',
      opacity: fade(lt, 0.5, 5.2, 6)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      letterSpacing: '0.16em',
      color: COL.ink3
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "\u259A"), "\xA0\xA0THE PRIMITIVE"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 800,
      fontSize: 46,
      letterSpacing: '-0.03em',
      color: COL.ink,
      marginTop: 14
    }
  }, "Write ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "encrypted"), " data on-chain.")), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 300,
      left: '50%',
      transform: `translateX(-50%) scale(${zoom})`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      width: 560
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: COL.card,
      border: `1px solid ${COL.line}`,
      borderRadius: 12,
      padding: '24px 26px',
      fontFamily: FONT.mono,
      fontSize: 19,
      lineHeight: 1.7,
      color: COL.ink,
      boxShadow: '0 18px 50px -22px rgba(43,39,36,0.3)',
      wordBreak: 'break-all'
    }
  }, /*#__PURE__*/React.createElement("div", null, l1), /*#__PURE__*/React.createElement("div", {
    style: {
      color: lt < 1.3 ? COL.ink : COL.ink2
    }
  }, l2)), /*#__PURE__*/React.createElement("svg", {
    width: "560",
    height: "150",
    viewBox: "0 0 560 150",
    style: {
      position: 'absolute',
      inset: 0,
      pointerEvents: 'none',
      overflow: 'visible'
    }
  }, /*#__PURE__*/React.createElement("rect", {
    x: "2",
    y: "2",
    width: "556",
    height: "146",
    rx: "12",
    fill: "none",
    stroke: COL.primary,
    strokeWidth: "2.5",
    strokeDasharray: sealLen,
    strokeDashoffset: sealLen * 2 * (1 - sealP),
    opacity: sealP > 0 ? 0.9 : 0
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 22,
      textAlign: 'center',
      fontFamily: FONT.sans,
      fontSize: 18,
      color: COL.ink2,
      opacity: A({
        from: 0,
        to: 1,
        start: 3.6,
        end: 4.4,
        ease: Easing.easeOutCubic
      })(lt)
    }
  }, "Sealed in a vault \u2014 readable only if you satisfy a ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink,
      fontFamily: FONT.mono,
      fontSize: 16
    }
  }, "condition"), ".")));
}

// ── S3 · The gate (money shot: decrypt) ──────────────────────────────────
function SceneGate() {
  const {
    localTime: lt
  } = uS();
  const locked = lt < 3.4;
  const decP = A({
    from: 0,
    to: 1,
    start: 3.6,
    end: 5.4,
    ease: Easing.easeInOutQuad
  })(lt);
  const pay = lt >= 2.0 && lt < 3.6;
  const cardZoom = A({
    from: 0.94,
    to: 1.04,
    start: 0,
    end: 7,
    ease: Easing.easeOutCubic
  })(lt);
  const payRow = A({
    from: 0,
    to: 1,
    start: 1.8,
    end: 2.4,
    ease: Easing.easeOutBack
  })(lt);
  const statusOpen = lt >= 3.4;
  // payload lines
  let p1, p2, pcol;
  if (lt < 3.6) {
    p1 = CIPHER;
    p2 = CIPHER2;
    pcol = COL.ink3;
  } else {
    p1 = scramble(PLAIN1, decP);
    p2 = scramble(PLAIN2, decP);
    pcol = decP > 0.98 ? COL.signal : COL.ink;
  }
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper2
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.4,
    cx: "50%",
    cy: "50%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 54,
      left: 0,
      right: 0,
      textAlign: 'center',
      opacity: fade(lt, 0.5, 6.2, 7)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 800,
      fontSize: 38,
      letterSpacing: '-0.03em',
      color: COL.ink
    }
  }, "Satisfy the condition \u2192 ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.signal
    }
  }, "it decrypts."))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 150,
      left: '50%',
      transform: `translateX(-50%) scale(${cardZoom})`,
      transformOrigin: 'top center'
    }
  }, /*#__PURE__*/React.createElement(WinCard, {
    x: 0,
    y: 0,
    w: 520,
    title: "<VaultGate uuid={4200} />",
    style: {
      position: 'relative'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 11,
      paddingBottom: 14,
      borderBottom: `1px solid ${COL.line}`,
      marginBottom: 14
    }
  }, [['vault.uuid', '4200', COL.ink], ['read.condition', 'Subscription', COL.primary], ['price.period', '5 $IP / 30d', COL.ink]].map(([k, v, c]) => /*#__PURE__*/React.createElement("div", {
    key: k,
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      fontFamily: FONT.mono,
      fontSize: 15,
      whiteSpace: 'nowrap'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink3,
      fontSize: 13
    }
  }, k), /*#__PURE__*/React.createElement("span", {
    style: {
      color: c
    }
  }, v)))), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 15.5,
      lineHeight: 1.7,
      background: COL.paper2,
      border: `1px solid ${COL.line}`,
      borderRadius: 8,
      padding: '14px 16px',
      minHeight: 76,
      color: pcol,
      wordBreak: 'break-all',
      transition: 'color .3s'
    }
  }, /*#__PURE__*/React.createElement("div", null, p1), /*#__PURE__*/React.createElement("div", null, p2)), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginTop: 14
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      fontFamily: FONT.mono,
      fontSize: 14,
      color: statusOpen ? COL.signal : COL.warn
    }
  }, /*#__PURE__*/React.createElement(Lock, {
    open: statusOpen,
    color: statusOpen ? COL.signal : COL.warn
  }), statusOpen ? 'condition satisfied · decrypted' : 'condition not met'), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 13,
      color: COL.ink3
    }
  }, "~15s read"))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: -38,
      top: 330,
      opacity: payRow,
      transform: `translateY(${(1 - payRow) * 14}px)`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      background: COL.card,
      border: `1px solid ${COL.line2}`,
      borderRadius: 12,
      padding: '10px 14px',
      boxShadow: '0 14px 36px -16px rgba(43,39,36,0.3)',
      whiteSpace: 'nowrap'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 9,
      height: 9,
      borderRadius: '50%',
      background: pay ? COL.warn : COL.signal,
      transition: 'background .3s'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 13.5,
      color: COL.ink
    }
  }, "agent 0x9f\u2026a3c1"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 13.5,
      color: statusOpen ? COL.signal : COL.primary
    }
  }, statusOpen ? '✓ paid 5 $IP' : 'subscribe()')))));
}

// ── S4 · One install ─────────────────────────────────────────────────────
function SceneInstall() {
  const {
    localTime: lt
  } = uS();
  const cmd = typed('npm create cdr-kit', A({
    from: 0,
    to: 1,
    start: 0.6,
    end: 1.7,
    ease: Easing.linear
  })(lt));
  const codeO = A({
    from: 0,
    to: 1,
    start: 2.0,
    end: 2.7,
    ease: Easing.easeOutCubic
  })(lt);
  const layers = [['Layer 3', 'Framework adapters · MCP · CLI'], ['Layer 2', 'TypeScript SDK · React · agent'], ['Layer 1', '9 Solidity conditions · vault']];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.45,
    cx: "28%",
    cy: "30%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 88,
      left: 96,
      opacity: fade(lt, 0.5, 4.4, 5)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 14,
      letterSpacing: '0.16em',
      color: COL.ink3
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "\u259A"), "\xA0\xA0ONE INSTALL"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 800,
      fontSize: 44,
      letterSpacing: '-0.03em',
      color: COL.ink,
      marginTop: 14,
      maxWidth: 480,
      lineHeight: 1.05
    }
  }, "One package.", /*#__PURE__*/React.createElement("br", null), "Real on-chain checks."), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 18,
      fontFamily: FONT.sans,
      fontSize: 17,
      color: COL.ink2,
      maxWidth: 430
    }
  }, "Gate any data behind a payment or license \u2014 in under a minute.")), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 150,
      left: 640,
      width: 540
    }
  }, /*#__PURE__*/React.createElement(WinCard, {
    x: 0,
    y: 0,
    w: 540,
    title: "terminal"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 17,
      color: COL.ink
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "$"), " ", cmd, /*#__PURE__*/React.createElement("span", {
    style: {
      opacity: lt % 1 < 0.5 ? 1 : 0,
      color: COL.ink3
    }
  }, "\u258B")), /*#__PURE__*/React.createElement("div", {
    style: {
      opacity: codeO,
      marginTop: 16,
      paddingTop: 16,
      borderTop: `1px solid ${COL.line}`,
      fontFamily: FONT.mono,
      fontSize: 15.5,
      lineHeight: 1.7
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "import"), " ", '{ VaultGate }', " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "from"), " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.signal
    }
  }, "\"@cdr-kit/react\""), ";"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 8
    }
  }, '<', /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#b5532f'
    }
  }, "VaultGate"), " uuid=", '{', /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.warn
    }
  }, "4200"), '}', " auto", '>'), /*#__PURE__*/React.createElement("div", null, '  {(data) => <pre>{decode(data)}</pre>}'), /*#__PURE__*/React.createElement("div", null, '</', /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#b5532f'
    }
  }, "VaultGate"), '>'))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 10,
      marginTop: 18,
      opacity: A({
        from: 0,
        to: 1,
        start: 3.0,
        end: 3.7,
        ease: Easing.easeOutCubic
      })(lt)
    }
  }, layers.map(([a, b], i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      flex: 1,
      background: COL.card,
      border: `1px solid ${COL.line}`,
      borderRadius: 10,
      padding: '11px 13px',
      transform: `translateY(${(1 - A({
        from: 0,
        to: 1,
        start: 3.0 + i * 0.12,
        end: 3.7 + i * 0.12,
        ease: Easing.easeOutBack
      })(lt)) * 12}px)`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 11.5,
      color: COL.primary,
      fontWeight: 700
    }
  }, a), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.sans,
      fontSize: 12.5,
      color: COL.ink2,
      marginTop: 4
    }
  }, b))))));
}

// ── S5 · The agent ───────────────────────────────────────────────────────
function SceneAgent() {
  const {
    localTime: lt
  } = uS();
  const lines = [['$ ', 'agent run --intent "trading signal"', COL.ink, 0.4], ['⚙ ', 'discover → matched vault 4200', COL.primary, 1.1], ['⚙ ', 'subscribe & access → paid 5 $IP', COL.primary, 1.8], ['✓ ', 'threshold met · decrypted locally', COL.signal, 2.5], ['→ ', 'decide: BUY ETH/USD (0.86)', COL.ink, 3.1]];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.4,
    cx: "70%",
    cy: "32%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 92,
      left: 0,
      right: 0,
      textAlign: 'center',
      opacity: fade(lt, 0.5, 3.6, 4)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.disp,
      fontWeight: 800,
      fontSize: 42,
      letterSpacing: '-0.03em',
      color: COL.ink
    }
  }, "An agent that buys its ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.primary
    }
  }, "own data.")), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.sans,
      fontSize: 18,
      color: COL.ink2,
      marginTop: 10
    }
  }, "Discover \u2192 pay \u2192 decrypt \u2192 decide. No human in the loop.")), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 226,
      left: '50%',
      transform: 'translateX(-50%)',
      width: 620
    }
  }, /*#__PURE__*/React.createElement(WinCard, {
    x: 0,
    y: 0,
    w: 620,
    title: "cdr-kit-example \xB7 vercel-ai"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 16,
      lineHeight: 1.85,
      minHeight: 170
    }
  }, lines.map(([pre, txt, col, t], i) => {
    const o = A({
      from: 0,
      to: 1,
      start: t,
      end: t + 0.35,
      ease: Easing.easeOutCubic
    })(lt);
    const shown = typed(txt, A({
      from: 0,
      to: 1,
      start: t,
      end: t + 0.5,
      ease: Easing.linear
    })(lt));
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        opacity: o,
        color: col
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        color: pre === '✓ ' ? COL.signal : pre === '→ ' ? COL.primary : COL.ink3
      }
    }, pre), shown);
  })))));
}

// ── S6 · Outro ───────────────────────────────────────────────────────────
function SceneOutro() {
  const {
    localTime: lt
  } = uS();
  const inP = A({
    from: 0,
    to: 1,
    start: 0.2,
    end: 1.0,
    ease: Easing.easeOutBack
  })(lt);
  const sub = A({
    from: 0,
    to: 1,
    start: 0.9,
    end: 1.6,
    ease: Easing.easeOutCubic
  })(lt);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COL.paper
    }
  }, /*#__PURE__*/React.createElement(Grid, {
    opacity: 0.7,
    cx: "50%",
    cy: "48%"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      transform: `scale(${0.9 + 0.1 * inP})`,
      opacity: inP
    }
  }, /*#__PURE__*/React.createElement(Lockup, {
    size: 1.5
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 28,
      fontFamily: FONT.mono,
      fontSize: 16,
      color: COL.ink2,
      opacity: sub,
      letterSpacing: '0.01em',
      whiteSpace: 'nowrap'
    }
  }, "15 packages \xB7 9 conditions \xB7 34 tools \xB7 ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: COL.ink
    }
  }, "MIT")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 20,
      display: 'flex',
      alignItems: 'center',
      gap: 14,
      opacity: sub
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: FONT.mono,
      fontSize: 22,
      fontWeight: 700,
      color: COL.primary
    }
  }, "cdrkit.xyz"), /*#__PURE__*/React.createElement(Pill, {
    tone: "signal"
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 7,
      height: 7,
      borderRadius: '50%',
      background: COL.signal,
      display: 'inline-block'
    }
  }), "Live on Aeneid"))));
}
Object.assign(window, {
  SceneHook,
  ScenePrimitive,
  SceneGate,
  SceneInstall,
  SceneAgent,
  SceneOutro
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "video/v1-explainer/scenes.jsx", error: String((e && e.message) || e) }); }

})();
