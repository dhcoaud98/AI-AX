"""
용어집 주간 체크: 아는 용어를 GitHub Issue 체크박스로 표시하면 "앎"으로 옮겨 줍니다.

  python glossary/weekly.py apply       열려 있는 '용어집' Issue에서 체크된 용어를 앎 처리 (매일 아침 브리핑 작업)
  python glossary/weekly.py new-issue   체크 반영 → 지난 Issue 닫기 → 이번 주 체크리스트 Issue 만들기 (매주 금요일)
  python glossary/weekly.py preview     만들어질 체크리스트 본문만 출력 (GitHub에 아무것도 안 함)

GitHub 작업은 gh CLI의 REST API(gh api)로 합니다.
체크는 한 방향입니다. 앎을 되돌리려면 terms.json에서 "앎": false로 고치세요.
"""
import json
import re
import subprocess
import sys

import build

REPO = "repos/dhcoaud98/AI-AX"
LABEL = "용어집"
CHECKED = re.compile(r"^\s*[-*]\s*\[[xX]\]\s*\*\*(.+?)\*\*", re.MULTILINE)


def gh(*args: str) -> object:
    out = subprocess.run(["gh", "api", *args], check=True, capture_output=True, text=True).stdout
    return json.loads(out) if out.strip() else None


def checklist_body(terms: dict, today) -> str:
    lines = [
        "이번 주까지 나온 용어 중 **이제 아는 것만 체크**해 주세요.",
        "다음 날 아침 브리핑 때 용어집의 '✅ 이제 아는 용어'로 옮겨지고, 다시 설명하지 않습니다.",
        "",
        "> 모르는 건 그냥 두면 됩니다. 이 Issue는 다음 주 금요일에 새 체크리스트로 바뀌며 자동으로 닫힙니다.",
        "",
    ]
    active = {k: v for k, v in terms.items() if build.status(v, today) == "공부"}
    for lv in reversed(build.LEVELS):
        group = sorted((k for k, v in active.items() if v["중요도"] == lv),
                       key=lambda k: (-len(active[k]["등장일"]), k))
        if not group:
            continue
        lines += [f"### {build.LEVEL_LABEL[lv]} ({len(group)})", ""]
        lines += [f"- [ ] **{k}** · {build.first_sentence(active[k]['뜻'])}" for k in group]
        lines.append("")
    if not active:
        lines.append("지금은 체크할 용어가 없습니다. 🎉")
    lines.append("[전체 용어집 보기](https://github.com/dhcoaud98/AI-AX/blob/master/glossary/README.md)")
    return "\n".join(lines) + "\n"


def checked_terms(body: str) -> list[str]:
    return [m.strip() for m in CHECKED.findall(body or "")]


def apply_bodies(bodies: list[str], today) -> list[list[str]]:
    """체크된 용어를 앎 처리하고, 본문마다 새로 앎이 된 용어 목록을 돌려줍니다."""
    terms = build.load_terms()
    names = {n.lower(): term for term, t in terms.items() for n in [term, *t["별칭"]]}
    per_body, newly, unknown = [], [], []
    for body in bodies:
        mine = []
        for name in checked_terms(body):
            term = names.get(name.lower())
            if term is None:
                unknown.append(name)
            elif not terms[term]["앎"]:
                terms[term]["앎"] = True
                newly.append(term)
                mine.append(term)
        per_body.append(mine)
    if unknown:
        print("주의: 용어집에 없는 이름이 체크되어 건너뜀:", ", ".join(sorted(set(unknown))))
    if newly:
        build.save_terms(terms)
        if build.main(["--today", today.isoformat()]) != 0:
            raise SystemExit(1)
    return per_body


def open_issues() -> list[dict]:
    issues = gh("-X", "GET", f"{REPO}/issues", "-f", f"labels={LABEL}", "-f", "state=open", "-f", "per_page=20")
    return [i for i in issues if "pull_request" not in i]


def cmd_apply(today) -> None:
    issues = open_issues()
    per_issue = apply_bodies([i["body"] or "" for i in issues], today)
    if not any(per_issue):
        print("새로 체크된 용어 없음")
        return
    for issue, mine in zip(issues, per_issue):
        if mine:
            print(f"✅ 앎 처리 (#{issue['number']}):", ", ".join(mine))
            gh(f"{REPO}/issues/{issue['number']}/comments", "-f",
               f"body=✅ 용어집에 반영했어요: {', '.join(mine)}")


def cmd_new_issue(today) -> None:
    cmd_apply(today)
    for i in open_issues():
        gh("-X", "PATCH", f"{REPO}/issues/{i['number']}", "-f", "state=closed", "-f", "state_reason=completed")
        print(f"지난 체크리스트 닫음: #{i['number']}")
    try:
        gh(f"{REPO}/labels", "-f", f"name={LABEL}", "-f", "color=0E8A16",
           "-f", "description=용어집 주간 체크리스트")
    except subprocess.CalledProcessError:
        pass  # 이미 있는 라벨
    terms = build.load_terms()
    issue = gh(f"{REPO}/issues", "-f", f"title=📖 용어집 주간 체크 | {today.isoformat()}",
               "-f", f"body={checklist_body(terms, today)}", "-f", f"labels[]={LABEL}")
    print(f"새 체크리스트: {issue['html_url']}")


def main(argv: list[str]) -> int:
    today = build.parse_today(argv)
    cmd = argv[0] if argv else ""
    if cmd == "apply":
        cmd_apply(today)
    elif cmd == "new-issue":
        cmd_new_issue(today)
    elif cmd == "preview":
        print(checklist_body(build.load_terms(), today))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
