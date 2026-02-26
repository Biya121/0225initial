"""
SEOULFIT Backend — FastAPI
==========================
실행: cd backend && uvicorn main:app --reload

흐름:
  1. POST /api/recommend
     → OpenAI로 키워드·아이돌 레퍼런스·해외 브랜드 생성
     → 무신사 크롤러로 한국 브랜드 실제 상품 검색
     → 크롤링 실패 시 AI fallback 데이터 사용

  2. GET  /api/exchange-rate  → Yahoo Finance 실시간 KRW→JPY

  3. POST /api/checkout       → Stripe Checkout (JPY, card + konbini)
"""

import json
import os
from typing import List, Optional

import httpx
import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from pydantic import BaseModel

from crawler import search_multiple_keywords

load_dotenv()

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="SEOULFIT API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")


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
        return 0.0973  # 1 KRW ≈ 0.097 JPY fallback


@app.get("/api/exchange-rate")
async def get_exchange_rate():
    rate = await _fetch_krw_jpy()
    return {"krw_to_jpy": rate, "source": "Yahoo Finance", "pair": "KRWJPY=X"}


# ══════════════════════════════════════════════════════════════════════════════
# 2. AI 추천  (키워드 생성 → 무신사 크롤링 → 해외 브랜드 AI 생성)
# ══════════════════════════════════════════════════════════════════════════════

class RecommendRequest(BaseModel):
    height: Optional[int] = None
    weight: Optional[int] = None
    body_type: str = ""
    styles: List[str] = []
    colors: List[str] = []
    budget_krw: str = ""
    email: str = ""


async def _ai_plan(req: RecommendRequest) -> dict:
    """
    OpenAI로:
      - 아이돌 스타일 레퍼런스
      - 무신사 검색 키워드 3개
      - 키워드별 style_tags, product_description
      - 해외 브랜드 2개 (상품명/설명/가격 포함)
      - 크롤링 실패 시 쓸 한국 브랜드 fallback 3개
    """
    prompt = f"""당신은 K-POP 아이돌 공항 패션 전문 스타일리스트입니다.

사용자 정보:
- 키: {req.height}cm, 체중: {req.weight}kg, 체형: {req.body_type}
- 원하는 스타일: {', '.join(req.styles) or '미기재'}
- 선호 색상: {', '.join(req.colors) or '미기재'}
- 예산 (KRW 기준): {req.budget_krw or '미기재'}

K-POP 공항 패션 레퍼런스:
- BTS RM: 오버핏 코트·슬랙스, 모노톤, 고급 스트리트 (Wooyoungmi, 무신사 스탠다드)
- BTS 뷔: 레이어드·빈티지 믹스 (Thom Browne, Celine)
- BLACKPINK 제니: 페미닌 엣지, 크롭 재킷, 하이웨스트 (Ader Error, Chanel)
- aespa 카리나: 미니멀 테크웨어, 슬림핏 (IISE, Off-White)
- EXO 카이: 올블랙, 타이트 실루엣 (Gucci, THISISNEVERTHAT)
- 뉴진스: Y2K 캐주얼, 데님 (무신사 스탠다드, Carhartt)

아래 JSON만 반환 (한국어):
{{
  "idol_name": "가장 잘 어울리는 아이돌 이름 (예: BTS RM, aespa 카리나)",
  "idol_style_ref": "이 사용자에게 어울리는 공항 패션 스타일 설명 (3문장, 구체적 브랜드·아이템 언급)",
  "search_keywords": [
    "무신사 검색어1 (예: 오버핏 코트)",
    "무신사 검색어2 (예: 슬림 슬랙스)",
    "무신사 검색어3 (예: 그래픽 후드)"
  ],
  "style_tags": {{
    "무신사 검색어1": ["태그A", "태그B"],
    "무신사 검색어2": ["태그C", "태그D"],
    "무신사 검색어3": ["태그E", "태그F"]
  }},
  "descriptions": {{
    "무신사 검색어1": "이 체형/스타일에 어울리는 이유 (1~2문장)",
    "무신사 검색어2": "이 체형/스타일에 어울리는 이유",
    "무신사 검색어3": "이 체형/스타일에 어울리는 이유"
  }},
  "korean_brands_fallback": [
    {{
      "brand": "한국 브랜드명 (Andersson Bell, IISE, THISISNEVERTHAT 등)",
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

- search_keywords: 무신사에서 실제로 검색할 수 있는 한국어 키워드
- korean_brands_fallback: 3개
- other_brands: 2개 (아이돌이 실제 착용한 해외 브랜드 우선)
- 예산({req.budget_krw})에 맞는 price_krw 설정
"""

    resp = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=2000,
    )
    return json.loads(resp.choices[0].message.content)


@app.post("/api/recommend")
async def recommend(req: RecommendRequest):
    """
    K-POP 아이돌 공항 패션 기반 AI 추천.
    한국 브랜드는 무신사 실제 상품(이미지 포함),
    해외 브랜드는 AI 생성 데이터로 반환.
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY 환경변수를 설정해주세요.")

    # ① AI로 키워드 + 아이돌 레퍼런스 + 해외 브랜드 생성
    try:
        plan = await _ai_plan(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI 오류: {e}")

    keywords: List[str] = plan.get("search_keywords", [])
    style_tags: dict = plan.get("style_tags", {})
    descriptions: dict = plan.get("descriptions", {})

    # ② 무신사 크롤링 (병렬)
    musinsa_products = await search_multiple_keywords(
        keywords,
        budget_krw=req.budget_krw,
        total_limit=3,
    )

    # ③ 크롤링 결과에 AI 생성 태그/설명 보강
    for i, p in enumerate(musinsa_products):
        matched_kw = keywords[i] if i < len(keywords) else (keywords[0] if keywords else "")
        p.setdefault("style_tags", style_tags.get(matched_kw, ["스타일리시", "트렌디"]))
        p.setdefault("product_description", descriptions.get(
            matched_kw,
            f"{req.body_type or '기본'} 체형에 잘 어울리는 아이템입니다.",
        ))

    # ④ 크롤링 실패 시 AI fallback 사용
    korean_brands = musinsa_products or plan.get("korean_brands_fallback", [])

    return {
        "idol_name":      plan.get("idol_name", "K-POP"),
        "idol_style_ref": plan.get("idol_style_ref", ""),
        "korean_brands":  korean_brands[:3],
        "other_brands":   plan.get("other_brands", [])[:2],
        "source_korean":  "musinsa" if musinsa_products else "ai_fallback",
    }


# ══════════════════════════════════════════════════════════════════════════════
# 3. Stripe Checkout  (JPY · カード + コンビニ決済)
# ══════════════════════════════════════════════════════════════════════════════

class CheckoutRequest(BaseModel):
    product_name: str
    brand: str
    price_jpy: int
    image_url: Optional[str] = None
    product_url: Optional[str] = None   # 무신사 상품 URL (참고용)
    email: str = ""
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


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
    # 무신사 이미지는 msscdn.net 도메인 → Stripe가 허용하는 HTTPS URL
    if req.image_url and req.image_url.startswith("https://"):
        product_data["images"] = [req.image_url]

    line_item = {
        "price_data": {
            "currency": "jpy",
            "product_data": product_data,
            "unit_amount": req.price_jpy,
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

    # konbini 먼저 시도, 미활성화 시 card만으로 재시도
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
            # konbini 비활성화 → card만으로 재시도
            continue
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=str(e))
