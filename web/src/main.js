import { DATA } from "./data.js";
import { wireTabs } from "./nav.js";
import { state } from "./state.js";
import { buildData } from "./views/datasets.js";
import { buildMetrics } from "./views/metrics.js";
import { buildParameters } from "./views/parameters.js";
import { buildPipeline } from "./views/pipeline.js";
import { buildPortfolio, watched } from "./views/portfolio.js";
import { buildResults } from "./views/results.js";

const byId = id => document.getElementById(id);

const generated = () => "generated " +
  new Date(DATA.today + "T00:00:00").toLocaleDateString(undefined, {month: "long", day: "numeric", year: "numeric"});

const SUBTITLES = {
  analysis: {
    portfolio: () => watched().length + " watched · " + generated(),
    metrics: () => "layout only · nothing here is wired to market data yet",
    pipeline: () => "reserved",
  },
  research: {
    data: () => "fixed datasets · jobs, what is cached, and whether it is fit to run on",
    parameters: () => "one combo config · any value given as a list is an axis",
    results: () => "every cell of a run · in-sample beside out-of-sample",
  },
};

const currentTab = () => state.workspace === "analysis" ? state.analysisTab : state.researchTab;

function onShow() {
  byId("subtitle").textContent = SUBTITLES[state.workspace][currentTab()]();
}

/* Workspaces. Switching hides one pane and shows the other; each keeps the tab
   it was on. */
wireTabs(byId("workspaces"), "ws", {analysis: byId("analysisWs"), research: byId("researchWs")}, name => {
  state.workspace = name;
  byId("wsTitle").textContent = name === "analysis" ? "Analysis" : "Research";
  onShow();
});

wireTabs(byId("analysisTabs"), "tab", {
  portfolio: byId("portfolioTab"),
  metrics: byId("metricsTab"),
  pipeline: byId("pipelineTab"),
}, name => { state.analysisTab = name; onShow(); });

wireTabs(byId("researchTabs"), "tab", {
  data: byId("dataTab"),
  parameters: byId("parametersTab"),
  results: byId("resultsTab"),
}, name => { state.researchTab = name; onShow(); });

/* Everything is built once, up front: nothing on the page changes after first
   paint, and no tab is expensive enough to defer. */
buildPortfolio();
buildMetrics();
buildPipeline();
buildData();
buildParameters();
buildResults();
onShow();
