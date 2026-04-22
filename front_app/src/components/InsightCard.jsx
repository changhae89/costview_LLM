// components/InsightCard.jsx
import { StyleSheet, Text, View } from 'react-native';
import { COLORS } from '../constants/colors';
import { TIME_HORIZON_MAP, GEO_SCOPE_MAP } from './PredictionCard';

export default function InsightCard({ newsAnalyses }) {
  const horizon = newsAnalyses.find(na => na.time_horizon)?.time_horizon;
  const geo = newsAnalyses.find(na => na.geo_scope)?.geo_scope;
  const buffers = newsAnalyses.map(na => na.buffer).filter(Boolean);
  const leads = newsAnalyses.map(na => na.leading_indicator).filter(Boolean);
  const reliabilityReasons = newsAnalyses.map(na => na.reliability_reason).filter(Boolean);

  const hasData = horizon || geo || buffers.length > 0 || leads.length > 0;
  if (!hasData) return null;

  const horizonInfo = horizon
    ? (TIME_HORIZON_MAP[horizon] ?? { label: horizon, icon: '⏱', color: '#888', bg: '#F3F4F6' })
    : null;
  const geoInfo = geo
    ? (GEO_SCOPE_MAP[geo] ?? { label: geo, icon: '📌' })
    : null;

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.title}>🤖 AI 심층 분석</Text>
        <View style={styles.beta}>
          <Text style={styles.betaText}>BETA</Text>
        </View>
      </View>

      <View style={styles.grid}>
        {horizonInfo ? (
          <View style={[styles.gridItem, { backgroundColor: horizonInfo.bg }]}>
            <Text style={styles.gridIcon}>{horizonInfo.icon}</Text>
            <View>
              <Text style={styles.gridLabel}>파급 기간</Text>
              <Text style={[styles.gridValue, { color: horizonInfo.color }]}>{horizonInfo.label}</Text>
            </View>
          </View>
        ) : null}
        {geoInfo ? (
          <View style={[styles.gridItem, { backgroundColor: '#F0FDF4' }]}>
            <Text style={styles.gridIcon}>{geoInfo.icon}</Text>
            <View>
              <Text style={styles.gridLabel}>영향 범위</Text>
              <Text style={[styles.gridValue, { color: '#166534' }]}>{geoInfo.label}</Text>
            </View>
          </View>
        ) : null}
      </View>

      {leads.length > 0 ? (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionIcon}>📊</Text>
            <Text style={styles.sectionLabel}>눈여겨볼 선행 지표</Text>
          </View>
          <Text style={styles.sectionText}>{leads[0]}</Text>
        </View>
      ) : null}

      {buffers.length > 0 ? (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionIcon}>🛡️</Text>
            <Text style={styles.sectionLabel}>완충 · 저항 요인</Text>
          </View>
          <Text style={styles.sectionText}>{buffers[0]}</Text>
        </View>
      ) : null}

      {reliabilityReasons.length > 0 ? (
        <View style={[styles.section, { borderBottomWidth: 0 }]}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionIcon}>💡</Text>
            <Text style={styles.sectionLabel}>AI 신뢰도 근거</Text>
          </View>
          <Text style={styles.sectionText}>{reliabilityReasons[0]}</Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.white, borderRadius: 20, padding: 16, marginBottom: 20,
    borderWidth: 1, borderColor: '#E0E7FF',
  },
  header: { flexDirection: 'row', alignItems: 'center', marginBottom: 14, gap: 8 },
  title: { fontSize: 13, fontWeight: '800', color: '#4F46E5', flex: 1 },
  beta: { backgroundColor: '#EDE9FE', borderRadius: 4, paddingHorizontal: 5, paddingVertical: 2 },
  betaText: { fontSize: 9, fontWeight: '800', color: '#7C3AED', letterSpacing: 0.5 },
  grid: { flexDirection: 'row', gap: 8, marginBottom: 12, flexWrap: 'wrap' },
  gridItem: { flexDirection: 'row', alignItems: 'center', borderRadius: 10, padding: 10, gap: 8, flex: 1, minWidth: 140 },
  gridIcon: { fontSize: 20 },
  gridLabel: { fontSize: 10, fontWeight: '600', color: COLORS.textMuted, marginBottom: 2 },
  gridValue: { fontSize: 12, fontWeight: '700' },
  section: { borderTopWidth: 1, borderTopColor: '#F3F4F6', paddingTop: 12, paddingBottom: 12 },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  sectionIcon: { fontSize: 14 },
  sectionLabel: { fontSize: 11, fontWeight: '800', color: COLORS.textPrimary },
  sectionText: { fontSize: 13, color: COLORS.textMuted, lineHeight: 19 },
});
