import { DATA } from "./data.js";

export const state = { view: "calendar", selected: new Set(), display: (DATA.fx && DATA.fx.currencies[0]) || "native", account: "all" };
