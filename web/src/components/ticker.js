/* ---- NumberTicker ----------------------------------------------------
   Port of https://github.com/joshua-repo/NumberTicker; the CSS block above
   records what is faithful and what is not. A ticker owns one <span> and one
   wheel per digit, and `set` re-targets those wheels rather than rewriting
   text, which is what makes the digits roll from the old number to the new
   one instead of snapping. */

// The original's resting offset: mid-wheel, between 4 and 5, before the
// first roll takes it to the real digit.
export const TK_NEUTRAL = 4.5;

export const tkOffset = n => "translateY(calc(var(--tk-h) * " + (-n) + "))";
// Digits are laid out 9 -> 0 top to bottom, so digit d sits at index 9 - d.

export const tkTarget = d => tkOffset(9 - d);

export const isDigit = ch => ch >= "0" && ch <= "9";

export function makeTicker(format, className) {
  const el = document.createElement("span");
  el.className = "ticker" + (className ? " " + className : "");
  let strips = [];
  let shape = null;   // the formatted text with digits blanked out
  let digits = [];

  function shapeOf(text) {
    return [...text].map(ch => (isDigit(ch) ? "#" : ch)).join("");
  }

  function build(text) {
    el.innerHTML = "";
    strips = [];
    for (const ch of text) {
      if (isDigit(ch)) {
        const col = document.createElement("span");
        col.className = "tk-col";
        const strip = document.createElement("span");
        strip.className = "tk-strip";
        for (let d = 9; d >= 0; d--) {
          const cell = document.createElement("span");
          cell.textContent = String(d);
          strip.appendChild(cell);
        }
        strip.style.transform = tkOffset(TK_NEUTRAL);
        col.appendChild(strip);
        el.appendChild(col);
        strips.push(strip);
      } else {
        // Separators, the currency symbol and the sign never animate.
        const sep = document.createElement("span");
        sep.className = "tk-sep";
        sep.textContent = ch;
        el.appendChild(sep);
      }
    }
  }

  function applyTargets() {
    digits.forEach((d, i) => { if (strips[i]) strips[i].style.transform = tkTarget(d); });
  }

  function set(value) {
    const text = format(value);
    digits = [...text].filter(isDigit).map(Number);
    const next = shapeOf(text);
    if (next !== shape) {
      // A different number of digits (or a moved comma) is a different set of
      // wheels; rebuilding restarts them from the neutral offset.
      shape = next;
      build(text);
      requestAnimationFrame(() => requestAnimationFrame(applyTargets));
    } else {
      applyTargets();
    }
  }

  /* Re-run the entrance roll. A transition cannot run on a `display: none`
     subtree, so a ticker built inside a hidden tab would simply appear at its
     value; views call this when they are revealed. */
  function replay() {
    for (const strip of strips) {
      strip.style.transition = "none";
      strip.style.transform = tkOffset(TK_NEUTRAL);
    }
    void el.offsetHeight;  // flush the reset before re-enabling the transition
    for (const strip of strips) strip.style.transition = "";
    requestAnimationFrame(applyTargets);
  }

  return {el, set, replay};
}
