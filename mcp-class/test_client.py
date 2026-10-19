"""서버가 잘 동작하는지 확인하는 테스트 클라이언트: python test_client.py"""
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

def text(r):
    if r.structured_content is not None:
        return r.structured_content.get("result", r.structured_content)
    return " ".join(c.text for c in r.content)

async def main():
    params = StdioServerParameters(command="python", args=["server.py"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            print("도구 목록:", [t.name for t in (await s.list_tools()).tools])
            print("1 now      :", text(await s.call_tool("now", {})))
            print("1 d_day    :", text(await s.call_tool("d_day", {"target": "2026-11-19"})))
            print("2 dice     :", text(await s.call_tool("roll_dice", {"count": 3})))
            print("2 pick     :", text(await s.call_tool("pick_one", {"items": ["짜장면", "김밥", "라면"]})))
            print("3 save     :", text(await s.call_tool("save_note", {"text": "내일 우산 챙기기"})))
            print("3 list     :", text(await s.call_tool("list_notes", {})))
            r = await s.read_resource("students://all"); print("4 resource :", r.contents[0].text.splitlines()[0])
            print("4 average  :", text(await s.call_tool("subject_average", {"subject": "수학"})))
            print("4 above    :", text(await s.call_tool("students_above", {"subject": "영어", "min_score": 90})))
            print("5 weather  :", text(await s.call_tool("weather", {"city": "서울"})))
            print("6 news     :", text(await s.call_tool("latest_news", {"topic": "개발", "count": 3})))
            print("6 search   :", text(await s.call_tool("latest_news", {"topic": "기업교육", "count": 3})))

asyncio.run(main())
