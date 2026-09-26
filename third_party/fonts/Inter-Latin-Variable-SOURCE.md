# Inter Latin variable font source

OrdaX vendors a local Latin subset of the Inter variable font for the shared Surface so the product does not depend on a runtime font network request.

- Runtime asset: `system/surface/ui/fonts/inter-latin-wght-normal.woff2`
- Upstream package repository: `fontsource/font-files`
- Upstream commit: `d946f2f5f48bb73bb238d189d3b182c98dcbca10`
- Upstream path: `fonts/variable/inter/files/inter-latin-wght-normal.woff2`
- Git blob SHA-1: `d15208de03cd1ad7c5199f0a0ce915fe841e4722`
- SHA-256: `3100e775e8616cd2611beecfa23a4263d7037586789b43f035236a2e6fbd4c62`
- Size: `48256` bytes
- Style: normal
- Variable weight range: 100–900
- License: `third_party/licenses/Inter-OFL-1.1.txt`

The vendored file is a Latin subset suitable for the current Portuguese/English Surface UI. It is loaded only through a relative local URL and is expected to be copied into offline product bundles by the repository source-graph builder.
