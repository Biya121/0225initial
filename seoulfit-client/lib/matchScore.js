// lib/matchScore.js

// 카테고리 ID → 브랜드 categories 매핑
const CAT_MAP = {
  outer:  ['outer'],
  top:    ['top'],
  bottom: ['bottom'],
  dress:  ['dress'],
  set:    ['set'],
};

// 스타일 ID → 브랜드 style_tags 매핑
const STYLE_TAG_MAP = {
  kkuankku:    ['미니멀', '캐주얼', '내추럴', '베이직'],
  kkukkukku:   ['포멀', '화려', '레이어드', '트렌디'],
  minimal:     ['미니멀', '베이직', '모던', '크린핏', '놈코어'],
  street:      ['스트릿', '오버핏', '그래픽', '젠더리스', 'Y2K'],
  y2k:         ['Y2K', '크롭', '페미닌', '컬러풀', '스트릿'],
  oldmoney:    ['클래식', '테일러드', '럭셔리', '하이엔드', '오피스룩'],
  highteen:    ['청순', '프레피', '캐주얼', '페미닌', '하이틴'],
  normcore:    ['베이직', '미니멀', '데일리', '놈코어'],
  gorpcore:    ['아웃도어', '기능성', '스포티'],
  preppy:      ['프레피', '체크', '클래식', '테일러드'],
  amekaji:     ['아메카지', '데님', '빈티지', '레트로'],
  feminin:     ['페미닌', '플로럴', '크로셰', '로맨틱'],
  chungchung:  ['데님', '캐주얼', 'Y2K'],
  layered:     ['레이어드', '믹스매치', '트렌디'],
  genderless:  ['젠더리스', '유니섹스', '오버핏'],
  cottagecore: ['플로럴', '내추럴', '로맨틱'],
  darkacademia:['트위드', '다크', '클래식'],
  dopamine:    ['컬러풀', '비비드', '트렌디'],
};

// 예산 ID → 가격 범위
const BUDGET_MAP = {
  under5:  { max: 50000 },
  '5to15': { min: 50000,  max: 150000 },
  '15to30':{ min: 150000, max: 300000 },
  over30:  { min: 300000 },
};

export function calcMatchScore(userInput, brand) {
  let score = 0;
  let maxScore = 0;

  const brandCats   = brand.categories  ?? [];
  const brandTags   = brand.style_tags  ?? [];
  const priceMin    = brand.price_range_krw?.min ?? 0;
  const priceMax    = brand.price_range_krw?.max ?? 9999999;

  // ── 1. 카테고리 매칭 (40점) — 가장 중요 ────────────
  if (userInput.categories?.length > 0) {
    maxScore += 40;
    const hitCount = userInput.categories.filter(catId => {
      const mapped = CAT_MAP[catId] ?? [catId];
      return mapped.some(c => brandCats.includes(c));
    }).length;
    score += Math.round((hitCount / userInput.categories.length) * 40);
  }

  // ── 2. 스타일 매칭 (35점) ───────────────────────────
  if (userInput.styles?.length > 0) {
    maxScore += 35;
    let styleHit = 0;
    userInput.styles.forEach(styleId => {
      const relatedTags = STYLE_TAG_MAP[styleId] ?? [];
      const hit = relatedTags.some(tag =>
        brandTags.some(bt => bt.includes(tag) || tag.includes(bt))
      );
      if (hit) styleHit++;
    });
    score += Math.round((styleHit / userInput.styles.length) * 35);
  }

  // ── 3. 예산 매칭 (25점) ─────────────────────────────
  if (userInput.budget) {
    maxScore += 25;
    const b = BUDGET_MAP[userInput.budget];
    if (b) {
      const ok = (!b.min || priceMax >= b.min) && (!b.max || priceMin <= b.max);
      if (ok) score += 25;
    }
  }

  // 선택 없으면 50점 기본
  if (maxScore === 0) return 50;
  return Math.round((score / maxScore) * 100);
}

export function rankBrands(userInput, brands) {
  return brands
    .map(brand => ({
      ...brand,
      matchScore: calcMatchScore(userInput, brand),
    }))
    .sort((a, b) => {
      const aBoost = a.idol_references?.some(r => r.confirmed) ? 5 : 0;
      const bBoost = b.idol_references?.some(r => r.confirmed) ? 5 : 0;
      return (b.matchScore + bBoost) - (a.matchScore + aBoost);
    });
}