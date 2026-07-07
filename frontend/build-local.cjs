const esbuild = require("esbuild");

esbuild.buildSync({
  entryPoints: ["src/main.tsx"],
  bundle: true,
  minify: true,
  sourcemap: true,
  format: "esm",
  outfile: "dist/assets/app.js",
  loader: {
    ".svg": "file",
  },
  assetNames: "assets/[name]-[hash]",
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
});
