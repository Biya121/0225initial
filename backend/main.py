"""
SEOULFIT Backend — FastAPI
==========================
실행: cd backend && uvicorn main:app --reload

흐름:
  1. POST /api/recommend
     → kpop-brands.json에서 matchScore로 브랜드 랭킹
     → 상위 3개 브랜드를 무신사 API 크롤링 (6h 캐시)
     → OpenAI로 아이돌 레퍼런스 + 해외 브랜드 생성
     → 크롤링 실패 시 AI fallback 사용

  2. GET  /api/exchange-rate  → Yahoo Finance 실시간 KRW→JPY

  3. POST /api/checkout       → Stripe Checkout (JPY, card + konbini)
"""

import asyncio
import json
import os
from pathlib import Path
from typing import List, Optional

import httpx
import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from pydantic import BaseModel

from crawler import load_brands, rank_brands, search_brand_cached

load_dotenv()

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="SEOULFIT API", version="2.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stripe.api_key      = os.getenv("STRIPE_SECRET_KEY", "")
openai_client       = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
FRONTEND_URL        = os.getenv("FRONTEND_URL", "http://localhost:5500")


# ══════════════════════════════════════════════════════════════════════════════
# 1. 환율  (Yahoo Finance KRW → JPY)
# ══════════════════════════════════════════════════════════════════════════════

async def _fetch_krw_jpy() -> float:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/KRWJPY=X"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                url,
                params={"interval": "1d", "range": "1d"},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            data = r.json()
            return float(data["chart"]["result"][0]["meta"]["regularMarketPrice"])
    except Exception as e:
        print(f"[exchange-rate] 오류: {e}")
        return 0.0973  # fallback


@app.get("/api/exchange-rate")
async def get_exchange_rate():
    rate = await _fetch_krw_jpy()
    return {"krw_to_jpy": rate, "source": "Yahoo Finance", "pair": "KRWJPY=X"}


# ══════════════════════════════════════════════════════════════════════════════
# 2. AI 추천  (브랜드 랭킹 → 무신사 크롤링 → AI 아이돌 레퍼런스)
# ══════════════════════════════════════════════════════════════════════════════

class RecommendRequest(BaseModel):
    height:     Optional[int]  = None
    weight:     Optional[int]  = None
    body_type:  str            = ""
    styles:     List[str]      = []
    colors:     List[str]      = []
    budget_krw: str            = ""
    email:      str            = ""


async def _ai_idol_ref(req: RecommendRequest, brands_info: str) -> dict:
    """
    OpenAI로 아이돌 레퍼런스 + 해외 브랜드 생성.
    무신사 브랜드 랭킹 결과를 컨텍스트로 제공.
    """
    prompt = f"""당신은 K-POP 아이돌 공항 패션 전문 스타일리스트입니다.

사용자 정보:
- 키: {req.height}cm, 체중: {req.weight}kg, 체형: {req.body_type}
- 원하는 스타일: {', '.join(req.styles) or '미기재'}
- 선호 색상: {', '.join(req.colors) or '미기재'}
- 예산 (KRW): {req.budget_krw or '미기재'}

이 사용자에게 추천된 무신사 브랜드 (matchScore 결과):
{brands_info}

아래 JSON만 반환 (한국어):
{{
  "idol_name": "가장 잘 어울리는 아이돌 이름 (예: BTS RM, aespa 카리나)",
  "idol_style_ref": "이 사용자에게 어울리는 공항 패션 스타일 설명 (3문장, 위 브랜드 언급 포함)",
  "product_descriptions": {{
    "brand_id_1": "이 브랜드 상품이 이 체형/스타일에 어울리는 이유 (1~2문장)",
    "brand_id_2": "이 브랜드 상품이 이 체형/스타일에 어울리는 이유",
    "brand_id_3": "이 브랜드 상품이 이 체형/스타일에 어울리는 이유"
  }},
  "korean_brands_fallback": [
    {{
      "brand": "한국 브랜드명",
      "product_name": "구체적 상품명",
      "product_description": "설명 2문장",
      "price_krw": 숫자,
      "style_tags": ["태그1", "태그2"],
      "is_korean": true,
      "source": "ai_fallback"
    }}
  ],
  "other_brands": [
    {{
      "brand": "해외 브랜드 (아이돌 착용 브랜드 우선)",
      "product_name": "상품명",
      "product_description": "설명 2문장",
      "price_krw": 숫자,
      "style_tags": ["태그1", "태그2"],
      "is_korean": false,
      "source": "ai"
    }}
  ]
}}

- korean_brands_fallback: 3개 (크롤링 실패 시 표시)
- other_brands: 2개
- 예산({req.budget_krw})에 맞는 price_krw 설정
"""
    resp = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=1800,
    )
    return json.loads(resp.choices[0].message.content)


@app.post("/api/recommend")
async def recommend(req: RecommendRequest):
    """
    K-POP 아이돌 공항 패션 AI 추천.

    1. kpop-brands.json에서 matchScore로 브랜드 랭킹
    2. 상위 3개 브랜드 무신사 크롤링 (6h 캐시)
    3. OpenAI로 아이돌 레퍼런스 + 해외 브랜드
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY 환경변수를 설정해주세요.")

    # ① matchScore로 브랜드 랭킹
    all_brands = load_brands()
    if not all_brands:
        raise HTTPException(status_code=500, detail="kpop-brands.json 로드 실패")

    user_input = {
        "styles":     req.styles,
        "budget_krw": req.budget_krw,
        "body_type":  req.body_type,
    }
    ranked   = rank_brands(user_input, all_brands)
    top3     = ranked[:3]

    # AI에게 넘길 브랜드 요약
    brands_info = "\n".join(
        f"- {b['name_ko']} ({b['id']}): {', '.join(b.get('style_tags', []))}"
        for b in top3
    )

    # ② 무신사 크롤링 + AI 생성 병렬 실행
    crawl_tasks = [
        search_brand_cached(b, req.budget_krw, limit=2) for b in top3
    ]
    ai_task = _ai_idol_ref(req, brands_info)

    crawl_results_nested, ai_plan = await asyncio.gather(
        asyncio.gather(*crawl_tasks, return_exceptions=True),
        ai_task,
        return_exceptions=True,
    )

    if isinstance(ai_plan, Exception):
        raise HTTPException(status_code=500, detail=f"OpenAI 오류: {ai_plan}")

    # ③ 크롤링 결과 병합 + AI 설명 보강
    desc_map: dict = ai_plan.get("product_descriptions", {})

    musinsa_products: List[dict] = []
    for i, result in enumerate(crawl_results_nested):
        if isinstance(result, Exception):
            print(f"[recommend] 크롤링 오류 ({top3[i]['id']}): {result}")
            continue
        brand = top3[i]
        for p in result:
            p.setdefault("style_tags",
                         brand.get("style_tags", ["스타일리시", "트렌디"])[:3])
            p.setdefault("product_description",
                         desc_map.get(brand["id"],
                                      f"{req.body_type or '기본'} 체형에 잘 어울리는 아이템입니다."))
            musinsa_products.append(p)

    # ④ 크롤링 실패 시 AI fallback
    korean_brands = musinsa_products[:3] or ai_plan.get("korean_brands_fallback", [])

    return {
        "idol_name":      ai_plan.get("idol_name", "K-POP"),
        "idol_style_ref": ai_plan.get("idol_style_ref", ""),
        "korean_brands":  korean_brands[:3],
        "other_brands":   ai_plan.get("other_brands", [])[:2],
        "source_korean":  "musinsa" if musinsa_products else "ai_fallback",
        "matched_brands": [b["id"] for b in top3],   # 디버그용
    }


# ══════════════════════════════════════════════════════════════════════════════
# 3. Stripe Checkout  (JPY · カード + コンビニ決済)
# ══════════════════════════════════════════════════════════════════════════════

class CheckoutRequest(BaseModel):
    product_name: str
    brand:        str
    price_jpy:    int
    image_url:    Optional[str] = None
    product_url:  Optional[str] = None
    email:        str = ""
    success_url:  Optional[str] = None
    cancel_url:   Optional[str] = None


@app.post("/api/checkout")
async def create_checkout(req: CheckoutRequest):
    """
    Stripe Checkout 세션 생성.
    결제수단: カード (Visa/MC/JCB) + コンビニ決済
    ※ konbini는 Stripe 계정에서 활성화 필요 (Japan Payments).
    """
    if not stripe.api_key:
        raise HTTPException(status_code=400, detail="STRIPE_SECRET_KEY 환경변수를 설정해주세요.")
    if req.price_jpy < 120:
        raise HTTPException(status_code=400, detail="최소 결제 금액은 ¥120입니다.")

    encoded_email = req.email.replace("@", "%40")
    success_url = (
        req.success_url
        or (
            f"{FRONTEND_URL}/fashion.html?payment=success"
            f"&email={encoded_email}"
            f"&product={req.product_name}"
            f"&brand={req.brand}"
            f"&price={req.price_jpy}"
        )
    )
    cancel_url = req.cancel_url or f"{FRONTEND_URL}/fashion.html"

    product_data: dict = {"name": f"{req.brand} — {req.product_name}"}
    if req.image_url and req.image_url.startswith("https://"):
        product_data["images"] = [req.image_url]

    line_item = {
        "price_data": {
            "currency":     "jpy",
            "product_data": product_data,
            "unit_amount":  req.price_jpy,
        },
        "quantity": 1,
    }

    base_kwargs = dict(
        line_items=[line_item],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        **({"customer_email": req.email} if req.email else {}),
    )

    for payment_methods in (["card", "konbini"], ["card"]):
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=payment_methods,
                **base_kwargs,
            )
            return {
                "checkout_url":    session.url,
                "session_id":      session.id,
                "payment_methods": payment_methods,
            }
        except stripe.error.InvalidRequestError:
            if payment_methods == ["card"]:
                raise
            continue
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=str(e))
