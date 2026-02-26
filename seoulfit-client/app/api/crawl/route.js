// app/api/crawl/route.js
import puppeteer from 'puppeteer';
import { writeFile, readFile, mkdir } from 'fs/promises';
import path from 'path';

const CACHE_PATH = path.join(process.cwd(), 'data', 'musinsa-cache.json');
const DELAY_MS = 3000;
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function crawlBrand(brandData) {
  const products = [];
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

    const url = `${brandData.musinsa_url}?sortCode=POPULAR`;
    console.log(`[puppeteer] 접속: ${url}`);
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    await sleep(5000);

    const items = await page.evaluate((brandName) => {
      const results = [];

      // 상품 링크 + 상품명이 있는 a 태그 목록
      const nameLinks = Array.from(document.querySelectorAll('a'))
        .filter(a => /\/products\/\d+/.test(a.href) && a.innerText?.trim().length > 2);

      nameLinks.slice(0, 12).forEach(link => {
        const name = link.innerText?.trim();
        if (!name) return;

        const goodsNo = link.href.match(/\/products\/(\d+)/)?.[1];

        // 이 링크의 부모 컨테이너 안에서 이미지, 가격 찾기
        // 부모를 3~5단계 올라가며 카드 컨테이너 탐색
        let card = link.parentElement;
        for (let i = 0; i < 6; i++) {
          if (!card) break;
          const img = card.querySelector('img[src*="msscdn.net"][src*="goods_img"]');
          const priceEl = card.querySelector('span.text-body_13px_semi, [class*="dMbRNh"]');
          if (img || priceEl) {
            const price = parseInt((priceEl?.textContent ?? '').replace(/[^0-9]/g, ''), 10) || 0;
            results.push({
              id: `musinsa_${goodsNo ?? Date.now()}`,
              name,
              brand: brandName,
              price_krw: price,
              image_url: img?.src ?? null,
              product_url: link.href,
              goods_no: goodsNo,
            });
            return;
          }
          card = card.parentElement;
        }

        // 카드 못 찾으면 이미지 없이라도 저장
        results.push({
          id: `musinsa_${goodsNo ?? Date.now()}`,
          name,
          brand: brandName,
          price_krw: 0,
          image_url: null,
          product_url: link.href,
          goods_no: goodsNo,
        });
      });

      return results;
    }, brandData.name_ko);

    products.push(...items);
    console.log(`[puppeteer] ${brandData.name_ko}: ${products.length}개 수집`);

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

      const cacheKey = brandData.id ?? brandData.musinsa_keyword;
      const cached = cache[cacheKey];
      if (cached?.crawled_at && Date.now() - new Date(cached.crawled_at).getTime() < SIX_HOURS) {
        console.log(`[crawl] 캐시 사용: ${cacheKey}`);
        results[cacheKey] = cached.products;
        continue;
      }

      const products = await crawlBrand(brandData);
      results[cacheKey] = products;
      cache[cacheKey] = { products, crawled_at: new Date().toISOString(), brand_name: brandData.name_ko };
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