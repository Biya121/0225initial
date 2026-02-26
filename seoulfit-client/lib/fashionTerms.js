// lib/fashionTerms.js
// 한국 트렌디 패션 용어 KO → JA 번역 테이블
// 꾸안꾸, 꾸꾸꾸 등 직역 불가 용어 의역 포함

export const fashionTerms = {
  // ── 스타일 용어 ──────────────────────────────
  styles: [
    {
      id: 'kkuankku',
      ko: '꾸안꾸',
      ja: '手抜き風オシャレ',
      ja_desc: '頑張ってないように見えて実はオシャレ',
      en: 'Effortless chic',
      tags: ['미니멀', '캐주얼', '내추럴'],
    },
    {
      id: 'kkukkukku',
      ko: '꾸꾸꾸',
      ja: 'フル着飾りスタイル',
      ja_desc: 'とことん着飾ったスタイル',
      en: 'Fully dressed up',
      tags: ['포멀', '화려', '레이어드'],
    },
    {
      id: 'minimal',
      ko: '미니멀',
      ja: 'ミニマル',
      ja_desc: 'シンプルで洗練されたスタイル',
      en: 'Minimal',
      tags: ['베이직', '모노톤', '클린'],
    },
    {
      id: 'street',
      ko: '스트릿',
      ja: 'ストリート',
      ja_desc: 'ストリートカルチャーに影響されたスタイル',
      en: 'Street',
      tags: ['오버핏', '그래픽', '스니커즈'],
    },
    {
      id: 'y2k',
      ko: 'Y2K',
      ja: 'Y2K',
      ja_desc: '2000年代初頭にインスパイアされたスタイル',
      en: 'Y2K',
      tags: ['로우라이즈', '크롭', '메탈릭'],
    },
    {
      id: 'oldmoney',
      ko: '올드머니',
      ja: 'オールドマネー',
      ja_desc: '上品でクラシックな富裕層スタイル',
      en: 'Old money',
      tags: ['클래식', '테일러드', '럭셔리'],
    },
    {
      id: 'highteen',
      ko: '하이틴룩',
      ja: 'ハイティーンルック',
      ja_desc: '青春感あふれる学生スタイル',
      en: 'High teen look',
      tags: ['청순', '프레피', '캐주얼'],
    },
    {
      id: 'normcore',
      ko: '놈코어',
      ja: 'ノームコア',
      ja_desc: '意図的に普通を目指したスタイル',
      en: 'Normcore',
      tags: ['베이직', '심플', '무지'],
    },
    {
      id: 'gorpcore',
      ko: '고프코어',
      ja: 'ゴープコア',
      ja_desc: 'アウトドアテイストの都会的スタイル',
      en: 'Gorpcore',
      tags: ['아웃도어', '기능성', '레이어드'],
    },
    {
      id: 'preppy',
      ko: '프레피',
      ja: 'プレッピー',
      ja_desc: 'アイビーリーグ風の上品カジュアル',
      en: 'Preppy',
      tags: ['체크', '니트', '로퍼'],
    },
    {
      id: 'amekaji',
      ko: '아메카지',
      ja: 'アメカジ',
      ja_desc: 'アメリカンカジュアルスタイル',
      en: 'American casual',
      tags: ['데님', '체크셔츠', '워크웨어'],
    },
    {
      id: 'feminin',
      ko: '페미닌',
      ja: 'フェミニン',
      ja_desc: '女性らしい優雅なスタイル',
      en: 'Feminine',
      tags: ['플로럴', '레이스', '파스텔'],
    },
    {
      id: 'chungchung',
      ko: '청청패션',
      ja: 'デニムオンデニム',
      ja_desc: 'デニム×デニムのコーデ',
      en: 'Denim on denim',
      tags: ['데님재킷', '데님팬츠', '캐주얼'],
    },
    {
      id: 'layered',
      ko: '레이어드',
      ja: 'レイヤードスタイル',
      ja_desc: '重ね着テクニックを駆使したスタイル',
      en: 'Layered',
      tags: ['레이어드', '믹스매치', '볼륨감'],
    },
    {
      id: 'genderless',
      ko: '젠더리스',
      ja: 'ジェンダーレス',
      ja_desc: '性別を超えたスタイル',
      en: 'Genderless',
      tags: ['오버핏', '유니섹스', '모던'],
    },
    {
      id: 'cottagecore',
      ko: '코티지코어',
      ja: 'コテージコア',
      ja_desc: '田舎の自然を感じるロマンティックスタイル',
      en: 'Cottagecore',
      tags: ['플로럴', '리넨', '내추럴'],
    },
    {
      id: 'darkacademia',
      ko: '다크아카데미아',
      ja: 'ダークアカデミア',
      ja_desc: '知的でダークなアカデミックスタイル',
      en: 'Dark academia',
      tags: ['트위드', '체크', '다크컬러'],
    },
    {
      id: 'dopamine',
      ko: '도파민 패션',
      ja: 'ドーパミンファッション',
      ja_desc: '鮮やかな色でテンションを上げるスタイル',
      en: 'Dopamine dressing',
      tags: ['비비드', '컬러풀', '팝아트'],
    },
  ],

  // ── 핏 / 실루엣 ──────────────────────────────
  fits: [
    { id: 'overfit',   ko: '오버핏',   ja: 'オーバーフィット',  en: 'Oversized' },
    { id: 'slimfit',   ko: '슬림핏',   ja: 'スリムフィット',    en: 'Slim fit' },
    { id: 'croptop',   ko: '크롭',     ja: 'クロップ',          en: 'Crop' },
    { id: 'wideleg',   ko: '와이드',   ja: 'ワイドレッグ',      en: 'Wide leg' },
    { id: 'flare',     ko: '플레어',   ja: 'フレア',            en: 'Flare' },
    { id: 'baggy',     ko: '배기',     ja: 'バギー',            en: 'Baggy' },
    { id: 'straight',  ko: '스트레이트', ja: 'ストレート',       en: 'Straight' },
  ],

  // ── 색상 ─────────────────────────────────────
  colors: [
    { id: 'black',     ko: '블랙',     ja: 'ブラック',   hex: '#0a0a0a' },
    { id: 'white',     ko: '화이트',   ja: 'ホワイト',   hex: '#f8f8f8' },
    { id: 'beige',     ko: '베이지',   ja: 'ベージュ',   hex: '#d4c5a9' },
    { id: 'navy',      ko: '네이비',   ja: 'ネイビー',   hex: '#1a2744' },
    { id: 'khaki',     ko: '카키',     ja: 'カーキ',     hex: '#7a7a52' },
    { id: 'gray',      ko: '그레이',   ja: 'グレー',     hex: '#888888' },
    { id: 'brown',     ko: '브라운',   ja: 'ブラウン',   hex: '#6b4c2a' },
    { id: 'cream',     ko: '크림',     ja: 'クリーム',   hex: '#fffbe6' },
    { id: 'camel',     ko: '카멜',     ja: 'キャメル',   hex: '#c19a6b' },
    { id: 'lavender',  ko: '라벤더',   ja: 'ラベンダー', hex: '#c4b5e8' },
    { id: 'mint',      ko: '민트',     ja: 'ミント',     hex: '#b2e4d4' },
    { id: 'pink',      ko: '핑크',     ja: 'ピンク',     hex: '#f4a7b9' },
    { id: 'red',       ko: '레드',     ja: 'レッド',     hex: '#cc2936' },
    { id: 'olive',     ko: '올리브',   ja: 'オリーブ',   hex: '#6b7c2a' },
    { id: 'ivory',     ko: '아이보리', ja: 'アイボリー', hex: '#fffff0' },
  ],

  // ── 옷 카테고리 ───────────────────────────────
  categories: [
    { id: 'outer',     ko: '아우터',   ja: 'アウター',   sub: ['코트', '재킷', '패딩', '무스탕', '블레이저'] },
    { id: 'top',       ko: '상의',     ja: 'トップス',   sub: ['니트', '맨투맨', '후드', '셔츠', '블라우스', '크롭탑'] },
    { id: 'bottom',    ko: '하의',     ja: 'ボトムス',   sub: ['와이드팬츠', '슬랙스', '데님', '스커트', '숏팬츠'] },
    { id: 'dress',     ko: '원피스',   ja: 'ワンピース', sub: ['미니', '미디', '맥시'] },
    { id: 'set',       ko: '세트업',   ja: 'セットアップ', sub: ['자켓세트', '트레이닝세트'] },
  ],

  // ── 예산 (JPY 기준) ───────────────────────────
  budgets: [
    { id: 'under5',   ko: '~5만원',     ja: '〜4,000円',   krw_max: 50000 },
    { id: '5to15',    ko: '5~15만원',   ja: '4,000〜11,000円', krw_min: 50000, krw_max: 150000 },
    { id: '15to30',   ko: '15~30만원',  ja: '11,000〜22,000円', krw_min: 150000, krw_max: 300000 },
    { id: 'over30',   ko: '30만원+',    ja: '22,000円〜', krw_min: 300000 },
  ],
};

// 현재 언어에 맞는 텍스트 반환 헬퍼
export function getTerm(term, lang = 'ko') {
  return term[lang] ?? term.ko;
}
