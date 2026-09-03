# StorCloud Play — Pixel Plates

The eight approved 1672×941 mockups are the visual source of truth for the main UI. Static art, lighting, composition and spacing come from the approved plate images. Only live regions (user/account data, catalog, ROM library, emulator canvas, Local Agent state, achievements and admin metrics) are rendered above the plates.

Mapping:
- `/` → `frontend/assets/mockups/home.jpg`
- `/catalog/` → `catalog.jpg`
- `/library/` → `library.jpg`
- `/retro/` → `retro.jpg`
- `/pc/` → `pc.jpg`
- `/achievements/` → `achievements.jpg`
- `/account/` → `account.jpg`
- `/admin/` → `admin.jpg`

The stage is fixed at 1672×941 and scales proportionally to the viewport. Ultrawide side areas use a blurred extension of the same plate rather than stretching the UI.
