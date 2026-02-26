"""
크롤링 데이터 정상화 검증 스크립트
====================================
실행: cd backend && python test_crawler.py

검사 항목:
  1. kpop-brands.json 로드
  2. matchScore 브랜드 랭킹
  3. CDN URL fallback 생성
  4. Playwright 실제 크롤링 (단일 브랜드)
  5. 캐시 파일 정합성
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from crawler import (
    _cdn_url,
    calc_match_score,
    load_brands,
    rank_brands,
    search_brand,
)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✔{RESET}  {msg}")
def fail(msg): print(f"  {RED}✘{RESET}  {msg}")
def info(msg): print(f"  {CYAN}·{RESET}  {msg}")


# ════════════════════════════════════════════════════════════════════════════
# 1. kpop-brands.json 로드
# ════════════════════════════════════════════════════════════════════════════

def test_load_brands():
    print(f"\n{YELLOW}[1] kpop-brands.json 로드{RESET}")
    brands = load_brands()
    if not brands:
        fail("브랜드 로드 실패 — backend/data/kpop-brands.json 확인")
        return []
    ok(f"{len(brands)}개 브랜드 로드 완료")
    for b in brands[:3]:
        info(f"  {b['name_ko']} ({b['id']})  스타일: {b.get('style_tags', [])}")
    return brands


# ════════════════════════════════════════════════════════════════════════════
# 2. matchScore 랭킹
# ════════════════════════════════════════════════════════════════════════════

def test_match_score(brands):
    print(f"\n{YELLOW}[2] matchScore 브랜드 랭킹{RESET}")
    test_inputs = [
        {"styles": ["미니멀", "캐주얼"], "budget_krw": "5~15만원", "body_type": "표준"},
        {"styles": ["스트리트", "Y2K"],  "budget_krw": "~5만원",   "body_type": "마른 체형"},
        {"styles": ["럭셔리 캐주얼"],    "budget_krw": "30만원+",  "body_type": "표준"},
    ]
    for user_input in test_inputs:
        ranked = rank_brands(user_input, brands)
        top3 = ranked[:3]
        info(f"스타일: {user_input['styles']}  예산: {user_input['budget_krw']}")
        for i, b in enumerate(top3, 1):
            score = calc_match_score(user_input, b)
            info(f"    {i}. {b['name_ko']} ({b['id']})  점수: {score}")
    ok("matchScore 랭킹 완료")


# ════════════════════════════════════════════════════════════════════════════
# 3. CDN URL fallback
# ════════════════════════════════════════════════════════════════════════════

def test_cdn_url():
    print(f"\n{YELLOW}[3] CDN URL fallback{RESET}")
    test_cases = [
        ("5621602", "https://image.msscdn.net/images/goods_img/5621/5621602/5621602_1_500.jpg"),
        ("1234567", "https://image.msscdn.net/images/goods_img/1234/1234567/1234567_1_500.jpg"),
        ("",        ""),
    ]
    all_pass = True
    for goods_no, expected in test_cases:
        result = _cdn_url(goods_no)
        if result == expected:
            ok(f"goods_no={goods_no!r:10} → {result or '(빈 문자열)'}")
        else:
            fail(f"goods_no={goods_no!r:10} → 기대: {expected}  실제: {result}")
            all_pass = False
    if all_pass:
        ok("CDN URL 생성 정상")


# ════════════════════════════════════════════════════════════════════════════
# 4. Playwright 실제 크롤링
# ════════════════════════════════════════════════════════════════════════════

async def test_crawl(brands):
    print(f"\n{YELLOW}[4] Playwright 실제 크롤링 (단일 브랜드){RESET}")

    target = next((b for b in brands if b["id"] == "musinsa_standard"), brands[0])
    info(f"테스트 브랜드: {target['name_ko']} ({target['id']})")
    info(f"URL: {target.get('musinsa_url', '없음')}")

    products = await search_brand(target, budget_krw="5~15만원", limit=3)

    if not products:
        fail("크롤링 결과 없음")
        info("→ playwright install chromium 실행 여부 확인")
        info("→ 네트워크 연결 상태 확인 (무신사 접속 가능 여부)")
        return

    ok(f"{len(products)}개 상품 수집")

    print(f"\n  {'필드':<18} {'검증':<8} 값")
    print(f"  {'-'*18} {'-'*8} {'-'*45}")

    errors = 0
    for i, p in enumerate(products, 1):
        print(f"\n  ── 상품 {i} ──────────────────────────────────────────")

        brand_ok = bool(p.get("brand"))
        print(f"  {'brand':<18} {'✔' if brand_ok else '✘':<8} {p.get('brand', '')}")
        if not brand_ok: errors += 1

        name_ok = bool(p.get("product_name"))
        print(f"  {'product_name':<18} {'✔' if name_ok else '✘':<8} {p.get('product_name', '')[:50]}")
        if not name_ok: errors += 1

        price = p.get("price_krw", 0)
        price_ok = price >= 1000
        print(f"  {'price_krw':<18} {'✔' if price_ok else '✘ (<1000원!)':<8} {price:,}원")
        if not price_ok: errors += 1

        img = p.get("image_url", "")
        img_ok = img.startswith("https://")
        cdn_flag = "(CDN fallback)" if "goods_img" in img else ""
        print(f"  {'image_url':<18} {'✔' if img_ok else '✘':<8} {img[:65]} {cdn_flag}")
        if not img_ok: errors += 1

        url_ok = p.get("product_url", "").startswith("https://")
        print(f"  {'product_url':<18} {'✔' if url_ok else '✘':<8} {p.get('product_url', '')}")
        if not url_ok: errors += 1

    print()
    if errors == 0:
        ok(f"전체 필드 검증 통과")
    else:
        fail(f"{errors}개 필드 이상 — 위 로그 확인")


# ════════════════════════════════════════════════════════════════════════════
# 5. 캐시 파일 정합성
# ════════════════════════════════════════════════════════════════════════════

def test_cache():
    print(f"\n{YELLOW}[5] 캐시 파일 상태{RESET}")
    cache_path = Path(__file__).parent / "data" / "musinsa-cache.json"
    if not cache_path.exists():
        info("캐시 파일 없음 (첫 실행 시 정상)")
        return

    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        ok(f"캐시 파일 존재: {cache_path}")
        ok(f"캐시 키 수: {len(cache)}")

        bad_prices, missing_imgs = [], []
        for key, entry in cache.items():
            for p in entry.get("products", []):
                if p.get("price_krw", 0) < 1000:
                    bad_prices.append((key, p.get("price_krw")))
                if not p.get("image_url"):
                    missing_imgs.append(key)

        if bad_prices:
            fail(f"가격 이상 항목 {len(bad_prices)}개: {bad_prices[:3]}")
            info("→ 캐시 삭제 후 재크롤링: rm backend/data/musinsa-cache.json")
        else:
            ok("가격 데이터 정상 (모두 1,000원 이상)")

        if missing_imgs:
            fail(f"이미지 없는 항목 {len(missing_imgs)}개")
        else:
            ok("이미지 URL 데이터 정상")
    except Exception as e:
        fail(f"캐시 파일 파싱 오류: {e}")


# ════════════════════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════════════════════

async def main():
    print(f"\n{'='*60}")
    print(f"  SEOULFIT 크롤링 데이터 정상화 검증")
    print(f"{'='*60}")

    brands = test_load_brands()
    if not brands:
        sys.exit(1)

    test_match_score(brands)
    test_cdn_url()
    await test_crawl(brands)
    test_cache()

    print(f"\n{'='*60}")
    print(f"  검증 완료")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
