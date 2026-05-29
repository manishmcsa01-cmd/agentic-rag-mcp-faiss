import asyncio, sys
sys.stdout.reconfigure(encoding='utf-8')

async def test():
    from crawl4ai import AsyncWebCrawler
    async with AsyncWebCrawler(verbose=False) as crawler:
        r = await crawler.arun(url='https://example.com')
        md = r.markdown
        text = str(getattr(md, 'raw_markdown', None) or getattr(md, 'fit_markdown', None) or md or '')
        status = getattr(r, 'status_code', 200)
        print(f'[OK] fetch_url via Playwright / crawl4ai')
        print(f'     status  : {status}')
        print(f'     chars   : {len(text)}')
        print(f'     preview : {text[:150].strip()}')

asyncio.run(test())
