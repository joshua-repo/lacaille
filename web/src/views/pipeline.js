import { emptyPanel } from "../components/panel.js";

/* Analysis > Pipeline.
 *
 * Reserved. What goes here has not been designed, so this pane commits to
 * nothing but its position and its width -- no stages, no arrows, no shape
 * that a later design would have to argue its way out of.
 */
export function buildPipeline() {
  document.getElementById("pipelineTab").appendChild(emptyPanel({
    title: "Pipeline",
    meta: "full width · shape undecided",
    tag: "reserved",
    text: "Reserved. Nothing is designed here yet.",
    height: 460,
  }));
}
