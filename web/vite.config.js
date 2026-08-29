import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

/* The whole point of this config is the *shape* of the output, not the speed
   of the build: pictor ships one self-contained HTML file with no external
   assets, so it works offline, opens off a one-shot local server, and can be
   archived or mailed as a single artefact. `viteSingleFile` inlines the JS and
   CSS back into index.html; the two limits below stop Vite from emitting any
   separate asset next to it. */
export default defineConfig({
  plugins: [viteSingleFile()],
  build: {
    // Straight into the Python package, not web/dist: the wheel ships
    // `src/pictor/**`, so a template living outside it would work from a
    // checkout and be missing from an install -- the worst kind of difference.
    outDir: "../src/pictor/_web",
    emptyOutDir: true,
    cssCodeSplit: false,
    assetsInlineLimit: 100_000_000,
    // Readable output. This file is something a person opens and inspects when
    // a number looks wrong, and the page is small enough that the bytes saved
    // by mangling are worth less than being able to read it.
    minify: false,
    target: "es2022",
  },
});
