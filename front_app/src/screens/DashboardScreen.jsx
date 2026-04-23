// screens/DashboardScreen.jsx — SCR-001 대시보드
import { useEffect, useMemo, useState, useRef } from 'react';
import {
  ActivityIndicator,
  BackHandler,
  Platform,
  RefreshControl,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  Modal,
  Pressable,
  Animated,
  PanResponder,
  Dimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import DirectionDot from '../components/DirectionDot';
import ReliabilityBadge from '../components/ReliabilityBadge';
import { CATEGORY_MAP, DIRECTION_MAP, MAGNITUDE_MAP, formatCategory } from '../constants/category';
import { COLORS } from '../constants/colors';
import { formatDateTime, formatNumber, getBenchmarkText, getIndexDescription } from '../lib/helpers';
import { useDashboard } from '../hooks/useDashboard';
import NewsDetailView from '../components/NewsDetailView';


// ── 리스크 카드 ────────────────────────────────────────────────
function RiskCard({ itemKey, label, desc, value, change, date, maxValue, onPressDetail }) {
  const changeNum = Number(change);
  const changeColor = changeNum > 0 ? COLORS.up : COLORS.down;
  const changeText = changeNum > 0
    ? `▲+${changeNum.toFixed(1)}`
    : changeNum < 0
      ? `▼${Math.abs(changeNum).toFixed(1)}`
      : '─ 0.0';
  // 실제 값 비율로 게이지 계산 (0~100%)
  const fillPct = maxValue && maxValue > 0 && value != null
    ? Math.min(100, Math.max(5, (Number(value) / maxValue) * 100))
    : 60;

  // 비율에 따라 게이지 바 색상 결정
  // 0~24%: 파란색, 25~49%: 노란색, 50~74%: 주황색, 75~100%: 빨간색
  const gaugeColor =
    fillPct < 25 ? '#60A5FA' :
    fillPct < 50 ? '#FBBF24' :
    fillPct < 75 ? '#F97316' :
                   '#EF4444';

  return (
    <View style={styles.riskCard}>
      <Text style={styles.riskLabel}>{label}</Text>
      <TouchableOpacity 
        style={styles.infoBtn} 
        hitSlop={{ top: 15, bottom: 15, left: 15, right: 15 }}
        onPress={() => onPressDetail({ key: itemKey, label, value, date })}
      >
        <Text style={styles.infoIcon}>ⓘ</Text>
      </TouchableOpacity>
      {desc && <Text style={{fontSize: 8, color: COLORS.textLight, marginBottom: 4}}>{desc}</Text>}
      <Text style={styles.riskValue} numberOfLines={1}>{value !== null && value !== undefined && value !== '' ? formatNumber(value) : '-'}</Text>
      <View style={styles.riskBar}>
        <View style={[styles.riskBarFill, { width: `${fillPct}%`, backgroundColor: gaugeColor }]} />
      </View>
      <Text style={[styles.riskChange, { color: changeColor }]}>{changeText}</Text>
      {date ? <Text style={styles.riskDate}>{date}</Text> : null}
    </View>
  );
}

// ── 카테고리 행 ────────────────────────────────────────────────
function CategoryRow({ item, isLast }) {
  const catName = formatCategory(item.category);
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
function NewsRow({ item, isLast, onPress }) {
  const mainChain = item.causal_chains?.[0];
  const keywords = item.raw_news?.keyword?.slice(0, 3) ?? [];

  // 날짜/시간 포맷팅 (공용 헬퍼 사용)
  const dateStr = formatDateTime(item.raw_news?.origin_published_at ?? item.created_at);

  return (
    <TouchableOpacity 
      style={[styles.newsRow, !isLast && styles.rowBorder]}
      onPress={() => onPress(item)}
      activeOpacity={0.7}
    >
      <View style={styles.newsRowTop}>
        <DirectionDot direction={mainChain?.direction ?? 'neutral'} size={7} />
        <Text style={styles.newsTitle} numberOfLines={2}>{item.summary}</Text>
      </View>
      <View style={styles.newsRowInfo}>
        <Text style={styles.newsDateText}>{dateStr}</Text>
        <ReliabilityBadge reliability={item.reliability} />
      </View>
      <Text style={styles.newsSummaryEn} numberOfLines={1}>{item.raw_news?.title ?? ''}</Text>
      <View style={styles.tagRow}>
        {(item.raw_news?.increased_items ?? []).map(k => (
          <View key={k} style={[styles.tag, { backgroundColor: COLORS.tagUpBg }]}>
            <Text style={[styles.tagText, { color: COLORS.tagUpText }]}>▲{formatCategory(k)}</Text>
          </View>
        ))}
        {(item.raw_news?.decreased_items ?? []).map(k => (
          <View key={k} style={[styles.tag, { backgroundColor: COLORS.tagDownBg }]}>
            <Text style={[styles.tagText, { color: COLORS.tagDownText }]}>▼{formatCategory(k)}</Text>
          </View>
        ))}
        {keywords.map(k => (
          <View key={k} style={styles.tagGray}>
            <Text style={styles.tagGrayText}>{k}</Text>
          </View>
        ))}
      </View>
    </TouchableOpacity>
  );
}

export default function DashboardScreen() {
  const insets = useSafeAreaInsets();
  const { metrics, chains: rawChains, newsList, loading, refreshing, refetch } = useDashboard();
  const [selected, setSelected] = useState(null);

  const [selectedRisk, setSelectedRisk] = useState(null);

  // 애니메이션 & 제스처 (바텀 시트)
  const panY = useRef(new Animated.Value(0)).current;
  const resetPositionAnim = Animated.timing(panY, {
    toValue: 0,
    duration: 300,
    useNativeDriver: true,
  });
  const closeAnim = Animated.timing(panY, {
    toValue: Dimensions.get('window').height,
    duration: 300,
    useNativeDriver: true,
  });

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => false,
      onMoveShouldSetPanResponder: (_, gestureState) => gestureState.dy > 5,
      onPanResponderMove: (_, gestureState) => {
        if (gestureState.dy > 0) {
          panY.setValue(gestureState.dy);
        }
      },
      onPanResponderRelease: (_, gestureState) => {
        if (gestureState.dy > 150 || gestureState.vy > 1.0) {
          closeAnim.start(() => setSelectedRisk(null));
        } else {
          resetPositionAnim.start();
        }
      },
    })
  ).current;

  useEffect(() => {
    if (selectedRisk) {
      panY.setValue(0);
    }
  }, [selectedRisk, panY]);

  // 카테고리별 그룹핑 (중복 체인 카운팅)
  const chains = useMemo(() => {
    if (!rawChains?.length) return [];
    const grouped = {};
    rawChains.forEach(c => {
      if (!grouped[c.category]) {
        grouped[c.category] = { ...c, news_count: 1 };
      } else {
        grouped[c.category].news_count += 1;
      }
    });
    return Object.values(grouped);
  }, [rawChains]);

  const news = useMemo(() => newsList.slice(0, 5), [newsList]);

  // 뒤로가기 핸들링
  useEffect(() => {
    const onBackPress = () => {
      if (selectedRisk) {
        setSelectedRisk(null);
        return true;
      }
      if (selected) {
        setSelected(null);
        return true;
      }
      return false;
    };
    const sub = BackHandler.addEventListener('hardwareBackPress', onBackPress);
    return () => sub.remove();
  }, [selected, selectedRisk]);

  const latest = metrics?.latest ?? {};
  const prev   = metrics?.prev ?? {};

  const CARDS = [
    { key: 'ai_gpr', label: '글로벌 불안지수', desc: '글로벌 불안지수', val: latest.ai_gpr_index, pval: prev.ai_gpr_index, date: latest.dates?.ai_gpr_index ?? latest.reference_date, max: 300 },
    { key: 'krw_usd', label: '원/달러 환율', desc: '거시 경제 환율', val: latest.krw_usd_rate, pval: prev.krw_usd_rate, date: latest.dates?.krw_usd_rate ?? latest.reference_date, max: 2000 },
    { key: 'wti', label: 'WTI 원유', desc: '국제 원유가 (달러)', val: latest.fred_wti, pval: prev.fred_wti, date: latest.dates?.fred_wti ?? latest.reference_date, max: 150 },
    { key: 'cpi', label: '한국 소비자물가', desc: '총지수 (2020=100)', val: latest.cpi_total, pval: prev.cpi_total, date: latest.dates?.cpi_total ?? latest.reference_date, max: 150 },
    { key: 'fed', label: '미 10년 국채', desc: '미국 10년물 금리 (%)', val: latest.fred_treasury_10y, pval: prev.fred_treasury_10y, date: latest.dates?.fred_treasury_10y ?? latest.reference_date, max: 8 },
  ];

  return (
    <View style={styles.root}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.headerBg} />

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
                itemKey={c.key}
                label={c.label} 
                desc={c.desc} 
                value={c.val} 
                change={(c.val ?? 0) - (c.pval ?? 0)} 
                date={c.date}
                maxValue={c.max}
                onPressDetail={setSelectedRisk}
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
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={refetch}
            tintColor={COLORS.primary}
            colors={[COLORS.primary]}
          />
        }
      >
        {loading && <ActivityIndicator color={COLORS.primary} style={{ marginBottom: 12 }} />}


        {/* 카테고리별 가격 영향 */}
        <Text style={styles.sectionLabel}>카테고리별 가격 영향</Text>
        <View style={styles.card}>
          {chains.length === 0 && !loading ? (
            <Text style={styles.emptyText}>데이터가 없습니다.</Text>
          ) : chains.map((item, i) => (
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
          {news.length === 0 && !loading ? (
            <Text style={styles.emptyText}>뉴스가 없습니다.</Text>
          ) : news.map((item, i) => (
            <NewsRow 
              key={item.id} 
              item={item} 
              isLast={i === news.length - 1} 
              onPress={setSelected}
            />
          ))}
        </View>

        <View style={{ height: 16 }} />
      </ScrollView>

      {/* 뉴스 상세 보기 연동 */}
      {selected && (
        <NewsDetailView 
          item={selected} 
          onClose={() => setSelected(null)} 
          topInset={insets.top}
          customBackText="대시보드"
        />
      )}

      {/* 리스크 상세 벤치마크 바텀 시트 */}
      <Modal
        visible={!!selectedRisk}
        transparent
        animationType="slide"
        onRequestClose={() => setSelectedRisk(null)}
      >
        <Pressable style={styles.modalOverlay} onPress={() => setSelectedRisk(null)}>
          <Animated.View
            style={[
              styles.bottomSheet,
              { paddingBottom: Math.max(insets.bottom, 20), transform: [{ translateY: panY }] }
            ]}
            {...panResponder.panHandlers}
          >
            <Pressable onPress={e => e.stopPropagation()}>
              <View style={styles.sheetHandle} />
              <Text style={styles.sheetTitle}>{selectedRisk?.label}</Text>
              
              {/* 지표 설명 */}
              <Text style={styles.sheetDescription}>
                {selectedRisk ? getIndexDescription(selectedRisk.key) : ''}
              </Text>

              <View style={{ flexDirection: 'row', alignItems: 'baseline', marginBottom: 16 }}>
                <Text style={styles.sheetValue}>{selectedRisk?.value !== null && selectedRisk?.value !== undefined ? formatNumber(selectedRisk?.value) : '-'}</Text>
                <Text style={styles.sheetDate}>{selectedRisk?.date ? `(${selectedRisk?.date})` : ''}</Text>
              </View>
              <View style={styles.sheetContentBox}>
                <Text style={styles.sheetBenchmarkText}>
                  {selectedRisk ? getBenchmarkText(selectedRisk.key, selectedRisk.value) : ''}
                </Text>
              </View>
              {selectedRisk?.key === 'ai_gpr' && (
                <Text style={styles.sheetDisclaimer}>
                  본 글로벌 불안지수는 지정학적 위험 지수(GPR Index) 방법론을 참고하여 본 서비스의 AI가 실시간 뉴스 기반으로 분석한 결과입니다.
                </Text>
              )}
            </Pressable>
          </Animated.View>
        </Pressable>
      </Modal>
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
    backgroundColor: COLORS.white,
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 12,
  },
  riskLabel:   { fontSize: 10, fontWeight: '700', color: COLORS.textMuted, marginBottom: 2 },
  riskValue:   { fontSize: 18, fontWeight: '700', color: COLORS.headerText },
  riskBar: {
    height: 3,
    backgroundColor: COLORS.border,
    borderRadius: 2,
    marginVertical: 4,
  },
  riskBarFill: { height: 3, backgroundColor: COLORS.primaryAccent, borderRadius: 2 },
  riskChange:  { fontSize: 10 },
  riskDate: { position: 'absolute', right: 10, bottom: 8, fontSize: 9, color: COLORS.textLight },
  errorBox: { backgroundColor: '#FEF2F2', borderRadius: 12, padding: 14, marginBottom: 12, borderWidth: 1, borderColor: '#FECACA' },
  errorText: { fontSize: 13, fontWeight: '700', color: '#991B1B', marginBottom: 4 },
  errorSub: { fontSize: 11, color: '#B91C1C' },
  emptyText: { padding: 14, fontSize: 13, color: COLORS.textMuted, textAlign: 'center' },

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
  newsRowTop:  { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 4, gap: 6 },
  newsTitle:   { flex: 1, fontSize: 13, fontWeight: '700', color: COLORS.textPrimary, lineHeight: 18 },
  newsRowInfo: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  newsDateText: { fontSize: 10, color: COLORS.textLight, fontWeight: '500', marginLeft: 13 },
  newsSummaryEn: { fontSize: 11, color: COLORS.textMuted, marginBottom: 8, marginLeft: 15 },
  tagRow:      { flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginLeft: 15 },
  tag:         { borderRadius: 4, paddingHorizontal: 5, paddingVertical: 2 },
  tagText:     { fontSize: 10, fontWeight: '600' },
  tagGray:     { backgroundColor: '#F3F4F6', borderRadius: 4, paddingHorizontal: 5, paddingVertical: 2 },
  tagGrayText: { fontSize: 10, color: COLORS.textMuted },

  // Info Button
  infoBtn: { position: 'absolute', top: 10, right: 10, opacity: 0.6 },
  infoIcon: { fontSize: 12, color: COLORS.textMuted },

  // Bottom Sheet Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  bottomSheet: {
    backgroundColor: COLORS.white,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingHorizontal: 24,
    paddingTop: 7,
  },
  sheetHandle: {
    width: 40,
    height: 4,
    backgroundColor: '#E5E7EB',
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 20,
  },
  sheetTitle: { fontSize: 13, color: COLORS.textMuted, fontWeight: '600', marginBottom: 4 },
  sheetDescription: { fontSize: 11, color: COLORS.textLight, marginBottom: 12, lineHeight: 16 },
  sheetValue: { fontSize: 32, fontWeight: '800', color: COLORS.textPrimary, marginRight: 8 },
  sheetDate:  { fontSize: 13, color: COLORS.textLight, fontWeight: '500' },
  sheetContentBox: {
    backgroundColor: '#F9FAFB',
    borderRadius: 12,
    padding: 16,
    marginTop: 8,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#F3F4F6',
  },
  sheetBenchmarkText: {
    fontSize: 15,
    lineHeight: 22,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },
  sheetDisclaimer: {
    fontSize: 10,
    color: COLORS.textLight,
    lineHeight: 14,
    marginTop: 8,
    textAlign: 'center',
  },
});
