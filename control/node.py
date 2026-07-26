#!/usr/bin/env python3
"""node.py — 트리 워크스페이스의 노드 락 · 우편함 · 릴리스 노트 CLI.

왜 있나: 여러 AI 세션이 하나의 워크스페이스를 병렬로 편집한다. 락이 없으면 같은 파일을
동시에 고쳐 서로의 편집을 덮어쓴다. 락이 너무 굵으면(글로벌 단일 락) 병렬성이 죽는다.
그리고 세션끼리는 실시간으로 대화할 수 없으므로, 일을 넘기려면 파일 기반 우편함이 필요하다.

설계 요약 (자세한 배경은 ../GUIDE.md):
  · 느슨형(shallow) 락 — 락은 **자기 노드의 파일만** 보호한다. 부모를 잡아도 자식은 안
    막힌다. 하위 파일을 건드려야 하면 그 하위 락을 **따로** 잡는다(락 여러 개 보유 정상).
  · 전체 순서(total order) — 락은 항상 (레벨, 노드ID) 오름차순으로만 잡는다. 위→아래,
    왼→오른. 이미 L5.3을 쥔 세션은 L4나 L5.1을 새로 잡을 수 없다(거부됨).
    모두가 같은 순서로 잡으므로 순환 대기가 성립하지 않는다 = 데드락 불가능.
  · 락은 차단 장치이자 **상태판** — 누가 어느 노드를 무슨 일로 쥐고 있는지 적는다.
    다른 세션이 `list` 한 번으로 비어있는 노드를 골라 병렬로 붙을 수 있게.

트리 구조는 이 파일에 하드코딩돼 있지 않다 — `tree.config.json`에서 읽는다.
(다른 경로를 쓰려면 `--config <경로>` 또는 환경변수 `TREE_CONFIG`.)

사용법:
  python3 node.py list                                   # 트리 전체 + 락 상태
  python3 node.py --as "L4·app·ops" claim L4 "릴리스 점검"
  python3 node.py --as "L4·app·ops" release L4 "점검 완료"
  python3 node.py --as "L4·app·ops" whoami                # 내 세션이 쥔 락
  python3 node.py --as "L4·app·ops" handoff L5.1 "…"     # 다른 노드 우편함에 할 일
  python3 node.py inbox L5.1                              # 내 우편함 확인
  python3 node.py inbox-done L5.1 1                       # 우편함 1번 완료 처리
  python3 node.py note L4 0.3.0 --changed "…" --why "…"  # 릴리스 노트 한 줄
  python3 node.py log L5.1 "결정: A안 채택"                # 노드 로그에 한 줄 append
  python3 node.py log L5.1 --tail 20                      # 노드 로그 최근 N줄

의존성: 파이썬 표준 라이브러리만. 서드파티 패키지 필요 없음(텔레그램 알림 포함).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

CONTROL_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = CONTROL_DIR / "tree.config.json"

_CFG: dict | None = None
_CFG_DIR: Path = CONTROL_DIR
_ROOT: Path = CONTROL_DIR.parent


# ── 설정 로딩 ────────────────────────────────────────────────────────────────

def load_config(path: str | None = None) -> dict:
    """tree.config.json 로드. 트리 구조·경로·알림 설정이 전부 여기서 온다."""
    global _CFG, _CFG_DIR, _ROOT
    if _CFG is not None:
        return _CFG
    p = Path(path or os.environ.get("TREE_CONFIG") or DEFAULT_CONFIG).expanduser()
    if not p.exists():
        print(f"❌ 설정 파일 없음 (config not found): {p}\n"
              f"   tree.config.json을 만들거나 --config 로 경로를 지정하라. "
              f"예시는 이 저장소의 control/tree.config.json 참조.")
        sys.exit(2)
    try:
        _CFG = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"❌ 설정 파일 JSON 오류 ({p}): {exc}")
        sys.exit(2)
    _CFG_DIR = p.resolve().parent
    _ROOT = _resolve(_CFG_DIR, _CFG.get("workspace_root", ".."))
    return _CFG


def _resolve(base: Path, raw: str) -> Path:
    """상대경로는 base 기준, 절대경로/~는 그대로."""
    q = Path(str(raw)).expanduser()
    return q if q.is_absolute() else (base / q).resolve()


# ── 노드 레지스트리 ───────────────────────────────────────────────────────────

_NATKEY = re.compile(r"(\d+)")


class Node:
    def __init__(self, nid: str, level: int, name: str, charter: Path, lock: Path):
        self.id, self.level, self.name = nid, level, name
        self.charter, self.lock = charter, lock

    @property
    def order(self) -> tuple:
        """전체 순서 키. 락은 반드시 이 순서 오름차순으로만 획득한다.

        숫자 부분은 int로 비교한다 — 문자열 비교면 'L5.10' < 'L5.2'가 돼서
        노드가 10개를 넘는 순간 순서가 뒤틀린다.
        """
        parts = tuple(int(s) if s.isdigit() else s
                      for s in _NATKEY.split(self.id.upper()) if s != "")
        return (self.level, parts)

    def __repr__(self) -> str:  # 디버깅용
        return f"<Node {self.id} L{self.level} {self.name}>"


_REG: list[Node] | None = None


def _lock_dir() -> Path:
    return _resolve(_CFG_DIR, load_config().get("lock_dir", "locks"))


def _inbox_dir() -> Path:
    return _resolve(_CFG_DIR, load_config().get("inbox_dir", "inbox"))


def _lock_path(nid: str) -> Path:
    safe = nid.replace("/", "_").replace(os.sep, "_")
    return _lock_dir() / f"{safe}.lock"


def _registry() -> list[Node]:
    """트리 노드 목록 = 설정의 nodes(고정) + auto_discover(디렉터리 스캔)."""
    global _REG
    if _REG is not None:
        return _REG
    cfg = load_config()
    reg: list[Node] = []
    seen: set[str] = set()

    for spec in cfg.get("nodes", []):
        nid = str(spec["id"])
        charter = _resolve(_ROOT, spec["charter"])
        lock = _resolve(_CFG_DIR, spec["lock"]) if spec.get("lock") else _lock_path(nid)
        reg.append(Node(nid, int(spec["level"]), spec.get("name", nid), charter, lock))
        seen.add(nid.upper())

    # 자식 노드는 디렉터리에서 자동 발견 — 파일 하나 만들면 노드가 하나 늘어난다.
    for spec in cfg.get("auto_discover", []):
        d = _resolve(_ROOT, spec["dir"])
        if not d.is_dir():
            continue
        excl = tuple(spec.get("exclude_suffixes", [".log.md", "-releases.md"]))
        prefix, level = spec.get("id_prefix", "L5."), int(spec.get("level", 5))
        seq = 0
        for f in sorted(d.glob(spec.get("glob", "*.md"))):
            if f.name.endswith(excl):
                continue
            seq += 1
            m = re.match(r"^(\d+)[-_]?(.*)$", f.stem)
            num = str(int(m.group(1))) if m else str(seq)
            name = (m.group(2) or f.stem) if m else f.stem
            nid = f"{prefix}{num}"
            if nid.upper() in seen:
                print(f"⚠️ 노드 ID 중복 무시 (duplicate id): {nid} ← {f}")
                continue
            seen.add(nid.upper())
            reg.append(Node(nid, level, name, f, _lock_path(nid)))

    reg.sort(key=lambda n: n.order)
    _REG = reg
    return reg


def _find(nid: str) -> Node | None:
    want = str(nid).strip().upper()
    for node in _registry():
        if node.id.upper() == want:
            return node
    return None


# ── 락 파일 ──────────────────────────────────────────────────────────────────

def _parse_lock(node: Node) -> dict | None:
    if not node.lock.exists():
        return None
    info: dict = {}
    for line in node.lock.read_text(encoding="utf-8").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = v.strip()
    return info or {"task": node.lock.read_text(encoding="utf-8").strip()}


def _session(arg: str | None) -> str:
    return arg or os.environ.get("TREE_SESSION") or os.environ.get("CLAUDE_SESSION") \
        or "unnamed-session"


def _held_by(session: str) -> list[tuple[Node, dict]]:
    out = []
    for node in _registry():
        info = _parse_lock(node)
        if info and info.get("session") == session:
            out.append((node, info))
    return out


def _stale(info: dict) -> float | None:
    """락이 몇 시간째 방치돼 있는지. 임계(stale_hours)를 넘으면 잊고 나간 락 의심.

    프로세스 생존으로는 판정할 수 없다 — 락 주인은 CLI 프로세스가 아니라 AI 세션이고,
    CLI는 락을 쓰자마자 종료하기 때문. 그래서 경과 시간으로만 본다.
    """
    try:
        started = datetime.strptime(info["started"], "%Y-%m-%d %H:%M").astimezone()
    except (KeyError, ValueError):
        return None
    limit = float(load_config().get("stale_hours", 6))
    hours = (datetime.now().astimezone() - started).total_seconds() / 3600
    return hours if hours >= limit else None


# ── 알림(선택) ───────────────────────────────────────────────────────────────
# 표준 라이브러리만 쓴다(urllib) — 서드파티 requests가 없어도 동작한다.
# 토큰은 절대 설정 파일이나 코드에 넣지 않는다. gitignore된 notify.conf에서만 읽는다.

def _notify_creds() -> tuple[str, str, str] | None:
    cfg = load_config().get("notify", {})
    if not cfg.get("enabled", False) or os.environ.get("TREE_NOTIFY") == "0":
        return None
    conf_path = _resolve(_CFG_DIR, cfg.get("conf", "notify.conf"))
    if not conf_path.exists():
        print(f"(알림 생략 — notify.conf 없음: {conf_path}. "
              f"notify.conf.example 참고)")
        return None
    conf: dict = {}
    for line in conf_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        conf[k.strip()] = v.strip()
    # 봇 여러 개를 쓸 수 있다(control/bots.py). 트리 노티는 `tree` 역할을 쓰고,
    # 없으면 접두사 없는 bot_token 으로 내려간다 — 봇 하나만 쓰던 설정도 그대로 동작.
    role = cfg.get("role", "tree")
    token = conf.get(f"{role}_bot_token") or conf.get("bot_token")
    chat = conf.get(f"{role}_chat_id") or conf.get("chat_id")
    if not token or not chat:
        print(f"(알림 생략 — {conf_path}에 {role}_bot_token/{role}_chat_id 도, "
              f"bot_token/chat_id 도 없음. notify.conf.example 참고)")
        return None
    return token, chat, cfg.get("prefix", "[tree]")


def _notify(text: str) -> None:
    """best-effort 알림. 실패해도 워크플로를 절대 깨지 않는다."""
    creds = _notify_creds()
    if not creds:
        return
    token, chat_csv, prefix = creds
    import urllib.request
    api = f"https://api.telegram.org/bot{token}/sendMessage"
    for cid in [c.strip() for c in chat_csv.split(",") if c.strip()]:
        try:
            body = json.dumps({"chat_id": cid, "text": f"{prefix} {text}",
                               "parse_mode": "HTML"}).encode("utf-8")
            req = urllib.request.Request(
                api, data=body, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10).read()
        except Exception as exc:  # noqa: BLE001 — 알림 실패가 작업을 막으면 안 된다
            print(f"(텔레그램 알림 실패 — 무시: {exc})")


# ── 세션 간 작업 큐(우편함) ───────────────────────────────────────────────────
# 세션은 데몬이 아니라 누가 턴을 줘야 깨어난다. 그래서 "자동 실행"은 불가하지만 비동기
# 우편함은 가능하다: 한 노드가 다른 노드 앞으로 할 일을 넣고(handoff), 대상 노드는 세션이
# 열릴 때 자기 우편함을 확인한다(inbox). 요청 텍스트는 지우지 않고 체크박스만 뒤집는다 —
# "무엇을 왜 부탁했나"가 남아야 나중에 맥락을 복원할 수 있기 때문.

def _inbox(nid: str) -> Path:
    return _inbox_dir() / f"{nid}.md"


def cmd_handoff(a) -> None:
    """대상 노드 우편함에 할 일을 넣는다(+선택적 알림). 대화를 옮기지 않는 비동기 인계."""
    target = _find(a.to)
    if not target:
        print(f"대상 노드 '{a.to}' 없음. `node.py list`로 확인."); sys.exit(1)
    frm = _session(a.session) if (a.session or os.environ.get("TREE_SESSION")
                                 or os.environ.get("CLAUDE_SESSION")) else (a.frm or "?")
    ts = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    box = _inbox(target.id)
    box.parent.mkdir(parents=True, exist_ok=True)
    if not box.exists():
        box.write_text(
            f"# {target.id} ({target.name}) — 작업 우편함 (inbox)\n\n"
            f"> 다른 세션이 이 노드 앞으로 남긴 할 일. `[ ]`=대기 `[x]`=완료.\n"
            f"> 확인: `node.py inbox {target.id}` · "
            f"완료처리: `node.py inbox-done {target.id} <번호>`\n\n", encoding="utf-8")
    with box.open("a", encoding="utf-8") as f:
        f.write(f"- [ ] ({ts}, ←{frm}) {a.task}\n")
    _notify(f"📬 <b>{target.id} {target.name}</b> 우편함에 새 작업\n{a.task}\n"
            f"(보낸 세션: {frm}) → 해당 세션 열어 처리")
    print(f"📬 {target.id} 우편함에 넣음: {a.task}\n"
          f"   (대상 세션이 열릴 때 확인된다 — 자동 실행되지 않는다)")


def cmd_inbox(a) -> None:
    """노드 우편함의 대기 작업 표시. 세션을 열면 제일 먼저 이걸 확인한다."""
    nodes = [_find(a.node)] if a.node else _registry()
    any_pending = False
    for node in nodes:
        if not node:
            continue
        box = _inbox(node.id)
        if not box.exists():
            continue
        lines = [l for l in box.read_text(encoding="utf-8").splitlines()
                 if l.startswith("- [")]
        pending = [l for l in lines if l.startswith("- [ ]")]
        if not pending and not a.all:
            continue
        any_pending = any_pending or bool(pending)
        print(f"── {node.id} ({node.name}) 우편함: 대기 {len(pending)}건 ──")
        show = lines if a.all else pending
        for i, l in enumerate(show):
            body = l.split(")", 1)[-1].strip() if ")" in l else l
            mark = "✅" if l.startswith("- [x]") else "⬜"
            print(f"  {i + 1}. {mark} {body}")
    if not any_pending and not a.all:
        print("대기 중인 작업 없음 (inbox clear). 🟢")


def cmd_inbox_done(a) -> None:
    node = _find(a.node)
    if not node:
        print(f"노드 '{a.node}' 없음."); sys.exit(1)
    box = _inbox(node.id)
    if not box.exists():
        print("우편함 없음."); return
    lines = box.read_text(encoding="utf-8").splitlines()
    task_idxs = [i for i, l in enumerate(lines) if l.startswith("- [ ]")]
    if not (1 <= a.n <= len(task_idxs)):
        print(f"대기 작업 {a.n}번 없음 (대기 {len(task_idxs)}건)."); sys.exit(1)
    li = task_idxs[a.n - 1]
    lines[li] = lines[li].replace("- [ ]", "- [x]", 1)
    box.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ {node.id} 우편함 {a.n}번 완료 처리. (요청 원문은 지우지 않는다)")


# ── 상태 조회 ────────────────────────────────────────────────────────────────

def _pad(s: str, width: int) -> str:
    """한글·한자는 터미널에서 두 칸을 먹는다 — 표가 어긋나지 않게 폭을 보정한다."""
    import unicodedata
    w = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)
    return s + " " * max(0, width - w)


def cmd_list(a) -> None:
    print("── 트리 노드 / 락 상태 (nodes & locks) ──")
    for node in _registry():
        info = _parse_lock(node)
        if info:
            age = _stale(info)
            stale = f" ⚠️{age:.0f}h째 방치?" if age else ""
            state = (f"🔒 {info.get('session', '?')} — {info.get('task', '?')}"
                     f" (since {info.get('started', '?')}){stale}")
        else:
            state = "🟢 idle"
        indent = "  " * max(0, node.level - 4) if node.level >= 5 else ""
        missing = "" if node.charter.exists() else "  ⚠️charter 없음"
        print(f"  {indent}{_pad(node.id, 8 - len(indent))}L{node.level} "
              f"{_pad(node.name, 26)} {state}{missing}")
    if a.session:
        mine = _held_by(a.session)
        print(f"\n  내 세션({a.session})이 쥔 락: "
              f"{', '.join(n.id for n, _ in mine) if mine else '없음'}")


def cmd_whoami(a) -> None:
    session = _session(a.session)
    mine = _held_by(session)
    print(f"세션(session): {session}")
    if not mine:
        print("  쥔 락 없음 — 아무 노드나 claim 가능."); return
    for node, info in mine:
        print(f"  🔒 {node.id} ({node.name}) — {info.get('task')} "
              f"since {info.get('started')}")
    top = max((n for n, _ in mine), key=lambda n: n.order)
    print(f"  → 다음 claim은 순서상 {top.id} 보다 뒤(아래/오른쪽) 노드만 가능.")


# ── 락 획득/해제 ─────────────────────────────────────────────────────────────

def cmd_claim(a) -> None:
    node = _find(a.node)
    if not node:
        print(f"노드 '{a.node}' 없음. `node.py list`로 확인."); sys.exit(1)
    session = _session(a.session)

    info = _parse_lock(node)
    if info:
        if info.get("session") == session:
            print(f"(이미 내 세션이 쥐고 있음: {info.get('task')}) — 그대로 진행."); return
        age = _stale(info)
        stale = (f"\n   ⚠️ {age:.0f}시간째 방치 — 잊고 나간 락일 수 있다. "
                 f"사용자에게 확인 후 --force") if age else ""
        if not a.force:
            print(f"❌ {node.id} ({node.name})는 다른 세션이 작업중 (locked):\n"
                  f"   세션: {info.get('session', '?')}\n"
                  f"   작업: {info.get('task', '?')}  (시작 {info.get('started', '?')})"
                  f"{stale}\n"
                  f"   → 끝나길 기다리거나, 다른 노드에서 병렬로 작업하라.")
            sys.exit(1)
        print(f"⚠️ --force: 기존 락({info.get('session')}) 덮어씀.")

    # 데드락 방지 — 전체 순서(레벨, 노드ID) 오름차순으로만 획득 가능
    for held, hinfo in _held_by(session):
        if node.order <= held.order:
            print(f"❌ 락 순서 위반 (lock ordering violation — 데드락 방지):\n"
                  f"   이미 보유: {held.id} ({hinfo.get('task')})\n"
                  f"   요청:      {node.id}\n"
                  f"   락은 항상 위→아래·왼→오른 순서로만 잡는다. {node.id}가 먼저 "
                  f"필요했다면\n"
                  f"   `node.py release {held.id} \"...\"` 후 {node.id} → {held.id} "
                  f"순으로 다시 잡아라.")
            sys.exit(1)

    ts = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    node.lock.parent.mkdir(parents=True, exist_ok=True)
    node.lock.write_text(
        f"node: {node.id}\nlevel: {node.level}\nname: {node.name}\n"
        f"session: {session}\ntask: {a.task}\npid: {os.getpid()}\nstarted: {ts}\n",
        encoding="utf-8")
    held_now = [n.id for n, _ in _held_by(session)]
    _notify(f"🔒 <b>{node.id} {node.name}</b> 작업 시작\n{a.task}\n(세션: {session})")
    print(f"🔒 {node.id} ({node.name}) 확보 (claimed) — {a.task}")
    print(f"   이 세션 보유 락: {', '.join(held_now)}")


def cmd_release(a) -> None:
    node = _find(a.node)
    if not node:
        print(f"노드 '{a.node}' 없음."); sys.exit(1)
    info = _parse_lock(node)
    if not info:
        print(f"({node.id} 락 없음 — claim 없이 release)"); return
    session = _session(a.session)
    if info.get("session") not in (session, None) and not a.force:
        print(f"❌ {node.id} 락 주인은 다른 세션({info.get('session')}). "
              f"뺏으려면 --force."); sys.exit(1)
    node.lock.unlink()
    _notify(f"🟢 <b>{node.id} {node.name}</b> 작업 종료 — 다음 작업 가능\n{a.result}")
    print(f"🟢 {node.id} ({node.name}) 해제 (released) — {a.result}")


# ── 릴리스 노트 / 로그 ───────────────────────────────────────────────────────

def _rel_to_root(p: Path) -> str:
    try:
        return str(p.relative_to(_ROOT))
    except ValueError:
        return str(p)


def cmd_note(a) -> None:
    """릴리스 노트 한 줄 추가. 모든 레벨이 같은 형식으로 버전 히스토리를 쌓는다.

    목적은 변경 이력이 아니라 **학습 자료**다 — 무엇을 바꿨나뿐 아니라 왜, 직전에 뭐가
    문제였나, 재사용 가능한 교훈이 뭔가를 함께 남긴다.
    """
    node = _find(a.node)
    if not node:
        print(f"노드 '{a.node}' 없음."); sys.exit(1)
    rn = node.charter.with_name(node.charter.stem + "-releases.md")
    if not rn.exists():
        rn.parent.mkdir(parents=True, exist_ok=True)
        rn.write_text(
            f"# {node.id} {node.name} — 릴리스 노트 (release notes)\n\n"
            f"> 이 노드에 가해진 변경의 버전 히스토리. 최신이 위.\n"
            f"> 형식·이유는 GUIDE.md 「버전화 원칙」 참조.\n"
            f"> 추가: `python3 control/node.py note {node.id} <버전> --changed \"...\"`\n\n",
            encoding="utf-8")
    ts = datetime.now().astimezone().strftime("%Y-%m-%d")
    # 각 항목을 리스트로 — 마크다운은 단순 줄바꿈을 한 문단으로 이어붙이는 렌더러가 많다.
    block = [f"## {a.version} — {ts}", "", f"- **바뀐 것 (changed):** {a.changed}"]
    if a.why:
        block.append(f"- **왜 (why):** {a.why}")
    if a.problem:
        block.append(f"- **이전 문제 (previous problem):** {a.problem}")
    if a.lesson:
        block.append(f"- **교훈·재사용 포인트 (lesson):** {a.lesson}")
    block.append("")

    body = rn.read_text(encoding="utf-8")
    idx = body.find("## ")  # 최신이 위 — 기존 첫 항목 앞에 끼워넣는다
    new = (body[:idx] + "\n".join(block) + "\n" + body[idx:]) if idx != -1 \
        else body.rstrip() + "\n\n" + "\n".join(block) + "\n"
    rn.write_text(new, encoding="utf-8")
    print(f"📝 {_rel_to_root(rn)} ← {a.version}: {a.changed[:60]}")


def cmd_log(a) -> None:
    """노드 로그(append-only 히스토리). charter가 '지금 상태'라면 로그는 '흐름'이다."""
    node = _find(a.node)
    if not node:
        print(f"노드 '{a.node}' 없음."); sys.exit(1)
    lg = node.charter.with_name(node.charter.stem + ".log.md")
    if a.message:
        if not lg.exists():
            lg.parent.mkdir(parents=True, exist_ok=True)
            lg.write_text(
                f"# {node.id} {node.name} — 대화·결정 로그 (append-only)\n\n"
                f"> 고정 상태(charter)는 {node.charter.name} 참조. 여기는 지우지 않는 "
                f"히스토리.\n\n", encoding="utf-8")
        ts = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
        with lg.open("a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **{a.who}**: {a.message}\n")
        print(f"🗒  {_rel_to_root(lg)} ← {a.message[:60]}")
        return
    if not lg.exists():
        print("(로그 없음)"); return
    lines = [l for l in lg.read_text(encoding="utf-8").splitlines()
             if l.startswith("- ")]
    for l in lines[-a.tail:]:
        print(l)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="트리 워크스페이스 노드 락 · 우편함 · 릴리스 노트")
    ap.add_argument("--config", default=None,
                    help="tree.config.json 경로 (기본: control/tree.config.json "
                         "또는 $TREE_CONFIG)")
    ap.add_argument("--as", dest="session", default=None,
                    help="세션 이름 (예: L4·app·ops). 없으면 $TREE_SESSION")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="트리 전체 + 락 상태")
    sub.add_parser("whoami", help="내 세션이 쥔 락")
    p = sub.add_parser("claim", help="노드 락 획득"); p.add_argument("node")
    p.add_argument("task"); p.add_argument("--force", action="store_true",
                                           help="stale 락 강제 탈취")
    p = sub.add_parser("release", help="노드 락 해제"); p.add_argument("node")
    p.add_argument("result"); p.add_argument("--force", action="store_true")
    p = sub.add_parser("note", help="릴리스 노트 추가")
    p.add_argument("node"); p.add_argument("version")
    p.add_argument("--changed", required=True); p.add_argument("--why")
    p.add_argument("--problem"); p.add_argument("--lesson")
    p = sub.add_parser("handoff", help="다른 노드 우편함에 할 일 넣기")
    p.add_argument("to"); p.add_argument("task")
    p.add_argument("--from", dest="frm", default=None, help="보낸 노드/세션(수동 지정)")
    p = sub.add_parser("inbox", help="우편함 확인")
    p.add_argument("node", nargs="?", default=None)
    p.add_argument("--all", action="store_true", help="완료분까지 전부")
    p = sub.add_parser("inbox-done", help="우편함 항목 완료 처리")
    p.add_argument("node"); p.add_argument("n", type=int)
    p = sub.add_parser("log", help="노드 로그 append / 조회")
    p.add_argument("node"); p.add_argument("message", nargs="?", default=None)
    p.add_argument("--who", default="me"); p.add_argument("--tail", type=int, default=20)
    a = ap.parse_args()
    load_config(a.config)
    {"list": cmd_list, "whoami": cmd_whoami, "claim": cmd_claim,
     "release": cmd_release, "note": cmd_note, "handoff": cmd_handoff,
     "inbox": cmd_inbox, "inbox-done": cmd_inbox_done, "log": cmd_log}[a.cmd](a)


if __name__ == "__main__":
    main()
