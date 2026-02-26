"""
Musinsa 상품 크롤러
===================
무신사 검색 API를 사용해 실제 상품 데이터(이미지 포함)를 가져옵니다.
API 응답 형식이 바뀔 경우를 대비해 여러 구조를 처리합니다.
"""

import asyncio
from typing import Dict, List, Optional, Tuple

import httpx

# ── 요청 헤더 (브라우저 위장) ──────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Referer": "https://www.musinsa.com/",
    "Origin": "https://www.musinsa.com",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

# 예산 → (min, max) KRW
BUDGET_RANGE: Dict[str, Tuple[int, int]] = {
    "~5만원":    (0,      50_000),
    "5~15만원":  (50_000, 150_000),
    "15~30만원": (150_000, 300_000),
    "30만원+":   (300_000, 9_999_999),
}

# ── 검색 엔드포인트 목록 (순서대로 시도) ──────────────────────────────────────
def _build_endpoints(keyword: str, budget_krw: str) -> List[Dict]:
    budget = BUDGET_RANGE.get(budget_krw)
    price_params = (
        {"minPrice": budget[0], "maxPrice": budget[1]} if budget else {}
    )
    return [
        # ① 무신사 검색 v4
        {
            "url": "https://www.musinsa.com/api/search/v4/goods",
            "params": {
                "keyword": keyword,
                "gf": "A",          # 전체 성별
                "sortCode": "pop_score",
                "page": 0,
                "size": 20,
                **price_params,
            },
        },
        # ② 검색 서버 (search.musinsa.com)
        {
            "url": "https://search.musinsa.com/api/search",
            "params": {
                "q": keyword,
                "type": "goods",
                "n": 20,
                "p": 1,
                **({"price_min": budget[0], "price_max": budget[1]} if budget else {}),
            },
        },
        # ③ 구버전 API
        {
            "url": "https://www.musinsa.com/search/goods",
            "params": {
                "q": keyword,
                "type": "goods",
                "sortCode": "popular",
                "page": 1,
                **({"minPrice": budget[0], "maxPrice": budget[1]} if budget else {}),
            },
        },
    ]


# ── 공개 함수 ──────────────────────────────────────────────────────────────────

async def search_musinsa(
    keyword: str,
    budget_krw: str = "",
    limit: int = 3,
) -> List[Dict]:
    """
    무신사에서 키워드로 상품 검색 → 정규화된 상품 목록 반환.
    모든 엔드포인트 실패 시 빈 리스트 반환.
    """
    endpoints = _build_endpoints(keyword, budget_krw)
    budget = BUDGET_RANGE.get(budget_krw)

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for ep in endpoints:
            try:
                r = await client.get(ep["url"], params=ep["params"], headers=HEADERS)
                if r.status_code != 200:
                    continue

                raw = r.json()
                items = _extract_list(raw)
                if not items:
                    continue

                products: List[Dict] = []
                for item in items:
                    p = _parse_item(item)
                    if not p:
                        continue
                    # 클라이언트 측 예산 필터 (API 필터가 작동 안 할 경우 대비)
                    if budget and not (budget[0] <= p["price_krw"] <= budget[1]):
                        continue
                    products.append(p)
                    if len(products) >= limit:
                        break

                if products:
                    print(f"[crawler] '{keyword}' → {len(products)}개 상품 ({ep['url']})")
                    return products

            except Exception as e:
                print(f"[crawler] {ep['url']} 실패: {e}")
                continue

    print(f"[crawler] '{keyword}' 크롤링 실패 — 모든 엔드포인트 소진")
    return []


async def search_multiple_keywords(
    keywords: List[str],
    budget_krw: str = "",
    total_limit: int = 3,
) -> List[Dict]:
    """
    여러 키워드로 병렬 검색 후 중복 제거하여 total_limit개 반환.
    """
    tasks = [search_musinsa(kw, budget_krw, limit=2) for kw in keywords]
    results_nested = await asyncio.gather(*tasks, return_exceptions=True)

    seen_ids: set = set()
    products: List[Dict] = []

    for result in results_nested:
        if isinstance(result, Exception):
            continue
        for p in result:
            uid = p.get("goods_no", "")
            if uid and uid in seen_ids:
                continue
            if uid:
                seen_ids.add(uid)
            products.append(p)
            if len(products) >= total_limit:
                return products

    return products


# ── 내부 파서 ──────────────────────────────────────────────────────────────────

def _extract_list(data) -> List:
    """다양한 무신사 API 응답 구조에서 goods 리스트 추출"""
    if isinstance(data, list):
        return data

    # {"data": {"goods": [...]}} 또는 {"data": {"list": [...]}}
    inner = data.get("data")
    if isinstance(inner, dict):
        for key in ("goods", "list", "items", "goodsList"):
            v = inner.get(key)
            if isinstance(v, list) and v:
                return v

    # {"data": [...]}
    if isinstance(inner, list):
        return inner

    # {"goods": [...]}  /  {"items": [...]}  /  {"list": [...]}
    for key in ("goods", "items", "list", "goodsList", "products"):
        v = data.get(key)
        if isinstance(v, list) and v:
            return v

    return []


def _parse_item(item: Dict) -> Optional[Dict]:
    """무신사 item dict → 정규화된 상품 dict"""
    try:
        # 상품 번호
        goods_no = str(
            item.get("goodsNo")
            or item.get("goods_no")
            or item.get("id")
            or item.get("goodsId")
            or ""
        )

        # 상품명
        name = (
            item.get("goodsNm")
            or item.get("goods_name")
            or item.get("name")
            or item.get("goodsName")
            or ""
        ).strip()

        # 브랜드명
        brand = ""
        brand_raw = item.get("brandNm") or item.get("brand_name") or ""
        if brand_raw:
            brand = brand_raw
        elif isinstance(item.get("brand"), dict):
            brand = (
                item["brand"].get("name")
                or item["brand"].get("brandNm")
                or ""
            )
        elif isinstance(item.get("brand"), str):
            brand = item["brand"]
        brand = brand.strip()

        # 가격 (원가 기준)
        price = 0
        price_raw = item.get("goodsPrice") or item.get("price") or {}
        if isinstance(price_raw, dict):
            price = int(
                price_raw.get("originPrice")
                or price_raw.get("normalPrice")
                or price_raw.get("price")
                or price_raw.get("salePrice")
                or 0
            )
        elif isinstance(price_raw, (int, float)):
            price = int(price_raw)

        if price == 0:
            price = int(
                item.get("normalPrice")
                or item.get("salePrice")
                or item.get("price")
                or 0
            )

        # 썸네일 이미지
        img = (
            item.get("thumbnailImageUrl")
            or item.get("thumbnail")
            or item.get("goods_img")
            or item.get("image")
            or item.get("imgUrl")
            or item.get("listImageUrl")
            or item.get("imageUrl")
            or ""
        )
        img = _normalize_img(img)

        # 상품 링크
        link = (
            item.get("linkUrl")
            or item.get("product_url")
            or item.get("url")
            or (f"/products/{goods_no}" if goods_no else "")
        )
        if link and not link.startswith("http"):
            link = "https://www.musinsa.com" + link

        # 필수값 체크
        if not name or not brand or price == 0:
            return None

        return {
            "goods_no":    goods_no,
            "brand":       brand,
            "product_name": name,
            "price_krw":   price,
            "image_url":   img,
            "product_url": link,
            "is_korean":   True,
            "source":      "musinsa",
        }

    except Exception as e:
        print(f"[crawler] _parse_item 오류: {e}")
        return None


def _normalize_img(url: str) -> str:
    """이미지 URL을 HTTPS 절대경로로 정규화"""
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
