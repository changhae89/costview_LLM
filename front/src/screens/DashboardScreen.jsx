// screens/DashboardScreen.jsx — SCR-001 대시보드
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import DirectionDot from '../components/DirectionDot';
import ReliabilityBadge from '../components/ReliabilityBadge';
import { CATEGORY_MAP, DIRECTION_MAP, MAGNITUDE_MAP } from '../constants/category';
import { COLORS } from '../constants/colors';
import { formatNumber } from '../lib/helpers';
import { fetchCausalChains, fetchDashboardMetrics, fetchNewsList } from '../lib/supabase';


// ── 리스크 카드 ────────────────────────────────────────────────
function RiskCard({ label, desc, value, change, date }) {
  const changeNum = Number(change);
  const changeColor = changeNum > 0 ? '#FF8A7A' : '#6EE7B7';
  const changeText = changeNum > 0
    ? `▲+${changeNum.toFixed(1)}`
    : changeNum < 0
      ? `▼${Math.abs(changeNum).toFixed(1)}`
      : '─ 0.0';

  return (
    <View style={styles.riskCard}>
      <Text style={styles.riskLabel}>{label}</Text>
      {desc && <Text style={{fontSize: 8, color: 'rgba(255,255,255,0.4)', marginBottom: 4}}>{desc}</Text>}
      <Text style={styles.riskValue} numberOfLines={1}>{value !== null && value !== undefined && value !== '' ? formatNumber(value) : '-'}</Text>
      <View style={styles.riskBar}>
        <View style={styles.riskBarFill} />
      </View>
      <Text style={[styles.riskChange, { color: changeColor }]}>{changeText}</Text>
      {date ? <Text style={styles.riskDate}>{date}</Text> : null}
    </View>
  );
}

// ── 카테고리 행 ────────────────────────────────────────────────
function CategoryRow({ item, isLast }) {
  const catName = CATEGORY_MAP[item.category] ?? item.category;
  const dir = DIRECTION_MAP[item.direction] ?? DIRECTION_MAP.neutral;
  const mag = MAGNITUDE_MAP[item.magnitude] ?? MAGNITUDE_MAP.low;
  const min = item.change_pct_min ?? 0;
  const max = item.change_pct_max ?? 0;

  let rangeText = '';
  if (item.direction === 'neutral') {
    rangeText = '─ 중립';
  } else if (min === max) {
    rangeText = `${dir.label.split(' ')[0]} 약${min > 0 ? '+' : ''}${min}%`;
  } else {
    rangeText = `${dir.label.split(' ')[0]}${min > 0 ? '+' : ''}${min}~${max > 0 ? '+' : ''}${max}%`;
  }

  return (
    <View style={[styles.categoryRow, !isLast && styles.rowBorder]}>
      <View style={styles.rowLeft}>
        <DirectionDot direction={item.direction} size={8} />
        <View>
          <Text style={styles.categoryName}>{catName}</Text>
          <Text style={styles.categoryCount}>{item.news_count ?? 0}건의 분석</Text>
        </View>
      </View>
      <View style={styles.rowRight}>
        <Text style={[styles.categoryChange, { color: dir.color }]}>{rangeText}</Text>
        <View style={styles.magnitudeDots}>
          {mag.dots.map((c, i) => (
            <View key={i} style={[styles.magnitudeDot, { backgroundColor: c }]} />
          ))}
        </View>
      </View>
    </View>
  );
}

// ── 뉴스 행 ───────────────────────────────────────────────────
function NewsRow({ item, isLast }) {
  const mainChain = item.causal_chains?.[0];
  const keywords = item.raw_news?.keyword?.slice(0, 3) ?? [];

  return (
    <View style={[styles.newsRow, !isLast && styles.rowBorder]}>
      <View style={styles.newsRowTop}>
        <DirectionDot direction={mainChain?.direction ?? 'neutral'} size={7} />
        <Text style={styles.newsTitle} numberOfLines={2}>{item.summary}</Text>
        <ReliabilityBadge reliability={item.reliability} />
      </View>
      <Text style={styles.newsSummaryEn} numberOfLines={1}>{item.raw_news?.title ?? ''}</Text>
      <View style={styles.tagRow}>
        {(item.raw_news?.increased_items ?? []).map(k => (
          <View key={k} style={[styles.tag, { backgroundColor: COLORS.tagUpBg }]}>
            <Text style={[styles.tagText, { color: COLORS.tagUpText }]}>▲{k}</Text>
          </View>
        ))}
        {(item.raw_news?.decreased_items ?? []).map(k => (
          <View key={k} style={[styles.tag, { backgroundColor: COLORS.tagDownBg }]}>
            <Text style={[styles.tagText, { color: COLORS.tagDownText }]}>▼{k}</Text>
          </View>
        ))}
        {keywords.map(k => (
          <View key={k} style={styles.tagGray}>
            <Text style={styles.tagGrayText}>{k}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

export default function DashboardScreen() {
  const insets = useSafeAreaInsets();
  const [metrics, setMetrics] = useState(null);
  const [chains, setChains] = useState([]);
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const [dash, ch, nw] = await Promise.all([
          fetchDashboardMetrics(),
          fetchCausalChains(),
          fetchNewsList(),
        ]);
        if (dash) setMetrics(dash);
        if (ch?.length > 0) {
          const grouped = {};
          ch.forEach(c => {
            if (!grouped[c.category]) {
              grouped[c.category] = { ...c, news_count: 1 };
            } else {
              grouped[c.category].news_count += 1;
            }
          });
          setChains(Object.values(grouped));
        }
        if (nw?.length > 0) setNews(nw.slice(0, 5));
      } catch { /* Supabase 미연결 시 mock 유지 */ }
      finally { setLoading(false); }
    })();
  }, []);

  const latest = metrics?.latest ?? {};
  const prev   = metrics?.prev ?? {};

  const CARDS = [
    { key: 'ai_gpr', label: 'AI 지수', desc: '지정학 위험 지수', val: latest.ai_gpr_index, pval: prev.ai_gpr_index, date: latest.dates?.ai_gpr_index ?? latest.reference_date },
    { key: 'krw_usd', label: '원/달러 환율', desc: '거시 경제 환율', val: latest.krw_usd_rate, pval: prev.krw_usd_rate, date: latest.dates?.krw_usd_rate ?? latest.reference_date },
    { key: 'wti', label: 'WTI 원유', desc: '국제 원유가 (달러)', val: latest.fred_wti, pval: prev.fred_wti, date: latest.dates?.fred_wti ?? latest.reference_date },
    { key: 'cpi', label: '한국 소비자물가', desc: '전년동월대비 (%)', val: latest.cpi_total, pval: prev.cpi_total, date: latest.dates?.cpi_total ?? latest.reference_date },
    { key: 'fed', label: '미 10년 국채', desc: '미국 10년물 금리 (%)', val: latest.fred_treasury_10y, pval: prev.fred_treasury_10y, date: latest.dates?.fred_treasury_10y ?? latest.reference_date },
  ];

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.headerBg} />

      {/* ── 헤더 ── */}
      <View style={[styles.header, { paddingTop: insets.top + 10 }]}>
        <View style={styles.headerTop}>
          <View>
            <Text style={styles.headerTitle}>대시보드</Text>
            <Text style={styles.headerSub}>실시간 종합 현황</Text>
          </View>
        </View>

        {/* 리스크 카드 가로 스크롤 */}
        <View style={{ marginHorizontal: -16 }}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.riskRow}>
            {CARDS.map(c => (
              <RiskCard 
                key={c.key} 
                label={c.label} 
                desc={c.desc} 
                value={c.val} 
                change={(c.val ?? 0) - (c.pval ?? 0)} 
                date={c.date}
              />
            ))}
          </ScrollView>
        </View>
      </View>

      {/* ── Body ── */}
      <ScrollView
        style={styles.body}
        contentContainerStyle={styles.bodyContent}
        showsVerticalScrollIndicator={false}
      >
        {loading && <ActivityIndicator color={COLORS.headerBg} style={{ marginBottom: 12 }} />}

        {/* 카테고리별 가격 영향 */}
        <Text style={styles.sectionLabel}>카테고리별 가격 영향</Text>
        <View style={styles.card}>
          {chains.map((item, i) => (
            <CategoryRow
              key={item.category + i}
              item={item}
              isLast={i === chains.length - 1}
            />
          ))}
        </View>

        {/* 최신 뉴스 */}
        <Text style={[styles.sectionLabel, { marginTop: 16 }]}>최신 뉴스</Text>
        <View style={styles.card}>
          {news.map((item, i) => (
            <NewsRow key={item.id} item={item} isLast={i === news.length - 1} />
          ))}
        </View>

        <View style={{ height: 16 }} />
      </ScrollView>
    </View>
  );
}

// ── StyleSheet ────────────────────────────────────────────────
const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: COLORS.screenBg },

  // Header
  header: {
    backgroundColor: COLORS.headerBg,
    paddingHorizontal: 16,
    paddingBottom: 14,
  },
  headerTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 14,
  },
  headerTitle: { fontSize: 17, fontWeight: '700', color: COLORS.headerText },
  headerSub:   { fontSize: 10, color: COLORS.headerAccent, marginTop: 2 },

  // Risk cards
  riskRow:   { flexDirection: 'row', gap: 8, paddingHorizontal: 16 },
  riskCard: {
    width: 120, // 가로 스크롤 시 카드의 고정 너비
    backgroundColor: 'rgba(255,255,255,0.10)',
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 12,
  },
  riskLabel:   { fontSize: 10, fontWeight: '700', color: 'rgba(255,255,255,0.9)', marginBottom: 2 },
  riskValue:   { fontSize: 18, fontWeight: '700', color: COLORS.headerText },
  riskBar: {
    height: 3,
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 2,
    marginVertical: 4,
  },
  riskBarFill: { width: '60%', height: 3, backgroundColor: 'rgba(255,255,255,0.4)', borderRadius: 2 },
  riskChange:  { fontSize: 10 },
  riskDate: { position: 'absolute', right: 10, bottom: 8, fontSize: 9, color: 'rgba(255,255,255,0.55)' },

  // Body
  body:        { flex: 1 },
  bodyContent: { padding: 14 },
  sectionLabel: {
    fontSize: 11,
    fontWeight: '500',
    color: COLORS.textMuted,
    letterSpacing: 0.3,
    marginBottom: 8,
  },
  card: {
    backgroundColor: COLORS.white,
    borderRadius: 14,
    overflow: 'hidden',
    ...Platform.select({
      ios:     { shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 8 },
      android: { elevation: 2 },
    }),
  },
  rowBorder:   { borderBottomWidth: 0.5, borderBottomColor: COLORS.border },

  // Category row
  categoryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 11,
    paddingHorizontal: 14,
  },
  rowLeft:     { flexDirection: 'row', alignItems: 'center', flex: 1 },
  rowRight:    { alignItems: 'flex-end' },
  categoryName:   { fontSize: 13, fontWeight: '700', color: COLORS.textPrimary },
  categoryCount:  { fontSize: 10, color: COLORS.textMuted, marginTop: 1 },
  categoryChange: { fontSize: 13, fontWeight: '700' },
  magnitudeDots:  { flexDirection: 'row', gap: 3, marginTop: 3 },
  magnitudeDot:   { width: 6, height: 6, borderRadius: 3 },

  // News row
  newsRow:     { paddingVertical: 11, paddingHorizontal: 14 },
  newsRowTop:  { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 3 },
  newsTitle:   { flex: 1, fontSize: 12, fontWeight: '700', color: COLORS.textPrimary, marginRight: 8 },
  newsSummaryEn: { fontSize: 11, color: COLORS.textMuted, marginBottom: 6, marginLeft: 15 },
  tagRow:      { flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginLeft: 15 },
  tag:         { borderRadius: 4, paddingHorizontal: 5, paddingVertical: 2 },
  tagText:     { fontSize: 10, fontWeight: '600' },
  tagGray:     { backgroundColor: '#F3F4F6', borderRadius: 4, paddingHorizontal: 5, paddingVertical: 2 },
  tagGrayText: { fontSize: 10, color: COLORS.textMuted },
});
