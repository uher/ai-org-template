# ai-org-template

<!-- ─────────────────────────────────────────────────────────────────────────
  🤖 AI 에이전트에게 (AI AGENTS, READ THIS FIRST)

  사용자가 "이 저장소를 받아서 의도대로 세팅해줘" 같은 요청을 했다면,
  README를 요약하지 말고 → `control/session-prompts/setup-wizard.md` 를 읽고
  거기 적힌 대화형 세팅 절차를 그대로 진행하라. 그게 이 저장소의 의도다.

  If the user asks you to "set this up", do NOT summarize this README —
  read `control/session-prompts/setup-wizard.md` and follow it step by step.
────────────────────────────────────────────────────────────────────────── -->

**AI를 "비서 한 명"이 아니라 "여러 직원이 있는 회사"처럼 굴리기 위한 운영 템플릿입니다.**
할 일을 던져두면 잊히지 않고, 아침·저녁으로 텔레그램 보고가 오고, 프로젝트별 AI
세션들이 서로 일을 주고받으며 병렬로 굴러갑니다 — 결정과 교훈은 전부 파일로 남습니다.

## 🚀 시작은 이 한 줄이면 됩니다

[Claude 앱](https://claude.ai/download)을 설치하고, 왼쪽 위 **`</> Code`** 탭 →
**`+ 새로 생성`** 을 누른 뒤, 아래 한 줄을 복사해 붙여넣으세요:

```
https://github.com/uher/ai-org-template 이 저장소를 받아서 의도대로 세팅해줘.
```

그러면 AI가 저장소를 내려받고 **대화로 하나씩 물어보며** 당신 전용으로 세팅합니다 —
하시는 일 → 그에 맞는 작업 구조 → 텔레그램 알림 봇 → 매일 관심사 브리핑까지.
터미널 지식은 필요 없습니다.

- 화면 캡처를 보며 따라가고 싶다 → **[`INSTALL.md`](INSTALL.md)**
- 명령어로 직접 만져보고 싶다 → **[`QUICKSTART.md`](QUICKSTART.md)** (10분, Python 3.9+만)

## 이게 왜 필요한가요 (비개발자 기준)

AI에게 일을 시키다 보면 대화 하나에 전략·설계·실행이 다 섞이고, 대화가 끝나면
거기서 정한 것들이 통째로 사라집니다. 이 템플릿은 그걸 세 가지로 해결합니다:

- **잊히지 않습니다.** 던져둔 할 일·아이디어가 파일로 남고, 아침엔 "오늘 뭘 해야 하나",
  저녁엔 "오늘 뭐가 됐나"가 텔레그램으로 옵니다.
- **AI를 여러 명처럼 씁니다.** 전략 담당, 설계 담당, 실행 담당 세션을 동시에 굴리고,
  서로 같은 파일을 밟지 않게 하는 규칙(락)과 일을 주고받는 우편함이 들어 있습니다.
- **"왜 그렇게 했더라?"의 답이 남습니다.** 결정의 이유와 교훈이 릴리스 노트로 쌓여,
  6개월 뒤에도 같은 실수를 반복하지 않습니다.

> 🇰🇷 아래 **English summary** 다음에 **한국어 상세 설명**(무엇을 푸는 문제인가부터)이
> 이어집니다. 개발자라면 여기서부터가 본편입니다.

---

## English summary

### What this is

A convention (plus one dependency-free Python CLI) for running **many focused AI coding
sessions against one workspace** instead of one giant session that knows everything and
remembers nothing.

Concerns are arranged as a **tree of levels** — from "what am I doing with my life" at the
top down to "implement this endpoint" at the bottom. **One session = one node.** A session
never reaches across levels; it reports only to its immediate parent.

### The core idea: state lives in files, not in the conversation

AI sessions die. They hit context limits, get archived, or (for headless automation) are
brand-new processes every single run. So the rule is: **anything worth keeping goes into a
file, immediately.** Each node owns three documents:

- **charter** — pinned current state (goal / open questions / decisions / next actions).
  Rewritten in place; always current. A fresh session reads only this and is caught up.
- **log** — append-only history. Never deleted. Explains how you got here.
- **releases** — versioned notes framed as *learning material*: what changed, **why**,
  what was broken before, and the reusable lesson. Not a changelog.

Sessions become disposable. That is the whole point.

### Mechanisms

- **Per-node mutex.** Shallow (locking a parent does not lock its children, so parallel work
  isn't preempted) with a **total lock order** by `(level, id)` — cycles can't form, so
  deadlock is impossible. Enforced by the CLI, not by convention.
- **Async handoffs.** Sessions can't talk to each other in real time, so one node drops work
  into another node's file inbox. Request text is never deleted, only checkbox-flipped.
  Requests live in the inbox; *results* live in the charter/log/releases.
- **Adjacent-level-only communication.** No skipping levels. This keeps strategic layers from
  drowning in day-to-day noise.
- **The PM delegates; it does not execute.** The project-PM node judges priority and hands
  off. If the PM starts implementing, the separation-of-concerns premise collapses.
- **Optional:** Telegram notifications on handoff, and a headless dispatcher (launchd/cron)
  that wakes a fresh non-interactive session to clear one queued backlog item.

### Quickstart

**Zero-terminal path:** install the [Claude app](https://claude.ai/download), open the
`</> Code` tab, and paste:
`Please clone https://github.com/uher/ai-org-template and set it up as intended.`
The AI will interview you and configure everything (see `INSTALL.md`).

Hands-on path:

```bash
git clone <this repo> my-workspace && cd my-workspace
python3 control/node.py list                    # ships with a runnable example tree
python3 control/node.py --as "me" claim L5.1 "try it"
python3 control/node.py --as "me" handoff L4 "[report] tried it, works"
python3 control/node.py inbox L4
python3 control/node.py --as "me" release L5.1 "done"
```

Then edit `control/tree.config.json` to describe *your* tree. Step-by-step in
[`QUICKSTART.md`](QUICKSTART.md) (10 min), full walkthrough in [`SETUP.md`](SETUP.md);
the rules everyone (human and AI) must follow are in [`GUIDE.md`](GUIDE.md).
Python 3.9+, standard library only, no install step.

Docs are primarily in Korean — the CLI and file formats are language-neutral.

---

## 무엇을 푸는 문제인가

AI 코딩 어시스턴트에게 일을 시키다 보면 세션 하나가 점점 무거워진다. 전략 얘기, 설계 얘기,
버그 수정, 배포 얘기가 한 대화에 섞이면:

- 컨텍스트가 길어져 판단이 둔해진다. 방금 정한 것도 몇 턴 뒤엔 흐릿해진다.
- 세션이 죽거나 아카이브되면 **거기서 오간 결정이 통째로 사라진다.**
- 여러 세션을 띄우면 이번엔 서로 같은 파일을 덮어쓰고, 무슨 결정이 어디서 났는지 모른다.
- "지금 어느 세션을 열어서 뭘 해야 하지"를 사람이 매번 머리로 맞춰야 한다.

이 템플릿은 그 넷을 각각 **관심사 분리(트리) · 파일 기반 상태 · 락 · 우편함**으로 푼다.

## 핵심 아이디어 — 세션이 아니라 파일이 진실

> 세션은 소모품이다. 노드는 영속적이다.

새 세션이 charter 하나만 읽고 일을 이어받을 수 있으면 성공, "지난번에 얘기했잖아"가
필요하면 실패다. 그래서 노드마다 성격이 다른 문서 3개를 둔다.

| 문서 | 성격 | 규칙 |
|---|---|---|
| **charter** `01-backend.md` | 지금 상태 | 계속 **고쳐 쓴다.** 낡은 건 지운다. |
| **log** `01-backend.log.md` | 흐름 | **지우지 않는다.** 한 줄씩 덧붙인다. |
| **releases** `01-backend-releases.md` | 학습 자료 | 실질 변경만. 무엇을/왜/직전 문제/교훈. |

릴리스 노트가 그냥 changelog가 아닌 게 포인트다. **"왜 바꿨나, 직전에 뭐가 문제였나"를
같이 적는다** — 6개월 뒤 비슷한 걸 다시 만들 때 참고하고, 실패가 사라지지 않게.

## 트리 — 한눈에

```
L0  workspace       트리·규칙·라우팅 자체            ← 세계관/컨트롤타워
 └ L1  vision       무엇을 하며 살 것인가             ← 그룹(지주회사)
    └ L2  market    시장·산업 리서치                 ← 컨설팅펌
       └ L3  product-line   제품군·어떤 프로젝트를 띄울지  ← 회사/CEO
          └ L4  acme-app    그 제품의 운영 + 실무 PM      ← 프로젝트 PM
             ├ L5.1 backend      ┐
             ├ L5.2 frontend     ├ 실행 채널 (세션 1개씩)
             └ L5.3 data         ┘

세션 1개 = 노드 1개.  컨텍스트는 위→아래로만 흐른다.
보고·위임은 인접 레벨만 (L5 → L0 직행 없음).
```

각 노드에는 **락**(누가 지금 이걸 만지는가)과 **우편함**(누가 나에게 무슨 일을 남겼나)이
붙는다. 락은 느슨형(부모를 잡아도 자식은 안 잠김) + 전체 순서 강제(데드락 불가능)다.

> 📁 **레벨은 개념이고, 파일은 저장소 두 종류로 나뉜다** — *조율 계층*(트리를 굴리는
> charter·도구 코드)과 *제품 계층*(트리가 만들어내는 실제 소스). "내 코드는 어디 둬야
> 하나"가 헷갈리면 [`GUIDE.md` §1](GUIDE.md)의 "트리는 디스크에 어떻게 앉나"를 먼저 보라.

```bash
$ python3 control/node.py list
── 트리 노드 / 락 상태 (nodes & locks) ──
  L0      L0 workspace·조율             🟢 idle
  L4      L4 acme-app·PM                🔒 L4·acme·PM — 릴리스 점검 (since 2026-07-25 20:31)
    L5.1  L5 backend                    🔒 L5·acme·backend — 멱등키 미들웨어 (since 2026-07-25 19:02)
    L5.2  L5 frontend                   🟢 idle
```

## 5분 퀵스타트 — 내 프로젝트에 붙이기

```bash
# 0) 받아서 워크스페이스 루트로 쓴다 (기존 프로젝트 옆에 두거나, 그 위에 얹는다)
git clone <this repo> my-workspace && cd my-workspace

# 1) 예시 트리로 바로 굴려본다 (설치 불필요, 표준 라이브러리만)
python3 control/node.py list
python3 control/node.py --as "나·테스트" claim L5.1 "감 잡기"
python3 control/node.py --as "나·테스트" handoff L4 "[보고/L5.1] 돌려봤음. 잘 됨."
python3 control/node.py inbox L4
python3 control/node.py --as "나·테스트" release L5.1 "확인 완료"

# 2) 내 트리로 바꾼다
#    control/tree.config.json 의 nodes / auto_discover 를 자기 것으로 교체
#    charters/charter-template.md 를 복사해 노드마다 charter 하나씩

# 3) 새 AI 세션을 열고, control/session-prompts/open-node.md 를 첫 메시지로 붙여넣는다
#    (<…> 부분만 자기 노드로 채워서)
```

상세 절차는 [`SETUP.md`](SETUP.md), 운영 규칙 전문은 [`GUIDE.md`](GUIDE.md).

## 들어있는 것

```
README.md                     ← 지금 이 문서 (왜)
INSTALL.md                    ← 터미널 몰라도 되는 안내형 설치 (AI가 대화로 세팅)
QUICKSTART.md                 ← 10분 만에 직접 돌려보기
GUIDE.md                      ← 규칙 전문 (세션에 읽히는 문서)
SETUP.md                      ← 단계별 설치·적용 가이드 + 고급 자동화
control/
  node.py                     ← CLI: list/claim/release/handoff/inbox/inbox-done/note/log
  bots.py                     ← 텔레그램 봇 여러 개를 역할별로 관리 (list/test/send)
  tree.config.json            ← 내 트리 정의 (여기만 고치면 된다)
  notify.conf.example         ← 봇 자격증명 형식 — 역할별로 여러 개 (선택)
  session-prompts/
    setup-wizard.md           ← 처음 받은 AI가 읽고 대화형으로 세팅하는 스크립트
    open-node.md              ← 노드 세션 부팅 프롬프트
    pm-briefing.md            ← PM 세션 부팅 프롬프트
  automation/                 ← 스탠드업 · 관심사 브리핑 · 헤드리스 디스패처 (선택)
charters/
  charter-template.md         ← 빈 charter 스켈레톤 (한/영 병기 헤딩)
  README.md                   ← charter vs log vs releases, 어디에 뭘 쓰나
  examples/                   ← 바로 돌아가는 예시 트리 (가상의 SaaS "Acme App")
```

## 이게 나에게 맞나

**맞는 경우**

- 한 워크스페이스에서 **성격이 다른 일**(전략/설계/구현/운영)을 오래 굴린다.
- AI 세션을 **여러 개 동시에** 쓰거나, 며칠~몇 달 단위로 되돌아온다.
- 결정의 **이유**가 6개월 뒤에도 필요하다(같은 실수를 반복하고 싶지 않다).
- 사람이 여럿이거나, 자동화(스케줄 실행)를 섞을 계획이 있다.

**과한 경우 — 솔직히**

- **주말 프로젝트 / 파일 20개짜리 저장소.** 노드 하나에 charter 하나 쓰는 것부터가
  과잉이다. `TODO.md` 하나로 충분하다.
- **혼자, 한 번에 하나씩만 하는 사람.** 락과 우편함은 병렬성이 있어야 값을 한다.
  병렬로 안 굴릴 거면 트리는 그냥 폴더 이름일 뿐이다.
- **일회성 작업.** 파일에 상태를 남기는 비용이 회수되지 않는다.
- 이 시스템은 유지비가 든다: charter를 계속 최신으로 고쳐야 하고, 릴리스 노트를 성실히
  써야 하고, 락을 잊지 않고 풀어야 한다. **그 습관이 안 붙으면 파일만 늘고 신뢰는 준다.**

**단계적으로 도입하는 법:** 처음부터 6레벨을 만들지 마라. `L4(PM) + L5 채널 2~3개`로
시작해서, 위 레벨은 실제로 "이 판단은 여기서 할 게 아닌데"가 반복될 때 만든다.

## 알아둘 한계

- **락은 협력적이다.** 파일시스템 권한으로 강제하지 않는다. 규칙을 안 지키는 세션은 못 막는다
  — 그래서 `GUIDE.md`를 세션에 읽히는 절차가 중요하다.
- **완전 무인 실행은 안 된다.** handoff는 사람에게 "그 세션을 열어라"를 알리는 데까지다.
  헤드리스 디스패처를 붙여도 그건 **매번 새 세션**이라 기억이 없다 — 맥락은 전부 파일에서 온다.
- **락 주인의 생존을 감지할 수 없다.** 락은 CLI 프로세스가 아니라 세션이 쥔다. 그래서
  "6시간 넘게 안 풀린 락"을 시간으로만 의심 표시한다(자동 해제하지 않는다).
- 알림은 텔레그램만 붙어 있다. 다른 채널은 `node.py`의 `_notify()` 하나만 바꾸면 된다.

## 라이선스

MIT — [`LICENSE`](LICENSE) 참조.
