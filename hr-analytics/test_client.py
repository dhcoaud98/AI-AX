"""서버가 잘 동작하는지 확인하는 테스트 클라이언트: uv run test_client.py"""
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
            r = await s.read_resource("hr://schema"); print("\n[schema]\n" + r.contents[0].text)
            print("\n[인원]\n" + text(await call("headcount", {"group_by": "부서"})))
            print("\n[이직률 2025]\n" + text(await call("turnover_rate", {"year": 2025})))
            print("\n[근속]\n" + text(await call("tenure_stats")))
            print("\n[평가 분포 전체]\n" + text(await call("rating_distribution")))
            print("\n[평가 분포 인사 → 숨김 확인]\n" + text(await call("rating_distribution", {"dept": "인사"})))
            print("\n[연봉 개발]\n" + text(await call("salary_stats", {"dept": "개발"})))
            print("\n[연봉 영업 팀장 → 숨김 확인]\n" + text(await call("salary_stats", {"dept": "영업", "level": "팀장"})))
            print("\n[연차 8개월차]\n" + text(await call("annual_leave", {"hire_date": "2026-02-02"})))
            print("\n[연차 7년차]\n" + text(await call("annual_leave", {"hire_date": "2019-03-04"})))
            print("\n[없는 부서]\n" + text(await call("turnover_rate", {"year": 2025, "dept": "재무"})))
            print("\n[조회 기록]\n" + text(await call("access_log", {"count": 3})))
            p = await s.get_prompt("turnover_report", {"year": "2025"})
            print("\n[prompt]\n" + p.messages[0].content.text.splitlines()[0])


asyncio.run(main())
