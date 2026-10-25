#!/usr/bin/env bash
# Local backend + Android development. Uses only the local Docker stack.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export GOOGLE_ADC_FILE="${GOOGLE_ADC_FILE:-${HOME}/.config/gcloud/application_default_credentials.json}"
# Old simulator-generated configs do not expose the fork's management API.
export ZENOH_MTLS_CONFIG_FILE=zenoh-router-mtls.json5

compose() {
  docker compose --project-directory "${REPO_ROOT}/backend" \
    -f "${REPO_ROOT}/backend/local-docker-compose.yml" \
    -f "${REPO_ROOT}/backend/local-docker-compose.gcs.yml" "$@"
}

start_backend() {
  if [[ ! -f "${GOOGLE_ADC_FILE}" ]]; then
    echo 'Google ADC is missing. Run: gcloud auth application-default login' >&2
    exit 1
  fi
  compose up -d --build --wait --wait-timeout 180 backend
  curl --fail --silent --show-error --max-time 5 http://localhost:8000/health
  echo
}

emulator_serial() {
  local serial state name
  while read -r serial state; do
    if [[ "${serial}" == emulator-* && "${state}" == device ]]; then
      name="$(adb -s "${serial}" emu avd name 2>/dev/null | tr -d '\r' | head -n 1)"
      if [[ "${name}" == "${ANDROID_AVD}" ]]; then
        echo "${serial}"
        return
      fi
    fi
  done < <(adb devices)
}

start_android() {
  export ANDROID_HOME="${ANDROID_HOME:-${HOME}/Library/Android/sdk}"
  if [[ -z "${JAVA_HOME:-}" ]]; then
    export JAVA_HOME
    JAVA_HOME="$(/usr/libexec/java_home -v 17 2>/dev/null || true)"
    # Java 17 installed for this checkout's previous verified Android build.
    if [[ -z "${JAVA_HOME}" ]]; then
      local candidate
      for candidate in /private/tmp/emi-jdk17/*/Contents/Home; do
        if [[ -x "${candidate}/bin/java" ]]; then
          JAVA_HOME="${candidate}"
          break
        fi
      done
    fi
  fi
  if [[ -z "${JAVA_HOME:-}" || ! -x "${JAVA_HOME}/bin/java" ]]; then
    echo 'Set JAVA_HOME to a Java 17 JDK before running Android.' >&2
    exit 1
  fi
  export PATH="${JAVA_HOME}/bin:${ANDROID_HOME}/platform-tools:${ANDROID_HOME}/emulator:${PATH}"
  export ANDROID_AVD="${ANDROID_AVD:-Medium_Phone}"
  adb start-server
  local serial booted=false attempt
  serial="$(emulator_serial)"
  if [[ -z "${serial}" ]]; then
    nohup emulator -avd "${ANDROID_AVD}" > "${TMPDIR:-/tmp}/emi-dev-emulator.log" 2>&1 < /dev/null &
  fi
  for ((attempt=0; attempt<120; attempt++)); do
    serial="$(emulator_serial)"
    if [[ -n "${serial}" ]] && [[ "$(adb -s "${serial}" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]]; then
      booted=true
      break
    fi
    sleep 1
  done
  if [[ "${booted}" != true ]]; then
    echo "Emulator did not boot. Check ${TMPDIR:-/tmp}/emi-dev-emulator.log" >&2
    exit 1
  fi
  adb -s "${serial}" reverse tcp:7447 tcp:7447
  adb -s "${serial}" reverse tcp:8081 tcp:8081
  export EXPO_PUBLIC_ZENOH_URL=tls/localhost:7447
  export REACT_NATIVE_PACKAGER_HOSTNAME=127.0.0.1
  # This is the public CA certificate, never a private key or management token.
  export EXPO_PUBLIC_ZENOH_CA_PEM
  EXPO_PUBLIC_ZENOH_CA_PEM="$(compose exec -T zenoh-app cat /run/emi-mower/identity/root_ca.pem)"
  cd "${REPO_ROOT}/app"
  # Expo's virtual development env module also reads dotenv files directly.
  # Keep a local override in sync with the shell exports. Preserve other settings.
  python3 - <<'PY'
import json
import os
import re
from pathlib import Path

path = Path('.env.local')
existing = path.read_text() if path.exists() else ''
existing = re.sub(
    r'(?ms)^# BEGIN EMI LOCAL ZENOH\n.*?^# END EMI LOCAL ZENOH\n?',
    '', existing,
)
block = '# BEGIN EMI LOCAL ZENOH\n'
for name in ('EXPO_PUBLIC_ZENOH_URL', 'EXPO_PUBLIC_ZENOH_CA_PEM'):
    block += name + '=' + json.dumps(os.environ[name]) + '\n'
block += '# END EMI LOCAL ZENOH\n'
path.write_text(existing.rstrip() + '\n' + block)
PY
  if [[ ! -d node_modules/expo ]]; then npm ci; fi
  npm run android -- --device "${ANDROID_AVD}"
}

case "${1:-start}" in
  start) start_backend; start_android ;;
  backend) start_backend ;;
  android) start_android ;;
  logs) compose logs -f --tail 50 backend zenoh-app zenoh-mtls ;;
  status) compose ps ;;
  stop) compose stop ;;
  *) echo 'Usage: scripts/dev.sh [start|backend|android|logs|status|stop]' >&2; exit 2 ;;
esac
