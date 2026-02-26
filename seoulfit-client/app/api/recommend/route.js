// app/api/recommend/route.js
import { rankBrands } from '@/lib/matchScore';
import { readFile } from 'fs/promises';
import path from 'path';

export async function POST(request) {
  try {
    const userInput = await request.json();

    const brandsPath = path.join(process.cwd(), 'data', 'kpop-brands.json');
    const brandsData = JSON.parse(await readFile(brandsPath, 'utf-8'));
    const brands = brandsData.brands;

    const ranked = rankBrands(userInput, brands);
    const top = ranked.slice(0, 10);

    // 캐시 로드
    const cachePath = path.join(process.cwd(), 'data', 'musinsa-cache.json');
    let cache = {};
    try { cache = JSON.parse(await readFile(cachePath, 'utf-8')); } catch {}

    const results = top.map(brand => ({
      ...brand,
      // ✅ brand.id 로 캐시 조회 (crawl과 동일한 키)
      products: cache[brand.id]?.products ?? [],
    }));

    return Response.json({ results });
  } catch (err) {
    console.error('[recommend]', err);
    return Response.json({ error: err.message }, { status: 500 });
  }
}