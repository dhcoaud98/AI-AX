"""
HR 피플 애널리틱스 MCP 서버: "AI한테 인사 데이터를 '안전하게' 보여 주기"

  도구는 숫자를 계산하고, AI는 해석한다.  단, 개인은 절대 드러내지 않는다.

  📈 분석    headcount, turnover_rate, tenure_stats, rating_distribution, salary_stats
  🗓 노무    annual_leave       → 근로기준법 기준 연차 계산
  🔒 보호    hr://schema        → 원본 대신 '어떤 칸이 민감한지' 설명서만 공개
             access_log         → 누가 언제 어떤 데이터를 봤는지 기록 확인
  📝 양식    turnover_report    → 이직 분석 보고서용 질문 양식 (Prompt)

개인정보 보호 원칙 (이 서버가 코드로 지키는 것)
  1. 원본 데이터는 AI에게 통째로 넘기지 않는다          → Resource는 스키마만
  2. 개인 단위 결과는 돌려주지 않는다                    → 모든 도구는 집계만
  3. 인원이 적은 집단은 숨긴다 (MIN_GROUP명 미만)        → 2명뿐인 부서 평균 연봉 = 사실상 개인 연봉
  4. 이름·연락처·생년월일은 어떤 도구도 읽지 않는다
  5. 모든 조회를 기록한다                                → access_log.txt

실행:      uv run server.py
테스트:    uv run test_client.py
"""
import csv
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from statistics import mean, median

# mcp 2.x는 MCPServer, 1.x는 FastMCP. 어느 버전이든 동작하도록 처리
try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer

mcp = MCPServer("hr-analytics")

HERE = Path(__file__).parent
EMPLOYEES_FILE = HERE / "employees.csv"
ACCESS_LOG = HERE / "access_log.txt"

MIN_GROUP = 3            # 이 인원 미만인 집단의 평가·연봉 통계는 숨김
GROUP_KEYS = ("부서", "직급")
RATINGS = ("S", "A", "B", "C")


def log(msg: str) -> None:
    """stdout은 Claude와 대화하는 통로이므로, 로그는 반드시 stderr로."""
    print(msg, file=sys.stderr)


def audit(tool: str, **args) -> None:
    """모든 조회를 파일에 남깁니다. 인사 데이터는 '누가 봤는지'가 남아야 합니다."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    detail = ", ".join(f"{k}={v}" for k, v in args.items()) or "-"
    with ACCESS_LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {tool}({detail})\n")


# ──────────────────────────────────────────────
# 데이터 읽기 (내부용: 도구가 아니므로 Claude는 직접 부를 수 없음)
# ──────────────────────────────────────────────
def _load() -> list[dict]:
    with EMPLOYEES_FILE.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _day(text: str) -> date | None:
    return date.fromisoformat(text) if text else None


def _active_on(row: dict, day: date) -> bool:
    """그날 재직 중이었는지. 퇴사일은 마지막 근무일로 봅니다."""
    left = _day(row["퇴사일"])
    return _day(row["입사일"]) <= day and (left is None or left >= day)


def _in_dept(rows: list[dict], dept: str) -> list[dict]:
    if dept in ("", "전체"):
        return rows
    picked = [r for r in rows if r["부서"] == dept]
    if not picked:
        names = sorted({r["부서"] for r in rows})
        raise ValueError(f"'{dept}' 부서는 없어요. 가능한 부서: 전체, {', '.join(names)}")
    return picked


def _years(start: date, end: date) -> int:
    return end.year - start.year - ((end.month, end.day) < (start.month, start.day))


def _months(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month - (end.day < start.day)


def _too_small(n: int) -> str:
    return (f"대상이 {n}명이라 결과를 숨겼어요. {MIN_GROUP}명 미만 집단의 통계는 "
            f"특정 개인의 정보를 사실상 드러내기 때문입니다. 더 큰 범위(예: 전체)로 조회해 주세요.")


# ──────────────────────────────────────────────
# 🔒 Resource: 원본 대신 '설명서'만 공개
# ──────────────────────────────────────────────
@mcp.resource("hr://schema")
def schema() -> str:
    """인사 데이터의 칸 구성과 민감도. 원본 데이터는 공개하지 않습니다."""
    return f"""인사 데이터 칸 구성 (원본은 공개하지 않음, 도구로 집계만 가능)

| 칸 | 민감도 | AI 접근 |
|---|---|---|
| 사번 | 식별자 | 사용 안 함 |
| 이름 | 개인식별정보 | 사용 안 함 |
| 연락처 | 개인식별정보 | 사용 안 함 |
| 부서, 직급 | 일반 | 집계 기준으로 사용 |
| 입사일, 퇴사일 | 일반 | 인원·이직률·근속 계산 |
| 평가등급 | 민감 | {MIN_GROUP}명 이상 집단의 분포만 |
| 연봉 | 민감 | {MIN_GROUP}명 이상 집단의 평균·중앙값만 (100만원 단위 반올림) |

모든 조회는 access_log.txt에 기록됩니다."""


# ──────────────────────────────────────────────
# 📈 분석 도구: 전부 '집계'만 돌려줌
# ──────────────────────────────────────────────
@mcp.tool()
def headcount(group_by: str = "부서", on_date: str = "") -> str:
    """특정 날짜(YYYY-MM-DD, 비우면 오늘)의 재직 인원을 부서별 또는 직급별로 셉니다.
    group_by: 부서 또는 직급."""
    audit("headcount", group_by=group_by, on_date=on_date or "오늘")
    if group_by not in GROUP_KEYS:
        return f"group_by는 {', '.join(GROUP_KEYS)} 중 하나만 가능해요."
    day = _day(on_date) or date.today()
    active = [r for r in _load() if _active_on(r, day)]
    counts = Counter(r[group_by] for r in active)
    lines = [f"- {k}: {v}명" for k, v in counts.most_common()]
    return f"{day} 기준 재직 {len(active)}명 ({group_by}별)\n" + "\n".join(lines)


@mcp.tool()
def turnover_rate(year: int, dept: str = "전체") -> str:
    """연간 이직률을 계산합니다. 이직률 = 그해 퇴사자 수 ÷ 평균 인원((연초 인원 + 연말 인원) ÷ 2).
    dept가 '전체'면 부서별로 나눠서 보여 줍니다. 입사 1년 안에 나간 '조기 퇴사'도 함께 셉니다."""
    audit("turnover_rate", year=year, dept=dept)
    try:
        rows = _in_dept(_load(), dept)
    except ValueError as e:
        return str(e)

    start, end = date(year, 1, 1), date(year, 12, 31)

    def calc(group: list[dict]) -> str:
        begin = sum(_active_on(r, start) for r in group)
        finish = sum(_active_on(r, end) for r in group)
        leavers = [r for r in group if r["퇴사일"] and _day(r["퇴사일"]).year == year]
        early = sum(_months(_day(r["입사일"]), _day(r["퇴사일"])) < 12 for r in leavers)
        avg = (begin + finish) / 2
        rate = f"{len(leavers) / avg * 100:.1f}%" if avg else "계산 불가"
        return (f"이직률 {rate} (퇴사 {len(leavers)}명 / 평균 {avg:g}명, "
                f"연초 {begin} → 연말 {finish}), 조기 퇴사 {early}명")

    if dept not in ("", "전체"):
        return f"{year}년 {dept}: {calc(rows)}"
    depts = sorted({r["부서"] for r in rows})
    lines = [f"- 전체: {calc(rows)}"] + [f"- {d}: {calc([r for r in rows if r['부서'] == d])}" for d in depts]
    return f"{year}년 이직률\n" + "\n".join(lines)


@mcp.tool()
def tenure_stats(dept: str = "전체") -> str:
    """현재 재직자의 근속연수(평균, 중앙값)와 근속 구간별 인원을 계산합니다."""
    audit("tenure_stats", dept=dept)
    try:
        rows = _in_dept(_load(), dept)
    except ValueError as e:
        return str(e)
    today = date.today()
    years = [(today - _day(r["입사일"])).days / 365.25 for r in rows if _active_on(r, today)]
    if not years:
        return f"{dept} 재직자가 없어요."
    bands = Counter("1년 미만" if y < 1 else "1~3년" if y < 3 else "3~5년" if y < 5 else "5년 이상" for y in years)
    order = ["1년 미만", "1~3년", "3~5년", "5년 이상"]
    return (f"{dept} 재직자 {len(years)}명 근속: 평균 {mean(years):.1f}년, 중앙값 {median(years):.1f}년\n"
            + "\n".join(f"- {b}: {bands.get(b, 0)}명" for b in order))


@mcp.tool()
def rating_distribution(dept: str = "전체") -> str:
    """현재 재직자의 평가등급(S/A/B/C) 분포를 보여 줍니다. 아직 평가받지 않은 신규 입사자는 제외합니다.
    인원이 적은 집단은 개인 식별 위험 때문에 결과를 숨깁니다."""
    audit("rating_distribution", dept=dept)
    try:
        rows = _in_dept(_load(), dept)
    except ValueError as e:
        return str(e)
    rated = [r["평가등급"] for r in rows if _active_on(r, date.today()) and r["평가등급"]]
    if len(rated) < MIN_GROUP:
        return _too_small(len(rated))
    counts = Counter(rated)
    return f"{dept} 평가 분포 ({len(rated)}명)\n" + "\n".join(
        f"- {g}: {counts.get(g, 0)}명 ({counts.get(g, 0) / len(rated) * 100:.0f}%)" for g in RATINGS)


@mcp.tool()
def salary_stats(dept: str = "전체", level: str = "전체") -> str:
    """현재 재직자 연봉의 평균과 중앙값(100만원 단위 반올림)을 보여 줍니다. 부서·직급으로 좁힐 수 있습니다.
    개인 연봉, 최고·최저 연봉은 제공하지 않으며, 인원이 적은 집단은 결과를 숨깁니다."""
    audit("salary_stats", dept=dept, level=level)
    try:
        rows = _in_dept(_load(), dept)
    except ValueError as e:
        return str(e)
    if level not in ("", "전체"):
        rows = [r for r in rows if r["직급"] == level]
    pay = [int(r["연봉"]) for r in rows if _active_on(r, date.today())]
    if len(pay) < MIN_GROUP:
        return _too_small(len(pay))

    def won(v: float) -> str:
        return f"약 {round(v, -2):,.0f}만원"

    return f"{dept}·{level} 재직자 {len(pay)}명 연봉: 평균 {won(mean(pay))}, 중앙값 {won(median(pay))}"


# ──────────────────────────────────────────────
# 🗓 노무: 연차 계산 (개인 데이터를 읽지 않는 순수 계산기)
# ──────────────────────────────────────────────
@mcp.tool()
def annual_leave(hire_date: str, on_date: str = "") -> str:
    """입사일(YYYY-MM-DD) 기준으로 특정 날짜(비우면 오늘)에 발생하는 연차 일수를 근로기준법 제60조에 따라 계산합니다.
    1년 미만: 1개월 개근 시 1일씩(최대 11일). 1년 이상: 15일, 3년차부터 2년마다 1일 가산(최대 25일)."""
    audit("annual_leave", hire_date=hire_date, on_date=on_date or "오늘")
    try:
        hire = date.fromisoformat(hire_date)
        day = date.fromisoformat(on_date) if on_date else date.today()
    except ValueError:
        return "날짜는 YYYY-MM-DD 형식으로 알려 주세요. 예: 2023-03-02"
    if day < hire:
        return "기준일이 입사일보다 빨라요."

    years = _years(hire, day)
    if years < 1:
        days = min(_months(hire, day), 11)
        basis = f"근속 1년 미만 (만 {_months(hire, day)}개월)"
    else:
        days = min(15 + (years - 1) // 2, 25)
        basis = f"근속 만 {years}년"
    return (f"{basis} → 연차 {days}일\n"
            "※ 출근율 80% 이상, 상시 5인 이상 사업장 가정. 실제 적용은 취업규칙과 노무 담당자 확인이 필요합니다.")


# ──────────────────────────────────────────────
# 🔒 투명성: 조회 기록 보기
# ──────────────────────────────────────────────
@mcp.tool()
def access_log(count: int = 10) -> str:
    """이 서버로 인사 데이터를 조회한 최근 기록을 보여 줍니다."""
    if not ACCESS_LOG.exists():
        return "아직 조회 기록이 없어요."
    lines = ACCESS_LOG.read_text(encoding="utf-8").strip().splitlines()
    return f"최근 조회 기록 {min(count, len(lines))}건 (전체 {len(lines)}건)\n" + "\n".join(lines[-count:])


# ──────────────────────────────────────────────
# 📝 Prompt: 미리 만든 질문 양식
# ──────────────────────────────────────────────
@mcp.prompt()
def turnover_report(year: str) -> str:
    """이직 분석 보고서 작성 양식."""
    return f"""{year}년 이직 현황을 분석해 경영진 보고용 요약을 만들어 주세요.

1. turnover_rate로 {year}년 전체와 부서별 이직률을 확인하세요.
2. tenure_stats로 부서별 근속 구조를 확인하세요.
3. 이직률이 가장 높은 부서의 특징을 숫자로 설명하고, 가능한 원인 가설 2가지와
   확인을 위해 필요한 추가 데이터(퇴사 면담, 채용 경로 등)를 제안하세요.
4. 개인을 특정할 수 있는 표현은 쓰지 마세요."""


if __name__ == "__main__":
    mcp.run()
