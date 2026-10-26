"""서버가 잘 동작하는지 확인하는 테스트 클라이언트: uv run test_client.py
(뉴스 도구는 인터넷이 필요합니다. 연결이 안 되면 에러 대신 이유 문장이 나오면 정상)"""
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def text(r):
    if r.structured_content is not None:
        return r.structured_content.get("result", r.structured_content)
    return " ".join(c.text for c in r.content)


async def main():
    params = StdioServerParameters(command=sys.executable, args=["server.py"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            call = lambda name, args={}: s.call_tool(name, args)
            print("도구 목록:", [t.name for t in (await s.list_tools()).tools])
            print("\n[노무]\n" + text(await call("hr_news", {"topic": "노무", "count": 3})))
            print("\n[자유 검색: 주4일제]\n" + text(await call("hr_news", {"topic": "주4일제", "count": 2})))
            print("\n[브리핑]\n" + text(await call("hr_briefing", {"count": 2, "days": 3})))
            print("\n[저장]\n" + text(await call("save_reading", {
                "title": "테스트 기사", "link": "https://example.com",
                "memo": "우리 회사 취업규칙에도 반영할 부분이 있는지 확인", "topic": "노무"})))
            print("\n[기록 보기]\n" + text(await call("list_readings")))
            p = await s.get_prompt("daily_hr_reading", {})
            print("\n[prompt]\n" + p.messages[0].content.text.splitlines()[0])


asyncio.run(main())
