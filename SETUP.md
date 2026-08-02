# SETUP — 내 프로젝트에 적용하기

`README.md`가 "무엇/왜"라면 이 문서는 **"어떻게"**다. 위에서부터 순서대로 따라가면 된다.
1~5단계까지가 필수(15분), 그 뒤는 전부 선택이다.

## 사전 준비

| 필요한 것 | 비고 |
|---|---|
| Python 3.9 이상 | 표준 라이브러리만 쓴다. `pip install` 없음. |
| AI 코딩 어시스턴트 | 세션을 여러 개 열 수 있으면 무엇이든. 셸 명령을 실행할 수 있어야 편하다. |
| (선택) git | 릴리스 노트·charter를 버전 관리하면 좋다. |
| (선택) 텔레그램 봇 | handoff 알림용. |
| (선택) launchd(macOS) / cron(Linux) | 헤드리스 자동화용. |

```bash
python3 --version    # 3.9+
```

---

## 1단계 — 디렉터리 배치 정하기

> **먼저 읽을 것:** 파일은 **조율 계층**(트리를 굴리는 것)과 **제품 계층**(트리가
> 만들어내는 것) 둘로 나뉜다. 개념은 [`GUIDE.md` §1 "트리는 디스크에 어떻게 앉나"]
> (GUIDE.md)에 있다. 아래는 그걸 실제 폴더로 옮기는 방법이다.

두 가지 방식이 있다. **처음이면 A를 권한다.**

### A. 워크스페이스를 프로젝트들 위에 둔다 (권장)

```
~/work/                          ← 워크스페이스 루트. ⚠️ 이건 저장소가 아니다(그냥 폴더)
│
├── control/                     ┐  조율 계층 — 저장소 1개
│   ├── node.py                  │  (여기서 `git init` 하고 싶다면
│   ├── tree.config.json         │   ~/work 가 아니라 이 묶음 기준으로)
│   └── (내가 만든 도구들…)        │
├── charters/                    │  L0~L4 charter
│   └── channels/                ┘  L5 채널 charter (자동 발견)
│
├── my-app/                      ← 제품 계층 — 각자 독립 저장소
└── another-app/                 ← 제품 계층
```

**세 가지만 기억하면 안 헷갈린다:**

| 질문 | 답 |
|---|---|
| 워크스페이스 루트(`~/work`)가 저장소인가? | **아니다.** 저장소들을 담는 폴더일 뿐이다 |
| 조율 저장소에 코드를 둬도 되나? | **된다.** `node.py`부터가 코드다. 트리를 굴리는 도구는 전부 여기 |
| charter만 있고 코드 저장소가 없는 노드는? | **정상이다.** 논의만 하는 상위 레벨은 원래 그렇다 |

> **한 노드가 두 저장소에 걸칠 때** (예: L4 charter는 조율 쪽, 그 제품 코드는 제품 쪽)
> — 사실의 **정본은 제품 저장소**에 두고 charter는 링크만 건다. 양쪽에 복사하면
> 곧 서로 다른 진실이 된다.

장점: 프로젝트 저장소를 오염시키지 않는다. 프로젝트가 여러 개여도 트리는 하나.
단점: 워크스페이스 자체를 git으로 관리하려면 저장소가 하나 더 생긴다.

### B. 기존 저장소 안에 넣는다

```
my-app/
├── control/
├── docs/channels/               ← L5 채널 charter를 여기에
└── src/
```

장점: 코드와 charter가 같은 저장소에서 같이 커밋된다(이력이 붙어 다닌다).
단점: 저장소가 여러 개가 되면 트리를 어디에 둘지 다시 고민해야 한다.

> 실전 팁: 처음엔 B로 시작해도 되지만, **두 번째 프로젝트가 생기는 순간 A로 옮기게 된다.**
> 옮기는 비용은 `tree.config.json`의 경로를 고치는 정도로 작다.

파일 복사:

```bash
cp -R ai-org-template/control  ~/work/control
cp -R ai-org-template/charters ~/work/charters
cp ai-org-template/GUIDE.md .gitignore ~/work/
```

---

## 2단계 — `control/tree.config.json` 고치기

이 파일이 **트리의 유일한 정의**다. `node.py`에는 트리가 하드코딩돼 있지 않다.

```jsonc
{
  "workspace_root": "..",          // charter 경로들의 기준. 이 설정 파일 위치 기준 상대경로
  "lock_dir": "locks",             // 런타임 상태(gitignore). 설정 파일 기준
  "inbox_dir": "inbox",            // 런타임 상태(gitignore)
  "stale_hours": 6,                // 이 시간 넘게 안 풀린 락은 list에 ⚠️

  "notify": { "enabled": false, "conf": "notify.conf", "prefix": "[tree]" },

  "nodes": [                       // 고정 노드 (L0~L4)
    { "id": "L4", "level": 4, "name": "my-app·PM", "charter": "charters/L4-my-app.md" }
  ],

  "auto_discover": [               // 디렉터리 스캔 → 파일 하나 = 노드 하나
    { "id_prefix": "L5.", "level": 5, "dir": "charters/channels",
      "glob": "*.md", "exclude_suffixes": [".log.md", "-releases.md"] }
  ]
}
```

### 규칙

- `id`는 트리 전체에서 유일해야 한다. `level`은 정수 — **락 순서가 이 값으로 결정된다.**
- `name`은 사람이 읽는 라벨(자유). 세션 이름과 맞춰 두면 `list` 출력이 읽기 쉽다.
- `charter` 경로는 `workspace_root` 기준. 파일이 아직 없어도 `list`는 동작한다(⚠️ 표시).
- **자동 발견 파일명은 `NN-이름.md`** 형식을 지켜라 — 앞 숫자가 노드 번호(`L5.3`),
  뒤가 이름(`data`)이 된다. `03-data.md` → `L5.3 data`.
- `.log.md` / `-releases.md`로 끝나는 곳은 자동 발견에서 제외된다(곁다리 파일이므로).

### 작게 시작하기

레벨 6개를 다 만들 필요 없다. 개인 프로젝트라면 이 정도가 현실적이다:

```jsonc
"nodes": [
  { "id": "L4", "level": 4, "name": "my-app·PM", "charter": "charters/L4-my-app.md" }
],
"auto_discover": [
  { "id_prefix": "L5.", "level": 5, "dir": "charters/channels" }
]
```

확인:

```bash
cd ~/work && python3 control/node.py list
```

---

## 3단계 — 첫 charter 만들기

```bash
mkdir -p ~/work/charters/channels
cp charters/charter-template.md ~/work/charters/L4-my-app.md
cp charters/charter-template.md ~/work/charters/channels/01-backend.md
```

각 파일에서 최소한 이 넷은 지금 채워라(나머지는 비워둬도 된다):

1. **한 줄 목표** — 이 노드가 존재하는 이유
2. **다루는 것 / 다루지 않는 것** — 특히 "다루지 않는 것"에 **어느 노드로 가야 하는지**를 적어라
3. **현재 상태** — 지금 어디까지 와 있나
4. **다음 행동** `- [ ]` — 체크박스 형식을 지켜라(스탠드업이 이 형식을 스캔한다)

잘 쓴 charter의 예: `charters/examples/channels/01-backend.md`
charter / log / releases의 역할 구분: `charters/README.md`

---

## 4단계 — 첫 claim → handoff → release 돌려보기

```bash
cd ~/work

# 지금 누가 뭘 하고 있나
python3 control/node.py list

# 작업 시작 선언 (파일을 고치기 전에 반드시)
python3 control/node.py --as "L5·my-app·backend" claim L5.1 "인증 흐름 정리"

# … 실제 작업 …

# 릴리스 노트 (실질적 변경이 있었으면 release 직전에)
python3 control/node.py note L5.1 0.1.0 \
  --changed "인증 토큰 갱신을 클라이언트가 아니라 게이트웨이에서 처리" \
  --why     "클라이언트마다 갱신 로직이 갈라져 버그가 반복됨" \
  --problem "만료 처리 누락으로 로그아웃 튕김 3건" \
  --lesson  "공통으로 지켜야 할 규칙은 통과 지점 한 곳으로 강제한다"

# 작업 종료
python3 control/node.py --as "L5·my-app·backend" release L5.1 "게이트웨이 갱신 적용"

# 부모(PM)에게 보고 — 인접 레벨만
python3 control/node.py --as "L5·my-app·backend" handoff L4 \
  "[보고/L5.1] 토큰 갱신 게이트웨이 이관 완료. 결정 필요: 만료 임계값 5분 vs 15분."

# PM 세션에서 확인
python3 control/node.py inbox L4
python3 control/node.py inbox-done L4 1
```

### 락에서 막히면

- `❌ … 다른 세션이 작업중` → 정상이다. **작업을 시작하지 말고** 그 세션이 끝나길 기다리거나
  다른 노드에서 병렬로 일한다. 6시간 넘게 방치된 락은 `list`에 ⚠️로 뜬다 —
  사람에게 확인한 뒤에만 `--force`.
- `❌ 락 순서 위반` → 락은 **(레벨, 노드ID) 오름차순으로만** 잡을 수 있다(데드락 방지).
  하위를 `release`하고 상위부터 다시 잡아라.

---

## 5단계 — AI 세션에 규칙 읽히기

**이 단계를 건너뛰면 나머지가 다 무의미하다.** 세션은 기본적으로 이 규칙을 모른다.

1. 새 세션을 연다.
2. `control/session-prompts/open-node.md`를 열어 `<…>`를 채운 뒤 **첫 메시지로 붙여넣는다.**
   (PM 노드라면 `pm-briefing.md`)
3. 도구에 프로젝트 규칙 파일(`CLAUDE.md`, `AGENTS.md`, `.cursorrules` 등)이 있다면
   거기에 **라우팅 표**와 핵심 규칙 요약을 넣어두면 매번 붙여넣는 양이 줄어든다:

```markdown
## 이 워크스페이스 규칙
세션 1개 = 노드 1개. 파일 수정 전 `python3 control/node.py claim <노드> "<작업>" --as "<세션>"`.
락은 (레벨,노드ID) 오름차순으로만. 보고·위임은 인접 레벨만. 전문은 GUIDE.md.

| 첫 마디 | 노드 | charter |
|---|---|---|
| "PM" / "운영" | L4 | charters/L4-my-app.md |
| "백엔드" | L5.1 | charters/channels/01-backend.md |
| "채널 N이야" | L5.N | charters/channels/0N-*.md |
```

---

## 선택 1 — 텔레그램 알림

handoff/claim/release 때 알림을 받는다. **없어도 시스템은 완전히 돌아간다.**

```bash
cp control/notify.conf.example control/notify.conf
# bot_token / chat_id 를 채운다 (여러 명이면 chat_id 를 쉼표로 나열)
chmod 600 control/notify.conf
```

`tree.config.json`에서 `"notify": { "enabled": true }`로 바꾸면 켜진다.

- 봇 만들기: 텔레그램 `@BotFather` → `/newbot` → 토큰 발급.
- `chat_id`: 그 봇에게 메시지를 한 번 보낸 뒤
  `curl "https://api.telegram.org/bot<토큰>/getUpdates"` → `result[].message.chat.id`.
- **토큰은 `notify.conf`에만 둔다.** `tree.config.json`이나 코드에 절대 넣지 않는다.
  `.gitignore`에 이미 들어있다. 일시적으로 끄려면 `TREE_NOTIFY=0`.
- 실전 교훈: **알림 채널을 용도별로 분리하라.** 트리 운영 알림이 진짜 장애 알림과 같은
  방에 섞이면, 정작 급한 알림을 놓친다.

발송에 실패하거나 `notify.conf`가 없으면 한 줄 안내만 찍고 **그냥 넘어간다** —
알림 실패가 작업을 막지 않는다.

---

## 선택 2 — 스탠드업 (매일 "어디에 뭐가 밀렸나")

```bash
python3 control/automation/standup.py --print   # 출력만
python3 control/automation/standup.py           # + 알림 발송
```

모든 노드의 우편함 대기 항목 + charter의 `- [ ]` 미완료를 한 장으로 모은다.
매일 아침 자동 실행하려면 `control/automation/crontab.example`(Linux) 또는
launchd(macOS, 아래 plist를 스탠드업용으로 복사해 명령만 바꾸면 된다).

---

## 선택 3 — 헤드리스 디스패처 (사람 없이 백로그 1건 처리)

**먼저 `control/automation/README.md`의 경고를 읽어라.** 이건 위험도가 있는 기능이다.

1. 프롬프트를 자기 트리에 맞게 고친다:
   `control/automation/prompts/backlog-dispatcher.md`
   → **자동화 허용 노드 표**를 반드시 자기 것으로 교체. 기준은 "실패하면 진짜 돈·사용자·
   외부 커뮤니케이션에 즉시 영향이 가는가". 가면 자동화 금지(항상 수동).
2. 스크립트 상단의 경로/CLI 이름을 확인한다: `control/automation/backlog-dispatcher.sh`
3. 실행 권한을 준다 — **사람이 직접.**
   ```bash
   chmod +x control/automation/backlog-dispatcher.sh
   ```
4. 먼저 **손으로 한 번 돌려본다.** 로그(`control/logs/backlog-<날짜>.log`)를 읽고
   범위를 벗어난 행동이 없는지 확인한 뒤에만 스케줄러에 건다.
5. macOS: `control/automation/com.example.tree-dispatcher.plist`의 `<YOUR-USER>` /
   `<WORKSPACE>`를 절대경로로 치환(launchd는 `~`를 모른다) →
   ```bash
   cp control/automation/com.example.tree-dispatcher.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.example.tree-dispatcher.plist
   launchctl start com.example.tree-dispatcher      # 즉시 한 번 실행해 확인
   ```
   Linux/WSL: `control/automation/crontab.example` 참고(WatchPaths 같은 즉시 반응이
   필요하면 `inotifywait` 워처를 따로 띄운다).

### 반드시 지킬 것 (실전에서 얻은 규칙)

- **승인 게이트를 끄지 마라.** 애매한 행동은 승인 대기에 걸려 그 턴이 실패하는 게 맞다
  (fail-closed = 사람이 없을 때의 안전한 기본값은 "아무것도 안 함").
- **AI가 자기 권한을 스스로 넓히게 하지 마라.** 권한 설정 파일 작성, `chmod +x`,
  승인 우회 플래그는 **사람이 직접** 한다.
- **한 번에 한 항목만.** 예산 상한을 걸고, 사람이 검토 가능한 크기로 자른다.
- **이미 잡힌 락은 건드리지 않게 하라.** 사람이 그 세션에서 작업 중일 수 있다.
- **결과는 반드시 부모 노드 우편함으로 보고**하게 한다. 로그 파일만 남기면 아무도 안 본다.

---

## 선택 4 — 여러 사람이 같은 트리를 쓸 때

- `.gitignore`에서 `control/locks/`와 `control/inbox/`를 **빼면** 락과 우편함이 공유된다.
  대신 커밋 충돌이 잦아진다(둘 다 자주 바뀌는 파일이다).
- 더 현실적인 방식: charter/releases만 git으로 공유하고, 락·우편함은 공유 폴더(예:
  드라이브 동기화 디렉터리)에 두고 `lock_dir`/`inbox_dir`을 그 절대경로로 지정한다.
- 세션 이름에 사람 이름을 넣어라: `L5·backend·jun`. 락 상태판의 "누가"가 진짜로 누구인지
  알 수 있어야 한다.

---

## 자주 겪는 문제

| 증상 | 원인·해결 |
|---|---|
| `❌ 설정 파일 없음` | `control/tree.config.json`이 없거나 경로가 다르다. `--config` 또는 `TREE_CONFIG`. |
| `노드 'L5.3' 없음` | 자동 발견 디렉터리 경로가 틀렸거나, 파일명이 `NN-이름.md`가 아니다. `list`로 확인. |
| `list`에 `⚠️charter 없음` | 설정의 charter 경로에 파일이 없다. 만들거나 경로를 고쳐라. |
| 락이 안 풀린 채 세션이 죽음 | 6시간 뒤 `list`에 ⚠️. 사람이 확인 후 `--force`로 회수. 자동 해제는 일부러 안 한다. |
| 세션이 규칙을 안 지킨다 | 부팅 프롬프트를 안 붙였거나 `GUIDE.md`를 안 읽혔다. 5단계로 돌아가라. |
| 알림이 안 온다 | `notify.enabled`가 false, `notify.conf` 없음, 또는 `TREE_NOTIFY=0`. 출력에 이유가 찍힌다. |

## 환경변수 정리

| 변수 | 용도 |
|---|---|
| `TREE_CONFIG` | 설정 파일 경로 (기본: `control/tree.config.json`) |
| `TREE_SESSION` | 세션 이름 (`--as`를 매번 안 쓰고 싶을 때) |
| `TREE_NOTIFY=0` | 알림 일시 중단 |
