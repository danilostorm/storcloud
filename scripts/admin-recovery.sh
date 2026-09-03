#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

username="${1:-}"

echo "StorCloud Admin Recovery"
echo "========================"

if [ -z "$username" ]; then
  readarray -t rows < <(docker compose exec -T api python - <<'PY'
from database import SessionLocal
from models import User
from sqlalchemy import select
with SessionLocal() as db:
    for u in db.scalars(select(User).order_by(User.id)).all():
        print(f"{u.username}|{u.role}|{1 if u.is_active else 0}")
PY
)

  if [ "${#rows[@]}" -eq 0 ]; then
    echo "No users exist yet. Create the first account from /account/ using the setup token."
    exit 1
  fi

  echo "Current users:"
  for row in "${rows[@]}"; do
    IFS='|' read -r name role active <<<"$row"
    echo "  $name [$role] active=$active"
  done

  admins=0
  for row in "${rows[@]}"; do
    IFS='|' read -r _ role _ <<<"$row"
    [ "$role" = "admin" ] && admins=$((admins+1))
  done

  if [ "$admins" -gt 0 ]; then
    echo "An administrator already exists. Pass a username explicitly only if you intentionally want another admin:"
    echo "  bash scripts/admin-recovery.sh USERNAME"
    exit 0
  fi

  if [ "${#rows[@]}" -eq 1 ]; then
    IFS='|' read -r username _ _ <<<"${rows[0]}"
    echo "No admin exists and there is only one account. Promoting: $username"
  else
    echo
    echo "No administrator exists, but there are multiple accounts. Choose one explicitly:"
    echo "  bash scripts/admin-recovery.sh USERNAME"
    exit 0
  fi
fi

docker compose exec -T api python - "$username" <<'PY'
import sys
from sqlalchemy import select
from database import SessionLocal
from models import User

username=sys.argv[1].strip().lower()
with SessionLocal() as db:
    user=db.scalar(select(User).where(User.username==username))
    if not user:
        raise SystemExit(f"User not found: {username}")
    user.role="admin"
    user.is_active=True
    db.commit()
    print(f"Promoted {user.username} to admin.")
PY

echo "Done. Refresh /account/; log out and back in only if your browser cached the old role."
