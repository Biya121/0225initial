"""
Musinsa 브랜드 크롤러 (Playwright 헤드리스 브라우저)
=====================================================
kpop-brands.json에 정의된 브랜드 페이지를 Playwright(Chromium)로 직접 렌더링해
상품 데이터를 추출합니다.

  - debug-crawl/route.js (Puppeteer) 로직을 Python async Playwright로 1:1 포팅
  - 이미지 없을 경우 msscdn.net CDN URL을 goodsNo로 직접 구성
  - 결과는 6시간 단위로 backend/data/musinsa-cache.json에 캐싱

초기 설치:
  pip install -r requirements.txt
  playwright install chromium
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
from playwright.async_api import async_playwright

# ── 경로 ──────────────────────────────────────────────────────────────────────
DATA_DIR    = Path(__file__).parent / "data"
CACHE_PATH  = DATA_DIR / "musinsa-cache.json"
BRANDS_PATH = DATA_DIR / "kpop-brands.json"
CACHE_TTL   = 6 * 3600  # 6시간

# ── 예산 범위 ─────────────────────────────────────────────────────────────────
BUDGET_RANGE: Dict[str, Tuple[int, int]] = {
    "~5만원":    (0,       50_000),
    "5~15만원":  (50_000,  150_000),
    "15~30만원": (150_000, 300_000),
    "30만원+":   (300_000, 9_999_999),
}

# ── 브라우저 식별 위장 ────────────────────────────────────────────────────────
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

# page.evaluate에 넘길 JS (Puppeteer debug-crawl/route.js와 동일 로직)
_JS_EXTRACT = """(brandName) => {
    const results = [];
    const nameLinks = Array.from(document.querySelectorAll('a'))
        .filter(a => /\\/products\\/\\d+/.test(a.href) && a.innerText?.trim().length > 2);

    nameLinks.slice(0, 12).forEach(link => {
        const name = link.innerText?.trim();
        if (!name) return;

        const goodsNo = link.href.match(/\\/products\\/(\\d+)/)?.[1];
        let card = link.parentElement;
        let img = null, price = 0;

        for (let i = 0; i < 8; i++) {
            if (!card) break;

            if (!img) {
                const imgEl = card.querySelector('img[src*="msscdn.net"]');
                if (imgEl?.src?.includes('goods_img')) img = imgEl.src;
            }
            if (!price) {
                const priceEl = card.querySelector(
                    'span.text-body_13px_semi, [class*="dMbRNh"]'
                );
                if (priceEl) {
                    const raw = priceEl.textContent.replace(/[^0-9]/g, '');
                    if (raw.length >= 4) price = parseInt(raw, 10);
                }
            }
            if (img && price) break;
            card = card.parentElement;
        }

        // 이미지 없으면 CDN URL 직접 구성 (debug-crawl 방식)
        if (!img && goodsNo) {
            const prefix = goodsNo.slice(0, 4);
            img = `https://image.msscdn.net/images/goods_img/${prefix}/${goodsNo}/${goodsNo}_1_500.jpg`;
        }

        results.push({
            name,
            brand:       brandName,
            price_krw:   price,
            image_url:   img   ?? null,
            product_url: link.href,
            goods_no:    goodsNo ?? null,
        });
    });

    return results;
}"""


# ══════════════════════════════════════════════════════════════════════════════
# 캐시 I/O
# ══════════════════════════════════════════════════════════════════════════════

def load_cache() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_cache(cache: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ══════════════════════════════════════════════════════════════════════════════
# 브랜드 데이터 로드
# ══════════════════════════════════════════════════════════════════════════════

def load_brands() -> List[Dict]:
    try:
        data = json.loads(BRANDS_PATH.read_text(encoding="utf-8"))
        return data.get("brands", [])
    except Exception as e:
        print(f"[brands] kpop-brands.json 로드 실패: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# matchScore (matchScore.js 포팅)
# ══════════════════════════════════════════════════════════════════════════════

_STYLE_MAP: Dict[str, List[str]] = {
    "미니멀":       ["미니멀", "베이직", "놈코어", "모던", "크린핏"],
    "스트리트":     ["스트릿", "스트리트", "그래픽", "오버핏"],
    "빈티지":       ["빈티지", "레트로", "아메카지", "프렌치"],
    "캐주얼":       ["캐주얼", "데일리", "베이직", "스포티"],
    "포멀":         ["포멀", "오피스룩", "테일러드", "클래식"],
    "Y2K":          ["Y2K", "하이틴", "컬러풀", "레이어드"],
    "아메카지":     ["아메카지", "빈티지", "데님", "캐주얼"],
    "럭셔리 캐주얼": ["럭셔리", "하이엔드", "아방가르드", "아티스틱"],
}


def calc_match_score(user_input: dict, brand: dict) -> int:
    score = 0
    brand_tags: List[str] = brand.get("style_tags", [])

    # 스타일 매칭 (35점)
    user_styles: List[str] = user_input.get("styles", [])
    if user_styles:
        matched = 0
        for style in user_styles:
            keywords = _STYLE_MAP.get(style, [style])
            for bt in brand_tags:
                if any(kw in bt for kw in keywords):
                    matched += 1
                    break
        score += int(35 * matched / len(user_styles))

    # 예산 매칭 (25점)
    budget_key = user_input.get("budget_krw", "")
    budget = BUDGET_RANGE.get(budget_key)
    if budget:
        brand_min = brand.get("price_range_krw", {}).get("min", 0)
        brand_max = brand.get("price_range_krw", {}).get("max", 9_999_999)
        if brand_min <= budget[1] and brand_max >= budget[0]:
            score += 25

    # 아이돌 레퍼런스 보너스 (+5)
    if any(ref.get("confirmed") for ref in brand.get("idol_references", [])):
        score += 5

    return score


def rank_brands(user_input: dict, brands: List[Dict]) -> List[Dict]:
    scored = [(calc_match_score(user_input, b), b) for b in brands]
    scored.sort(key=lambda x: -x[0])
    return [b for _, b in scored]


# ══════════════════════════════════════════════════════════════════════════════
# CDN URL 유틸
# ══════════════════════════════════════════════════════════════════════════════

def _cdn_url(goods_no: str) -> str:
    """goodsNo로 msscdn.net 이미지 URL 직접 구성 (debug-crawl 방식)"""
    if not goods_no:
        return ""
    prefix = goods_no[:4]
    return (
        f"https://image.msscdn.net/images/goods_img"
        f"/{prefix}/{goods_no}/{goods_no}_1_500.jpg"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Playwright 크롤러 (핵심)
# ══════════════════════════════════════════════════════════════════════════════

async def _crawl_brand_playwright(
    brand_data: Dict,
    budget: Optional[Tuple[int, int]],
    limit: int,
) -> List[Dict]:
    """
    Playwright(Chromium)로 브랜드 페이지를 렌더링하여 상품 추출.
    debug-crawl/route.js Puppeteer 로직과 동일.
    """
    musinsa_url = brand_data.get("musinsa_url", "")
    if not musinsa_url:
        print(f"[playwright] {brand_data.get('name_ko', '?')}: musinsa_url 없음")
        return []

    url = musinsa_url + "?sortCode=POPULAR"
    brand_name = brand_data.get("name_ko", "")
    print(f"[playwright] 접속: {url}")

    raw_items: List[Dict] = []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            page = await browser.new_page()
            await page.set_user_agent(_UA)
            await page.set_extra_http_headers({"Accept-Language": "ko-KR,ko;q=0.9"})
            await page.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
            )

            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(5000)   # React 렌더링 대기

            raw_items = await page.evaluate(_JS_EXTRACT, brand_name)
            print(
                f"[playwright] {brand_name}: {len(raw_items)}개 추출, "
                f"이미지: {sum(1 for i in raw_items if i.get('image_url'))}개"
            )
            await browser.close()

    except Exception as e:
        print(f"[playwright] {brand_name} 실패: {e}")
        return []

    # 정규화 + 예산 필터
    products: List[Dict] = []
    for item in raw_items:
        price = item.get("price_krw", 0)
        name  = item.get("name", "").strip()

        if not name or price < 1000:
            continue
        if budget and not (budget[0] <= price <= budget[1]):
            continue

        goods_no  = item.get("goods_no") or ""
        image_url = item.get("image_url") or _cdn_url(goods_no)   # CDN fallback

        products.append({
            "goods_no":      goods_no,
            "brand":         brand_name,
            "product_name":  name,
            "price_krw":     price,
            "image_url":     image_url,
            "product_url":   item.get("product_url", ""),
            "is_korean":     True,
            "source":        "musinsa",
        })
        if len(products) >= limit:
            break

    print(f"[playwright] {brand_name}: 최종 {len(products)}개 상품")
    return products


# ══════════════════════════════════════════════════════════════════════════════
# 공개 함수
# ══════════════════════════════════════════════════════════════════════════════

async def search_brand(brand_data: Dict, budget_krw: str = "", limit: int = 4) -> List[Dict]:
    """단일 브랜드 크롤링 (캐시 미사용)"""
    budget = BUDGET_RANGE.get(budget_krw)
    products = await _crawl_brand_playwright(brand_data, budget, limit)

    for p in products:
        p.setdefault("style_tags", brand_data.get("style_tags", [])[:3])

    return products


async def search_brand_cached(brand_data: Dict, budget_krw: str = "", limit: int = 4) -> List[Dict]:
    """캐시 우선 브랜드 크롤링 (TTL: 6h)"""
    brand_id  = brand_data.get("id", brand_data.get("name_ko", "unknown"))
    cache_key = f"{brand_id}__{budget_krw or 'all'}"

    cache = load_cache()
    cached = cache.get(cache_key)
    if cached and (time.time() - cached.get("ts", 0)) < CACHE_TTL:
        print(f"[cache] HIT: {cache_key} ({len(cached.get('products', []))}개)")
        return cached.get("products", [])

    products = await search_brand(brand_data, budget_krw, limit)

    cache[cache_key] = {
        "products":   products,
        "ts":         time.time(),
        "brand_name": brand_data.get("name_ko"),
        "crawled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    save_cache(cache)
    return products
