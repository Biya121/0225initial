'use client';

import { useState, useEffect, useCallback } from 'react';
import { fashionTerms, getTerm } from '@/lib/fashionTerms';

const LANG_LABELS = { ko: '한국어', ja: '日本語' };
const formatJPY = (krw, rate) => `¥${Math.ceil(krw * rate).toLocaleString('ja-JP')}`;
const formatKRW = (krw) => `${krw.toLocaleString('ko-KR')}원`;

// ── 아이돌 레퍼런스 번역 ───────────────────────────
const IDOL_JA = {
  '카리나 (에스파)': 'カリナ (aespa)',
  '지효 (트와이스)': 'ジヒョ (TWICE)',
  '아이브 멤버들': 'IVEメンバー',
  '뉴진스': 'NewJeans',
  '에스파 멤버들': 'aespaメンバー',
  '르세라핌 멤버들': 'LE SSERAFIMメンバー',
  '블랙핑크 멤버들': 'BLACKPINKメンバー',
  '트와이스 멤버들': 'TWICEメンバー',
  'BTS': 'BTS',
  '다양한 아이돌': '様々なアイドル',
};
const OCCASION_JA = {
  '공항 패션': '空港ファッション',
  '인스타그램 일상': 'インスタグラム日常',
  '공식 화보': '公式グラビア',
  '스타일리스트 픽': 'スタイリスト選定',
  '데일리 착용': 'デイリー着用',
};
const STYLE_TAG_JA = {
  '페미닌':'フェミニン','트렌디':'トレンディ','오피스룩':'オフィスルック','클래식':'クラシック',
  '캐주얼':'カジュアル','미니멀':'ミニマル','베이직':'ベーシック','젠더리스':'ジェンダーレス',
  '모던':'モダン','데일리':'デイリー','아방가르드':'アバンギャルド','아티스틱':'アーティスティック',
  '스트릿':'ストリート','오버핏':'オーバーフィット','하이엔드':'ハイエンド','럭셔리':'ラグジュアリー',
  '테일러드':'テーラード','빈티지':'ヴィンテージ','레트로':'レトロ','스포티':'スポーティ',
  '기능성':'機能性','프렌치':'フレンチ','로맨틱':'ロマンティック','플로럴':'フローラル',
  '하이틴':'ハイティーン','가성비':'コスパ','Y2K':'Y2K','컬러풀':'カラフル','놈코어':'ノームコア',
};

function translateIdolRef(ref, lang) {
  if (lang === 'ko') return ref;
  return {
    ...ref,
    idol: IDOL_JA[ref.idol] ?? ref.idol,
    occasion: OCCASION_JA[ref.occasion] ?? ref.occasion,
  };
}

// ── 커서 ───────────────────────────────────────────
function Cursor() {
  useEffect(() => {
    const cur = document.getElementById('cur');
    const cur2 = document.getElementById('cur2');
    if (!cur || !cur2) return;
    let mx=0,my=0,rx=0,ry=0;
    const onMove = e => { mx=e.clientX; my=e.clientY; cur2.style.left=mx+'px'; cur2.style.top=my+'px'; };
    document.addEventListener('mousemove', onMove);
    let raf;
    const tick = () => { rx+=(mx-rx)*.11; ry+=(my-ry)*.11; cur.style.left=rx+'px'; cur.style.top=ry+'px'; raf=requestAnimationFrame(tick); };
    tick();
    return () => { document.removeEventListener('mousemove', onMove); cancelAnimationFrame(raf); };
  }, []);
  return null;
}

// ── 섹션 라벨 ──────────────────────────────────────
function SectionLabel({ children }) {
  return (
    <div style={{ fontFamily:'var(--f-mono)', fontSize:'.58rem', letterSpacing:'.28em',
      color:'var(--purple)', textTransform:'uppercase', marginBottom:'10px', marginTop:'28px' }}>
      {children}
    </div>
  );
}

// ── 가로 태그 행 ───────────────────────────────────
function TagRow({ items, selected, onToggle, getLabel, getColor, single=false }) {
  return (
    <div style={{ display:'flex', gap:'6px', overflowX:'auto', paddingBottom:'6px', scrollbarWidth:'none' }}>
      {items.map(item => {
        const isActive = single ? selected===item.id : selected.includes(item.id);
        return (
          <button key={item.id} onClick={() => onToggle(item.id)}
            onMouseEnter={() => document.body.classList.add('ch')}
            onMouseLeave={() => document.body.classList.remove('ch')}
            style={{
              flexShrink:0, fontFamily:'var(--f-mono)', fontSize:'.6rem', letterSpacing:'.08em',
              border:`1.5px solid ${isActive ? 'var(--purple)' : 'var(--border)'}`,
              padding:'7px 18px', cursor:'none', whiteSpace:'nowrap',
              color: isActive ? 'var(--black)' : 'rgba(10,10,10,.38)',
              background: isActive ? 'var(--purple-glow)' : 'transparent',
              transition:'all .18s', borderRadius:'2px',
              display:'inline-flex', alignItems:'center', gap:'7px',
            }}>
            {getColor?.(item) && <span style={{ width:'9px', height:'9px', borderRadius:'50%', flexShrink:0, background:getColor(item), border:'1px solid rgba(0,0,0,.12)' }} />}
            {getLabel(item)}
          </button>
        );
      })}
    </div>
  );
}

// ── 브랜드 카드 (3열) ──────────────────────────────
function BrandCard({ brand, rate, lang, onSelect, selected }) {
  const rawRef = brand.idol_references?.[0];
  const idolRef = rawRef ? translateIdolRef(rawRef, lang) : null;
  const priceMin = brand.price_range_krw?.min;
  const priceMax = brand.price_range_krw?.max;
  const displayName = lang==='ja' ? (brand.name_ja ?? brand.name_en ?? brand.name_ko) : brand.name_ko;
  const tags = brand.style_tags?.slice(0,3).map(t => lang==='ja' ? (STYLE_TAG_JA[t]??t) : t);

  return (
    <div onClick={() => onSelect(brand)}
      onMouseEnter={() => document.body.classList.add('ch')}
      onMouseLeave={() => document.body.classList.remove('ch')}
      style={{
        border:`1.5px solid ${selected ? 'var(--purple)' : 'var(--border)'}`,
        padding:'20px 18px', cursor:'none', transition:'all .2s',
        background: selected ? 'var(--purple-glow)' : '#fff',
        position:'relative', overflow:'hidden',
        display:'flex', flexDirection:'column', gap:'8px',
      }}>
      <div style={{ position:'absolute', left:0, top:0, right:0, height:'3px', background:'var(--purple)',
        transform: selected ? 'scaleX(1)' : 'scaleX(0)', transition:'transform .25s', transformOrigin:'left' }} />

      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
        <div>
          <div style={{ fontFamily:'var(--f-disp)', fontSize:'1.25rem', letterSpacing:'.04em', lineHeight:1.1 }}>{displayName}</div>
          {lang==='ja' && brand.name_ko!==displayName && (
            <div style={{ fontFamily:'var(--f-mono)', fontSize:'.44rem', color:'rgba(80,68,175,.5)', marginTop:'2px' }}>{brand.name_ko}</div>
          )}
        </div>
        <div style={{ textAlign:'right', flexShrink:0, marginLeft:'8px' }}>
          <div style={{ fontFamily:'var(--f-disp)', fontSize:'1.8rem', color:'var(--purple)', lineHeight:1 }}>{brand.matchScore ?? '—'}</div>
          <div style={{ fontFamily:'var(--f-mono)', fontSize:'.38rem', letterSpacing:'.12em', color:'rgba(80,68,175,.4)' }}>MATCH</div>
        </div>
      </div>

      <div style={{ display:'flex', gap:'4px', flexWrap:'wrap' }}>
        {tags?.map(tag => <span key={tag} style={{ fontFamily:'var(--f-mono)', fontSize:'.44rem', color:'rgba(10,10,10,.3)', border:'1px solid var(--border)', padding:'2px 7px' }}>{tag}</span>)}
      </div>

      {idolRef && (
        <div style={{ fontFamily:'var(--f-mono)', fontSize:'.5rem', color: idolRef.confirmed ? 'var(--purple)' : 'rgba(80,68,175,.45)', display:'flex', alignItems:'center', gap:'5px' }}>
          <span>{idolRef.confirmed ? '✦' : '◇'}</span>
          <span style={{ overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{idolRef.idol} — {idolRef.item}</span>
        </div>
      )}
      {idolRef?.occasion && (
        <div style={{ fontFamily:'var(--f-mono)', fontSize:'.44rem', color:'rgba(80,68,175,.4)' }}>{idolRef.occasion}</div>
      )}
      {priceMin && (
        <div style={{ fontFamily:'var(--f-mono)', fontSize:'.5rem', color:'rgba(10,10,10,.35)', marginTop:'auto' }}>
          {lang==='ja' ? `${formatJPY(priceMin,rate)} 〜 ${formatJPY(priceMax,rate)}` : `${formatKRW(priceMin)} — ${formatKRW(priceMax)}`}
        </div>
      )}
      {selected && (
        <div style={{ fontFamily:'var(--f-mono)', fontSize:'.48rem', color:'var(--purple)', textAlign:'center', marginTop:'6px', borderTop:'1px solid var(--border)', paddingTop:'8px' }}>
          ↓ {lang==='ja' ? 'カタログを見る' : '카탈로그 보기'}
        </div>
      )}
    </div>
  );
}

// ── 상품 카드 ──────────────────────────────────────
function ProductCard({ product, rate, lang, onClick }) {
  const COLORS = ['#e8e4f4','#f4e8f0','#e4eef8','#f0f4e4','#f8f0e4','#e4f4f0'];
  const bg = COLORS[Math.abs((product.id?.charCodeAt(8)??0)) % COLORS.length];
  const [imgOk, setImgOk] = useState(true);

  return (
    <div onClick={onClick}
      onMouseEnter={() => document.body.classList.add('ch')}
      onMouseLeave={() => document.body.classList.remove('ch')}
      style={{ border:'1.5px solid var(--border)', cursor:'none', transition:'border-color .2s', overflow:'hidden', background:'#fff', display:'flex', flexDirection:'column' }}>
      <div style={{ width:'100%', paddingTop:'120%', position:'relative', background:bg }}>
        {product.image_url && imgOk ? (
          <img
            src={`/api/img-proxy?url=${encodeURIComponent(product.image_url)}`}
            alt={product.name}
            onError={() => setImgOk(false)}
            style={{ position:'absolute', inset:0, width:'100%', height:'100%', objectFit:'cover' }}
          />
        ) : (
          <div style={{ position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center', flexDirection:'column', gap:'8px' }}>
            <div style={{ fontFamily:'var(--f-disp)', fontSize:'2.4rem', color:'rgba(80,68,175,.2)' }}>✦</div>
          </div>
        )}
      </div>
      <div style={{ padding:'12px' }}>
        <div style={{ fontFamily:'var(--f-mono)', fontSize:'.5rem', letterSpacing:'.08em', color:'var(--purple)', marginBottom:'4px' }}>{product.brand}</div>
        <div style={{ fontFamily:'var(--f-body)', fontSize:'.74rem', lineHeight:1.4, marginBottom:'8px',
          display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical', overflow:'hidden' }}>
          {product.name}
        </div>
        <div style={{ fontFamily:'var(--f-mono)', fontSize:'.62rem', fontWeight:500 }}>
          {product.price_krw > 0
            ? (lang==='ja' ? formatJPY(product.price_krw,rate) : formatKRW(product.price_krw))
            : (lang==='ja' ? '価格未定' : '가격 미정')}
        </div>
      </div>
    </div>
  );
}

// ── 카탈로그 가로 스크롤 ───────────────────────────
function ProductCatalog({ brand, products, rate, lang, onProductClick, crawling }) {
  if (!brand) return null;
  const L = (ko,ja) => lang==='ja' ? ja : ko;
  const displayName = lang==='ja' ? (brand.name_ja ?? brand.name_en ?? brand.name_ko) : brand.name_ko;

  return (
    <div style={{ marginTop:'48px', paddingTop:'40px', borderTop:'1px solid var(--border)' }}>
      <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:'20px' }}>
        <div style={{ display:'flex', alignItems:'baseline', gap:'12px' }}>
          <span style={{ fontFamily:'var(--f-disp)', fontSize:'1.8rem', letterSpacing:'.04em' }}>{displayName}</span>
          <span style={{ fontFamily:'var(--f-mono)', fontSize:'.55rem', letterSpacing:'.15em', color:'var(--purple)' }}>CATALOG</span>
          {crawling && <span style={{ fontFamily:'var(--f-mono)', fontSize:'.44rem', color:'var(--purple-mid)' }}>{L('크롤링 중...','取得中...')}</span>}
        </div>
        <span style={{ fontFamily:'var(--f-mono)', fontSize:'.5rem', color:'rgba(80,68,175,.35)' }}>{products.length} ITEMS</span>
      </div>

      {products.length === 0 && !crawling ? (
        <div style={{ padding:'40px 0', textAlign:'center', fontFamily:'var(--f-mono)', fontSize:'.6rem', color:'rgba(80,68,175,.3)' }}>
          {L('상품을 불러오는 중입니다...','商品を読み込んでいます...')}
        </div>
      ) : (
        <div style={{ display:'flex', gap:'16px', overflowX:'auto', paddingBottom:'16px', scrollbarWidth:'thin', scrollbarColor:'var(--border) transparent' }}>
          {products.map(product => (
            <div key={product.id} style={{ flexShrink:0, width:'200px' }}>
              <ProductCard product={product} rate={rate} lang={lang} onClick={() => onProductClick(product)} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── 상품 상세 팝업 ─────────────────────────────────
function ProductDetail({ product, rate, lang, onClose, onAddCart }) {
  const [detailData, setDetailData] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [currentImg, setCurrentImg] = useState(0);
  const L = (ko,ja) => lang==='ja' ? ja : ko;

  useEffect(() => {
    if (!product?.goods_no) return;
    let cancelled = false;
    setLoadingDetail(true);
    setDetailData(null);
    setCurrentImg(0);

    fetch(`/api/product-detail?goodsNo=${product.goods_no}`)
      .then(r => r.json())
      .then(d => { if (!cancelled) setDetailData(d); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoadingDetail(false); });

    return () => { cancelled = true; };
  }, [product?.goods_no]);

  const allImages = [
    product.image_url,
    ...(detailData?.extra_images ?? []),
  ].filter(Boolean);

  const info = detailData?.info ?? {};

  return (
    <div style={{ position:'fixed', inset:0, zIndex:3000, background:'rgba(10,10,10,.65)', backdropFilter:'blur(10px)', display:'flex', alignItems:'center', justifyContent:'center', padding:'20px' }}
      onClick={onClose}>
      <div style={{ background:'var(--bg)', maxWidth:'680px', width:'100%', maxHeight:'90vh', overflowY:'auto',
        border:'1.5px solid var(--border)', padding:'40px', position:'relative' }}
        onClick={e=>e.stopPropagation()}>

        <button onClick={onClose}
          onMouseEnter={() => document.body.classList.add('ch')}
          onMouseLeave={() => document.body.classList.remove('ch')}
          style={{ position:'absolute', top:'20px', right:'20px', background:'none', border:'none', cursor:'none',
            fontFamily:'var(--f-mono)', fontSize:'.58rem', letterSpacing:'.15em', color:'rgba(10,10,10,.35)' }}>
          CLOSE ✕
        </button>

        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'32px', alignItems:'start' }}>
          {/* 이미지 영역 */}
          <div>
            {/* 메인 이미지 */}
            <div style={{ background:'var(--purple-ghost)', paddingTop:'125%', position:'relative', marginBottom:'10px' }}>
              {allImages[currentImg] ? (
                <img src={`/api/img-proxy?url=${encodeURIComponent(allImages[currentImg])}`}
                  alt={product.name}
                  style={{ position:'absolute', inset:0, width:'100%', height:'100%', objectFit:'cover' }} />
              ) : (
                <div style={{ position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center' }}>
                  <span style={{ fontFamily:'var(--f-disp)', fontSize:'3rem', color:'rgba(80,68,175,.2)' }}>✦</span>
                </div>
              )}
            </div>

            {/* 썸네일 스트립 */}
            {allImages.length > 1 && (
              <div style={{ display:'flex', gap:'6px', overflowX:'auto', scrollbarWidth:'none' }}>
                {allImages.map((img, i) => (
                  <div key={i} onClick={() => setCurrentImg(i)}
                    style={{ flexShrink:0, width:'52px', height:'52px', border:`1.5px solid ${currentImg===i ? 'var(--purple)' : 'var(--border)'}`,
                      cursor:'pointer', overflow:'hidden', background:'var(--purple-ghost)' }}>
                    <img src={`/api/img-proxy?url=${encodeURIComponent(img)}`}
                      style={{ width:'100%', height:'100%', objectFit:'cover' }} />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 상품 정보 */}
          <div>
            <div style={{ fontFamily:'var(--f-mono)', fontSize:'.55rem', letterSpacing:'.15em', color:'var(--purple)', marginBottom:'8px' }}>{product.brand}</div>
            <div style={{ fontFamily:'var(--f-disp)', fontSize:'1.4rem', letterSpacing:'.02em', lineHeight:1.2, marginBottom:'16px' }}>{product.name}</div>

            {/* 가격 */}
            <div style={{ fontFamily:'var(--f-disp)', fontSize:'2rem', color:'var(--purple)', marginBottom:'4px' }}>
              {product.price_krw > 0 ? (lang==='ja' ? formatJPY(product.price_krw,rate) : formatKRW(product.price_krw)) : '—'}
            </div>
            {lang==='ja' && product.price_krw > 0 && (
              <div style={{ fontFamily:'var(--f-mono)', fontSize:'.48rem', color:'rgba(80,68,175,.4)', marginBottom:'20px' }}>({formatKRW(product.price_krw)})</div>
            )}

            {/* 상품 정보 테이블 */}
            {(info.material || info.fit || info.color || info.size || loadingDetail) && (
              <div style={{ border:'1px solid var(--border)', padding:'14px', marginBottom:'20px', marginTop:'16px' }}>
                {loadingDetail ? (
                  <div style={{ fontFamily:'var(--f-mono)', fontSize:'.5rem', color:'rgba(80,68,175,.4)' }}>{L('상세 정보 로딩 중...','詳細情報読み込み中...')}</div>
                ) : (
                  [
                    ['소재', 'MATERIAL', info.material],
                    ['핏',   'FIT',      info.fit],
                    ['색상', 'COLOR',    info.color],
                    ['사이즈', 'SIZE',   info.size],
                  ].filter(([,,v]) => v).map(([ko, en, val]) => (
                    <div key={en} style={{ display:'flex', gap:'12px', marginBottom:'7px', alignItems:'flex-start' }}>
                      <div style={{ fontFamily:'var(--f-mono)', fontSize:'.44rem', letterSpacing:'.1em', color:'var(--purple)', flexShrink:0, minWidth:'52px' }}>{en}</div>
                      <div style={{ fontFamily:'var(--f-body)', fontSize:'.65rem', color:'rgba(10,10,10,.7)', lineHeight:1.5 }}>{val}</div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* 버튼 */}
            <button onClick={() => onAddCart(product)}
              onMouseEnter={() => document.body.classList.add('ch')}
              onMouseLeave={() => document.body.classList.remove('ch')}
              style={{ width:'100%', padding:'13px', fontFamily:'var(--f-disp)', fontSize:'.95rem', letterSpacing:'.2em',
                color:'#fff', background:'var(--purple)', border:'none', cursor:'none', marginBottom:'8px' }}>
              {L('장바구니 담기','カートに入れる')}
            </button>
            <a href={product.product_url} target="_blank" rel="noopener noreferrer"
              onMouseEnter={() => document.body.classList.add('ch')}
              onMouseLeave={() => document.body.classList.remove('ch')}
              style={{ display:'block', padding:'11px', fontFamily:'var(--f-mono)', fontSize:'.56rem', letterSpacing:'.15em',
                color:'var(--purple)', border:'1.5px solid var(--border)', textDecoration:'none', textAlign:'center', cursor:'none' }}>
              {L('무신사에서 보기 →','MUSINSAで見る →')}
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── 장바구니 패널 ──────────────────────────────────
function CartPanel({ cart, rate, lang, onRemove, onCheckout, onClose, checkoutLoading }) {
  const total = cart.reduce((s,p) => s+(p.price_krw||0), 0);
  const L = (ko,ja) => lang==='ja' ? ja : ko;
  return (
    <div style={{ position:'fixed', top:0, right:0, bottom:0, width:'340px', background:'var(--bg)', borderLeft:'1.5px solid var(--border)', zIndex:2000, display:'flex', flexDirection:'column' }}>
      <div style={{ padding:'22px', borderBottom:'1px solid var(--border)', display:'flex', justifyContent:'space-between', alignItems:'center' }}>
        <span style={{ fontFamily:'var(--f-disp)', fontSize:'1.3rem' }}>{L('장바구니','カート')}</span>
        <button onClick={onClose}
          onMouseEnter={() => document.body.classList.add('ch')}
          onMouseLeave={() => document.body.classList.remove('ch')}
          style={{ background:'none', border:'none', cursor:'none', fontFamily:'var(--f-mono)', fontSize:'.58rem', color:'rgba(10,10,10,.35)' }}>✕</button>
      </div>
      <div style={{ flex:1, overflow:'auto', padding:'14px' }}>
        {cart.length===0 ? (
          <div style={{ textAlign:'center', padding:'60px 0', fontFamily:'var(--f-mono)', fontSize:'.58rem', color:'rgba(80,68,175,.35)' }}>
            {L('장바구니가 비었어요','カートが空です')}
          </div>
        ) : cart.map((item,i) => (
          <div key={i} style={{ display:'flex', gap:'10px', padding:'10px 0', borderBottom:'1px solid var(--border)' }}>
            <div style={{ width:'54px', height:'72px', flexShrink:0, background:'var(--purple-ghost)', overflow:'hidden' }}>
              {item.image_url && <img src={`/api/img-proxy?url=${encodeURIComponent(item.image_url)}`} style={{ width:'100%', height:'100%', objectFit:'cover' }} />}
            </div>
            <div style={{ flex:1 }}>
              <div style={{ fontFamily:'var(--f-body)', fontSize:'.72rem', lineHeight:1.4, marginBottom:'4px' }}>{item.name}</div>
              <div style={{ fontFamily:'var(--f-mono)', fontSize:'.58rem', color:'var(--purple)' }}>
                {item.price_krw > 0 ? (lang==='ja' ? formatJPY(item.price_krw,rate) : formatKRW(item.price_krw)) : '—'}
              </div>
            </div>
            <button onClick={() => onRemove(i)}
              onMouseEnter={() => document.body.classList.add('ch')}
              onMouseLeave={() => document.body.classList.remove('ch')}
              style={{ background:'none', border:'none', cursor:'none', color:'rgba(10,10,10,.25)', fontSize:'.7rem' }}>✕</button>
          </div>
        ))}
      </div>
      {cart.length>0 && (
        <div style={{ padding:'18px', borderTop:'1px solid var(--border)' }}>
          <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'6px' }}>
            <span style={{ fontFamily:'var(--f-mono)', fontSize:'.6rem' }}>{L('합계','合計')}</span>
            <span style={{ fontFamily:'var(--f-disp)', fontSize:'1.3rem', color:'var(--purple)' }}>
              {lang==='ja' ? formatJPY(total,rate) : formatKRW(total)}
            </span>
          </div>
          {lang==='ja' && <div style={{ fontFamily:'var(--f-mono)', fontSize:'.44rem', color:'rgba(80,68,175,.4)', textAlign:'right', marginBottom:'14px' }}>({formatKRW(total)})</div>}
          <button onClick={onCheckout} disabled={checkoutLoading}
            onMouseEnter={() => document.body.classList.add('ch')}
            onMouseLeave={() => document.body.classList.remove('ch')}
            style={{ width:'100%', padding:'13px', fontFamily:'var(--f-disp)', fontSize:'.95rem', letterSpacing:'.2em',
              color:'#fff', background: checkoutLoading ? 'var(--purple-mid)' : 'var(--purple)', border:'none', cursor:'none' }}>
            {checkoutLoading ? L('처리 중...','処理中...') : L('Stripe로 결제하기','Stripeで決済する')}
          </button>
          <div style={{ fontFamily:'var(--f-mono)', fontSize:'.44rem', color:'rgba(80,68,175,.35)', textAlign:'center', marginTop:'8px' }}>
            {L('VISA · Mastercard · PayPay · 콘비니 결제','VISA · Mastercard · PayPay · コンビニ払い')}
          </div>
        </div>
      )}
    </div>
  );
}

// ── 메인 ───────────────────────────────────────────
export default function FashionPage() {
  const [lang, setLang] = useState('ko');
  const [rate, setRate] = useState(0.11);
  const [selStyles, setSelStyles] = useState([]);
  const [selColors, setSelColors] = useState([]);
  const [selCategories, setSelCategories] = useState([]);
  const [selBodyType, setSelBodyType] = useState(null);
  const [selBudget, setSelBudget] = useState(null);
  const [selFits, setSelFits] = useState([]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [selectedBrand, setSelectedBrand] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [crawling, setCrawling] = useState(false);
  const [cart, setCart] = useState([]);
  const [cartOpen, setCartOpen] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);

  const bodyTypes = [
    { id:'wave',     ko:'웨이브형',     ja:'ウェーブ型' },
    { id:'straight', ko:'스트레이트형', ja:'ストレート型' },
    { id:'neutral',  ko:'뉴트럴형',     ja:'ナチュラル型' },
  ];

  useEffect(() => {
    fetch('/api/exchange').then(r=>r.json()).then(d=>{ if(d.rate) setRate(d.rate); }).catch(()=>{});
  }, []);

  const toggleMulti = (list, setList, id) =>
    setList(prev => prev.includes(id) ? prev.filter(x=>x!==id) : [...prev, id]);

  const handleRecommend = useCallback(async () => {
    setLoading(true); setResults([]); setSelectedBrand(null);
    try {
      const res = await fetch('/api/recommend', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ styles:selStyles, colors:selColors, categories:selCategories, budget:selBudget, bodyType:selBodyType, fits:selFits }),
      });
      const data = await res.json();
      setResults(data.results ?? []);
    } catch(err) { console.error(err); }
    finally { setLoading(false); }
  }, [selStyles, selColors, selCategories, selBudget, selBodyType, selFits]);

  const handleSelectBrand = useCallback(async (brand) => {
    if (selectedBrand?.id === brand.id) { setSelectedBrand(null); return; }
    setSelectedBrand(brand);
    const existing = results.find(b=>b.id===brand.id);
    if (existing?.products?.length > 0) return;
    setCrawling(true);
    try {
      const res = await fetch('/api/crawl', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ brands:[{ id:brand.id, name_ko:brand.name_ko, musinsa_keyword:brand.musinsa_keyword, musinsa_url:brand.musinsa_url }] }),
      });
      const data = await res.json();
      const crawledProducts = data.results?.[brand.id] ?? [];
      setResults(prev => prev.map(b => b.id===brand.id ? {...b, products:crawledProducts} : b));
    } catch(err) { console.error('[crawl]', err); }
    finally { setCrawling(false); }
  }, [selectedBrand, results]);

  const addCart = (product) => { setCart(p=>[...p, product]); setSelectedProduct(null); };
  const removeCart = (i) => setCart(p=>p.filter((_,idx)=>idx!==i));

  const handleCheckout = async () => {
    setCheckoutLoading(true);
    try {
      const res = await fetch('/api/checkout', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ items:cart, currency:'jpy', rate }),
      });
      const { url } = await res.json();
      if (url) window.location.href = url;
    } catch(err) { console.error(err); }
    finally { setCheckoutLoading(false); }
  };

  const L = (ko,ja) => lang==='ja' ? ja : ko;

  return (
    <>
      <div id="cur" /><div id="cur2" />
      <Cursor />
      <div className="noise" />

      {/* 헤더 */}
      <header style={{ position:'fixed', top:0, left:0, right:0, zIndex:400, height:'60px',
        display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 48px',
        background:'rgba(240,238,248,.94)', backdropFilter:'blur(14px)', borderBottom:'1px solid var(--border)' }}>
        <a href="/"
          onMouseEnter={() => document.body.classList.add('ch')}
          onMouseLeave={() => document.body.classList.remove('ch')}
          style={{ fontFamily:'var(--f-disp)', fontSize:'1.7rem', letterSpacing:'.22em', color:'var(--black)', textDecoration:'none', fontWeight:300 }}>
          SEOUL<em style={{ color:'var(--purple)', fontStyle:'italic' }}>FIT</em>
        </a>
        <nav style={{ display:'flex', gap:'36px' }}>
          {[{label:L('AI 큐레이터','AIキュレーター'),href:'/fashion'},{label:L('AI 포토부스','AIフォトブース'),href:'/photobooth'},{label:L('픽셀 서울','ピクセルソウル'),href:'/game'}].map(item=>(
            <a key={item.href} href={item.href}
              onMouseEnter={() => document.body.classList.add('ch')}
              onMouseLeave={() => document.body.classList.remove('ch')}
              style={{ fontFamily:'var(--f-mono)', fontSize:'.72rem', letterSpacing:'.16em',
                color:item.href==='/fashion' ? 'var(--purple)' : 'rgba(10,10,10,.4)',
                textDecoration:'none', textTransform:'uppercase',
                borderBottom:item.href==='/fashion' ? '1.5px solid var(--purple)' : 'none', paddingBottom:'2px' }}>
              {item.label}
            </a>
          ))}
        </nav>
        <div style={{ display:'flex', gap:'12px', alignItems:'center' }}>
          <div style={{ display:'flex', border:'1.5px solid var(--border)' }}>
            {['ko','ja'].map(l=>(
              <button key={l} onClick={() => setLang(l)}
                onMouseEnter={() => document.body.classList.add('ch')}
                onMouseLeave={() => document.body.classList.remove('ch')}
                style={{ fontFamily:'var(--f-mono)', fontSize:'.55rem', padding:'5px 13px', cursor:'none', border:'none',
                  background:lang===l ? 'var(--purple)' : 'transparent',
                  color:lang===l ? '#fff' : 'rgba(10,10,10,.35)', transition:'all .2s' }}>
                {LANG_LABELS[l]}
              </button>
            ))}
          </div>
          <button onClick={() => setCartOpen(true)}
            onMouseEnter={() => document.body.classList.add('ch')}
            onMouseLeave={() => document.body.classList.remove('ch')}
            style={{ fontFamily:'var(--f-mono)', fontSize:'.58rem', background:'none', border:'1.5px solid var(--border)',
              padding:'5px 14px', cursor:'none', color:'var(--black)', display:'flex', alignItems:'center', gap:'7px' }}>
            {L('장바구니','カート')}
            {cart.length>0 && <span style={{ background:'var(--purple)', color:'#fff', borderRadius:'50%', width:'16px', height:'16px', fontSize:'.46rem', display:'flex', alignItems:'center', justifyContent:'center' }}>{cart.length}</span>}
          </button>
        </div>
      </header>

      {/* 히어로 */}
      <div style={{ padding:'100px 10vw 36px' }}>
        <div style={{ fontFamily:'var(--f-mono)', fontSize:'.56rem', letterSpacing:'.3em', color:'var(--purple)', marginBottom:'14px' }}>CARD 01 — AI FASHION CURATOR</div>
        <h1 style={{ fontFamily:'var(--f-disp)', fontSize:'clamp(3rem,6vw,7rem)', lineHeight:.92, fontWeight:300, marginBottom:'16px' }}>
          {L('AI 패션','AIファッション')}<br/>
          <em style={{ color:'var(--purple)', fontStyle:'italic' }}>{L('큐레이터','キュレーター')}</em>
        </h1>
        <p style={{ fontFamily:'var(--f-mono)', fontSize:'.64rem', lineHeight:2, color:'rgba(10,10,10,.42)', maxWidth:'380px' }}>
          {L('체형, 스타일, 예산을 선택하면 AI가 K-POP 아이돌이 실제 착용한 한국 브랜드를 추천합니다.','体型・スタイル・予算を選ぶとAIがK-POPアイドル着用の韓国ブランドを提案します。')}
        </p>
      </div>

      <div style={{ height:'1px', background:'var(--border)', margin:'0 10vw' }} />

      {/* 선택 폼 */}
      <div style={{ padding:'36px 10vw 0' }}>
        <SectionLabel>{L('체형 타입','ボディタイプ')}</SectionLabel>
        <TagRow items={bodyTypes} selected={selBodyType} single onToggle={id=>setSelBodyType(p=>p===id?null:id)} getLabel={item=>getTerm(item,lang)} />
        <SectionLabel>{L('옷 카테고리','アイテム')}</SectionLabel>
        <TagRow items={fashionTerms.categories} selected={selCategories} onToggle={id=>toggleMulti(selCategories,setSelCategories,id)} getLabel={item=>getTerm(item,lang)} />
        <SectionLabel>{L('스타일','スタイル')}</SectionLabel>
        <TagRow items={fashionTerms.styles} selected={selStyles} onToggle={id=>toggleMulti(selStyles,setSelStyles,id)} getLabel={item=>getTerm(item,lang)} />
        <SectionLabel>{L('핏 / 실루엣','フィット')}</SectionLabel>
        <TagRow items={fashionTerms.fits} selected={selFits} onToggle={id=>toggleMulti(selFits,setSelFits,id)} getLabel={item=>getTerm(item,lang)} />
        <SectionLabel>{L('색상','カラー')}</SectionLabel>
        <TagRow items={fashionTerms.colors} selected={selColors} onToggle={id=>toggleMulti(selColors,setSelColors,id)} getLabel={item=>getTerm(item,lang)} getColor={item=>item.hex} />
        <SectionLabel>{L('예산','予算')}</SectionLabel>
        <TagRow items={fashionTerms.budgets} selected={selBudget} single onToggle={id=>setSelBudget(p=>p===id?null:id)} getLabel={item=>getTerm(item,lang)} />

        <button onClick={handleRecommend} disabled={loading}
          onMouseEnter={() => document.body.classList.add('ch')}
          onMouseLeave={() => document.body.classList.remove('ch')}
          style={{ marginTop:'28px', marginBottom:'48px', padding:'15px 60px', fontFamily:'var(--f-disp)',
            fontSize:'1rem', letterSpacing:'.28em', color:'#fff',
            background:loading ? 'var(--purple-mid)' : 'var(--purple)', border:'none', cursor:'none', transition:'background .2s' }}>
          {loading ? L('AI 분석 중...','AI分析中...') : L('AI 추천 실행하기','AIで推薦する')}
        </button>
      </div>

      <div style={{ height:'1px', background:'var(--border)', margin:'0 10vw' }} />

      {/* 결과 */}
      <div style={{ padding:'48px 10vw 80px' }}>
        <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:'28px' }}>
          <div style={{ fontFamily:'var(--f-disp)', fontSize:'1.8rem', fontWeight:300 }}>{L('추천 브랜드','おすすめブランド')}</div>
          {results.length>0 && <div style={{ fontFamily:'var(--f-mono)', fontSize:'.52rem', color:'rgba(80,68,175,.35)' }}>{results.length} BRANDS</div>}
        </div>

        {results.length===0 && !loading && (
          <div style={{ padding:'80px 0', textAlign:'center', fontFamily:'var(--f-mono)', fontSize:'.62rem', color:'rgba(80,68,175,.3)' }}>
            <div style={{ fontFamily:'var(--f-disp)', fontSize:'3rem', marginBottom:'14px' }}>✦</div>
            {L('위에서 스타일을 선택하고 AI 추천을 실행해 보세요.','スタイルを選択してAI推薦を実行してください。')}
          </div>
        )}

        {results.length>0 && (
          <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:'16px' }}>
            {results.map(brand=>(
              <BrandCard key={brand.id} brand={brand} rate={rate} lang={lang}
                selected={selectedBrand?.id===brand.id} onSelect={handleSelectBrand} />
            ))}
          </div>
        )}

        {selectedBrand && (
          <ProductCatalog
            brand={selectedBrand}
            products={results.find(b=>b.id===selectedBrand.id)?.products ?? []}
            rate={rate} lang={lang} crawling={crawling}
            onProductClick={setSelectedProduct} />
        )}
      </div>

      {selectedProduct && (
        <ProductDetail product={selectedProduct} rate={rate} lang={lang}
          onClose={() => setSelectedProduct(null)} onAddCart={addCart} />
      )}
      {cartOpen && (
        <CartPanel cart={cart} rate={rate} lang={lang}
          onRemove={removeCart} onCheckout={handleCheckout}
          onClose={() => setCartOpen(false)} checkoutLoading={checkoutLoading} />
      )}
    </>
  );
}