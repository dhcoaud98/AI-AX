"""
MCP 교육용 서버: AI에게 여섯 가지 능력 달아 주기

  1단계 ⏰ 시계      now, d_day          → 현재 시간 (AI는 지금이 언제인지 모름)
  2단계 🎲 주사위    roll_dice, pick_one → 진짜 무작위 (AI는 진짜 무작위를 못 만듦)
  3단계 📝 메모장    save_note, list_notes → 기억 (새 채팅을 열면 AI는 잊어버림)
  4단계 📊 성적표    students://all, subject_average, students_above → 내 파일 읽기
  5단계 🌤 날씨      weather             → 실시간 외부 정보
  6단계 📰 뉴스      latest_news         → 오늘 나온 새 소식 (AI는 최신 뉴스를 모름)

실행:      uv run server.py
테스트:    uv run mcp dev server.py
"""
import csv
import random
import sys
from datetime import date, datetime
from pathlib import Path

import json
import xml.etree.ElementTree as ET
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

# mcp 2.x는 MCPServer, 1.x는 FastMCP. 어느 버전이든 동작하도록 처리
try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer

mcp = MCPServer("mcp-class")

HERE = Path(__file__).parent          # Claude Desktop은 작업 폴더가 다르므로 항상 이 파일 기준 경로를 사용
NOTES_FILE = HERE / "notes.txt"
STUDENTS_FILE = HERE / "students.csv"


def log(msg: str) -> None:
    """stdout은 Claude와 대화하는 통로이므로, 로그는 반드시 stderr로."""
    print(msg, file=sys.stderr)


# ──────────────────────────────────────────────
# 1단계 ⏰ 시계: "AI한테 시계를 달아 준 거예요"
# ──────────────────────────────────────────────
@mcp.tool()
def now() -> str:
    """현재 날짜, 요일, 시간을 알려줍니다. 오늘 날짜나 지금 시간이 필요할 때 사용하세요."""
    weekdays = "월화수목금토일"
    t = datetime.now()
    return f"{t:%Y-%m-%d} ({weekdays[t.weekday()]}) {t:%H:%M}"


@mcp.tool()
def d_day(target: str) -> str:
    """목표 날짜(YYYY-MM-DD 형식)까지 며칠 남았는지 계산합니다."""
    days = (date.fromisoformat(target) - date.today()).days
    if days > 0:
        return f"D-{days} ({days}일 남음)"
    if days == 0:
        return "D-Day (오늘!)"
    return f"D+{-days} ({-days}일 지남)"


# ──────────────────────────────────────────────
# 2단계 🎲 주사위: "AI한테 진짜 주사위를 쥐여 준 거예요"
# ──────────────────────────────────────────────
@mcp.tool()
def roll_dice(sides: int = 6, count: int = 1) -> list[int]:
    """주사위를 굴립니다. sides: 면의 수(기본 6), count: 굴릴 개수(기본 1)."""
    return [random.randint(1, sides) for _ in range(count)]


@mcp.tool()
def pick_one(items: list[str]) -> str:
    """목록에서 하나를 무작위로 뽑습니다. 발표 순서, 점심 메뉴 정하기 등에 사용하세요."""
    return random.choice(items)


# ──────────────────────────────────────────────
# 3단계 📝 메모장: "AI한테 수첩을 준 거예요"
# ──────────────────────────────────────────────
@mcp.tool()
def save_note(text: str) -> str:
    """메모를 파일에 저장합니다. 새 채팅에서도 list_notes로 다시 볼 수 있습니다."""
    stamp = datetime.now().strftime("%m-%d %H:%M")
    with NOTES_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {text}\n")
    log(f"note saved: {text}")
    return f"저장했어요: {text}"


@mcp.tool()
def list_notes() -> str:
    """저장된 메모 전체를 보여줍니다."""
    if not NOTES_FILE.exists() or not NOTES_FILE.read_text(encoding="utf-8").strip():
        return "저장된 메모가 없어요."
    return NOTES_FILE.read_text(encoding="utf-8")


# ──────────────────────────────────────────────
# 4단계 📊 성적표: "AI한테 우리 반 서랍 열쇠를 준 거예요"
# ──────────────────────────────────────────────
def _load_students() -> list[dict]:
    with STUDENTS_FILE.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


@mcp.resource("students://all")
def all_students() -> str:
    """우리 반 성적표 원본(CSV). Resource는 Claude가 '읽는 자료'입니다."""
    return STUDENTS_FILE.read_text(encoding="utf-8")


@mcp.tool()
def subject_average(subject: str) -> str:
    """과목(국어/영어/수학)의 반 평균 점수를 계산합니다."""
    rows = _load_students()
    if subject not in rows[0]:
        return f"'{subject}' 과목은 없어요. 가능한 과목: 국어, 영어, 수학"
    scores = [int(r[subject]) for r in rows]
    return f"{subject} 평균: {sum(scores) / len(scores):.1f}점 ({len(scores)}명)"


@mcp.tool()
def students_above(subject: str, min_score: int) -> list[str]:
    """특정 과목에서 min_score점 이상인 학생 이름을 찾습니다."""
    return [r["이름"] for r in _load_students() if int(r[subject]) >= min_score]


# ──────────────────────────────────────────────
# 5단계 🌤 날씨: "AI한테 인터넷 창문을 열어 준 거예요"
#   Open-Meteo: 무료, API 키 필요 없음
# ──────────────────────────────────────────────
WEATHER_CODES = {
    0: "맑음", 1: "대체로 맑음", 2: "구름 조금", 3: "흐림", 45: "안개", 48: "안개",
    51: "약한 이슬비", 53: "이슬비", 55: "강한 이슬비", 61: "약한 비", 63: "비", 65: "강한 비",
    71: "약한 눈", 73: "눈", 75: "강한 눈", 80: "소나기", 81: "소나기", 82: "강한 소나기",
    95: "뇌우", 96: "우박 동반 뇌우", 99: "우박 동반 뇌우",
}


def format_weather(city: str, current: dict) -> str:
    sky = WEATHER_CODES.get(current["weather_code"], "알 수 없음")
    return (f"{city} 현재 날씨: {sky}, {current['temperature_2m']}°C, "
            f"강수량 {current['precipitation']}mm, 바람 {current['wind_speed_10m']}km/h")


def _get_json(url: str, params: dict) -> dict:
    with urlopen(f"{url}?{urlencode(params)}", timeout=10) as res:
        return json.load(res)


@mcp.tool()
def weather(city: str) -> str:
    """도시의 현재 날씨를 실시간으로 조회합니다. 예: 서울, 부산, Tokyo"""
    try:
        return _fetch_weather(city)
    except OSError as e:  # 인터넷 끊김, 타임아웃 등 → 에러 대신 이유를 알려주면 Claude가 상황을 설명할 수 있음
        log(f"weather error: {e}")
        return f"날씨 서버에 연결하지 못했어요 ({e}). 인터넷 연결을 확인해 주세요."


def _fetch_weather(city: str) -> str:
    geo = _get_json("https://geocoding-api.open-meteo.com/v1/search",
                    {"name": city, "count": 1, "language": "ko"})
    if not geo.get("results"):
        return f"'{city}' 도시를 찾지 못했어요."
    place = geo["results"][0]
    data = _get_json("https://api.open-meteo.com/v1/forecast", {
        "latitude": place["latitude"], "longitude": place["longitude"],
        "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
        "timezone": "auto",
    })
    return format_weather(place["name"], data["current"])


# ──────────────────────────────────────────────
# 6단계 📰 뉴스: "AI한테 신문을 쥐여 준 거예요"
#   RSS: 사이트의 '새 글 목록'만 깔끔하게 정리해 둔 파일. 무료, API 키 필요 없음
#   도구는 제목만 가져오고, 요약과 해석은 Claude가 합니다.
# ──────────────────────────────────────────────
NEWS_FEEDS = {
    "AI": "https://huggingface.co/blog/feed.xml",        # Hugging Face 블로그 (AI 모델·기술)
    "개발": "https://github.blog/changelog/feed/",        # GitHub 새 기능 소식
    "AX": "https://blogs.nvidia.com/feed/",               # NVIDIA 블로그 (기업 AI 도입)
}
ATOM = "{http://www.w3.org/2005/Atom}"


def _google_news_url(keyword: str) -> str:
    """등록 안 된 주제는 구글 뉴스 검색 RSS로 찾습니다. (예: 기업교육, 팀스파르타)"""
    return f"https://news.google.com/rss/search?q={quote(keyword)}&hl=ko&gl=KR&ceid=KR:ko"


def _read_feed(url: str, count: int) -> list[str]:
    # 일부 사이트는 프로그램 접속을 막기 때문에 브라우저처럼 이름표(User-Agent)를 붙여 요청
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (mcp-class)"})
    with urlopen(req, timeout=10) as res:
        root = ET.parse(res).getroot()

    lines = []
    for item in list(root.iter("item"))[:count]:            # RSS 형식
        lines.append(f"- {item.findtext('title', '').strip()} "
                     f"({item.findtext('pubDate', '').strip()[:16]})\n  {item.findtext('link', '').strip()}")
    for entry in list(root.iter(f"{ATOM}entry"))[:count - len(lines)]:   # Atom 형식
        link = entry.find(f"{ATOM}link")
        lines.append(f"- {entry.findtext(f'{ATOM}title', '').strip()} "
                     f"({entry.findtext(f'{ATOM}updated', '').strip()[:10]})\n  {link.get('href') if link is not None else ''}")
    return lines


@mcp.tool()
def latest_news(topic: str, count: int = 5) -> str:
    """관심 분야의 최신 글 제목, 날짜, 링크를 가져옵니다. 새 소식이나 업데이트, 최근 뉴스를 물으면 사용하세요.
    topic: AI, 개발, AX 중 하나. 그 밖의 단어(예: 기업교육, 팀스파르타)는 구글 뉴스에서 검색합니다.
    count: 가져올 글 개수(기본 5)."""
    url = NEWS_FEEDS.get(topic) or _google_news_url(topic)
    try:
        lines = _read_feed(url, count)
    except (OSError, ET.ParseError) as e:   # 인터넷 끊김, 사이트 차단, 잘못된 RSS → 이유를 문장으로
        log(f"news error: {e}")
        return f"'{topic}' 뉴스를 가져오지 못했어요 ({e}). 인터넷 연결이나 RSS 주소를 확인해 주세요."
    if not lines:
        return f"'{topic}' 관련 새 글을 찾지 못했어요."
    return f"[{topic}] 최신 글 {len(lines)}개\n" + "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
