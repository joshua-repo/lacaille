import { el } from "../dom.js";

/* The page's one pane of glass with a header: a title, a line of context under
   it, and an optional tag on the right saying what the pane is waiting on.
   Returns the root and the body so the caller fills the body itself. */
export function panel({title, meta, tag, cls}) {
  const root = el("section", "panel" + (cls ? " " + cls : ""));
  const head = el("div", "panel-hd");
  const left = el("div");
  left.appendChild(el("h2", null, title));
  if (meta) left.appendChild(el("div", "panel-meta", meta));
  head.appendChild(left);
  if (tag) head.appendChild(el("span", "panel-tag", tag));
  root.appendChild(head);
  const body = el("div", "panel-body");
  root.appendChild(body);
  return {root, body};
}

/* An honest empty state: the space the thing will occupy, and one sentence on
   what goes there.

   Deliberately not a mocked-up chart. A fake curve in an empty pane is worse
   than an empty one, because the next person cannot tell which parts are real
   and which are scenery. The height is the part of the layout that *is* real,
   which is why it is a parameter. */
export function emptyBody(text, height) {
  const node = el("div", "panel-empty", text);
  if (height) node.style.minHeight = height + "px";
  return node;
}

/* A panel that is nothing but its empty state. */
export function emptyPanel({title, meta, tag, cls, text, height}) {
  const {root, body} = panel({title, meta, tag, cls});
  body.appendChild(emptyBody(text, height));
  return root;
}

export function regionTitle(text) {
  return el("h2", "region-title", text);
}
