// app/api/checkout/route.js

import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

export async function POST(request) {
  try {
    const { items, currency = 'jpy', rate = 0.11 } = await request.json();

    if (!items?.length) {
      return Response.json({ error: '상품 없음' }, { status: 400 });
    }

    const line_items = items.map(item => ({
      price_data: {
        currency,
        product_data: {
          name: item.name,
          description: item.brand,
          ...(item.image_url ? { images: [item.image_url] } : {}),
        },
        // JPY는 소수점 없음
        unit_amount: Math.ceil(item.price_krw * rate),
      },
      quantity: 1,
    }));

    const session = await stripe.checkout.sessions.create({
      payment_method_types: [
        'card',
        'paypay',       // 일본 1위 간편결제
        'konbini',      // 편의점 결제
      ],
      line_items,
      mode: 'payment',
      success_url: `${process.env.NEXT_PUBLIC_BASE_URL}/fashion?success=1`,
      cancel_url: `${process.env.NEXT_PUBLIC_BASE_URL}/fashion?cancelled=1`,
      metadata: {
        source: 'seoulfit',
      },
    });

    return Response.json({ url: session.url });
  } catch (err) {
    console.error('[checkout]', err);
    return Response.json({ error: err.message }, { status: 500 });
  }
}
