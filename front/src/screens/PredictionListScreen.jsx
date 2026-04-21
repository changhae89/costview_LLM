// screens/PredictionListScreen.jsx — SCR-003 품목별 물가 예측 (v2)
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Animated,
  BackHandler,
  Dimensions,
  Easing,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { CATEGORY_MAP, DIRECTION_MAP, MAGNITUDE_MAP, formatCategory } from '../constants/category';
import { COLORS } from '../constants/colors';
import { fetchPredictions } from '../lib/supabase';

const { width: SCREEN_W } = Dimensions.get('window');

// ── 시간 지평 / 지역 범위 레이블 매핑 ──────────────────────────
const TIME_HORIZON_MAP = {
  short:  { label: '단기 (1~3개월)', icon: '⚡', color: '#D85A30', bg: '#FEF3EB' },
  medium: { label: '중기 (3~6개월)', icon: '📅', color: '#B45309', bg: '#FEFCE8' },
  long:   { label: '장기 (6개월+)',  icon: '🔭', color: '#0369A1', bg: '#EFF6FF' },
};
const GEO_SCOPE_MAP = {
  domestic: { label: '국내 한정',   icon: '🇰🇷' },
  global:   { label: '글로벌 영향', icon: '🌐' },
  regional: { label: '지역 한정',   icon: '📍' },
};

const FILTER_CHIPS = [
  { label: '전체', value: '', type: 'all' },
  { label: '▲ 상승', value: 'up', type: 'dir' },
  { label: '▼ 하락', value: 'down', type: 'dir' },
  { label: '연료·에너지', value: 'fuel', type: 'cat' },
  { label: '교통·여행', value: 'travel', type: 'cat' },
  { label: '전기·가스', value: 'utility', type: 'cat' },
  { label: '식음료', value: 'dining', type: 'cat' },
];

function Chip({ label, active, onPress }) {
  return (
    <Pressable onPress={onPress} style={[styles.chip, active && styles.chipActive]}>
      <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
    </Pressable>
  );
}

// ── 파급 기간 배지 ──────────────────────────────────────────────
function TimeHorizonBadge({ value }) {
  if (!value) return null;
  const info = TIME_HORIZON_MAP[value] ?? { label: value, icon: '⏱', color: '#888', bg: '#F3F4F6' };
  return (
    <View style={[styles.horizonBadge, { backgroundColor: info.bg }]}>
      <Text style={styles.horizonIcon}>{info.icon}</Text>
      <Text style={[styles.horizonText, { color: info.color }]}>{info.label}</Text>
    </View>
  );
}

// ── 지역 범위 배지 ──────────────────────────────────────────────
function GeoScopeBadge({ value }) {
  if (!value) return null;
  const info = GEO_SCOPE_MAP[value] ?? { label: value, icon: '📌' };
  return (
    <View style={styles.geoBadge}>
      <Text style={styles.geoIcon}>{info.icon}</Text>
      <Text style={styles.geoText}>{info.label}</Text>
    </View>
  );
}

// ── 예측 카드 ─────────────────────────────────────────────────
function PredictionCard({ item, onPress }) {
  const dir = DIRECTION_MAP[item.direction] ?? DIRECTION_MAP.neutral;
  const mag = MAGNITUDE_MAP[item.magnitude] ?? MAGNITUDE_MAP.low;
  const catName = formatCategory(item.category);
  const count = item.news_analyses?.length ?? 0;

  // 첫 번째 뉴스의 time_horizon / geo_scope 사용 (일반적으로 동일)
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
    if (item.change_pct_min == null && item.change_pct_max == null) return '변동폭 미상';
    const minVal = item.change_pct_min;
    const maxVal = item.change_pct_max;
    const signMin = minVal > 0 ? '+' : '';
    const signMax = maxVal > 0 ? '+' : '';
    if (minVal === maxVal) return `약 ${signMin}${minVal}%`;
    const minStr = minVal != null ? minVal : '?';
    const maxStr = maxVal != null ? maxVal : '?';
    return `${signMin}${minStr} ~ ${signMax}${maxStr}%`;
  }, [item]);

  const magBadge = {
    high: { bg: COLORS.highBg, color: COLORS.highText },
    medium: { bg: COLORS.medBg, color: COLORS.medText },
    low: { bg: COLORS.lowBg, color: COLORS.lowText },
  }[item.magnitude] ?? { bg: COLORS.lowBg, color: COLORS.lowText };

  return (
    <Pressable
      onPress={() => onPress(item)}
      style={[styles.predCard, { borderTopColor: topBorderColor }]}
    >
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

        {/* 파급기간 + 지역 뱃지 행 */}
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

// ── AI 심층 분석 인사이트 카드 ─────────────────────────────────
function InsightCard({ newsAnalyses }) {
  // 대표 인사이트: time_horizon, geo_scope, buffer, leading_indicator 중 가장 빈도 높은 것 추출
  const horizon = newsAnalyses.find(na => na.time_horizon)?.time_horizon;
  const geo = newsAnalyses.find(na => na.geo_scope)?.geo_scope;
  const buffers = newsAnalyses.map(na => na.buffer).filter(Boolean);
  const leads = newsAnalyses.map(na => na.leading_indicator).filter(Boolean);
  const reliabilityReasons = newsAnalyses.map(na => na.reliability_reason).filter(Boolean);

  const hasData = horizon || geo || buffers.length > 0 || leads.length > 0;
  if (!hasData) return null;

  const horizonInfo = horizon ? (TIME_HORIZON_MAP[horizon] ?? { label: horizon, icon: '⏱', color: '#888', bg: '#F3F4F6' }) : null;
  const geoInfo = geo ? (GEO_SCOPE_MAP[geo] ?? { label: geo, icon: '📌' }) : null;

  return (
    <View style={styles.insightCard}>
      <View style={styles.insightHeader}>
        <Text style={styles.insightTitle}>🤖 AI 심층 분석</Text>
        <View style={styles.insightBeta}>
          <Text style={styles.insightBetaText}>BETA</Text>
        </View>
      </View>

      <View style={styles.insightGrid}>
        {horizonInfo ? (
          <View style={[styles.insightItem, { backgroundColor: horizonInfo.bg }]}>
            <Text style={styles.insightItemIcon}>{horizonInfo.icon}</Text>
            <View>
              <Text style={styles.insightItemLabel}>파급 기간</Text>
              <Text style={[styles.insightItemValue, { color: horizonInfo.color }]}>{horizonInfo.label}</Text>
            </View>
          </View>
        ) : null}

        {geoInfo ? (
          <View style={[styles.insightItem, { backgroundColor: '#F0FDF4' }]}>
            <Text style={styles.insightItemIcon}>{geoInfo.icon}</Text>
            <View>
              <Text style={styles.insightItemLabel}>영향 범위</Text>
              <Text style={[styles.insightItemValue, { color: '#166534' }]}>{geoInfo.label}</Text>
            </View>
          </View>
        ) : null}
      </View>

      {leads.length > 0 ? (
        <View style={styles.insightSection}>
          <View style={styles.insightSectionHeader}>
            <Text style={styles.insightSectionIcon}>📊</Text>
            <Text style={styles.insightSectionLabel}>눈여겨볼 선행 지표</Text>
          </View>
          <Text style={styles.insightSectionText}>{leads[0]}</Text>
        </View>
      ) : null}

      {buffers.length > 0 ? (
        <View style={styles.insightSection}>
          <View style={styles.insightSectionHeader}>
            <Text style={styles.insightSectionIcon}>🛡️</Text>
            <Text style={styles.insightSectionLabel}>완충 · 저항 요인</Text>
          </View>
          <Text style={styles.insightSectionText}>{buffers[0]}</Text>
        </View>
      ) : null}

      {reliabilityReasons.length > 0 ? (
        <View style={[styles.insightSection, { borderBottomWidth: 0 }]}>
          <View style={styles.insightSectionHeader}>
            <Text style={styles.insightSectionIcon}>💡</Text>
            <Text style={styles.insightSectionLabel}>AI 신뢰도 근거</Text>
          </View>
          <Text style={styles.insightSectionText}>{reliabilityReasons[0]}</Text>
        </View>
      ) : null}
    </View>
  );
}

// ── 품목 상세 (슬라이드 전환) ─────────────────────────────────
function PredictionDetailView({ item, onClose, topInset }) {
  const slideAnim = useRef(new Animated.Value(SCREEN_W)).current;

  useEffect(() => {
    Animated.timing(slideAnim, {
      toValue: 0, duration: 320,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();
  }, [slideAnim]);

  const handleClose = () => {
    Animated.timing(slideAnim, {
      toValue: SCREEN_W, duration: 250,
      easing: Easing.in(Easing.cubic),
      useNativeDriver: true,
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
    if (item.change_pct_min == null && item.change_pct_max == null) return '변동폭 미상';
    const minVal = item.change_pct_min;
    const maxVal = item.change_pct_max;
    const signMin = minVal > 0 ? '+' : '';
    const signMax = maxVal > 0 ? '+' : '';
    if (minVal === maxVal) return `약 ${signMin}${minVal}%`;
    const minStr = minVal != null ? minVal : '?';
    const maxStr = maxVal != null ? maxVal : '?';
    return `${signMin}${minStr} ~ ${signMax}${maxStr}%`;
  }, [item]);

  const magBadge = {
    high: { bg: COLORS.highBg, color: COLORS.highText },
    medium: { bg: COLORS.medBg, color: COLORS.medText },
    low: { bg: COLORS.lowBg, color: COLORS.lowText },
  }[item.magnitude] ?? { bg: COLORS.lowBg, color: COLORS.lowText };

  return (
    <Animated.View style={[styles.detailRoot, { transform: [{ translateX: slideAnim }] }]}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.headerBg} />

      {/* 상세 헤더 */}
      <View style={[styles.detailHeader, { paddingTop: topInset + 10 }]}>
        <TouchableOpacity onPress={handleClose} style={styles.backBtn} hitSlop={15}>
          <Text style={styles.backText}>← 목록으로 돌아가기</Text>
        </TouchableOpacity>

        <View style={styles.detailTitleRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.detailCatName}>{catName}</Text>
            <Text style={[styles.detailRange, { color: COLORS.white }]}>{rangeText}</Text>
          </View>
          <View style={styles.detailHeaderRight}>
            <View style={[styles.magBadge, { backgroundColor: magBadge.bg }]}>
              <Text style={[styles.magBadgeText, { color: magBadge.color }]}>{mag.label}</Text>
            </View>
            <Text style={[styles.detailDirLabel, { color: dir.color === '#111827' ? COLORS.white : dir.color }]}>{dir.label} 추세</Text>
          </View>
        </View>

        {/* 헤더 내 배지 뱃지 (파급기간 + 지역) */}
        {(timeHorizon || geoScope) ? (
          <View style={[styles.badgeRow, { marginTop: 12 }]}>
            {timeHorizon ? <TimeHorizonBadge value={timeHorizon} /> : null}
            {geoScope ? <GeoScopeBadge value={geoScope} /> : null}
          </View>
        ) : null}
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.detailBody}>

        {/* 인과관계 시각화 (Flow) */}
        <Text style={styles.sectionLabel}>인과관계 메커니즘</Text>
        <View style={styles.detailCard}>
          <View style={styles.visualFlow}>
            {/* 원인 노드 */}
            <View style={styles.flowNodeBox}>
              <View style={[styles.nodeIcon, { backgroundColor: COLORS.highBg }]}>
                <Text style={{ fontSize: 16 }}>⚡</Text>
              </View>
              <View style={styles.nodeContent}>
                <Text style={styles.nodeTag}>원인 (Event)</Text>
                <Text style={styles.nodeText}>{item.event}</Text>
              </View>
            </View>

            <View style={styles.flowLineContainer}>
              <View style={styles.flowLine} />
              <View style={styles.flowArrowTip} />
            </View>

            {/* 메커니즘 (가교) */}
            <View style={styles.flowNodeBox}>
              <View style={[styles.nodeIcon, { backgroundColor: COLORS.medBg }]}>
                <Text style={{ fontSize: 16 }}>⚙️</Text>
              </View>
              <View style={styles.nodeContent}>
                <Text style={styles.nodeTag}>전달 경로 (Mechanism)</Text>
                <Text style={styles.nodeText}>{item.mechanism}</Text>
              </View>
            </View>

            <View style={styles.flowLineContainer}>
              <View style={styles.flowLine} />
              <View style={styles.flowArrowTip} />
            </View>

            {/* 결과 노드 */}
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

        {/* 월간 영향액 카드 */}
        {item.monthly_impact ? (
          <View style={styles.monthlyImpactCard}>
            <View style={styles.monthlyImpactLeft}>
              <Text style={styles.monthlyImpactLabel}>📦 월간 예상 영향액</Text>
              <Text style={styles.monthlyImpactValue}>약 {item.monthly_impact.toLocaleString()}원</Text>
            </View>
            <Text style={styles.monthlyImpactSub}>가계 평균 기준</Text>
          </View>
        ) : null}

        {/* AI 심층 분석 인사이트 */}
        <InsightCard newsAnalyses={newsAnalyses} />

        {/* 근거 뉴스 리스트 */}
        <Text style={[styles.sectionLabel, { marginTop: 8 }]}>분석 근거 뉴스 ({newsAnalyses.length}건)</Text>
        {newsAnalyses.map((na) => {
          const raw = na.raw_news;
          const date = raw?.origin_published_at?.slice(0, 10) ?? na.created_at?.slice(0, 10);
          const reliabilityPct = Math.round((na.reliability ?? 0) * 100);

          return (
            <View key={na.id} style={styles.newsDetailCard}>
              <View style={styles.newsDetailHeader}>
                <Text style={styles.newsSource}>기사 발행일: {date}</Text>
                <View style={styles.reliabilityBadge}>
                  <Text style={styles.reliabilityText}>신뢰도 {reliabilityPct}%</Text>
                </View>
              </View>
              <Text style={styles.newsTitle}>{raw?.title ?? '제목 없음'}</Text>

              {na.related_indicators && na.related_indicators.length > 0 ? (
                <View style={styles.relIndRow}>
                  {na.related_indicators.map((ind, i) => (
                    <View key={i} style={styles.relIndTag}>
                      <Text style={styles.relIndTagText}>#{formatCategory(ind)}</Text>
                    </View>
                  ))}
                </View>
              ) : null}

              <View style={styles.summaryBox}>
                <Text style={styles.summaryLabel}>🤖 AI 분석 요약</Text>
                <Text style={styles.summaryText}>{na.summary}</Text>
              </View>

              {/* 신뢰도 근거 */}
              {na.reliability_reason ? (
                <View style={styles.reasonBox}>
                  <Text style={styles.reasonLabel}>💡 신뢰도 근거</Text>
                  <Text style={styles.reasonText}>{na.reliability_reason}</Text>
                </View>
              ) : null}

              {/* 선행 지표 */}
              {na.leading_indicator ? (
                <View style={styles.leadBox}>
                  <Text style={styles.leadLabel}>📊 선행 지표</Text>
                  <Text style={styles.leadText}>{na.leading_indicator}</Text>
                </View>
              ) : null}

              {/* 완충 요인 */}
              {na.buffer ? (
                <View style={styles.bufferBox}>
                  <Text style={styles.bufferLabel}>🛡️ 완충 요인</Text>
                  <Text style={styles.bufferText}>{na.buffer}</Text>
                </View>
              ) : null}

              {raw?.news_url ? (
                <TouchableOpacity
                  style={styles.newsLinkBtn}
                  onPress={() => Linking.openURL(raw.news_url).catch(() => { })}
                >
                  <Text style={styles.newsLinkText}>뉴스 원문 읽기 ↗</Text>
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

// ── 목록 메인 ─────────────────────────────────────────────────
export default function PredictionListScreen() {
  const insets = useSafeAreaInsets();
  const [predictions, setPredictions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [dirFilter, setDirFilter] = useState('');
  const [catFilter, setCatFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [hasError, setHasError] = useState(false);

  const loadData = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setHasError(false);

      const data = await fetchPredictions();
      if (data?.length > 0) setPredictions(data);
    } catch (e) {
      console.warn('[PredictionListScreen] loadData error:', e);
      setHasError(true);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const onBackPress = () => {
      if (selected) {
        setSelected(null);
        return true;
      }
      return false;
    };
    const subscription = BackHandler.addEventListener('hardwareBackPress', onBackPress);
    return () => subscription.remove();
  }, [selected]);

  const filtered = predictions.filter(item => {
    if (dirFilter && item.direction !== dirFilter) return false;
    if (catFilter && item.category !== catFilter) return false;
    return true;
  });

  const isAllActive = dirFilter === '' && catFilter === '';

  if (selected) {
    return (
      <PredictionDetailView
        item={selected}
        onClose={() => setSelected(null)}
        topInset={insets.top}
      />
    );
  }

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.headerBg} />

      <View style={[styles.header, { paddingTop: insets.top + 10 }]}>
        <View style={styles.headerTop}>
          <Text style={styles.headerTitle}>품목 예측</Text>
          <Text style={styles.headerSub}>카테고리별 가격 변동 · AI 분석</Text>
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
          {FILTER_CHIPS.map(c => {
            const active =
              c.type === 'all'
                ? isAllActive
                : c.type === 'dir'
                  ? dirFilter === c.value
                  : catFilter === c.value;
            return (
              <Chip
                key={c.value + c.type}
                label={c.label}
                active={active}
                onPress={() => {
                  if (c.type === 'all') { setDirFilter(''); setCatFilter(''); }
                  else if (c.type === 'dir') setDirFilter(dirFilter === c.value ? '' : c.value);
                  else setCatFilter(catFilter === c.value ? '' : c.value);
                }}
              />
            );
          })}
        </ScrollView>
      </View>

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => loadData(true)}
            tintColor={COLORS.headerBg}
            colors={[COLORS.headerBg]}
          />
        }
      >
        <Text style={styles.listSectionLabel}>카테고리별 예측 ({filtered.length}건)</Text>
        {loading && <ActivityIndicator color={COLORS.headerBg} style={{ marginBottom: 12, marginTop: 10 }} />}
        {hasError && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>🔌 데이터를 불러오지 못했어요.</Text>
            <Text style={styles.errorSub}>네트워크 연결을 확인해주세요.</Text>
          </View>
        )}
        {!loading && !hasError && filtered.length === 0 && (
          <Text style={styles.emptyText}>예측 데이터가 없습니다.</Text>
        )}
        {filtered.map(item => (
          <PredictionCard key={item.id} item={item} onPress={setSelected} />
        ))}
        <View style={{ height: 20 }} />
      </ScrollView>
    </View>
  );
}

// ── StyleSheet ─────────────────────────────────────────────────
const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: COLORS.screenBg },

  // Header
  header: { backgroundColor: COLORS.headerBg, paddingBottom: 10 },
  headerTop: { paddingHorizontal: 16, marginBottom: 10 },
  headerTitle: { fontSize: 17, fontWeight: '700', color: COLORS.headerText },
  headerSub: { fontSize: 10, color: COLORS.headerAccent, marginTop: 2 },
  chipRow: { paddingHorizontal: 16, paddingBottom: 8, gap: 8 },
  chip: {
    borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5,
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)',
  },
  chipActive: { backgroundColor: COLORS.white },
  chipText: { fontSize: 11, color: 'rgba(255,255,255,0.65)' },
  chipTextActive: { color: COLORS.headerBg, fontWeight: '700' },

  // List
  listContent: { padding: 12 },
  listSectionLabel: {
    fontSize: 11, fontWeight: '600', color: COLORS.textMuted,
    letterSpacing: 0.5, marginBottom: 12, paddingHorizontal: 4,
    textTransform: 'uppercase',
  },

  // Badge row (on card)
  badgeRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap', marginBottom: 10 },
  horizonBadge: { flexDirection: 'row', alignItems: 'center', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4, gap: 4 },
  horizonIcon: { fontSize: 11 },
  horizonText: { fontSize: 11, fontWeight: '700' },
  geoBadge: { flexDirection: 'row', alignItems: 'center', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4, gap: 4, backgroundColor: '#F0FDF4' },
  geoIcon: { fontSize: 11 },
  geoText: { fontSize: 11, fontWeight: '700', color: '#166534' },

  // Prediction card
  predCard: {
    backgroundColor: COLORS.white, borderRadius: 16,
    borderTopWidth: 4, marginBottom: 16, overflow: 'hidden',
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
  errorBox: { backgroundColor: '#FEF2F2', borderRadius: 12, padding: 14, marginBottom: 12, borderWidth: 1, borderColor: '#FECACA' },
  errorText: { fontSize: 13, fontWeight: '700', color: '#991B1B', marginBottom: 4 },
  errorSub: { fontSize: 11, color: '#B91C1C' },
  emptyText: { padding: 24, fontSize: 13, color: COLORS.textMuted, textAlign: 'center' },

  // Monthly impact card (detail view)
  monthlyImpactCard: {
    backgroundColor: '#EFF6FF', borderRadius: 14, padding: 16, marginBottom: 16,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    borderLeftWidth: 4, borderLeftColor: '#3B82F6',
  },
  monthlyImpactLeft: {},
  monthlyImpactLabel: { fontSize: 11, fontWeight: '700', color: '#1E40AF', marginBottom: 4 },
  monthlyImpactValue: { fontSize: 22, fontWeight: '900', color: '#1E3A8A' },
  monthlyImpactSub: { fontSize: 10, color: '#93C5FD' },

  // AI Insight Card
  insightCard: {
    backgroundColor: COLORS.white, borderRadius: 20, padding: 16, marginBottom: 20,
    borderWidth: 1, borderColor: '#E0E7FF',
    ...Platform.select({
      ios: { shadowColor: '#6366F1', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.08, shadowRadius: 12 },
      android: { elevation: 3 },
    }),
  },
  insightHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 14, gap: 8 },
  insightTitle: { fontSize: 13, fontWeight: '800', color: '#4F46E5', flex: 1 },
  insightBeta: { backgroundColor: '#EDE9FE', borderRadius: 4, paddingHorizontal: 5, paddingVertical: 2 },
  insightBetaText: { fontSize: 9, fontWeight: '800', color: '#7C3AED', letterSpacing: 0.5 },
  insightGrid: { flexDirection: 'row', gap: 8, marginBottom: 12, flexWrap: 'wrap' },
  insightItem: { flexDirection: 'row', alignItems: 'center', borderRadius: 10, padding: 10, gap: 8, flex: 1, minWidth: 140 },
  insightItemIcon: { fontSize: 20 },
  insightItemLabel: { fontSize: 10, fontWeight: '600', color: COLORS.textMuted, marginBottom: 2 },
  insightItemValue: { fontSize: 12, fontWeight: '700' },
  insightSection: {
    borderTopWidth: 1, borderTopColor: '#F3F4F6',
    paddingTop: 12, paddingBottom: 12,
  },
  insightSectionHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  insightSectionIcon: { fontSize: 14 },
  insightSectionLabel: { fontSize: 11, fontWeight: '800', color: COLORS.textPrimary },
  insightSectionText: { fontSize: 13, color: COLORS.textMuted, lineHeight: 19 },

  // Detail
  detailRoot: { ...StyleSheet.absoluteFillObject, backgroundColor: COLORS.screenBg, zIndex: 100 },
  detailHeader: { backgroundColor: COLORS.headerBg, paddingHorizontal: 16, paddingBottom: 20 },
  backBtn: { marginBottom: 16 },
  backText: { fontSize: 13, color: 'rgba(255,255,255,0.7)', fontWeight: '600' },
  detailTitleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' },
  detailCatName: { fontSize: 16, color: COLORS.headerAccent, fontWeight: '600', marginBottom: 2 },
  detailRange: { fontSize: 32, fontWeight: '900', color: COLORS.white },
  detailHeaderRight: { alignItems: 'flex-end' },
  detailDirLabel: { fontSize: 14, fontWeight: '700', marginTop: 4 },
  detailBody: { padding: 16 },
  sectionLabel: { fontSize: 12, fontWeight: '800', color: COLORS.textPrimary, letterSpacing: 0.8, marginBottom: 12, textTransform: 'uppercase' },
  detailCard: {
    backgroundColor: COLORS.white, borderRadius: 20, padding: 20, marginBottom: 16,
    ...Platform.select({
      ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.1, shadowRadius: 12 },
      android: { elevation: 3 },
    }),
  },

  // Visual Flow
  visualFlow: {},
  flowNodeBox: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  nodeIcon: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  nodeContent: { flex: 1 },
  nodeTag: { fontSize: 10, fontWeight: '800', color: COLORS.textLight, marginBottom: 2, textTransform: 'uppercase' },
  nodeText: { fontSize: 14, color: COLORS.textPrimary, fontWeight: '600', lineHeight: 20 },
  flowLineContainer: { height: 30, marginLeft: 20, justifyContent: 'center' },
  flowLine: { width: 2, flex: 1, backgroundColor: '#E5E7EB' },
  flowArrowTip: { position: 'absolute', bottom: -2, left: -3, width: 8, height: 8, borderRightWidth: 2, borderBottomWidth: 2, borderColor: '#E5E7EB', transform: [{ rotate: '45deg' }] },

  // News Detail Card
  newsDetailCard: {
    backgroundColor: COLORS.white, borderRadius: 16, padding: 16, marginBottom: 12,
    borderLeftWidth: 4, borderLeftColor: COLORS.headerBg,
    ...Platform.select({ ios: { shadowOpacity: 0.05, shadowRadius: 5 }, android: { elevation: 1 } }),
  },
  newsDetailHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  newsSource: { fontSize: 11, fontWeight: '700', color: COLORS.headerBg },
  reliabilityBadge: { backgroundColor: '#ECFDF5', borderRadius: 5, paddingHorizontal: 6, paddingVertical: 2 },
  reliabilityText: { fontSize: 10, fontWeight: '700', color: '#065F46' },
  newsDate: { fontSize: 11, color: COLORS.textLight },
  newsTitle: { fontSize: 15, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 12, lineHeight: 22 },
  relIndRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 12 },
  relIndTag: { backgroundColor: '#E0F2FE', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2 },
  relIndTagText: { fontSize: 10, fontWeight: '700', color: '#0369A1' },
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
  newsLinkBtn: { alignSelf: 'flex-end', paddingVertical: 4, paddingHorizontal: 8, marginTop: 4 },
  newsLinkText: { fontSize: 12, color: COLORS.headerBg, fontWeight: '700' },
});
