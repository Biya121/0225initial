// app/api/crawl/route.js
import puppeteer from 'puppeteer';
import { writeFile, readFile, mkdir } from 'fs/promises';
import path from 'path';

const CACHE_PATH = path.join(process.cwd(), 'data', 'musinsa-cache.json');
const DELAY_MS = 3500;
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function crawlBrand(brandData) {
  let browser;
  const products = [];

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

    const url = `${brandData.musinsa_url}?sortCode=POPULAR`;
    console.log(`[puppeteer] 접속: ${url}`);
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    await sleep(5000);

    const items = await page.evaluate((brandName) => {
      const results = [];

      // 상품명 a 태그 (텍스트 있는 것만)
      const nameLinks = Array.from(document.querySelectorAll('a'))
        .filter(a => /\/products\/\d+/.test(a.href) && a.innerText?.trim().length > 2);

      nameLinks.slice(0, 12).forEach(link => {
        const name = link.innerText?.trim();
        if (!name) return;

        const goodsNo = link.href.match(/\/products\/(\d+)/)?.[1];

        // 카드 컨테이너 탐색 (최대 8단계 위로)
        let card = link.parentElement;
        let img = null;
        let price = 0;

        for (let i = 0; i < 8; i++) {
          if (!card) break;

          // 이미지: msscdn.net + goods_img 포함
          if (!img) {
            const imgEl = card.querySelector('img[src*="msscdn.net"]');
            if (imgEl?.src?.includes('goods_img')) img = imgEl.src;
          }

          // 가격: 4자리 이상 숫자 (최소 1,000원)
          if (!price) {
            const priceEl = card.querySelector('span.text-body_13px_semi, [class*="dMbRNh"]');
            if (priceEl) {
              const raw = priceEl.textContent.replace(/[^0-9]/g, '');
              if (raw.length >= 4) price = parseInt(raw, 10);
            }
          }

          if (img && price) break;
          card = card.parentElement;
        }

        // 이미지 없으면 상품번호로 CDN URL 직접 구성 (debug-crawl 방식)
        if (!img && goodsNo) {
          const prefix = goodsNo.slice(0, 4);
          img = `https://image.msscdn.net/images/goods_img/${prefix}/${goodsNo}/${goodsNo}_1_500.jpg`;
        }

        results.push({
          id: `musinsa_${goodsNo ?? Date.now()}`,
          name,
          brand: brandName,
          price_krw: price,
          image_url: img ?? null,
          product_url: link.href,
          goods_no: goodsNo ?? null,
        });
      });

      return results;
    }, brandData.name_ko);

    products.push(...items);
    console.log(`[puppeteer] ${brandData.name_ko}: ${products.length}개 수집, 이미지: ${items.filter(i => i.image_url).length}개`);

  } catch (err) {
    console.error(`[puppeteer] 실패 (${brandData.name_ko}):`, err.message);
  } finally {
    if (browser) await browser.close();
  }

  return products;
}

export async function POST(request) {
  try {
    const body = await request.json();
    const brandList = body.brands ?? [];

    let cache = {};
    try { cache = JSON.parse(await readFile(CACHE_PATH, 'utf-8')); } catch {}

    const results = {};
    const SIX_HOURS = 6 * 60 * 60 * 1000;

    for (const brandItem of brandList) {
      const brandData = typeof brandItem === 'string'
        ? { id: brandItem, name_ko: brandItem, musinsa_keyword: brandItem, musinsa_url: null }
        : brandItem;

      // brand.id로 캐시 키 통일 (recommend/route.js와 동일)
      const cacheKey = brandData.id ?? brandData.musinsa_keyword;
      const cached = cache[cacheKey];
      if (cached?.crawled_at && Date.now() - new Date(cached.crawled_at).getTime() < SIX_HOURS) {
        console.log(`[crawl] 캐시 사용: ${cacheKey}`);
        results[cacheKey] = cached.products;
        continue;
      }

      const products = await crawlBrand(brandData);
      results[cacheKey] = products;
      cache[cacheKey] = {
        products,
        crawled_at: new Date().toISOString(),
        brand_name: brandData.name_ko,
      };
      await sleep(DELAY_MS);
    }

    await mkdir(path.dirname(CACHE_PATH), { recursive: true });
    await writeFile(CACHE_PATH, JSON.stringify(cache, null, 2));

    return Response.json({ success: true, results });
  } catch (err) {
    console.error('[crawl] 오류:', err);
    return Response.json({ error: err.message }, { status: 500 });
  }
}

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const brand = searchParams.get('brand');
    const cache = JSON.parse(await readFile(CACHE_PATH, 'utf-8'));
    if (brand) return Response.json(cache[brand] ?? { products: [] });
    return Response.json(cache);
  } catch {
    return Response.json({});
  }
}
