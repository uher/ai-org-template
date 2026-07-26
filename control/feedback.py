"""이 템플릿 자체에 대한 버그 리포트 / 기능 요청을 개발자에게 보내는 창구.

동작 방식 — **개인정보를 지키는 쪽으로 일부러 이렇게 만들었다:**
  1) 이슈 제목과 본문을 받아 GitHub "새 이슈" 화면을 **미리 채운 URL**을 만든다.
  2) 사용자가 그 URL을 열어 내용을 눈으로 확인하고, **자기 GitHub 계정으로 직접** 제출한다.
  → 이 스크립트는 아무것도 자동 전송하지 않는다. 서버도, 숨은 토큰도 없다.
     무엇이 나가는지 사용자가 제출 직전에 100% 볼 수 있다.

AI 세션에게 (setup-wizard / 규칙 파일이 이 규약을 가리킨다):
  - 사용자가 이 템플릿의 버그·불편·기능 아이디어를 말하면 "개발자에게 보고할까요?" 라고
    제안하라. 동의 없이는 아무것도 하지 마라.
  - 본문 초안을 만들어 **먼저 사용자에게 전문을 보여주고**, 승인 후 이 스크립트로 URL을
    만들어라. 토큰 · 로컬 경로 · 이름/이메일 등 개인정보는 절대 본문에 넣지 마라.

  python3 control/feedback.py bug "제목" --body "무엇을 하다가 / 무슨 일이 / 기대한 것"
  python3 control/feedback.py idea "제목" --body "어떤 상황에서 무엇이 있었으면 하는지"
  python3 control/feedback.py bug "제목" --body-file draft.md --open
"""
from __future__ import annotations

import argparse
import sys
import urllib.parse

# 이 템플릿의 원본 저장소. 포크해서 자기 것으로 배포한다면 여기만 바꾸면 된다.
UPSTREAM = "uher/ai-org-template"

TEMPLATE = {
    "bug": ("bug", """## 무엇을 하다가
<!-- 예: setup-wizard 2단계에서 텔레그램 봇 테스트 중 -->
{body}

## 무슨 일이 일어났나 / 기대한 것

## 환경 (아는 것만)
- OS:
- Python:
- 템플릿 버전/커밋:

<!-- ⚠️ 토큰·개인정보·로컬 경로는 넣지 마세요. -->
"""),
    "idea": ("enhancement", """## 어떤 상황에서
{body}

## 무엇이 있었으면 하는지

## 지금은 어떻게 우회하고 있는지 (있다면)
"""),
}


def build_url(kind: str, title: str, body: str) -> str:
    label, tmpl = TEMPLATE[kind]
    full = tmpl.format(body=body.strip() or "<!-- 여기에 적어주세요 -->")
    q = urllib.parse.urlencode(
        {"title": title, "body": full, "labels": label}, quote_via=urllib.parse.quote)
    return f"https://github.com/{UPSTREAM}/issues/new?{q}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["bug", "idea"], help="bug=버그, idea=기능 요청")
    ap.add_argument("title", help="이슈 제목 (한 줄 요약)")
    ap.add_argument("--body", default="", help="본문")
    ap.add_argument("--body-file", default="", help="본문을 파일에서 읽기")
    ap.add_argument("--open", action="store_true", dest="open_browser",
                    help="브라우저로 바로 열기 (기본은 URL 출력만)")
    a = ap.parse_args()

    body = a.body
    if a.body_file:
        try:
            body = open(a.body_file, encoding="utf-8").read()
        except OSError as e:
            print(f"본문 파일을 읽을 수 없다: {e}")
            sys.exit(1)

    url = build_url(a.kind, a.title, body)
    if len(url) > 7000:
        print("⚠️ 본문이 너무 길어 URL이 잘릴 수 있다 — 핵심만 남기고 줄여라.")
    print("아래 링크를 열어 내용을 확인하고, 본인 GitHub 계정으로 제출하세요:")
    print()
    print(url)
    if a.open_browser:
        import webbrowser
        webbrowser.open(url)


if __name__ == "__main__":
    main()
