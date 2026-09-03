# Mockup implementation rule

The approved StorCloud Play multi-page mockup is the visual source of truth.

Implementation rules:

1. Do not replace cinematic artwork with generic flat gradients when mockup artwork exists.
2. Extract/fabricate page artwork as dedicated assets under `frontend/assets/art/` and layer live HTML on top.
3. Keep text, counters, usernames, game lists and controls as live DOM data; never bake them into screenshots.
4. Match mockup proportions first: compact top bar, short hero, dense 16:9 game rails, fixed controller footer and TV/gamepad focus.
5. Game cover/background art from the user's library overrides generic page art when available.
6. Responsive/mobile layouts may reflow but must preserve the same visual identity.
7. New pages must reuse the console design system rather than introducing a dashboard/SaaS look.
