"""텔레그램 봇 **여러 개**를 역할별로 관리한다 (표준 라이브러리만, 의존성 없음).

왜 여러 개인가 — 알림을 한 봇에 몰면 정작 급한 것을 놓친다. 실전에서 이렇게 갈린다:

  tree       트리 운영 노티 (claim/handoff/우편함)      — node.py가 자동 발송
  secretary  개인 비서 (오늘 할 일 / 결과 / 양방향 요청) — 사람이 직접 대화
  report     외부 수신자용 리포트 (고객·투자자·팀)       — 톤과 내용이 다르다
  alert      장애·이상 감지 (조용해야 정상)              — 울리면 즉시 봐야 하는 채널

역할 이름은 **자유다.** `notify.conf`에 `<역할>_bot_token` / `<역할>_chat_id` 한 쌍을
추가하면 그 역할이 생긴다. 코드를 고칠 필요 없다.

  # 설정 확인 (토큰은 마스킹해서 보여준다)
  python3 control/bots.py list
  # 실제로 살아있는지 확인 — 각 봇에 테스트 메시지 발송
  python3 control/bots.py test
  python3 control/bots.py test secretary
  # 보내기
  python3 control/bots.py send secretary "오늘 할 일 3건"

  # 다른 파이썬 코드에서
  import bots
  bots.send("alert", "체결 지연 감지")
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CONF = Path(__file__).resolve().parent / "notify.conf"

# 역할을 못 찾았을 때 이 순서로 내려간다. 설정이 하나뿐인 사람도 그냥 굴러가게.
FALLBACK = ("tree", "default", "")


def _conf() -> dict:
    if not CONF.exists():
        return {}
    out = {}
    for ln in CONF.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def roles() -> list[str]:
    """설정에 존재하는 역할 이름들. 접두사 없는 `bot_token`은 ''(기본)으로 잡힌다."""
    found = []
    for k in _conf():
        m = re.fullmatch(r"(?:(.+)_)?bot_token", k)
        if m:
            found.append(m.group(1) or "")
    return sorted(found)


def get(role: str = "tree") -> tuple[str, list[str]] | None:
    """(토큰, chat_id 목록). 없으면 FALLBACK 순서로 내려가고, 끝내 없으면 None."""
    c = _conf()
    for r in (role, *FALLBACK):
        key = f"{r}_bot_token" if r else "bot_token"
        chat_key = f"{r}_chat_id" if r else "chat_id"
        tok = c.get(key)
        if tok:
            chats = [x.strip() for x in c.get(chat_key, "").split(",") if x.strip()]
            return tok, chats
    return None


def _post(token: str, method: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def send(role: str, text: str, parse_mode: str = "HTML") -> bool:
    """역할 봇으로 발송. 발송 실패가 호출자를 죽이면 안 되므로 예외를 삼키고 False를 준다."""
    creds = get(role)
    if not creds:
        print(f"(발송 생략 — '{role}' 역할의 봇이 notify.conf에 없다. "
              f"notify.conf.example 참고)")
        return False
    token, chats = creds
    if not chats:
        print(f"(발송 생략 — '{role}' 역할에 chat_id가 없다)")
        return False
    ok = True
    for cid in chats:
        payload = {"chat_id": cid, "text": text, "disable_web_page_preview": True}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            _post(token, "sendMessage", payload)
        except urllib.error.HTTPError as e:
            # HTML 파싱 실패(사용자 입력의 <, & 등)로 알림이 조용히 사라지는 게 최악 —
            # 태그를 벗기고 평문으로 한 번 더 시도한다.
            if parse_mode:
                try:
                    _post(token, "sendMessage",
                          {"chat_id": cid, "text": re.sub(r"<[^>]+>", "", text),
                           "disable_web_page_preview": True})
                    continue
                except Exception:  # noqa: BLE001
                    pass
            print(f"발송 실패({role}→{cid}): HTTP {e.code} {e.read()[:200]!r}")
            ok = False
        except Exception as exc:  # noqa: BLE001
            print(f"발송 실패({role}→{cid}): {exc}")
            ok = False
    return ok


def whoami(role: str) -> str:
    """봇 자격 확인 — 토큰이 살아있는지, 어떤 봇인지."""
    creds = get(role)
    if not creds:
        return "설정 없음"
    try:
        r = _post(creds[0], "getMe", {})
        u = r.get("result", {})
        return f"@{u.get('username')} ({u.get('first_name')})"
    except Exception as exc:  # noqa: BLE001
        return f"❌ 토큰 확인 실패: {exc}"


def _mask(tok: str) -> str:
    return tok[:8] + "…" + tok[-4:] if len(tok) > 14 else "…"


def main() -> None:
    args = sys.argv[1:]
    cmd = args[0] if args else "list"

    if cmd == "list":
        rs = roles()
        if not rs:
            print("notify.conf에 봇이 없다. control/notify.conf.example 를 복사해서 시작하라:")
            print("  cp control/notify.conf.example control/notify.conf && chmod 600 control/notify.conf")
            return
        print(f"── 등록된 봇 {len(rs)}개 ──")
        c = _conf()
        for r in rs:
            tok = c.get(f"{r}_bot_token" if r else "bot_token", "")
            chats = c.get(f"{r}_chat_id" if r else "chat_id", "")
            n = len([x for x in chats.split(",") if x.strip()])
            print(f"  {r or '(기본)':12s} {_mask(tok):18s} 수신자 {n}명")
        print("\n살아있는지 확인:  python3 control/bots.py test")
        return

    if cmd == "test":
        targets = [args[1]] if len(args) > 1 else roles()
        if not targets:
            print("설정된 봇이 없다.")
            return
        for r in targets:
            print(f"  {r or '(기본)':12s} {whoami(r)}", end="  ")
            ok = send(r, f"✅ <b>{r or '기본'}</b> 봇 연결 테스트 — 이 메시지가 보이면 정상입니다.")
            print("발송 OK" if ok else "발송 실패")
        return

    if cmd == "send":
        if len(args) < 3:
            print('사용법: python3 control/bots.py send <역할> "메시지"')
            sys.exit(1)
        sys.exit(0 if send(args[1], args[2]) else 1)

    print(__doc__)


if __name__ == "__main__":
    main()
