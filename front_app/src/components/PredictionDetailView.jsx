// components/PredictionDetailView.jsx
import { useEffect, useMemo, useRef } from 'react';
import {
  Animated, Dimensions, Easing, Linking, Platform,
  ScrollView, StatusBar, StyleSheet, Text, TouchableOpacity, View,
} from 'react-native';
import { DIRECTION_MAP, MAGNITUDE_MAP, formatCategory } from '../constants/category';
import { COLORS } from '../constants/colors';
import InsightCard from './InsightCard';
import { TimeHorizonBadge, GeoScopeBadge } from './PredictionCard';

const { width: SCREEN_W } = Dimensions.get('window');

export default function PredictionDetailView({ item, onClose, topInset }) {
  const slideAnim = useRef(new Animated.Value(SCREEN_W)).current;

  useEffect(() => {
    Animated.timing(slideAnim, {
      toValue: 0, duration: 320,
      easing: Easing.out(Easing.cubic), useNativeDriver: true,
    }).start();
  }, [slideAnim]);

  const handleClose = () => {
    Animated.timing(slideAnim, {
      toValue: SCREEN_W, duration: 250,
      easing: Easing.in(Easing.cubic), useNativeDriver: true,
    }).start(() => onClose());
  };

  const dir = DIRECTION_MAP[item.direction] ?? DIRECTION_MAP.neutral;
  const mag = MAGNITUDE_MAP[item.magnitude] ?? MAGNITUDE_MAP.low;
  const catName = formatCategory(item.category);
  const newsAnalyses = item.news_analyses ?? [];
  const firstNews = newsAnalyses[0];
  const timeHorizon = firstNews?.time_horizon;
  const geoScope = firstNews?.geo_scope;

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
    <Animated.View style={[styles.root, { transform: [{ translateX: slideAnim }] }]}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.headerBg} />

      <View style={[styles.header, { paddingTop: topInset + 10 }]}>
        <TouchableOpacity onPress={handleClose} style={styles.backBtn} hitSlop={15}>
          <Text style={styles.backText}>← 목록으로 돌아가기</Text>
        </TouchableOpacity>
        <View style={styles.titleRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.catName}>{catName}</Text>
            <Text style={[styles.range, { color: COLORS.textPrimary }]}>{rangeText}</Text>
          </View>
          <View style={styles.headerRight}>
            <View style={[styles.magBadge, { backgroundColor: magBadge.bg }]}>
              <Text style={[styles.magBadgeText, { color: magBadge.color }]}>{mag.label}</Text>
            </View>
            <Text style={[styles.dirLabel, { color: dir.color === '#111827' ? COLORS.white : dir.color }]}>
              {dir.label} 추세
            </Text>
          </View>
        </View>
        {(timeHorizon || geoScope) ? (
          <View style={[styles.badgeRow, { marginTop: 12 }]}>
            {timeHorizon ? <TimeHorizonBadge value={timeHorizon} /> : null}
            {geoScope ? <GeoScopeBadge value={geoScope} /> : null}
          </View>
        ) : null}
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.body}>
        <Text style={styles.sectionLabel}>인과관계 메커니즘</Text>
        <View style={styles.card}>
          <View style={styles.visualFlow}>
            <View style={styles.flowNodeBox}>
              <View style={[styles.nodeIcon, { backgroundColor: COLORS.highBg }]}>
                <Text style={{ fontSize: 16 }}>⚡</Text>
              </View>
              <View style={styles.nodeContent}>
                <Text style={styles.nodeTag}>원인 (Event)</Text>
                <Text style={styles.nodeText}>{item.event}</Text>
              </View>
            </View>
            <View style={styles.flowLineContainer}><View style={styles.flowLine} /><View style={styles.flowArrowTip} /></View>
            <View style={styles.flowNodeBox}>
              <View style={[styles.nodeIcon, { backgroundColor: COLORS.medBg }]}>
                <Text style={{ fontSize: 16 }}>⚙️</Text>
              </View>
              <View style={styles.nodeContent}>
                <Text style={styles.nodeTag}>전달 경로 (Mechanism)</Text>
                <Text style={styles.nodeText}>{item.mechanism}</Text>
              </View>
            </View>
            <View style={styles.flowLineContainer}><View style={styles.flowLine} /><View style={styles.flowArrowTip} /></View>
            <View style={styles.flowNodeBox}>
              <View style={[styles.nodeIcon, { backgroundColor: item.direction === 'up' ? COLORS.tagUpBg : COLORS.tagDownBg }]}>
                <Text style={{ fontSize: 16 }}>{item.direction === 'up' ? '📈' : '📉'}</Text>
              </View>
              <View style={styles.nodeContent}>
                <Text style={styles.nodeTag}>결과 (Result)</Text>
                <Text style={[styles.nodeText, { fontWeight: '700', color: item.direction === 'up' ? COLORS.tagUpText : COLORS.tagDownText }]}>
                  {catName} 가격 {dir.label}
                </Text>
              </View>
            </View>
          </View>
        </View>

        {item.monthly_impact ? (
          <View style={styles.impactCard}>
            <View>
              <Text style={styles.impactLabel}>📦 월간 예상 영향액</Text>
              <Text style={styles.impactValue}>약 {item.monthly_impact.toLocaleString()}원</Text>
            </View>
            <Text style={styles.impactSub}>가계 평균 기준</Text>
          </View>
        ) : null}

        <InsightCard newsAnalyses={newsAnalyses} />

        <Text style={[styles.sectionLabel, { marginTop: 8 }]}>분석 근거 뉴스 ({newsAnalyses.length}건)</Text>
        {newsAnalyses.map((na) => {
          const raw = na.raw_news;
          const date = raw?.origin_published_at?.slice(0, 10) ?? na.created_at?.slice(0, 10);
          const reliabilityPct = Math.round((na.reliability ?? 0) * 100);
          return (
            <View key={na.id} style={styles.newsCard}>
              <View style={styles.newsHeader}>
                <Text style={styles.newsSource}>기사 발행일: {date}</Text>
                <View style={styles.relBadge}>
                  <Text style={styles.relBadgeText}>신뢰도 {reliabilityPct}%</Text>
                </View>
              </View>
              <Text style={styles.newsTitle}>{raw?.title ?? '제목 없음'}</Text>
              {na.related_indicators?.length > 0 ? (
                <View style={styles.indRow}>
                  {na.related_indicators.map((ind, i) => (
                    <View key={i} style={styles.indTag}>
                      <Text style={styles.indTagText}>#{formatCategory(ind)}</Text>
                    </View>
                  ))}
                </View>
              ) : null}
              <View style={styles.summaryBox}>
                <Text style={styles.summaryLabel}>🤖 AI 분석 요약</Text>
                <Text style={styles.summaryText}>{na.summary}</Text>
              </View>
              {na.reliability_reason ? (
                <View style={styles.reasonBox}>
                  <Text style={styles.reasonLabel}>💡 신뢰도 근거</Text>
                  <Text style={styles.reasonText}>{na.reliability_reason}</Text>
                </View>
              ) : null}
              {na.leading_indicator ? (
                <View style={styles.leadBox}>
                  <Text style={styles.leadLabel}>📊 선행 지표</Text>
                  <Text style={styles.leadText}>{na.leading_indicator}</Text>
                </View>
              ) : null}
              {na.buffer ? (
                <View style={styles.bufferBox}>
                  <Text style={styles.bufferLabel}>🛡️ 완충 요인</Text>
                  <Text style={styles.bufferText}>{na.buffer}</Text>
                </View>
              ) : null}
              {raw?.news_url ? (
                <TouchableOpacity style={styles.linkBtn} onPress={() => Linking.openURL(raw.news_url).catch(() => { })}>
                  <Text style={styles.linkText}>뉴스 원문 읽기 ↗</Text>
                </TouchableOpacity>
              ) : null}
            </View>
          );
        })}
        <View style={{ height: 40 }} />
      </ScrollView>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  root: { ...StyleSheet.absoluteFillObject, backgroundColor: COLORS.screenBg, zIndex: 100 },
  header: { backgroundColor: COLORS.headerBg, paddingHorizontal: 16, paddingBottom: 20 },
  backBtn: { marginBottom: 16 },
  backText: { fontSize: 13, color: COLORS.textPrimary, fontWeight: '600' },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' },
  catName: { fontSize: 16, color: COLORS.headerAccent, fontWeight: '600', marginBottom: 2 },
  range: { fontSize: 32, fontWeight: '900' },
  headerRight: { alignItems: 'flex-end' },
  magBadge: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3, marginBottom: 4 },
  magBadgeText: { fontSize: 10, fontWeight: '700' },
  dirLabel: { fontSize: 14, fontWeight: '700', marginTop: 4 },
  badgeRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  body: { padding: 16 },
  sectionLabel: { fontSize: 12, fontWeight: '800', color: COLORS.textPrimary, letterSpacing: 0.8, marginBottom: 12, textTransform: 'uppercase' },
  card: {
    backgroundColor: COLORS.white, borderRadius: 20, padding: 20, marginBottom: 16,
    ...Platform.select({
      ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.1, shadowRadius: 12 },
      android: { elevation: 3 },
    }),
  },
  visualFlow: {},
  flowNodeBox: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  nodeIcon: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  nodeContent: { flex: 1 },
  nodeTag: { fontSize: 10, fontWeight: '800', color: COLORS.textLight, marginBottom: 2, textTransform: 'uppercase' },
  nodeText: { fontSize: 14, color: COLORS.textPrimary, fontWeight: '600', lineHeight: 20 },
  flowLineContainer: { height: 30, marginLeft: 20, justifyContent: 'center' },
  flowLine: { width: 2, flex: 1, backgroundColor: '#E5E7EB' },
  flowArrowTip: { position: 'absolute', bottom: -2, left: -3, width: 8, height: 8, borderRightWidth: 2, borderBottomWidth: 2, borderColor: '#E5E7EB', transform: [{ rotate: '45deg' }] },
  impactCard: { backgroundColor: '#EFF6FF', borderRadius: 14, padding: 16, marginBottom: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderLeftWidth: 4, borderLeftColor: '#3B82F6' },
  impactLabel: { fontSize: 11, fontWeight: '700', color: '#1E40AF', marginBottom: 4 },
  impactValue: { fontSize: 22, fontWeight: '900', color: '#1E3A8A' },
  impactSub: { fontSize: 10, color: '#93C5FD' },
  newsCard: { backgroundColor: COLORS.white, borderRadius: 16, padding: 16, marginBottom: 12, borderLeftWidth: 4, borderLeftColor: COLORS.primary },
  newsHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  newsSource: { fontSize: 11, fontWeight: '700', color: COLORS.primary },
  relBadge: { backgroundColor: '#ECFDF5', borderRadius: 5, paddingHorizontal: 6, paddingVertical: 2 },
  relBadgeText: { fontSize: 10, fontWeight: '700', color: '#065F46' },
  newsTitle: { fontSize: 15, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 12, lineHeight: 22 },
  indRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 12 },
  indTag: { backgroundColor: '#E0F2FE', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2 },
  indTagText: { fontSize: 10, fontWeight: '700', color: '#0369A1' },
  summaryBox: { backgroundColor: '#F8FAFC', borderRadius: 10, padding: 12, marginBottom: 10 },
  summaryLabel: { fontSize: 10, fontWeight: '800', color: COLORS.textMuted, marginBottom: 6, textTransform: 'uppercase' },
  summaryText: { fontSize: 13, color: COLORS.textPrimary, lineHeight: 20 },
  reasonBox: { backgroundColor: '#FFFBEB', borderRadius: 10, padding: 12, marginBottom: 10, borderLeftWidth: 3, borderLeftColor: '#F59E0B' },
  reasonLabel: { fontSize: 10, fontWeight: '800', color: '#92400E', marginBottom: 4 },
  reasonText: { fontSize: 12, color: '#78350F', lineHeight: 18 },
  leadBox: { backgroundColor: '#EFF6FF', borderRadius: 10, padding: 12, marginBottom: 10, borderLeftWidth: 3, borderLeftColor: '#3B82F6' },
  leadLabel: { fontSize: 10, fontWeight: '800', color: '#1E40AF', marginBottom: 4 },
  leadText: { fontSize: 12, color: '#1E3A8A', lineHeight: 18 },
  bufferBox: { backgroundColor: '#F0FDF4', borderRadius: 10, padding: 12, marginBottom: 10, borderLeftWidth: 3, borderLeftColor: '#22C55E' },
  bufferLabel: { fontSize: 10, fontWeight: '800', color: '#166534', marginBottom: 4 },
  bufferText: { fontSize: 12, color: '#14532D', lineHeight: 18 },
  linkBtn: { alignSelf: 'flex-end', paddingVertical: 4, paddingHorizontal: 8, marginTop: 4 },
  linkText: { fontSize: 12, color: COLORS.primary, fontWeight: '700' },
});
