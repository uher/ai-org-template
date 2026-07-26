# QUICKSTART — 10분 만에 굴려보기

이 문서 하나만 위에서 아래로 따라가면 된다. 개념 설명은 없다 —
**먼저 돌아가는 걸 보고**, 그 다음에 [`README.md`](README.md)(왜)와
[`SETUP.md`](SETUP.md)(제대로 붙이기)를 읽어라.

필요한 것: **Python 3.9+ 하나.** 설치도, `pip install`도, 계정도 없다.

---

## 1분 — 돌려보기

```bash
git clone https://github.com/uher/ai-org-template my-workspace
cd my-workspace
python3 control/node.py list
```

가상의 SaaS 회사("Acme App") 예시 트리가 그대로 뜬다. 이게 **상태판**이다 —
지금 어느 노드를 누가 쥐고 있는지 한 화면.

```
── 트리 노드 / 락 상태 ──
  L0      L0 workspace·조율       🟢 idle
  L1      L1 vision·비전          🟢 idle
  …
    L5.1  L5 backend             🟢 idle
```

---

## 3분 — 한 바퀴 돌려보기 (이게 시스템의 전부다)

세션 두 개가 협업하는 상황을 혼자서 흉내 내 본다.
`--as` 에 들어가는 이름이 **"지금 말하는 세션이 누구인가"** 다.

```bash
# ① 백엔드 채널 세션이 일을 시작한다고 선언 (파일 고치기 전에 필수)
python3 control/node.py --as "나·backend" claim L5.1 "멱등키 미들웨어"

python3 control/node.py list          # 🔒 로 바뀐 걸 확인

# ② 일이 끝났다. 위(PM)에게 보고를 남긴다 — 실시간 대화가 아니라 파일 우편함으로.
python3 control/node.py --as "나·backend" handoff L4 \
  "[보고/L5.1] 멱등키 미들웨어 완료. 중복 결제 재현 안 됨. 배포 시점은 PM 판단 필요."

# ③ 학습 자료로 남긴다 (변경 이력이 아니라, 6개월 뒤의 나를 위한 기록)
python3 control/node.py note L5.1 0.1.0 \
  --changed "멱등키 미들웨어 추가" \
  --why "결제 재시도에서 중복 청구 발생" \
  --problem "재시도 정책이 애플리케이션마다 제각각이었다" \
  --lesson "멱등성은 핸들러가 아니라 경계(미들웨어)에서 보장해야 한다"

# ④ 락을 푼다
python3 control/node.py --as "나·backend" release L5.1 "완료, PM 확인 대기"

# ⑤ PM 세션이 되어 우편함을 확인한다
python3 control/node.py inbox L4
python3 control/node.py inbox-done L4 1        # 처리했으면 체크
```

지금 본 게 전부다: **락**(안 밟기) · **우편함**(비동기 협업) · **릴리스 노트**(안 잊기).
나머지는 이 셋을 습관으로 만드는 규칙일 뿐이다.

> `git status` 를 쳐보면 방금 만든 락/우편함 파일이 보인다. 이것들은 **런타임 상태**라
> `.gitignore` 에 들어 있다. 저장소에 커밋되는 건 charter·log·releases 뿐이다.

---

## 5분 — 내 트리로 바꾸기

**핵심: 처음부터 6레벨을 만들지 마라.** 대부분은 이 둘로 충분하다.

```
L4  프로젝트 PM      ← 우선순위를 정하고 배분한다. 직접 구현하지 않는다.
 ├ L5.1 채널 A       ← 세션 하나가 여기만 판다
 └ L5.2 채널 B
```

위 레벨(L0~L3)은 **"이 판단은 여기서 할 게 아닌데"가 반복될 때** 만든다.
안 그러면 채울 내용 없는 charter만 늘고 신뢰가 준다.

`control/tree.config.json` 에서 `nodes` 를 자기 것으로 바꾼다:

```json
"nodes": [
  { "id": "L4", "level": 4, "name": "my-app·PM", "charter": "charters/L4-my-app.md" }
],
"auto_discover": [
  { "id_prefix": "L5.", "level": 5, "dir": "charters/channels", "glob": "*.md",
    "exclude_suffixes": [".log.md", "-releases.md"] }
]
```

charter를 만든다. `auto_discover` 덕분에 **채널은 파일을 만들면 노드가 생긴다.**

```bash
mkdir -p charters/channels
cp charters/charter-template.md charters/L4-my-app.md
cp charters/charter-template.md charters/channels/01-backend.md
python3 control/node.py list          # 내 트리가 뜨면 성공
```

---

## 마지막 1분 — AI 세션에 규칙 읽히기

새 AI 세션(Claude Code, Cursor, 무엇이든)을 열고
[`control/session-prompts/open-node.md`](control/session-prompts/open-node.md) 를
**첫 메시지로 통째로 붙여넣는다.** `<…>` 부분만 자기 값으로 채우면 된다.

그 프롬프트가 세션에게 시키는 것: 시작할 때 `list` → `inbox` → charter 읽기,
일하기 전에 `claim`, 끝낼 때 charter 갱신 → `note` → `release` → 부모에게 `handoff`.

여러 도구를 섞어 쓴다면 규칙 파일을 각 도구가 자동으로 읽는 위치에 심어두면 편하다
(Claude Code는 `CLAUDE.md`, Cursor는 `.cursorrules`). 내용은 이렇게 한 줄이면 된다:

```markdown
이 워크스페이스는 ai-org-template 규약을 따른다. 작업 전에 `GUIDE.md` 를 읽어라.
세션 1개 = 노드 1개. 파일을 고치기 전에 `node.py claim`, 끝나면 `release`.
```

---

## 첫 주는 이렇게 굴러간다

| 언제 | 무엇 |
|---|---|
| **월요일 아침** | PM 세션을 연다. `node.py list` + `inbox L4` → "이번 주 뭘 먼저" 판단 → 채널마다 `handoff` 로 배분. |
| **일하는 중** | 채널 세션을 하나씩 연다. 자기 우편함만 보고, 자기 노드만 고친다. 끝나면 charter 갱신 → `note` → `release` → PM에게 `handoff` 로 보고. |
| **막혔을 때** | 다른 노드 일이면 **직접 하지 않는다.** `handoff` 로 넘긴다. 이걸 어기는 순간 트리는 의미가 없다. |
| **금요일** | `*-releases.md` 를 훑는다. 이번 주에 뭘 배웠는지가 거기 있다. |

---

## 자주 하는 실수 세 가지

1. **PM이 직접 구현한다.** 가장 흔하고 가장 치명적이다. PM 세션이 코드를 고치기 시작하면
   컨텍스트가 다시 한 세션에 뭉치고, 트리는 폴더 이름으로 전락한다.
2. **릴리스 노트를 changelog처럼 쓴다.** "무엇을 바꿨다"만 적으면 6개월 뒤 아무 쓸모가 없다.
   `--problem`(직전에 뭐가 문제였나)과 `--lesson`(재사용 교훈)이 이 파일의 존재 이유다.
3. **charter를 append-only로 쓴다.** charter는 **고쳐 쓰는** 문서다(지금 상태).
   흐름은 `*.log.md` 가 맡는다. 둘을 섞으면 새 세션이 뭘 믿어야 할지 모른다.

---

## 다음에 읽을 것

- [`README.md`](README.md) — 왜 이렇게 만들었나, 나에게 맞는 도구인가, 한계는 무엇인가
- [`GUIDE.md`](GUIDE.md) — 규칙 전문. **AI 세션에 읽히는 문서**가 바로 이것이다
- [`SETUP.md`](SETUP.md) — 기존 프로젝트에 제대로 붙이기 + 텔레그램 알림 · 스탠드업 ·
  헤드리스 디스패처 같은 선택 기능
