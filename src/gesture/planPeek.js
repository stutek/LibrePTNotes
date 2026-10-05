// Kopija iz LibrePT: src/modules/clipboard/planPeek.js, commit 403715f9 (MIT, Simon Tutek). Kretnja L je namenoma enaka kot v LibrePT.
// src/modules/clipboard/planPeek.js — the "blanket" gesture on the live clipboard: press-and-hold
// shrinks the current plan by itself, a sideways drag pulls it aside to
// show the previous or next plan drawn underneath. Behaviour lives in the prototype
// .private/prototypes/odeja.html (approved 2026-09-14) — this is that prototype's pointer handling,
// adapted to the real overlay.
//
// Knows nothing about sessions, clients or state: it drives pointer events on ONE element (the
// blanket) and toggles classes on it and on the two under-layer elements a callback hands it. The
// two under-layers are rendered by controllers/planPeekController.js — this module never asks what
// is in them, only whether a side has something to uncover (`has-plan`, or `has-create-card` for the
// "create a plan" card the controller draws when there is no next plan). That decides the
// quarter-distance rubber band with nothing there.
//
// Opening is a SECOND stroke, upward, and not a release (ruled 2026-09-30). Once the pull has
// uncovered at least OPEN_PULL_PCT of the width, that under-layer is marked `is-open-ready` (its
// header swaps to "Slide up to open"); an upward stroke of OPEN_UP_PX from the deepest point of the
// pull then slides the blanket off and calls `onOpen(side)`. Every release springs back.
//
// Until that ruling the RELEASE opened, past 70 % of the width. Reading the neighbour properly and
// leaving the current session were then the same movement: the widest look the gesture allows
// (MAX_PULL_PCT) could only be taken from inside the state where letting go navigated, so the
// trainer had to pull the plan back before lifting the thumb. The two strokes separate the look from
// the leaving, and the look is now free at every distance.
//
// WHAT opening means — a route, the planning form — is the controller's.
//
// The one inline style this module sets is `--plan-pull` (docs/ARCHITECTURE.md "look and layout
// live only in CSS" — a drag offset is exactly the kind of runtime number that rule carves out for
// a custom property). Every other visual change is a class; planPeek.css owns what the classes do,
// including prefers-reduced-motion.

// Timings and distances are the prototype's own defaults (Simon approved the prototype as a whole,
// 2026-09-14), not independently chosen here.
const HOLD_MS = 250;
const LOCK_PX = 8; // movement before an axis (x/y) is decided
const EDGE_PX = 24; // a press this close to either side edge is the phone's own back gesture
const MAX_PULL_PCT = 0.85; // of the blanket's own width
const RUBBER_START_PCT = 0.8; // of MAX_PULL_PCT — beyond this the pull resists further movement
const NO_NEIGHBOUR_FACTOR = 0.25; // how far the blanket still moves with nothing to reveal
const SPRING_MS = 280; // must match planPeek.css's `.is-springing` transition
// Opening: the pull that ARMS it, and the upward stroke that PERFORMS it. The pull is measured
// against the overlay's width, not the narrowed blanket's, as the prototype measures its phone: a
// quarter of a 390px phone is 98px — far enough that a thumb brushing the plan between sets has
// armed nothing, and near enough that the trainer never has to sweep the plan almost off the screen
// to be allowed to leave.
const OPEN_PULL_PCT = 0.25;
// The upward stroke, measured from the DEEPEST point of the pull and never from where the press
// began: measured from the press, a single diagonal sweep would satisfy both directions at once and
// open something the trainer only meant to look at.
const OPEN_UP_PX = 64;
// Where the sideways offset stops following the finger. From here on the plan stays where it was
// pulled to, so it does not slide back out from under the second stroke while that stroke is made.
const PIN_UP_PX = 8;
const LEAVE_MS = 220; // must match planPeek.css's `.is-leaving` transition

// Rows denser while held/dragging, eased back the same way (planPeek.css's `.is-held` transition).
const DENSE_SETTLE_MS = 220;

function clampPull(dx, width, hasNeighbour) {
  const max = width * MAX_PULL_PCT;
  const sign = Math.sign(dx);
  let pull = Math.abs(dx);
  const softLimit = max * RUBBER_START_PCT;
  if (pull > softLimit) {
    const over = pull - softLimit;
    const span = max - softLimit;
    pull = softLimit + span * (1 - Math.exp(-over / span));
  }
  pull = Math.min(pull, max);
  return sign * pull * (hasNeighbour ? 1 : NO_NEIGHBOUR_FACTOR);
}

function prefersReducedMotion() {
  return Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches);
}

/**
 * Wire the blanket gesture. `blanket` is the element wrapping the title bar, client tabs and
 * clipboard body (#active-session-blanket). `deps`:
 *   getUnderLayers()  — () => { past: HTMLElement|null, future: HTMLElement|null }
 *   isDisabled()      — () => bool; true in edit mode, where the reorder drag owns the surface
 *   onOpen(side)      — ("past"|"future") => void; called once the blanket has slid off
 *   onPeekBegin()     — () => void; the under-layers are about to become visible. Whatever has to
 *                       be MEASURED about them is measured here, not when they were drawn.
 * Idempotent: wiring twice on the same element is a no-op (the controller calls this once).
 */
export function initPlanPeek(blanket, { getUnderLayers, isDisabled, onOpen, onPeekBegin }) {
  if (!blanket || blanket.dataset.planPeekWired) return;
  blanket.dataset.planPeekWired = "1";

  let drag = null; // { id, x, y, axis, side, ready, hold, anchorEl }
  let leaving = false; // the blanket is sliding off; a new press must not grab it mid-slide

  function setPull(px) {
    blanket.style.setProperty("--plan-pull", `${px}px`);
  }

  function setHeld(on) {
    if (blanket.classList.contains("is-held") === on) return;
    // The under-layers become visible on this exact class, so this is the moment anything measured
    // ABOUT them has to be measured: the deck settles its own scroll a tenth of a second after it
    // renders, and a position read before that is out by however far the active card still had to
    // travel (12px, seen in the alignment test).
    if (on) onPeekBegin?.();
    blanket.classList.add("is-animating-held");
    blanket.classList.toggle("is-held", on);
    setTimeout(() => blanket.classList.remove("is-animating-held"), DENSE_SETTLE_MS);
  }

  function setSide(side) {
    const { past, future } = getUnderLayers() || {};
    past?.classList.toggle("is-side-chosen", side === "past");
    future?.classList.toggle("is-side-chosen", side === "future");
    blanket.classList.toggle("side-past", side === "past");
    blanket.classList.toggle("side-future", side === "future");
  }

  function layerFor(side) {
    const { past, future } = getUnderLayers() || {};
    return side === "past" ? past : future;
  }

  function hasNeighbour(side) {
    const el = layerFor(side);
    return !!(el?.classList.contains("has-plan") || el?.classList.contains("has-create-card"));
  }

  // Armed: this side is uncovered far enough that an upward stroke would open it. The layer's
  // header swaps to "Slide up to open" by this class alone, so arming never re-renders it mid-drag.
  function setOpenReady(side, ready) {
    const { past, future } = getUnderLayers() || {};
    past?.classList.toggle("is-open-ready", ready && side === "past");
    future?.classList.toggle("is-open-ready", ready && side === "future");
  }

  // The overlay's width: the blanket itself is 120px narrower while held.
  function fullWidth() {
    const host = blanket.parentElement || blanket;
    return host.getBoundingClientRect().width || 1;
  }

  function pointerdown(e) {
    if (leaving || isDisabled?.()) return;
    if (e.button !== undefined && e.button !== 0) return;
    // The trainer's own control (a card, a button inside the deck) still opens/taps normally: a
    // press that never crosses LOCK_PX or HOLD_MS produces no gesture of ours at all, so we don't
    // need to filter targets here — only refuse the strip the phone reserves for its back swipe.
    const rect = blanket.getBoundingClientRect();
    if (e.clientX - rect.left < EDGE_PX || rect.right - e.clientX < EDGE_PX) return;

    const anchorEl = e.target.closest(
      ".exercise-deck-card, .plan-sheet-block, .plan-sheet-row, .clipboard-body > *",
    );
    const pressed = {
      id: e.pointerId,
      x: e.clientX,
      y: e.clientY,
      axis: null,
      side: null,
      ready: false,
      anchorEl,
      // The deepest point of the sideways pull so far, and the height the finger was at when it
      // reached it: the upward stroke is measured from there (OPEN_UP_PX). `pinned` says that
      // stroke has begun, so the offset stops following the finger sideways (PIN_UP_PX).
      peakDx: 0,
      peakY: e.clientY,
      pinned: false,
    };
    drag = pressed;
    blanket.classList.remove("is-springing");
    pressed.hold = setTimeout(() => {
      if (drag === pressed && !drag.axis) setHeld(true);
    }, HOLD_MS);
  }

  // Which way the finger went FIRST decides whose gesture this is: sideways is ours to pull, and
  // anything else stays the browser's own scroll.
  function lockAxis(e, dx, dy) {
    if (Math.hypot(dx, dy) < LOCK_PX) return;
    drag.axis = Math.abs(dx) > Math.abs(dy) ? "x" : "y";
    clearTimeout(drag.hold);
    if (drag.axis === "x") {
      blanket.setPointerCapture?.(e.pointerId);
      setHeld(true);
      return;
    }
    // A vertical move is a normal scroll; if the hold had already shrunk the blanket, undo it —
    // the trainer is reading the deck, not asking to see a neighbour.
    setHeld(false);
  }

  // How far the finger has risen since the pull was at its deepest, which is what the second stroke
  // is measured by. The deepest point stops moving once that rise has begun, so a thumb drifting
  // sideways as it travels up neither deepens the pull nor moves the point the rise is measured
  // from.
  function riseSincePeak(e, dx) {
    if (!drag.pinned && Math.abs(dx) > Math.abs(drag.peakDx)) {
      drag.peakDx = dx;
      drag.peakY = e.clientY;
    }
    const up = drag.peakY - e.clientY;
    if (up >= PIN_UP_PX) drag.pinned = true;
    return up;
  }

  // The L is complete. The second stroke opens, not the release that follows it: a finished gesture
  // waiting for the finger to lift would still be cancellable by moving back down, and nothing on
  // the screen would say so.
  function openAfterStroke() {
    const finished = drag;
    clearTimeout(finished.hold);
    drag = null;
    setOpenReady(null, false);
    leave(finished.side);
  }

  function pointermove(e) {
    if (!drag || e.pointerId !== drag.id) return;
    const dx = e.clientX - drag.x;
    const dy = e.clientY - drag.y;

    if (!drag.axis) lockAxis(e, dx, dy);
    if (drag.axis !== "x") return;
    e.preventDefault();

    const up = riseSincePeak(e, dx);
    // Once pinned the side is settled too: the gesture is already committed to the neighbour it
    // uncovered, and reading the side off a drifting dx could swap it mid-stroke.
    const side = drag.pinned && drag.side ? drag.side : dx > 0 ? "past" : "future";
    const width = fullWidth();
    const neighbour = hasNeighbour(side);
    const pull = clampPull(drag.pinned ? drag.peakDx : dx, width, neighbour);
    if (side !== drag.side) {
      drag.side = side;
      setSide(side);
    }
    const ready = neighbour && Math.abs(pull) >= width * OPEN_PULL_PCT;
    if (ready !== drag.ready) {
      drag.ready = ready;
      setOpenReady(side, ready);
    }
    blanket.classList.toggle("pulled-right", pull > 0);
    blanket.classList.toggle("pulled-left", pull < 0);
    setPull(pull);

    if (ready && up >= OPEN_UP_PX) openAfterStroke();
  }

  function release(e) {
    if (!drag || e.pointerId !== drag.id) return;
    const finished = drag;
    clearTimeout(finished.hold);
    drag = null;

    // EVERY release springs back, whatever it was armed for: opening happens on the upward stroke
    // (pointermove), so by the time a finger lifts, a gesture that was going to open has already
    // opened and taken `drag` with it. A release reaching here is a look that is over — including a
    // pointercancel, the browser taking the gesture back for a scroll or a system swipe.
    setOpenReady(null, false);
    blanket.classList.remove("pulled-right", "pulled-left");
    setSide(null);
    setHeld(false);
    if (finished.axis === "x") {
      blanket.classList.add("is-springing");
      setPull(0);
      setTimeout(() => blanket.classList.remove("is-springing"), SPRING_MS);
    }
  }

  // Slide off in the direction of the pull, then open. Opening re-renders the plan into this same
  // blanket, so it is put back in place in the same task as onOpen: the new plan is what paints
  // next, never the old one springing back. Reduced motion: no slide, same outcome, no wait.
  function leave(side) {
    leaving = true;
    const reduced = prefersReducedMotion();
    if (!reduced) {
      blanket.classList.add("is-leaving");
      setPull((side === "past" ? 1 : -1) * fullWidth());
    }
    const finish = () => {
      try {
        onOpen?.(side);
      } finally {
        blanket.classList.remove("is-leaving", "pulled-right", "pulled-left");
        setSide(null);
        setHeld(false);
        setPull(0);
        leaving = false;
      }
    };
    if (reduced) finish();
    else setTimeout(finish, LEAVE_MS);
  }

  blanket.addEventListener("pointerdown", pointerdown);
  // move/up/cancel on window, not the blanket: setPointerCapture keeps them targeted at the
  // blanket regardless, but a release that lands just outside it (a fast swipe) must still end the
  // gesture rather than leaving `drag` set — the same reason the prototype listens on window.
  window.addEventListener("pointermove", pointermove);
  window.addEventListener("pointerup", release);
  window.addEventListener("pointercancel", release);
}
