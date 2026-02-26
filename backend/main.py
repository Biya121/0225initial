"""
SEOULFIT Backend — FastAPI
==========================
실행: cd backend && uvicorn main:app --reload
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

load_dotenv()

# ── App & CORS ────────────────────────────────────────────────────────────────
app = FastAPI(title="SEOULFIT API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Clients ───────────────────────────────────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. 환율: KRW → JPY  (Yahoo Finance)
# ═══════════════════════════════════════════════════════════════════════════════

async def _fetch_krw_jpy() -> float:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/KRWJPY=X"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SEOULFIT/1.0)"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, params={"interval": "1d", "range": "1d"}, headers=headers)
            data = r.json()
            rate = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            return float(rate)
    except Exception as e:
        print(f"[exchange-rate] Yahoo Finance 오류: {e}")
        return 0.0973  # fallback: 약 1 KRW = 0.097 JPY (2025년 기준)


@app.get("/api/exchange-rate")
async def get_exchange_rate():
    """Yahoo Finance 실시간 KRW→JPY 환율"""
    rate = await _fetch_krw_jpy()
    return {"krw_to_jpy": rate, "source": "Yahoo Finance", "pair": "KRWJPY=X"}


# ═══════════════════════════════════════════════════════════════════════════════
# 2. AI 패션 추천  (OpenAI GPT-4o-mini)
# ═══════════════════════════════════════════════════════════════════════════════

class RecommendRequest(BaseModel):
    height: Optional[int] = None
    weight: Optional[int] = None
    body_type: str = ""
    styles: List[str] = []
    colors: List[str] = []
    budget_krw: str = ""
    email: str = ""


@app.post("/api/recommend")
async def recommend(req: RecommendRequest):
    """K-POP 아이돌 공항 패션 기반 AI 추천 (한국 브랜드 우선)"""
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY 환경변수를 설정해주세요.")

    prompt = f"""당신은 K-POP 아이돌의 공항 패션을 전문으로 하는 한국 패션 스타일리스트입니다.

사용자 정보:
- 키: {req.height}cm, 체중: {req.weight}kg, 체형: {req.body_type}
- 원하는 스타일: {', '.join(req.styles) or '미기재'}
- 선호 색상: {', '.join(req.colors) or '미기재'}
- 예산 (한국 원화 기준): {req.budget_krw or '미기재'}

K-POP 아이돌 공항 패션 스타일 참고:
- BTS RM: 클린한 오버핏, 모노톤, 고급 스트리트 믹스 (Wooyoungmi, Maison Margiela)
- BTS 뷔: 레이어드 룩, 럭셔리+스트릿 믹스 (Celine, Dior)
- BLACKPINK 제니: 여성스러운 엣지, 하이엔드+캐주얼 믹스 (Chanel, Ader Error)
- aespa 카리나: 미래지향적 미니멀, 테크웨어 요소 (IISE, Off-white)
- EXO 카이: 클래식 올블랙, 타이트한 실루엣 (Gucci)
- 뉴진스: Y2K, 캐주얼, 학생룩 (MUSINSA Standard, Carhartt)
- 공통점: 편안하면서도 스타일리시, 브랜드 로고 포인트, 오버핏 또는 슬림 믹스

아래 JSON 형식으로만 답하세요 (한국어로):
{{
  "idol_name": "참고할 아이돌 이름 (예: BTS RM, aespa 카리나)",
  "idol_style_ref": "이 사용자에게 어울리는 아이돌 공항 스타일 설명 (2-3문장, 구체적으로)",
  "korean_brands": [
    {{
      "brand": "브랜드명 (실제 한국 브랜드)",
      "product_name": "구체적 상품명",
      "product_description": "상품 스타일 설명 (2문장, 왜 이 사람에게 어울리는지)",
      "price_krw": 가격(숫자만, 원화),
      "style_tags": ["태그1", "태그2", "태그3"],
      "product_type": "상의/아우터/바지/신발/가방/액세서리 중 하나",
      "image_prompt": "white background, full product shot, Korean fashion item, {product_type}, professional clothing photography, no model"
    }}
  ],
  "other_brands": [
    {{
      "brand": "브랜드명 (해외 브랜드)",
      "product_name": "상품명",
      "product_description": "상품 설명 (2문장)",
      "price_krw": 가격(숫자만),
      "style_tags": ["태그1", "태그2"],
      "product_type": "상의/아우터/바지/신발",
      "image_prompt": "white background, full product shot, fashion item, professional product photography"
    }}
  ]
}}

추천 규칙:
- korean_brands: 3개 추천. Andersson Bell, IISE, MMMG, Wooyoungmi, Graphpaper Korea,
  무신사 스탠다드, Ader Error, THISISNEVERTHAT, COVERNAT, LEESLE, 4Dimension 등에서 선택
- other_brands: 2개 추천. 해외 브랜드 (아이돌이 실제 착용한 브랜드 우선)
- 가격은 사용자 예산({req.budget_krw})에 맞게 조정
- 체형({req.body_type})과 키({req.height}cm)를 고려한 핏 추천
"""

    try:
        resp = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=2000,
        )
        data = json.loads(resp.choices[0].message.content)
        return data
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI 응답 파싱 실패")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI 오류: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. 상품 이미지 생성  (DALL-E 3)
# ═══════════════════════════════════════════════════════════════════════════════

class ImageRequest(BaseModel):
    prompt: str


@app.post("/api/generate-image")
async def generate_image(req: ImageRequest):
    """상품 이미지 AI 생성 (DALL-E 3, 흰 배경 제품 사진)"""
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY 환경변수를 설정해주세요.")

    full_prompt = (
        f"Korean fashion brand product, white clean background, {req.prompt}, "
        "professional e-commerce product photography, high resolution, "
        "no text, no watermark, no model, just the clothing item"
    )

    try:
        resp = await openai_client.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return {"image_url": resp.data[0].url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 생성 실패: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Stripe 결제 (JPY, 일본 결제수단)
# ═══════════════════════════════════════════════════════════════════════════════

class CheckoutRequest(BaseModel):
    product_name: str
    brand: str
    price_jpy: int           # 엔화 금액 (정수)
    image_url: Optional[str] = None
    email: str = ""
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


@app.post("/api/checkout")
async def create_checkout(req: CheckoutRequest):
    """
    Stripe Checkout 세션 생성 (JPY, 일본 결제수단)
    지원: 카드 (Visa/Mastercard/JCB) + コンビニ決済
    ※ Stripe 계정에서 konbini 결제수단을 활성화해야 합니다.
    """
    if not stripe.api_key:
        raise HTTPException(status_code=400, detail="STRIPE_SECRET_KEY 환경변수를 설정해주세요.")

    if req.price_jpy < 120:
        raise HTTPException(status_code=400, detail="Stripe JPY 최소 결제 금액은 ¥120입니다.")

    encoded_email = req.email.replace("@", "%40")
    success_url = (
        req.success_url
        or f"{FRONTEND_URL}/fashion.html?payment=success"
           f"&email={encoded_email}"
           f"&product={req.product_name}"
           f"&brand={req.brand}"
           f"&price={req.price_jpy}"
    )
    cancel_url = req.cancel_url or f"{FRONTEND_URL}/fashion.html"

    product_data: dict = {"name": f"{req.brand} — {req.product_name}"}
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

    # 일본에서 사용 가능한 결제수단. konbini는 Stripe 계정에서 활성화 필요
    payment_methods = ["card"]
    try:
        # konbini 지원 가능한지 테스트용으로 추가
        payment_methods = ["card", "konbini"]
        session = stripe.checkout.Session.create(
            payment_method_types=payment_methods,
            line_items=[line_item],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            **({"customer_email": req.email} if req.email else {}),
        )
    except stripe.error.InvalidRequestError:
        # konbini 미활성화 시 카드만으로 재시도
        payment_methods = ["card"]
        session = stripe.checkout.Session.create(
            payment_method_types=payment_methods,
            line_items=[line_item],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            **({"customer_email": req.email} if req.email else {}),
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "checkout_url": session.url,
        "session_id": session.id,
        "payment_methods": payment_methods,
    }
