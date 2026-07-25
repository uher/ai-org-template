#!/usr/bin/env python3
"""standup.py — 노드별 대기 작업 다이제스트("어느 세션을 열어 뭘 해야 하나").

여러 세션(채널)으로 나눠 일하면 "지금 어느 세션을 열어야 하지"가 흩어진다. 이 스크립트가
모든 노드의 **우편함 대기 항목**과 **charter의 「다음 행동」 미완료 체크박스**를 모아
한 장으로 만든다. 출근 알람처럼 쓰면 된다.

  python3 control/automation/standup.py --print   # 출력만
  python3 control/automation/standup.py           # 출력 + 텔레그램 발송(notify 설정 시)

의존성: 표준 라이브러리만. 트리 정의는 node.py가 읽는 tree.config.json을 그대로 쓴다.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import node  # noqa: E402 — 트리 레지스트리·우편함·알림을 재사용한다


def _charter_todos(charter_path) -> list[str]:
    """charter의 「다음 행동」 미완료 항목. 형식(`- [ ] …`)을 지켜야 스캔된다."""
    try:
        lines = charter_path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, AttributeError, OSError):
        return []
    return [l[6:].strip() for l in lines if l.startswith("- [ ]")]


def _inbox_pending(nid: str) -> list[str]:
    box = node._inbox(nid)
    if not box.exists():
        return []
    out = []
    for l in box.read_text(encoding="utf-8").splitlines():
        if l.startswith("- [ ]"):
            out.append(l.split(")", 1)[-1].strip() if ")" in l else l[5:].strip())
    return out


def build() -> tuple[str, int]:
    """(다이제스트 텍스트, 총 대기건수)."""
    sections, total = [], 0
    for n in node._registry():
        inbox = _inbox_pending(n.id)
        todos = _charter_todos(n.charter)
        cnt = len(inbox) + len(todos)
        if cnt == 0:
            continue
        total += cnt
        lock = node._parse_lock(n)
        busy = f"  🔒{lock.get('session')}" if lock else ""
        head = f"▸ <b>{n.id} {n.name}</b> — 대기 {cnt}건{busy}"
        items = [f"  📬 {t[:70]}" for t in inbox] + [f"  ☐ {t[:70]}" for t in todos]
        sections.append(head + "\n" + "\n".join(items[:6])
                        + (f"\n  …외 {len(items) - 6}건" if len(items) > 6 else ""))
    if not sections:
        return "✅ 대기 작업 없음 — 모든 노드 깨끗합니다.", 0
    ts = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    header = (f"📋 <b>세션 스탠드업</b> ({ts})\n"
              f"총 대기 {total}건 · 아래 세션을 열어 처리하세요.\n")
    return header + "\n\n".join(sections), total


def main() -> None:
    ap = argparse.ArgumentParser(description="노드별 대기 작업 다이제스트")
    ap.add_argument("--config", default=None, help="tree.config.json 경로")
    ap.add_argument("--print", dest="print_only", action="store_true",
                    help="발송하지 않고 출력만")
    a = ap.parse_args()
    node.load_config(a.config)
    text, total = build()
    print(text.replace("<b>", "").replace("</b>", ""))
    if a.print_only:
        return
    node._notify(text)  # notify.conf가 없으면 조용히 건너뛴다
    print(f"[발송 시도 완료] 대기 {total}건")


if __name__ == "__main__":
    main()
