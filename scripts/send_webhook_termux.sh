#!/usr/bin/env bash

set -euo pipefail

API_URL="${FREXOR_API_URL:-}"
TOKEN="${FREXOR_WEBHOOK_TOKEN:-}"
EXTERNAL_ID=""
NAME="Dummy Termux"
POSITION="Operator"
TEST_DATE="$(date +%F)"
WAIT_FOR_RESULT=false
POLL_SECONDS=3
MAX_POLLS=200

usage() {
  cat <<'EOF'
Kirim payload assessment dummy lengkap dari Termux.

Penggunaan:
  ./send_webhook_termux.sh --url URL [opsi]

Opsi:
  --url URL              URL FastAPI, contoh http://192.168.99.50:8000
  --external-id ID       ID unik; default dibuat otomatis
  --name NAME            Nama dummy, maksimal 20 karakter
  --position POSITION    Posisi dummy, maksimal 20 karakter
  --date YYYY-MM-DD      Tanggal tes; default tanggal perangkat
  --wait                 Tunggu status akhir job
  --poll-seconds N       Interval status saat --wait; default 3
  --max-polls N          Batas polling saat --wait; default 200
  -h, --help             Tampilkan bantuan

Token dapat disediakan melalui FREXOR_WEBHOOK_TOKEN. Jika tidak ada,
script meminta token secara tersembunyi dan tidak menyimpannya.
EOF
}

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

while (($# > 0)); do
  case "$1" in
    --url)
      (($# >= 2)) || fail "--url memerlukan nilai"
      API_URL="$2"
      shift 2
      ;;
    --external-id)
      (($# >= 2)) || fail "--external-id memerlukan nilai"
      EXTERNAL_ID="$2"
      shift 2
      ;;
    --name)
      (($# >= 2)) || fail "--name memerlukan nilai"
      NAME="$2"
      shift 2
      ;;
    --position)
      (($# >= 2)) || fail "--position memerlukan nilai"
      POSITION="$2"
      shift 2
      ;;
    --date)
      (($# >= 2)) || fail "--date memerlukan nilai"
      TEST_DATE="$2"
      shift 2
      ;;
    --wait)
      WAIT_FOR_RESULT=true
      shift
      ;;
    --poll-seconds)
      (($# >= 2)) || fail "--poll-seconds memerlukan nilai"
      POLL_SECONDS="$2"
      shift 2
      ;;
    --max-polls)
      (($# >= 2)) || fail "--max-polls memerlukan nilai"
      MAX_POLLS="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Argumen tidak dikenal: $1"
      ;;
  esac
done

command -v curl >/dev/null 2>&1 || fail "curl belum terpasang: pkg install curl"
command -v jq >/dev/null 2>&1 || fail "jq belum terpasang: pkg install jq"

[[ -n "$API_URL" ]] || fail "Gunakan --url atau isi FREXOR_API_URL"
API_URL="${API_URL%/}"

if [[ -z "$TOKEN" ]]; then
  read -r -s -p "Webhook token: " TOKEN
  printf '\n'
fi
[[ -n "$TOKEN" ]] || fail "Webhook token kosong"

[[ ${#NAME} -le 20 ]] || fail "Nama maksimal 20 karakter"
[[ ${#POSITION} -le 20 ]] || fail "Posisi maksimal 20 karakter"
[[ "$TEST_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || fail "Tanggal harus YYYY-MM-DD"
[[ "$POLL_SECONDS" =~ ^[1-9][0-9]*$ ]] || fail "--poll-seconds harus bilangan positif"
[[ "$MAX_POLLS" =~ ^[1-9][0-9]*$ ]] || fail "--max-polls harus bilangan positif"

if [[ -z "$EXTERNAL_ID" ]]; then
  EXTERNAL_ID="TERMUX-$(date +%Y%m%d-%H%M%S)"
fi

TEMP_DIRECTORY="$(mktemp -d)"
trap 'rm -rf -- "$TEMP_DIRECTORY"' EXIT
PAYLOAD_FILE="$TEMP_DIRECTORY/payload.json"
RESPONSE_FILE="$TEMP_DIRECTORY/response.json"

jq -n \
  --arg external_id "$EXTERNAL_ID" \
  --arg name "$NAME" \
  --arg position "$POSITION" \
  --arg test_date "$TEST_DATE" \
  '{
    external_id: $external_id,
    name: $name,
    position: $position,
    test_date: $test_date,
    answers: {
      disc: [
        range(1; 25) |
        {question_no: ., mirip: "A", tidak_mirip: "B"}
      ],
      vak: [
        range(1; 31) |
        {question_no: ., answer: "A"}
      ],
      iq: [
        range(1; 61) |
        {question_no: ., answer: "A"}
      ]
    }
  }' >"$PAYLOAD_FILE"

printf 'Mengirim external_id=%s ke %s\n' "$EXTERNAL_ID" "$API_URL"

HTTP_STATUS="$(
  curl --silent --show-error \
    --output "$RESPONSE_FILE" \
    --write-out '%{http_code}' \
    --request POST \
    "$API_URL/api/v1/webhooks/assessments" \
    --header "Authorization: Bearer $TOKEN" \
    --header 'Content-Type: application/json' \
    --data-binary "@$PAYLOAD_FILE"
)"

if [[ "$HTTP_STATUS" != "200" && "$HTTP_STATUS" != "201" ]]; then
  printf 'HTTP %s\n' "$HTTP_STATUS" >&2
  jq . "$RESPONSE_FILE" 2>/dev/null || cat "$RESPONSE_FILE"
  exit 1
fi

jq . "$RESPONSE_FILE"
JOB_ID="$(jq -r '.job_id // empty' "$RESPONSE_FILE")"
[[ -n "$JOB_ID" ]] || fail "Respons tidak memiliki job_id"

if [[ "$WAIT_FOR_RESULT" != true ]]; then
  printf '\nPeriksa status:\n'
  printf './send_webhook_termux.sh --url %q --external-id %q --wait\n' "$API_URL" "$EXTERNAL_ID"
  exit 0
fi

printf '\nMenunggu job %s...\n' "$JOB_ID"

for ((poll = 1; poll <= MAX_POLLS; poll++)); do
  HTTP_STATUS="$(
    curl --silent --show-error \
      --output "$RESPONSE_FILE" \
      --write-out '%{http_code}' \
      "$API_URL/api/v1/jobs/$JOB_ID" \
      --header "Authorization: Bearer $TOKEN"
  )"

  if [[ "$HTTP_STATUS" != "200" ]]; then
    printf 'Pemeriksaan status gagal: HTTP %s\n' "$HTTP_STATUS" >&2
    jq . "$RESPONSE_FILE" 2>/dev/null || cat "$RESPONSE_FILE"
    exit 1
  fi

  JOB_STATUS="$(jq -r '.status' "$RESPONSE_FILE")"
  printf '[%d/%d] status=%s\n' "$poll" "$MAX_POLLS" "$JOB_STATUS"

  case "$JOB_STATUS" in
    DONE)
      jq . "$RESPONSE_FILE"
      printf '\nSUKSES: job selesai.\n'
      exit 0
      ;;
    FAILED|REVIEW_REQUIRED)
      jq . "$RESPONSE_FILE"
      printf '\nGAGAL: job memerlukan pemeriksaan.\n' >&2
      exit 2
      ;;
  esac

  sleep "$POLL_SECONDS"
done

printf 'TIMEOUT: job belum selesai setelah %d pemeriksaan.\n' "$MAX_POLLS" >&2
jq . "$RESPONSE_FILE"
exit 3
