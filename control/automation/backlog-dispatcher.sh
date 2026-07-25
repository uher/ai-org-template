#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# backlog-dispatcher.sh — 헤드리스 디스패처 (선택 기능, EXAMPLE)
#
# 무엇: 사람이 세션을 열지 않아도, 우편함에 쌓인 일을 **자동화가 허용된 노드에 한해서만**
#       한 번에 하나씩 처리하도록 AI를 비대화식(headless)으로 깨운다.
#
# 왜 필요한가: 세션은 데몬이 아니다. 누가 턴을 줘야 깨어난다. 그래서 우편함에 일이
#       쌓여도 아무도 열지 않으면 그냥 쌓인 채로 있다. OS 스케줄러(launchd/cron)가
#       주기적으로, 또는 우편함 디렉터리가 바뀔 때 이 스크립트를 실행해 그 갭을 메운다.
#
# 중요한 한계(반드시 이해할 것):
#   · 이 실행은 **매번 완전히 새 세션**이다. 이전 실행의 기억이 없다. 맥락은 전부
#     charter/로그/우편함 파일에서 다시 읽어야 한다 — 그래서 이 시스템이 파일 기반이다.
#   · 사람이 안 보고 있으므로 **범위를 좁게** 묶어야 한다. 아래 AUTOMATED_NODES에
#     명시한 노드 밖은 손대지 않게 프롬프트에서도 못 박는다.
#   · 승인 게이트를 끄지 마라. 애매한 행동은 승인 대기에 걸려 그 턴이 그냥 실패하는 게
#     맞다(fail-closed = 사람이 없을 때 "아무것도 안 함"이 안전한 기본값).
#   · **AI가 스스로 자기 권한을 넓히게 하지 마라** — 권한 설정 파일 작성, chmod +x,
#     승인 우회 플래그 같은 건 사람이 직접 한다. (실전에서 반복 확인된 함정)
#
# 설치: SETUP.md의 「선택: 헤드리스 디스패처」 참조. 아래 경로/명령은 전부 예시다.
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

# ── 여기부터 사용자가 고칠 부분 ──────────────────────────────────────────────
CTRL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # control/ 디렉터리
WORKROOT="$(cd "$CTRL/.." && pwd)"                        # 워크스페이스 루트
AI_CLI="${AI_CLI:-claude}"                                # 헤드리스로 부를 CLI
PROMPT_FILE="$CTRL/automation/prompts/backlog-dispatcher.md"
LOG_DIR="$CTRL/logs"
WEEKDAYS_ONLY="${WEEKDAYS_ONLY:-1}"                       # 1이면 주말엔 실행 안 함
# ─────────────────────────────────────────────────────────────────────────────

mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/backlog-$(date +%F).log"

echo "[$(date +%H:%M:%S)] === 헤드리스 백로그 처리 시작 ===" | tee -a "$LOG"

# 주말 방어(스케줄러가 평일만 발화해도 이중 안전장치)
if [ "$WEEKDAYS_ONLY" = "1" ]; then
  dow=$(date +%u)
  [ "$dow" -ge 6 ] && { echo "주말 — 생략" | tee -a "$LOG"; exit 0; }
fi

[ -f "$PROMPT_FILE" ] || { echo "프롬프트 없음: $PROMPT_FILE" | tee -a "$LOG"; exit 1; }
PROMPT="$(cat "$PROMPT_FILE")"

cd "$WORKROOT" || exit 1

# --no-session-persistence: 이 실행은 흔적을 남기지 않는 일회성 세션이다.
#                           맥락은 오직 파일(charter/우편함)에서만 온다.
# --max-budget-usd        : 무인 실행이 폭주하지 않게 상한을 둔다.
"$AI_CLI" -p "$PROMPT" \
  --add-dir "$WORKROOT" \
  --max-budget-usd 5 \
  --output-format json \
  --no-session-persistence \
  >>"$LOG" 2>&1

echo "[$(date +%H:%M:%S)] === 종료 (로그: $LOG · 결과 보고는 PM 노드 우편함) ===" \
  | tee -a "$LOG"
