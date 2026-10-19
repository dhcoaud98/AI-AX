"""
용어집 정리 스크립트: python glossary/build.py [--today YYYY-MM-DD]

하는 일
  1. terms.json 형식 검사 (필수 항목, 중요도 값, 날짜, 별칭 중복)
  2. 등장 횟수로 중요도 다시 계산: 3일 나올 때마다 한 단계 올림 (몰라도 → 대충 → 꼭)
  3. terms.json을 같은 모양으로 다시 저장
  4. glossary/README.md (전체 목록) 새로 만들기
     - ⚪ 몰라도 됨 용어가 30일 넘게 다시 안 나오면 '💤 한동안 안 나온 용어'로 접어 둠
       (다시 나오면 자동으로 목록에 돌아옴. terms.json은 바뀌지 않음)
  5. 이번 실행에서 중요도가 오른 용어를 "⬆️ 승격: ..."으로 출력

--today는 시험용입니다. 생략하면 한국 시간 오늘 날짜를 씁니다.
문제가 있으면 무엇이 틀렸는지 출력하고 종료 코드 1로 끝납니다.
"""
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
TERMS_FILE = HERE / "terms.json"
README_FILE = HERE / "README.md"

LEVELS = ["몰라도", "대충", "꼭"]
LEVEL_LABEL = {"꼭": "🔴 꼭 알기", "대충": "🟡 대충 알기", "몰라도": "⚪ 몰라도 됨"}
PROMOTE_EVERY = 3
DORMANT_DAYS = 30
FIELDS = ["영문", "별칭", "분야", "뜻", "왜중요", "처음중요도", "중요도", "등장일", "앎"]
KST = timezone(timedelta(hours=9))


def today_kst() -> date:
    return datetime.now(KST).date()


def parse_today(argv: list[str]) -> date:
    if "--today" in argv:
        return date.fromisoformat(argv[argv.index("--today") + 1])
    return today_kst()


def daily_path(day: str) -> str:
    y, m, _ = day.split("-")
    return f"daily/{y}/{m}/{day}.md"


def status(t: dict, today: date) -> str:
    """'앎'(다 익힘) / '잠듦'(⚪인데 30일 넘게 안 나옴) / '공부'(지금 목록에 보일 용어)"""
    if t["앎"]:
        return "앎"
    if t["중요도"] == "몰라도" and (today - date.fromisoformat(t["등장일"][-1])).days > DORMANT_DAYS:
        return "잠듦"
    return "공부"


def load_terms() -> dict:
    return json.loads(TERMS_FILE.read_text(encoding="utf-8"))


def save_terms(terms: dict) -> None:
    TERMS_FILE.write_text(json.dumps(terms, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check(terms: dict) -> list[str]:
    errors = []
    seen_names: dict[str, str] = {}
    for term, t in terms.items():
        missing = [f for f in FIELDS if f not in t]
        if missing:
            errors.append(f"'{term}': 빠진 항목 {missing}")
            continue
        if t["처음중요도"] not in LEVELS:
            errors.append(f"'{term}': 처음중요도는 {LEVELS} 중 하나여야 함 (지금: {t['처음중요도']})")
        if not isinstance(t["앎"], bool):
            errors.append(f"'{term}': 앎은 true 또는 false여야 함 (지금: {t['앎']!r})")
        if not t["등장일"]:
            errors.append(f"'{term}': 등장일이 비어 있음")
        for d in t["등장일"]:
            try:
                date.fromisoformat(d)
            except ValueError:
                errors.append(f"'{term}': 날짜 형식 오류 {d!r} (YYYY-MM-DD)")
        for name in [term, *t["별칭"]]:
            key = name.lower()
            if key in seen_names and seen_names[key] != term:
                errors.append(f"'{name}'이(가) '{seen_names[key]}'와 '{term}'에 중복으로 들어 있음")
            seen_names[key] = term
    return errors


def normalize(terms: dict) -> dict:
    out = {}
    for term in sorted(terms):
        t = terms[term]
        t["등장일"] = sorted(set(t["등장일"]))
        base = LEVELS.index(t["처음중요도"])
        t["중요도"] = LEVELS[min(base + len(t["등장일"]) // PROMOTE_EVERY, len(LEVELS) - 1)]
        out[term] = {f: t[f] for f in FIELDS} | {k: v for k, v in t.items() if k not in FIELDS}
    return out


def first_sentence(text: str) -> str:
    return text.split(". ")[0].rstrip(".") + "."


def render_readme(terms: dict, today: date) -> str:
    by_status = {s: {k: v for k, v in terms.items() if status(v, today) == s} for s in ("공부", "잠듦", "앎")}
    active, dormant, known = by_status["공부"], by_status["잠듦"], by_status["앎"]
    counts = {lv: sum(1 for t in active.values() if t["중요도"] == lv) for lv in LEVELS}
    days = sorted({d for t in terms.values() for d in t["등장일"]})

    lines = [
        "# 📖 AX·AI·기업교육 용어집",
        "",
        "매일 브리핑에 나온 용어 중 **처음 보는 분야 용어만** 골라 쌓는 나만의 용어집입니다.",
        "단어 공부로 산으로 가지 않도록, 모든 용어에 **꼭 알기 / 대충 알기 / 몰라도 됨** 판정을 붙였습니다.",
        "",
        f"- 전체 {len(terms)}개 · 공부할 용어 {len(active)}개 "
        f"(🔴 {counts['꼭']} · 🟡 {counts['대충']} · ⚪ {counts['몰라도']}) · "
        f"한동안 안 나온 용어 {len(dormant)}개 · 이제 아는 용어 {len(known)}개",
        f"- 기록 기간: {days[0]} ~ {days[-1]} ({len(days)}일)" if days else "- 기록 기간: 없음",
        "",
        "## 읽는 법",
        "",
        "| 판정 | 의미 |",
        "|---|---|",
        "| 🔴 꼭 알기 | 내 업무와 바로 연결됩니다. 뜻과 '왜 중요한지'까지 읽어 두세요. |",
        "| 🟡 대충 알기 | 한 줄 뜻만 알면 기사를 읽는 데 지장 없습니다. |",
        "| ⚪ 몰라도 됨 | 넘어가도 됩니다. 걸리면 그때 한 줄만 보세요. |",
        "",
        f"- 같은 용어가 **{PROMOTE_EVERY}일 나올 때마다 한 단계씩 자동으로 올라갑니다.** 자주 나오면 알아 둘 때가 된 것입니다.",
        f"- ⚪ 용어가 **{DORMANT_DAYS}일 넘게 다시 안 나오면 아래로 자동으로 접힙니다.** 다시 나오면 목록에 돌아옵니다.",
        "- 다 익힌 용어는 매주 금요일 올라오는 **[용어집 주간 체크](https://github.com/dhcoaud98/AI-AX/issues?q=label%3A%EC%9A%A9%EC%96%B4%EC%A7%91)** Issue에서 체크하면, "
        "다음 날 아침 '이제 아는 용어'로 옮겨집니다.",
        "",
        "- 매일 새로 나온 용어: [`daily/`](daily/) (날짜별 파일)",
        "- 원본 데이터: [`terms.json`](terms.json) (브라우저 확장이나 MCP 도구가 읽는 파일)",
        "",
    ]
    for lv in reversed(LEVELS):
        group = {k: v for k, v in active.items() if v["중요도"] == lv}
        if not group:
            continue
        lines += [f"## {LEVEL_LABEL[lv]} ({len(group)})", "", "| 용어 | 한 줄 뜻 | 등장 | 처음 본 날 |", "|---|---|---|---|"]
        ordered = sorted(group.items(), key=lambda kv: (-len(kv[1]["등장일"]), kv[1]["등장일"][0], kv[0]))
        for term, t in ordered:
            eng = f" <sub>{t['영문']}</sub>" if t["영문"] and t["영문"] != term else ""
            first = t["등장일"][0]
            lines.append(f"| **{term}**{eng} | {first_sentence(t['뜻'])} | {len(t['등장일'])}일 "
                         f"| [{first}]({daily_path(first)}) |")
        lines.append("")
    if dormant:
        lines += ["<details>", f"<summary>💤 한동안 안 나온 용어 ({len(dormant)})</summary>", ""]
        lines += [f"- **{term}**: {first_sentence(t['뜻'])} (마지막 등장 {t['등장일'][-1]})"
                  for term, t in dormant.items()]
        lines += ["", "</details>", ""]
    if known:
        lines += ["<details>", f"<summary>✅ 이제 아는 용어 ({len(known)})</summary>", ""]
        lines += [f"- **{term}**: {first_sentence(t['뜻'])}" for term, t in known.items()]
        lines += ["", "</details>", ""]
    lines += ["> 이 파일은 `python glossary/build.py`가 `terms.json`으로 자동 생성합니다. 직접 고치지 마세요."]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    today = parse_today(argv)
    terms = load_terms()
    errors = check(terms)
    if errors:
        print("용어집 오류:", *errors, sep="\n- ")
        return 1
    before = {term: t.get("중요도") for term, t in terms.items()}
    terms = normalize(terms)
    for term, t in terms.items():
        if before[term] in LEVELS and LEVELS.index(t["중요도"]) > LEVELS.index(before[term]):
            print(f"⬆️ 승격: {term} ({before[term]} → {t['중요도']}, {len(t['등장일'])}일 등장)")
    for term, t in terms.items():
        if not (HERE / daily_path(t["등장일"][0])).exists():
            print(f"주의: '{term}'의 처음 본 날 일별 파일이 없습니다 → glossary/{daily_path(t['등장일'][0])}")
    save_terms(terms)
    README_FILE.write_text(render_readme(terms, today), encoding="utf-8")
    print(f"완료: 용어 {len(terms)}개, README 갱신")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
