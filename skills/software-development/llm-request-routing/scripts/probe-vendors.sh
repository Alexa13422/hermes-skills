#!/usr/bin/env bash
# Пінг кожного вендора шлюзу реальним chat-completion.
#
# Навіщо: /v1/models і склад комбо — це лише декларації. Креденшел за
# переліченою моделлю може бути з виснаженою квотою або протухлим OAuth, і
# тоді priority/quota-ланцюг тихо деградує до того вендора, що ще відповідає.
# Запускати ПЕРЕД побудовою мапи ролей чи перебудовою комбо; усе, що не 200,
# вважати відсутнім.
#
# Використання: ./probe-vendors.sh [host]    # типово localhost:20128

set -uo pipefail
HOST="${1:-localhost:20128}"

OKEY=$(grep -h "HERMES_CUSTOM_LOCALHOST_20128_API_KEY" ~/.hermes/.env | head -1 | cut -d= -f2- | tr -d '"'"'"' ')
if [ -z "$OKEY" ]; then echo "не знайдено ключ шлюзу в ~/.hermes/.env" >&2; exit 1; fi

# По одній моделі на вендора на tier. Правити під фактичні ID.
MODELS=(
  "claude/claude-opus-5-5"
  "claude/claude-sonnet-5-5"
  "claude/claude-haiku-5-5"
  "codex/gpt-6-sol"
  "codex/gpt-5.6-terra"
  "codex/gpt-5.6-luna"
  "kiro/claude-sonnet-5"
)

printf "%-30s %-6s %s\n" MODEL HTTP DETAIL
for M in "${MODELS[@]}"; do
  CODE=$(curl -s -m 60 -o /tmp/probe.json -w "%{http_code}" \
    -H "Authorization: Bearer $OKEY" -H "Content-Type: application/json" \
    -d "{\"model\":\"$M\",\"max_tokens\":10,\"messages\":[{\"role\":\"user\",\"content\":\"reply OK\"}]}" \
    "http://$HOST/v1/chat/completions")
  DETAIL=$(python3 - <<'EOF'
import json
try:
    d = json.load(open('/tmp/probe.json'))
except Exception:
    print(open('/tmp/probe.json').read()[:95]); raise SystemExit
if 'error' in d:
    print(str(d['error'].get('message', ''))[:95])
elif 'message' in d:
    print(str(d['message'])[:95])
else:
    try:
        print('live ->', d['choices'][0]['message']['content'][:30].replace('\n', ' '))
    except Exception:
        print('200, але несподівана форма відповіді')
EOF
)
  printf "%-30s %-6s %s\n" "$M" "$CODE" "$DETAIL"
done

cat <<'NOTE'

Як читати результат:
  200                  вендор придатний
  429 quota threshold  поріг, накладений шлюзом; спробувати підняти його
                       перед перебудовою комбо
  400 INVALID_MODEL_ID неправильний ID для цього провайдера або протухлий OAuth
NOTE
