"""
Musinsa 브랜드 크롤러 (kpop-brands.json 기반)
================================================
kpop-brands.json에 정의된 브랜드 목록을 기준으로 무신사 API를 호출합니다.
- API 응답에서 이미지 URL이 없으면 CDN URL을 goodsNo로 직접 구성합니다.
- 결과는 6시간 단위로 backend/data/musinsa-cache.json에 캐싱합니다.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx

# ── 경로 ──────────────────────────────────────────────────────────────────────
DATA_DIR    = Path(__file__).parent / "data"
CACHE_PATH  = DATA_DIR / "musinsa-cache.json"
BRANDS_PATH = DATA_DIR / "kpop-brands.json"
CACHE_TTL   = 6 * 3600  # 6시간 (초)

# ── 요청 헤더 ─────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.musinsa.com/",
    "Origin": "https://www.musinsa.com",
}

# ── 예산 범위 ─────────────────────────────────────────────────────────────────
BUDGET_RANGE: Dict[str, Tuple[int, int]] = {
    "~5만원":    (0,       50_000),
    "5~15만원":  (50_000,  150_000),
    "15~30만원": (150_000, 300_000),
    "30만원+":   (300_000, 9_999_999),
}


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
    """
    브랜드 ↔ 사용자 입력 매칭 점수 (0~100+).
    matchScore.js 알고리즘 포팅.
    """
    score = 0
    brand_tags: List[str] = brand.get("style_tags", [])

    # ① 스타일 매칭 (35점)
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

    # ② 예산 매칭 (25점)
    budget_key = user_input.get("budget_krw", "")
    budget = BUDGET_RANGE.get(budget_key)
    if budget:
        brand_min = brand.get("price_range_krw", {}).get("min", 0)
        brand_max = brand.get("price_range_krw", {}).get("max", 9_999_999)
        if brand_min <= budget[1] and brand_max >= budget[0]:
            score += 25

    # ③ 아이돌 레퍼런스 확인 보너스 (+5)
    if any(ref.get("confirmed") for ref in brand.get("idol_references", [])):
        score += 5

    return score


def rank_brands(user_input: dict, brands: List[Dict]) -> List[Dict]:
    """사용자 입력에 따라 브랜드를 점수 내림차순으로 정렬"""
    scored = [(calc_match_score(user_input, b), b) for b in brands]
    scored.sort(key=lambda x: -x[0])
    return [b for _, b in scored]


# ══════════════════════════════════════════════════════════════════════════════
# 무신사 API 검색
# ══════════════════════════════════════════════════════════════════════════════

def _cdn_url(goods_no: str) -> str:
    """
    무신사 CDN 이미지 URL 직접 구성 (debug-crawl/route.js 방식).
    goods_no의 앞 4자리 = 서브디렉토리
    예) 5621602 → images/goods_img/5621/5621602/5621602_1_500.jpg
    """
    if not goods_no:
        return ""
    prefix = goods_no[:4]
    return (
        f"https://image.msscdn.net/images/goods_img"
        f"/{prefix}/{goods_no}/{goods_no}_1_500.jpg"
    )


def _normalize_img(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://image.msscdn.net" + url
    if url.startswith("http://"):
        return url.replace("http://", "https://", 1)
    return url


def _extract_list(data) -> List:
    """다양한 무신사 API 응답 구조에서 goods 리스트 추출"""
    if isinstance(data, list):
        return data
    inner = data.get("data")
    if isinstance(inner, dict):
        for key in ("goods", "list", "items", "goodsList"):
            v = inner.get(key)
            if isinstance(v, list) and v:
                return v
    if isinstance(inner, list):
        return inner
    for key in ("goods", "items", "list", "goodsList", "products"):
        v = data.get(key)
        if isinstance(v, list) and v:
            return v
    return []


def _parse_item(item: Dict, brand_name_fallback: str = "") -> Optional[Dict]:
    """무신사 item dict → 정규화된 상품 dict"""
    try:
        goods_no = str(
            item.get("goodsNo") or item.get("goods_no")
            or item.get("id") or item.get("goodsId") or ""
        )

        name = (
            item.get("goodsNm") or item.get("goods_name")
            or item.get("name") or item.get("goodsName") or ""
        ).strip()

        brand = ""
        brand_raw = item.get("brandNm") or item.get("brand_name") or ""
        if brand_raw:
            brand = brand_raw
        elif isinstance(item.get("brand"), dict):
            brand = item["brand"].get("name") or item["brand"].get("brandNm") or ""
        elif isinstance(item.get("brand"), str):
            brand = item["brand"]
        brand = brand.strip() or brand_name_fallback

        # 가격: 원가 기준, 최소 1,000원 이상이어야 유효
        price = 0
        price_raw = item.get("goodsPrice") or item.get("price") or {}
        if isinstance(price_raw, dict):
            price = int(
                price_raw.get("originPrice")
                or price_raw.get("normalPrice")
                or price_raw.get("salePrice")
                or price_raw.get("price")
                or 0
            )
        elif isinstance(price_raw, (int, float)):
            price = int(price_raw)

        if price < 1000:
            price = int(
                item.get("normalPrice") or item.get("salePrice")
                or item.get("price") or 0
            )

        # 이미지: API 응답 → 없으면 CDN fallback
        img = (
            item.get("thumbnailImageUrl") or item.get("thumbnail")
            or item.get("goods_img") or item.get("image")
            or item.get("imgUrl") or item.get("listImageUrl")
            or item.get("imageUrl") or ""
        )
        img = _normalize_img(img)
        if not img and goods_no:
            img = _cdn_url(goods_no)  # ← CDN fallback (debug-crawl 방식)

        link = (
            item.get("linkUrl") or item.get("product_url") or item.get("url")
            or (f"/products/{goods_no}" if goods_no else "")
        )
        if link and not link.startswith("http"):
            link = "https://www.musinsa.com" + link

        if not name or price < 1000:
            return None

        return {
            "goods_no":          goods_no,
            "brand":             brand,
            "product_name":      name,
            "price_krw":         price,
            "image_url":         img,
            "product_url":       link,
            "is_korean":         True,
            "source":            "musinsa",
        }
    except Exception as e:
        print(f"[crawler] _parse_item 오류: {e}")
        return None


async def _search_api(keyword: str, budget: Optional[Tuple[int, int]], limit: int) -> List[Dict]:
    """
    무신사 검색 API 3개 엔드포인트를 순서대로 시도.
    성공 시 정규화된 상품 목록 반환, 전부 실패 시 빈 리스트.
    """
    price_p = {"minPrice": budget[0], "maxPrice": budget[1]} if budget else {}
    endpoints = [
        {
            "url": "https://www.musinsa.com/api/search/v4/goods",
            "params": {"keyword": keyword, "gf": "A", "sortCode": "pop_score",
                       "page": 0, "size": 20, **price_p},
        },
        {
            "url": "https://search.musinsa.com/api/search",
            "params": {"q": keyword, "type": "goods", "n": 20, "p": 1,
                       **({'price_min': budget[0], 'price_max': budget[1]} if budget else {})},
        },
        {
            "url": "https://www.musinsa.com/search/goods",
            "params": {"q": keyword, "type": "goods", "sortCode": "popular",
                       "page": 1, **price_p},
        },
    ]

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for ep in endpoints:
            try:
                r = await client.get(ep["url"], params=ep["params"], headers=HEADERS)
                if r.status_code != 200:
                    continue
                items = _extract_list(r.json())
                if not items:
                    continue

                products: List[Dict] = []
                for item in items:
                    p = _parse_item(item, brand_name_fallback=keyword)
                    if not p:
                        continue
                    if budget and not (budget[0] <= p["price_krw"] <= budget[1]):
                        continue
                    products.append(p)
                    if len(products) >= limit:
                        break

                if products:
                    print(f"[crawler] '{keyword}' → {len(products)}개 ({ep['url']})")
                    return products
            except Exception as e:
                print(f"[crawler] {ep['url']} 실패: {e}")

    print(f"[crawler] '{keyword}' 크롤링 실패 — 모든 엔드포인트 소진")
    return []


# ══════════════════════════════════════════════════════════════════════════════
# 공개 함수
# ══════════════════════════════════════════════════════════════════════════════

async def search_brand(brand_data: Dict, budget_krw: str = "", limit: int = 4) -> List[Dict]:
    """
    단일 브랜드 검색.
    brand_data: kpop-brands.json의 브랜드 항목
    """
    keyword = brand_data.get("musinsa_keyword") or brand_data.get("name_ko", "")
    brand_name = brand_data.get("name_ko", keyword)
    brand_id   = brand_data.get("id", keyword)

    budget = BUDGET_RANGE.get(budget_krw)
    products = await _search_api(keyword, budget, limit)

    for p in products:
        p["brand_id"] = brand_id
        p["brand"] = p["brand"] or brand_name  # 브랜드명 보강
        p.setdefault("style_tags", brand_data.get("style_tags", [])[:3])
        # 이미지 없으면 CDN 재시도
        if not p["image_url"] and p.get("goods_no"):
            p["image_url"] = _cdn_url(p["goods_no"])

    return products


async def search_brand_cached(brand_data: Dict, budget_krw: str = "", limit: int = 4) -> List[Dict]:
    """
    캐시 우선 브랜드 검색 (TTL: 6h).
    캐시 미스 또는 만료 시 실제 크롤링 후 저장.
    """
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
