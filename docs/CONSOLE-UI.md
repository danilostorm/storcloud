# StorCloud Console UI

StorCloud's primary UI is a console-style launcher inspired by modern living-room gaming dashboards rather than an admin SaaS layout.

## Design rules

- horizontal game rails are the main browsing pattern
- the focused game can change the large ambient background
- game covers use portrait artwork; execution catalog cards can use 16:9 art
- primary actions use large rounded buttons suitable for TV viewing
- keyboard arrow keys and gamepads use spatial navigation
- Gamepad A activates the focused item; B navigates back
- layout remains usable with mouse/touch on desktop/mobile
- account/admin controls are secondary to the game library

## Shared assets

- `frontend/assets/console.css` — visual system
- `frontend/assets/spatial-nav.js` — keyboard/gamepad focus navigation

## Current console-style surfaces

- Home
- Hybrid Catalog
- Retro Library
- Account
- Admin

The Retro player, PC Local, achievements and streaming diagnostics can reuse the same assets while keeping controls appropriate for their workflows.
