// lib/formatPrice.js

let cachedRate = null;
let cacheTime = null;
const CACHE_MS = 30 * 60 * 1000; // 30분

// 서버사이드 환율 조회 (Node.js / Next.js API Route에서 사용)
export async function getExchangeRate() {
  const now = Date.now();
  if (cachedRate && cacheTime && now - cacheTime < CACHE_MS) {
    return cachedRate;
  }
  try {
    const res = await fetch(
      `https://v6.exchangerate-api.com/v6/${process.env.EXCHANGE_API_KEY}/pair/KRW/JPY`
    );
    const data = await res.json();
    cachedRate = data.conversion_rate;
    cacheTime = now;
    return cachedRate;
  } catch {
    // fallback: 고정 환율
    return 0.11;
  }
}

// KRW → JPY 변환 + 포맷
export function formatJPY(krw, rate = 0.11) {
  const jpy = Math.ceil(krw * rate);
  return `¥${jpy.toLocaleString('ja-JP')}`;
}

// KRW 포맷
export function formatKRW(krw) {
  return `${krw.toLocaleString('ko-KR')}원`;
}
