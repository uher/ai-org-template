# control/session-prompts/ — 세션 부팅 프롬프트

새 AI 세션을 열 때 **첫 메시지로 통째로 붙여넣는** 프롬프트다. `<…>` 부분만 자기 노드에
맞게 채우면 된다.

| 파일 | 언제 |
|---|---|
| `open-node.md` | 아무 노드나 열거나 이어받을 때 (가장 자주 씀) |
| `pm-briefing.md` | PM 노드(보통 L4)를 열어 전체 상황 파악 → 우선순위 → 배분할 때 |

## 팁

- 노드마다 채워진 사본을 만들어 두면 매번 편집할 필요가 없다. 예:
  `control/session-prompts/filled/L5.1-backend.md`
  (`filled/`는 자기 트리 고유 내용이므로 템플릿에는 포함하지 않았다.)
- 도구에 "프로젝트 규칙 파일"(예: `CLAUDE.md`, `.cursorrules`, `AGENTS.md`)이 있다면,
  **첫 마디 → 어느 노드**의 라우팅 표를 거기에 적어두면 프롬프트가 훨씬 짧아진다:

  ```
  - "PM" / "운영"  → L4, charter: charters/L4-acme-app.md
  - "백엔드"       → L5.1, charter: charters/channels/01-backend.md
  - "채널 N이야"   → L5.N (자동 발견)
  ```
- 프롬프트가 길다고 줄이지 마라. 세션 기억은 사라지지만 이 텍스트는 매번 다시 붙는다 —
  일관성이 여기서 나온다.
