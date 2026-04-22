// components/PredictionCard.jsx
import { useMemo } from 'react';
import { Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { CATEGORY_MAP, DIRECTION_MAP, MAGNITUDE_MAP, formatCategory } from '../constants/category';
import { COLORS } from '../constants/colors';

// ── 파급기간 / 지역 범위 배지 ──────────────────────────────────
const TIME_HORIZON_MAP = {
  short: { label: '단기 (1~3개월)', icon: '⚡', color: '#D85A30', bg: '#FEF3EB' },
  medium: { label: '중기 (3~6개월)', icon: '📅', color: '#B45309', bg: '#FEFCE8' },
  long: { label: '장기 (6개월+)', icon: '🔭', color: '#0369A1', bg: '#EFF6FF' },
};
const GEO_SCOPE_MAP = {
  domestic: { label: '국내 한정', icon: '🇰🇷' },
  global: { label: '글로벌 영향', icon: '🌐' },
  regional: { label: '지역 한정', icon: '📍' },
};

export function TimeHorizonBadge({ value }) {
  if (!value) return null;
  const info = TIME_HORIZON_MAP[value] ?? { label: value, icon: '⏱', color: '#888', bg: '#F3F4F6' };
  return (
    <View style={[styles.horizonBadge, { backgroundColor: info.bg }]}>
      <Text style={styles.horizonIcon}>{info.icon}</Text>
      <Text style={[styles.horizonText, { color: info.color }]}>{info.label}</Text>
    </View>
  );
}

export function GeoScopeBadge({ value }) {
  if (!value) return null;
  const info = GEO_SCOPE_MAP[value] ?? { label: value, icon: '📌' };
  return (
    <View style={styles.geoBadge}>
      <Text style={styles.geoIcon}>{info.icon}</Text>
      <Text style={styles.geoText}>{info.label}</Text>
    </View>
  );
}

export { TIME_HORIZON_MAP, GEO_SCOPE_MAP };

export default function PredictionCard({ item, onPress }) {
  const dir = DIRECTION_MAP[item.direction] ?? DIRECTION_MAP.neutral;
  const mag = MAGNITUDE_MAP[item.magnitude] ?? MAGNITUDE_MAP.low;
  const catName = formatCategory(item.category);
  const count = item.news_analyses?.length ?? 0;
  const firstNews = item.news_analyses?.[0];
  const timeHorizon = firstNews?.time_horizon;
  const geoScope = firstNews?.geo_scope;
  const previewText = firstNews?.summary ?? item.event;
  const newsDate = firstNews?.raw_news?.origin_published_at?.slice(0, 10)
    ?? firstNews?.created_at?.slice(0, 10)
    ?? '';
  const topBorderColor =
    item.direction === 'up' ? COLORS.up :
      item.direction === 'down' ? COLORS.down : '#E5E7EB';

  const rangeText = useMemo(() => {
    if (item.direction === 'neutral') return '─ 중립';
    if (item.change_pct_min == null && item.change_pct_max == null) return '소폭 변동';
    const minVal = item.change_pct_min;
    const maxVal = item.change_pct_max;
    const signMin = minVal > 0 ? '+' : '';
    const signMax = maxVal > 0 ? '+' : '';
    if (minVal === maxVal) return `약 ${signMin}${minVal}%`;
    return `${signMin}${minVal ?? '?'} ~ ${signMax}${maxVal ?? '?'}%`;
  }, [item]);

  const magBadge = {
    high: { bg: COLORS.highBg, color: COLORS.highText },
    medium: { bg: COLORS.medBg, color: COLORS.medText },
    low: { bg: COLORS.lowBg, color: COLORS.lowText },
  }[item.magnitude] ?? { bg: COLORS.lowBg, color: COLORS.lowText };

  return (
    <Pressable onPress={() => onPress(item)} style={[styles.predCard, { borderTopColor: topBorderColor }]}>
      <View style={styles.predCardTop}>
        <View style={styles.predHeading}>
          <View style={{ flex: 1 }}>
            <Text style={styles.predCatEn}>{item.category.toUpperCase()}</Text>
            <Text style={styles.predCatKo}>{catName}</Text>
          </View>
          <View style={styles.predRight}>
            <View style={[styles.magBadge, { backgroundColor: magBadge.bg }]}>
              <Text style={[styles.magBadgeText, { color: magBadge.color }]}>{mag.label}</Text>
            </View>
            <View style={styles.magDots}>
              {mag.dots.map((c, i) => (
                <View key={i} style={[styles.magDot, { backgroundColor: c }]} />
              ))}
            </View>
          </View>
        </View>

        <View style={styles.predMainRow}>
          <View style={[styles.dirIconBox, { backgroundColor: dir.color + '15' }]}>
            <Text style={[styles.dirIconText, { color: dir.color }]}>
              {item.direction === 'up' ? '▲' : item.direction === 'down' ? '▼' : '─'}
            </Text>
          </View>
          <View style={styles.predValBox}>
            <Text style={[styles.predRange, { color: dir.color }]}>{rangeText}</Text>
            <Text style={styles.predDirLabel}>{dir.label} 전망</Text>
          </View>
        </View>

        <Text style={styles.predDesc} numberOfLines={1}>{item.event}</Text>

        {(timeHorizon || geoScope) ? (
          <View style={styles.badgeRow}>
            {timeHorizon ? <TimeHorizonBadge value={timeHorizon} /> : null}
            {geoScope ? <GeoScopeBadge value={geoScope} /> : null}
          </View>
        ) : null}

        {item.monthly_impact ? (
          <View style={styles.impactBox}>
            <Text style={styles.impactLabel}>월간 예상 영향액</Text>
            <Text style={styles.impactValue}>약 {item.monthly_impact.toLocaleString()}원</Text>
          </View>
        ) : null}
      </View>

      <View style={styles.predDivider} />
      <View style={styles.predPreview}>
        <View style={{ flex: 1 }}>
          <View style={styles.predPreviewHeader}>
            <Text style={styles.predPreviewTag}>핵심 근거</Text>
            {newsDate ? <Text style={styles.predDate}>{newsDate}</Text> : null}
          </View>
          <Text style={styles.predPreviewText} numberOfLines={1}>{previewText}</Text>
        </View>
        <View style={styles.predCountBadge}>
          <Text style={styles.predCountText}>{count}건</Text>
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  badgeRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap', marginBottom: 10 },
  horizonBadge: { flexDirection: 'row', alignItems: 'center', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4, gap: 4 },
  horizonIcon: { fontSize: 11 },
  horizonText: { fontSize: 11, fontWeight: '700' },
  geoBadge: { flexDirection: 'row', alignItems: 'center', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4, gap: 4, backgroundColor: '#F0FDF4' },
  geoIcon: { fontSize: 11 },
  geoText: { fontSize: 11, fontWeight: '700', color: '#166534' },
  predCard: {
    backgroundColor: COLORS.white, borderRadius: 16, borderTopWidth: 4, marginBottom: 16, overflow: 'hidden',
    ...Platform.select({
      ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.08, shadowRadius: 10 },
      android: { elevation: 3 },
    }),
  },
  predCardTop: { padding: 16, paddingBottom: 12 },
  predHeading: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 },
  predCatEn: { fontSize: 10, color: COLORS.textLight, fontWeight: '600', letterSpacing: 0.5, marginBottom: 2 },
  predCatKo: { fontSize: 18, fontWeight: '800', color: COLORS.textPrimary },
  predMainRow: { flexDirection: 'row', alignItems: 'center', marginVertical: 12, gap: 12 },
  dirIconBox: { width: 44, height: 44, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  dirIconText: { fontSize: 22, fontWeight: '700' },
  predValBox: { flex: 1 },
  predRange: { fontSize: 24, fontWeight: '800', lineHeight: 28 },
  predDirLabel: { fontSize: 12, color: COLORS.textMuted, fontWeight: '500' },
  predRight: { alignItems: 'flex-end' },
  magBadge: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3, marginBottom: 4 },
  magBadgeText: { fontSize: 10, fontWeight: '700' },
  magDots: { flexDirection: 'row', gap: 3 },
  magDot: { width: 6, height: 6, borderRadius: 3 },
  predDesc: { fontSize: 13, color: COLORS.textMuted, fontWeight: '500', lineHeight: 18, marginBottom: 8 },
  impactBox: { backgroundColor: '#F0F9FF', borderRadius: 8, padding: 8, marginTop: 4 },
  impactLabel: { fontSize: 9, fontWeight: '700', color: '#0369A1', textTransform: 'uppercase', marginBottom: 2 },
  impactValue: { fontSize: 14, fontWeight: '800', color: '#0C4A6E' },
  predDivider: { height: 1, backgroundColor: '#F3F4F6' },
  predPreview: { flexDirection: 'row', alignItems: 'center', padding: 12, paddingHorizontal: 16, backgroundColor: '#F9FAFB' },
  predPreviewHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 },
  predPreviewTag: { fontSize: 9, fontWeight: '800', color: COLORS.headerBg, textTransform: 'uppercase' },
  predPreviewText: { fontSize: 12, color: COLORS.textPrimary, fontWeight: '500' },
  predDate: { fontSize: 10, color: COLORS.textLight },
  predCountBadge: { backgroundColor: '#E5E7EB', borderRadius: 6, paddingHorizontal: 6, paddingVertical: 2, marginLeft: 8 },
  predCountText: { fontSize: 10, fontWeight: '700', color: COLORS.textMuted },
});
