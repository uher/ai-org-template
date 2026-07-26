#!/usr/bin/env bash
# 관심사 브리핑 — 헤드리스 AI 세션을 깨워 오늘의 관심 주제를 검색·요약해 텔레그램으로 보낸다.
#
# ⚠️ 비용이 든다. 실행 1회당 웹 검색 + 요약 토큰이 소모된다(대략 몇십 센트~몇 달러).
#    --max-budget-usd 로 상한을 걸어두었으니 필요에 맞게 조절하라.
#    비용을 원치 않으면 이 자동화를 아예 켜지 마라 — 시스템의 필수 요소가 아니다.
#
# 준비:
#   cp control/automation/interests.md.example control/automation/interests.md
#   # 관심사를 채운다. (세팅 마법사가 대신 채워주기도 한다)
#   cp control/notify.conf.example control/notify.conf && chmod 600 control/notify.conf
#   # secretary_bot_token / secretary_chat_id 를 채운다 (없으면 tree 로 보낸다)
#
# 수동 실행 / 스케줄 등록:
#   bash control/automation/interest-brief.sh
#   crontab: 0 8 * * *  bash /path/to/control/automation/interest-brief.sh
#   macOS launchd: com.example.tree-dispatcher.plist 를 참고해 경로만 바꿔 등록
#
# 환경변수:
#   AI_CLI          헤드리스로 부를 CLI (기본 claude)
#   BRIEF_BUDGET    1회 예산 상한 USD (기본 2)
set -uo pipefail

CTRL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # control/
WORKROOT="$(cd "$CTRL/.." && pwd)"                        # 워크스페이스 루트
AI_CLI="${AI_CLI:-claude}"
BUDGET="${BRIEF_BUDGET:-2}"
PROMPT_FILE="$CTRL/automation/prompts/interest-brief.md"
INTERESTS="$CTRL/automation/interests.md"
LOG_DIR="$CTRL/logs"
mkdir -p "$LOG_DIR" "$CTRL/automation/briefs"
LOG="$LOG_DIR/interest-brief-$(date +%F).log"

echo "[$(date +%H:%M:%S)] === 관심사 브리핑 시작 ===" | tee -a "$LOG"

# interests.md 가 없으면 조용히 종료 — 추측으로 브리핑을 만들면 소음만 남는다.
if [ ! -f "$INTERESTS" ]; then
  echo "interests.md 없음 — 생략. (interests.md.example 을 복사해 채워라)" | tee -a "$LOG"
  exit 0
fi
[ -f "$PROMPT_FILE" ] || { echo "프롬프트 없음: $PROMPT_FILE" | tee -a "$LOG"; exit 1; }

command -v "$AI_CLI" >/dev/null 2>&1 || {
  echo "AI CLI 를 찾을 수 없다: $AI_CLI (AI_CLI 환경변수로 경로 지정)" | tee -a "$LOG"
  exit 1
}

cd "$WORKROOT" || exit 1
"$AI_CLI" -p "$(cat "$PROMPT_FILE")" \
  --add-dir "$WORKROOT" \
  --max-budget-usd "$BUDGET" \
  --output-format json \
  --no-session-persistence \
  >>"$LOG" 2>&1

echo "[$(date +%H:%M:%S)] === 종료 (로그: $LOG · 보관: control/automation/briefs/) ===" \
  | tee -a "$LOG"
