# Canonical OrdaX Web build

Presentation: system/surface/workspace. Thin entry: system/composition/web/main.tsx.
Root package.json/package-lock.json own dependencies.

From repository root:

    npm ci --ignore-scripts --no-audit --no-fund
    npm run build --workspace tools/surface-web
    npm run verify --workspace tools/surface-web
    python tools/surface-web/build.py build --source-commit <full-git-sha> --out-dir out/web-client
    python tools/surface-web/build.py verify --out-dir out/web-client
    node tools/surface-web/browser-smoke.mjs --bundle-dir out/web-client

npm run preview --workspace tools/surface-web serves compiled presentation at
http://127.0.0.1:4201/; ?view=projects selects a view. No alternate product route
or redirect. Node >=22.18 is needed on the build/proof host, not user browsers.

Chrome/Chromium or Edge is required for proof; ORDAX_CHROME_BIN can specify the
executable. Evidence is generated under out/web-viewport-proof.

Framework, assets and font are locally bundled. Candidate receipts contain
source-input and emitted-file digests; they are not signed releases.
Service connections are the next stage. Pending controls and unavailable states
remain; labeled demonstrations grant no authority. Native/Account browser proofs
share only test infrastructure under tools/browser-proof.
