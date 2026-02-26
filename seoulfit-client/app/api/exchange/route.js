// app/api/exchange/route.js

let cachedRate = null;
let cacheTime = null;
const CACHE_MS = 30 * 60 * 1000;

export async function GET() {
  const now = Date.now();
  if (cachedRate && cacheTime && now - cacheTime < CACHE_MS) {
    return Response.json({ rate: cachedRate, cached: true });
  }

  try {
    const apiKey = process.env.EXCHANGE_API_KEY;
    if (!apiKey) throw new Error('EXCHANGE_API_KEY 없음');

    const res = await fetch(
      `https://v6.exchangerate-api.com/v6/${apiKey}/pair/KRW/JPY`
    );
    const data = await res.json();
    cachedRate = data.conversion_rate;
    cacheTime = now;

    return Response.json({ rate: cachedRate, cached: false });
  } catch {
    return Response.json({ rate: 0.11, cached: false, fallback: true });
  }
}
