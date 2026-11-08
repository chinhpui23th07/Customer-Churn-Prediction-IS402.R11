#!/usr/bin/env bash
set -euo pipefail

source_dir="${GITHUB_WORKSPACE:?Run only from GitHub Actions checkout}"
target_dir="/home/azureuser/churn"
evidence_dir="/home/azureuser/kkbox-evidence"
files=(src/kkbox/api.py src/kkbox/web/app.js src/kkbox/web/index.html src/kkbox/web/style.css)
mkdir -p "$evidence_dir"
backup="$evidence_dir/18_before_ci_deploy_$(date -u +%Y%m%dT%H%M%SZ).tar.gz"

cd "$target_dir"
tar -czf "$backup" "${files[@]}"

restore_old() {
  tar -xzf "$backup" -C "$target_dir"
  sudo systemctl restart kkbox-api
  sudo systemctl start caddy
  echo "DEPLOY_ROLLED_BACK"
}

sudo systemctl stop caddy
for file in "${files[@]}"; do
  install -m 0644 "$source_dir/$file" "$target_dir/$file"
done

if ! sudo systemctl restart kkbox-api; then
  restore_old
  exit 1
fi

ready=0
for _ in {1..20}; do
  if curl -fsS http://127.0.0.1:8000/health 2>/dev/null | grep -q '"status":"ready"'; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" != 1 ]]; then
  restore_old
  exit 1
fi

sudo systemctl start caddy
printf 'DEPLOYED_COMMIT=%s\n' "${GITHUB_SHA:?}"
curl -fsS http://127.0.0.1:8000/health
