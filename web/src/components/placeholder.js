import { el } from "../dom.js";

/* An honest empty state: what will live here, and what it waits on.
 *
 * Deliberately not a mocked-up UI. A fake chart in an empty workspace is worse
 * than an empty one, because the next person cannot tell which parts are real
 * and which are scenery.
 */
export function buildPlaceholder(root, {title, meta, tag, lede, items, note}) {
  if (root.childElementCount) return;   // built once; nothing here is live

  const card = el("section", "acct placeholder");
  const head = el("div", "acct-hd");
  const left = el("div");
  left.appendChild(el("h2", null, title));
  left.appendChild(el("div", "acct-meta", meta));
  head.appendChild(left);
  if (tag) head.appendChild(el("span", "acct-tag", tag));
  card.appendChild(head);

  const body = el("div", "acct-rows");
  body.appendChild(el("p", "ph-lede", lede));
  const list = el("div", "ph-list");
  for (const [name, what] of items) {
    const item = el("div", "ph-item");
    item.appendChild(el("div", "sym", name));
    item.appendChild(el("div", "qty", what));
    list.appendChild(item);
  }
  body.appendChild(list);
  if (note) body.appendChild(el("div", "note", note));
  card.appendChild(body);
  root.appendChild(card);
}
