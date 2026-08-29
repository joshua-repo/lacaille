export function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

/* The 'recent headline' marker. Lives here rather than in a view because
   both the calendar chips and the Gantt rows draw it. */
export function starIcon() {
  const b = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  b.setAttribute("class", "star");
  b.setAttribute("viewBox", "0 0 24 24");
  b.setAttribute("fill", "currentColor");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M12 2l2.9 6.6 7.1.6-5.4 4.7 1.7 7-6.3-3.9-6.3 3.9 1.7-7L2 9.2l7.1-.6z");
  b.appendChild(path);
  return b;
}
