// app/api/img-proxy/route.js
export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const url = searchParams.get('url');
  if (!url) return new Response('url 필요', { status: 400 });

  const allowed = ['msscdn.net', 'musinsa.com'];
  if (!allowed.some(d => url.includes(d))) {
    return new Response('허용되지 않은 도메인', { status: 403 });
  }

  try {
    const res = await fetch(url, {
      headers: {
        'Referer': 'https://www.musinsa.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9',
      },
      signal: AbortSignal.timeout(10000),
    });

    if (!res.ok) return new Response('이미지 없음', { status: 404 });

    const contentType = res.headers.get('content-type') || 'image/jpeg';
    const buffer = await res.arrayBuffer();

    return new Response(buffer, {
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=86400',
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch (err) {
    return new Response('이미지 로드 실패', { status: 502 });
  }
}