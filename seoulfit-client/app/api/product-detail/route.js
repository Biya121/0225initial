// app/api/product-detail/route.js
// 무신사 상품 상세 페이지 크롤링 (이미지 여러 장 + 소재/핏 정보)
import puppeteer from 'puppeteer';

const sleep = ms => new Promise(r => setTimeout(r, ms));

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const goodsNo = searchParams.get('goodsNo');
  if (!goodsNo) return Response.json({ error: 'goodsNo 필요' }, { status: 400 });

  let browser;
  try {
    browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled'],
    });

    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
    await page.setExtraHTTPHeaders({ 'Accept-Language': 'ko-KR,ko;q=0.9' });
    await page.evaluateOnNewDocument(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    });

    await page.goto(`https://www.musinsa.com/products/${goodsNo}`, {
      waitUntil: 'networkidle2', timeout: 25000,
    });
    await sleep(4000);

    const detail = await page.evaluate(() => {
      // 상품 이미지 여러 장 (goods_img 포함된 것만)
      const extra_images = Array.from(
        document.querySelectorAll('img[src*="msscdn.net"]')
      )
        .map(img => img.src)
        .filter(src => src.includes('goods_img') || src.includes('goods_photos'))
        .filter((src, i, arr) => arr.indexOf(src) === i)
        .slice(0, 8);

      // 상품 정보 테이블 파싱
      const info = {};
      // 무신사 상세 정보는 dl/dt/dd 또는 table tr 구조
      document.querySelectorAll('dl').forEach(dl => {
        const dts = dl.querySelectorAll('dt');
        const dds = dl.querySelectorAll('dd');
        dts.forEach((dt, i) => {
          const key = dt.innerText?.trim();
          const val = dds[i]?.innerText?.trim();
          if (!key || !val) return;
          if (/소재|material|혼용률/i.test(key)) info.material = val;
          if (/핏|fit/i.test(key)) info.fit = val;
          if (/색상|color/i.test(key)) info.color = val;
          if (/사이즈|size/i.test(key)) info.size = val;
          if (/제조|made|원산지/i.test(key)) info.made = val;
          if (/시즌|season/i.test(key)) info.season = val;
          if (/스타일|style/i.test(key)) info.style = val;
        });
      });

      // table 방식도 시도
      document.querySelectorAll('table tr').forEach(tr => {
        const cells = tr.querySelectorAll('td, th');
        if (cells.length < 2) return;
        const key = cells[0]?.innerText?.trim();
        const val = cells[1]?.innerText?.trim();
        if (!key || !val) return;
        if (/소재|material|혼용률/i.test(key)) info.material = val;
        if (/핏|fit/i.test(key)) info.fit = val;
        if (/색상|color/i.test(key)) info.color = val;
        if (/사이즈|size/i.test(key)) info.size = val;
        if (/제조|made|원산지/i.test(key)) info.made = val;
      });

      // 상품명 재확인
      const nameEl = document.querySelector(
        'h1, h2, [class*="goods_name"], [class*="GoodsName"], [class*="product-name"]'
      );

      // 가격 재확인
      const priceEl = document.querySelector('span.text-body_13px_semi, [class*="dMbRNh"]');
      const priceText = priceEl?.textContent?.trim() ?? '';
      const price = parseInt(priceText.replace(/[^0-9]/g, ''), 10) || 0;

      return { extra_images, info, name: nameEl?.innerText?.trim(), price };
    });

    return Response.json({ success: true, goodsNo, ...detail });

  } catch (err) {
    console.error('[product-detail]', err.message);
    return Response.json({ success: false, error: err.message, extra_images: [], info: {} });
  } finally {
    if (browser) await browser.close();
  }
}