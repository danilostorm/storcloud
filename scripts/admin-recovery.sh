#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

username="${1:-}"

echo "StorCloud Admin Recovery"
echo "========================"

echo "Current users:"
docker compose exec -T api python - <<'PY'
from database import SessionLocal
from models import User
from sqlalchemy import select
with SessionLocal() as db:
    users=db.scalars(select(User).order_by(User.id)).all()
    if not users:
        print("  (no users)")
    for u in users:
        print(f"  {u.id}: {u.username} [{u.role}] active={u.is_active}")
PY

if [ -z "$username" ]; then
  echo
  echo "Usage: bash scripts/admin-recovery.sh USERNAME"
  echo "This command runs locally on the StorCloud VM and promotes that existing account."
  exit 0
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

echo "Done. Log out and log back in if the browser still shows the old role."
