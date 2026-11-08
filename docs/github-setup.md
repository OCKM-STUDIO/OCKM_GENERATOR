# GitHub repository

Public repository: [OCKM-STUDIO/OCKM_GENERATOR](https://github.com/OCKM-STUDIO/OCKM_GENERATOR).
Simon authorised publication on 8 November 2026 after trying the native Mac preview.

## Presentation

Keep **very early alpha** visible in the README, repository description and release
notes. Downloads remain GitHub prereleases until their reliability and platform
coverage justify a stable release. The README links the current Mac alpha directly;
GitHub's latest-release shortcut may omit prereleases.

`docs/img/banner.svg` is the README banner. Keep the PERF-1 acknowledgement and links
in the README alongside the existing source-level credits.

## Publishing builds

The repository contains the shared engine, Pi host and `mac/` Swift host. Mac app
bundles and dependency caches stay out of Git; ZIP bundles belong on Releases.
State the architecture, minimum macOS, signing status, checks performed and known
limitations in each release. Keep dependency sources and licence notices available.

Personal audio, projects, settings and `.pi/` credentials remain excluded. Review
only the intended source and documentation changes before pushing.

See [the Mac guide](../mac/README.md) for building and [the README](../README.md)
for platform setup.
