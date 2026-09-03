# StorCloud Retro Library

StorCloud keeps one unified Retro library and player. The user selects a game; emulator cores remain an internal implementation detail.

## Library flow

1. User signs in.
2. User uploads a ROM they are authorized to use.
3. StorCloud stores the ROM privately under `storage/roms/<user-id>/`.
4. The library can automatically scan artwork.
5. The game opens in the unified Nostalgist.js / RetroArch WASM player.
6. Save states can sync to the StorCloud account.

## Artwork scan

The built-in scanner uses the public Libretro thumbnail collection, following the same general artwork source used by RetroAssembly.

StorCloud normalizes common ROM filename tags such as region/revision suffixes, maps the selected platform to the Libretro platform name, and searches for:

- `Named_Boxarts` — primary library cover
- `Named_Snaps` — optional background/screenshot

Matched media is downloaded and cached locally in:

```text
storage/media/<user-id>/<rom-id>/
```

This means the launcher uses same-origin cached artwork after the scan instead of hotlinking every cover on every page load.

If automatic matching fails, users can upload a PNG, JPEG or WebP cover manually from **Minha Biblioteca**.

## Scan API

```text
POST /library/roms/{id}/scan
POST /library/scan
GET  /library/roms/{id}/metadata
GET  /library/roms/{id}/cover
GET  /library/roms/{id}/background
POST /library/roms/{id}/cover
```

`POST /library/scan` returns the private user's items for client-batched scanning. The browser scans sequentially to avoid hammering the upstream artwork service.

## Privacy

ROM files and cached artwork are scoped to the authenticated user. The cover/background endpoints verify ROM ownership before serving files.

## Backups

`bash scripts/backup.sh` includes:

- PostgreSQL metadata
- cloud saves
- private ROM library
- cached/custom artwork

## Future metadata providers

The metadata model already has fields for description, developer, publisher, release date and genres. Future providers can fill these without changing the player or personal library contract.
