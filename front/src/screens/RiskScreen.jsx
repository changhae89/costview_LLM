// screens/RiskScreen.jsx — SCR-004 리스크 지수
import { useEffect, useMemo, useState, useRef } from 'react';
import {
  ActivityIndicator,
  Animated,
  Dimensions,
  Easing,
  Platform,
  Pressable,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  View,
  Modal,
  TouchableOpacity
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LineChart } from 'react-native-chart-kit';
import { COLORS } from '../constants/colors';
import { calcStats, formatNumber } from '../lib/helpers';
import { fetchUnifiedDaily, fetchUnifiedMonthly } from '../lib/supabase';

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get('window');
const CHART_MIN_WIDTH = SCREEN_W - 28;

const VIEW_CATEGORIES = [
  { id: 'gpr', label: '지정학' },
  { id: 'macro', label: '거시/금리' },
  { id: 'commodity', label: '원자재' },
  { id: 'inflation', label: '물가/실물' },
];

const ALL_SERIES = {
  gpr: [
    { key: 'ai_gpr_index', label: 'AI 지정학 위험 지수', color: '#D85A30', strokeWidth: 2 },
    { key: 'oil_disruptions', label: '석유 차질(÷10)', color: '#EF9F27', strokeWidth: 1.5, div: 10 },
    { key: 'gpr_original', label: '기존 GPR', color: '#888780', MathWidth: 1 },
    { key: 'non_oil_gpr', label: '비석유', color: '#2E86AB', strokeWidth: 1.5 },
  ],
  macro: [
    { key: 'krw_usd_rate', label: '원/달러 환율', color: '#4361EE', strokeWidth: 1.5 },
    { key: 'kr_bond_3y', label: '국고채 3년물(%)', color: '#F72585', strokeWidth: 1.5 },
    { key: 'fred_treasury_10y', label: '미 10년물(%)', color: '#3A0CA3', strokeWidth: 1.5 },
    { key: 'fred_treasury_2y', label: '미 2년물(%)', color: '#4CC9F0', strokeWidth: 1.5 },
    { key: 'fred_fedfunds', label: '미 기준금리(%)', color: '#FCAF58', strokeWidth: 1.5 },
  ],
  commodity: [
    { key: 'fred_wti', label: 'WTI 원유', color: '#E63946', strokeWidth: 1.5 },
    { key: 'fred_brent', label: '브렌트유', color: '#F4A261', strokeWidth: 1.5 },
    { key: 'import_price_crude_oil', label: '원유 수입물가', color: '#2A9D8F', strokeWidth: 1.5 },
    { key: 'import_price_natural_gas', label: '천연가스 수입물가', color: '#E9C46A', strokeWidth: 1.5 },
  ],
  inflation: [
    { key: 'cpi_total', label: '한국 소비자물가', color: '#E63946', strokeWidth: 1.5 },
    { key: 'core_cpi', label: '한국 근원물가', color: '#F1FAEE', strokeWidth: 1.5 },
    { key: 'cpi_agro', label: '농축수산물', color: '#A8DADC', strokeWidth: 1.5 },
    { key: 'fred_cpi', label: '미국 CPI', color: '#457B9D', strokeWidth: 1.5 },
    { key: 'fred_pce', label: '미국 PCE', color: '#1D3557', strokeWidth: 1.5 },
  ]
};

// ── 탭 버튼 ───────────────────────────────────────────────────
function TabBtn({ label, active, onPress }) {
  return (
    <Pressable onPress={onPress} style={[styles.tabBtn, active && styles.tabBtnActive]}>
      <Text style={[styles.tabBtnText, active && styles.tabBtnTextActive]}>{label}</Text>
    </Pressable>
  );
}

// ── 범위 칩 ───────────────────────────────────────────────────
function RangeChip({ label, active, onPress }) {
  return (
    <Pressable onPress={onPress} style={[styles.rangeChip, active && styles.rangeChipActive]}>
      <Text style={[styles.rangeChipText, active && styles.rangeChipTextActive]}>{label}</Text>
    </Pressable>
  );
}

// ── 통계 셀 ───────────────────────────────────────────────────
function StatCell({ label, value, sub, subColor }) {
  return (
    <View style={styles.statCell}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
      {sub ? <Text style={[styles.statSub, subColor && { color: subColor }]}>{sub}</Text> : null}
    </View>
  );
}

// ── 메인 화면 ─────────────────────────────────────────────────
export default function RiskScreen() {
  const insets = useSafeAreaInsets();
  const [category, setCategory] = useState('gpr');
  const [tab, setTab] = useState('daily');   // 'daily' | 'monthly'
  const [range, setRange] = useState('20');
  const [daily, setDaily] = useState([]);
  const [monthly, setMonthly] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tooltip, setTooltip] = useState(null);

  // 모달 및 필터 State
  const [showFilterModal, setShowFilterModal] = useState(false);
  const [showFullscreen, setShowFullscreen] = useState(false);
  const [startDate, setStartDate] = useState('2026-03-01');
  const [endDate, setEndDate] = useState('2026-03-31');

  // 모두 보이게 초기화
  const initVisible = {};
  Object.values(ALL_SERIES).flat().forEach(s => { initVisible[s.key] = true; });
  const [visibleSeries, setVisibleSeries] = useState(initVisible);

  const currentSeries = ALL_SERIES[category];

  // 애니메이션 State (마스킹 기법)
  const animMaskX = useRef(new Animated.Value(0)).current;
  const fsAnimMaskX = useRef(new Animated.Value(0)).current;

  // 날짜 자동 하이픈 포맷팅 함수
  const handleDateInput = (text, setter) => {
    const digits = text.replace(/\D/g, '');
    let formatted = digits;
    if (digits.length >= 5 && digits.length <= 6) {
      formatted = `${digits.slice(0, 4)}-${digits.slice(4)}`;
    } else if (digits.length >= 7) {
      formatted = `${digits.slice(0, 4)}-${digits.slice(4, 6)}-${digits.slice(6, 8)}`;
    }
    setter(formatted);
  };

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const [d, m] = await Promise.all([
          fetchUnifiedDaily(),
          fetchUnifiedMonthly(),
        ]);
        if (d?.length > 0) setDaily(d);
        if (m?.length > 0) setMonthly(m);
      } catch { /* mock 유지 */ }
      finally { setLoading(false); }
    })();
  }, []);

  const rawData = tab === 'daily'
    ? daily
    : monthly.length > 0 ? monthly : daily;

  const slicedData = useMemo(() => {
    let result = rawData;
    if (range === 'all') {
      result = rawData;
    } else if (range === 'custom' && startDate && endDate) {
      result = rawData.filter(d => d.reference_date >= startDate && d.reference_date <= endDate);
    } else {
      const n = range === '10' ? 10 : 20;
      result = rawData.slice(-n);
    }

    if (result.length > 150) {
      const step = Math.ceil(result.length / 150);
      result = result.filter((_, i) => i % step === 0);
    }
    return result;
  }, [rawData, range, startDate, endDate]);

  const pStats = useMemo(() => {
    if (!currentSeries[0]) return null;
    return calcStats(slicedData, currentSeries[0].key);
  }, [slicedData, currentSeries]);

  const sStats = useMemo(() => {
    if (currentSeries.length < 2) return null;
    return calcStats(slicedData, currentSeries[1].key);
  }, [slicedData, currentSeries]);

  // 그래프 가로 확대/스크롤 (보이는 데이터 포인트당 35px 지정)
  const chartWidth = Math.max(CHART_MIN_WIDTH, slicedData.length * 35);
  const fsChartWidth = Math.max(chartWidth, SCREEN_W * 1.5);

  useEffect(() => {
    animMaskX.setValue(0);
    Animated.timing(animMaskX, {
      toValue: chartWidth, // 마스크를 우측으로 끝까지 밀어냄
      duration: 2500,      // 너무 빠르지 않도록 1.2초 -> 2.5초로 연장
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true, // 60FPS 네이티브 구동 보장
    }).start();

    fsAnimMaskX.setValue(0);
    Animated.timing(fsAnimMaskX, {
      toValue: fsChartWidth, // 크게보기용 더 넓은 너비
      duration: 2000,      // 1.2초 -> 2.0초로 연장
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();
  }, [slicedData, visibleSeries, chartWidth, fsChartWidth, showFullscreen, category, animMaskX, fsAnimMaskX]);

  const { chartLabels, activeDatasets } = useMemo(() => {
    const labels = [];
    const step = Math.ceil(slicedData.length / (chartWidth / 55));

    const seriesMap = {};
    currentSeries.forEach(s => { seriesMap[s.key] = []; });

    for (let i = 0; i < slicedData.length; i++) {
      const d = slicedData[i];
      labels.push(i % step === 0 ? (d.reference_date?.slice(2) ?? '') : '');

      currentSeries.forEach(s => {
        let val = Number(d[s.key]) || 0;
        if (s.div) val = val / s.div;
        seriesMap[s.key].push(val);
      });
    }

    const datasets = currentSeries
      .filter(s => visibleSeries[s.key])
      .map(s => ({
        data: seriesMap[s.key],
        color: () => s.color,
        strokeWidth: s.strokeWidth || 1.5,
      }));

    if (datasets.length === 0) {
      datasets.push({ data: [0], color: () => 'transparent' });
    }

    return { chartLabels: labels, activeDatasets: datasets };
  }, [slicedData, chartWidth, visibleSeries, currentSeries]);

  const activeSeries = useMemo(() => currentSeries.filter(s => visibleSeries[s.key]), [currentSeries, visibleSeries]);

  const dateRange = slicedData.length >= 2
    ? `${slicedData[0].reference_date} ~ ${slicedData[slicedData.length - 1].reference_date}`
    : '';

  const formatTooltipValue = (series, row) => {
    if (!row) return '-';
    const raw = row[series.key];
    if (raw === null || raw === undefined || raw === '') return '-';
    const numeric = Number(raw);
    if (Number.isNaN(numeric)) return '-';
    const value = series.div ? numeric / series.div : numeric;
    return formatNumber(value);
  };

  const renderLineChart = (width, height, isFullscreen = false) => (
    <View style={{ width, height, position: 'relative' }}>
      <LineChart
        data={{
          labels: chartLabels,
          datasets: activeDatasets,
        }}
        width={width}
        height={height}
        withInnerLines
        withOuterLines={false}
        withShadow={false}
        fromZero
        chartConfig={{
          backgroundColor: COLORS.white,
          backgroundGradientFrom: COLORS.white,
          backgroundGradientTo: COLORS.white,
          decimalPlaces: 0,
          color: (opacity = 1) => `rgba(30,58,95,${opacity})`,
          labelColor: (opacity = 1) => `rgba(107,114,128,${opacity})`,
          propsForDots: { r: '4', strokeWidth: '1.5', stroke: COLORS.white },
          propsForBackgroundLines: { strokeDasharray: '', stroke: '#E5E7EB' },
        }}
        onDataPointClick={({ index, value }) => {
          const row = slicedData[index];
          if (!row) return;
          setTooltip({ index, date: row.reference_date, value });
        }}
        style={{ marginLeft: -12, borderRadius: 8 }}
      />
      <View style={styles.hitOverlay} pointerEvents="box-none">
        {slicedData.map((row, index) => {
          const left = `${(index / Math.max(1, slicedData.length)) * 100}%`;
          const width = `${100 / Math.max(1, slicedData.length)}%`;
          return (
            <Pressable
              key={`hit-${index}`}
              onPress={() => setTooltip({ index, date: row.reference_date, value: row })}
              style={[styles.hitArea, { left, width }]}
            />
          );
        })}
      </View>
      <Animated.View
        pointerEvents="none"
        style={{
          position: 'absolute',
          top: 0, bottom: 0, right: 0, left: 0,
          backgroundColor: COLORS.white,
          transform: [{ translateX: isFullscreen ? fsAnimMaskX : animMaskX }]
        }}
      />
    </View>
  );

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.headerBg} />

      {/* 헤더 */}
      <View style={[styles.header, { paddingTop: insets.top + 10 }]}>
        <View style={styles.headerTop}>
          <Text style={styles.headerTitle}>리스크/통합 지표</Text>
          <Text style={styles.headerSub}>지정학 및 거시경제 동향</Text>
        </View>

        <View style={styles.tabRow}>
          {VIEW_CATEGORIES.map(cat => (
            <TabBtn key={cat.id} label={cat.label} active={category === cat.id} onPress={() => setCategory(cat.id)} />
          ))}
        </View>

        <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
          <View style={styles.tabRow}>
            <TabBtn label="일간" active={tab === 'daily'} onPress={() => setTab('daily')} />
            <TabBtn label="월간" active={tab === 'monthly'} onPress={() => setTab('monthly')} />
          </View>
          <View style={styles.rangeRow}>
            <RangeChip label="10일" active={range === '10'} onPress={() => setRange('10')} />
            <RangeChip label="20일" active={range === '20'} onPress={() => setRange('20')} />
            <RangeChip label="필터" active={range === 'custom'} onPress={() => setShowFilterModal(true)} />
          </View>
        </View>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.body}>
        {loading && <ActivityIndicator color={COLORS.headerBg} style={{ marginBottom: 12 }} />}

        {/* 통계 카드 */}
        {pStats && (
          <View style={styles.statsGrid}>
            <StatCell
              label={currentSeries[0]?.label}
              value={formatNumber(pStats.last)}
              sub={pStats.change > 0 ? `▲+${pStats.change}` : `▼${pStats.change}`}
              subColor={pStats.change > 0 ? COLORS.up : COLORS.down}
            />
            {sStats && currentSeries[1] && (
              <StatCell
                label={currentSeries[1]?.label}
                value={formatNumber(sStats.last)}
                sub={sStats.change > 0 ? `▲+${sStats.change}` : `▼${sStats.change}`}
                subColor={sStats.change > 0 ? COLORS.up : COLORS.down}
              />
            )}
            <StatCell label="기간 최고" value={formatNumber(pStats.max)} sub={pStats.maxDate ?? ''} />
            <StatCell label="기간 최저" value={formatNumber(pStats.min)} sub={pStats.minDate ?? ''} />
          </View>
        )}

        {/* 차트 영역 */}
        <View style={styles.chartCard}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <View>
              <Text style={styles.chartTitle}>{tab === 'daily' ? '일간' : '월간'} 리스크/지수 추이</Text>
              <Text style={styles.chartSubtitle}>{dateRange}</Text>
            </View>
            <TouchableOpacity style={styles.expandBtn} onPress={() => setShowFullscreen(true)}>
              <Text style={styles.expandBtnText}>⛶ 크게 보기</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.legendRow}>
            {currentSeries.map(s => {
              const isActive = visibleSeries[s.key];
              return (
                <Pressable
                  key={s.key}
                  style={[styles.legendItem, !isActive && { opacity: 0.3 }]}
                  onPress={() => setVisibleSeries(prev => ({ ...prev, [s.key]: !prev[s.key] }))}
                >
                  <View style={[styles.legendDot, { backgroundColor: s.color }]} />
                  <Text style={[styles.legendText, !isActive && { textDecorationLine: 'line-through' }]}>
                    {s.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          {slicedData.length >= 2 ? (
            <ScrollView horizontal showsHorizontalScrollIndicator={true} bounces={false}>
              {renderLineChart(chartWidth, 190)}
            </ScrollView>
          ) : (
            <Text style={{ textAlign: 'center', color: '#999', marginVertical: 30 }}>데이터 부족</Text>
          )}

          <Text style={styles.chartNote}>* 차트 포인트를 터치하면 해당 날짜의 지수 값을 확인할 수 있습니다.</Text>

          {/* ── 터치 툴팁 패널 ─────────────────────────────── */}
          {tooltip && (
            <View style={styles.tooltipPanel}>
              <View style={styles.tooltipPanelHeader}>
                <Text style={styles.tooltipDate}>{tooltip.date}</Text>
                <Pressable onPress={() => setTooltip(null)} hitSlop={8}>
                  <Text style={styles.tooltipClose}>닫기</Text>
                </Pressable>
              </View>
              {activeSeries.map(s => (
                <View key={s.key} style={styles.tooltipRow}>
                  <View style={[styles.legendDot, { backgroundColor: s.color }]} />
                  <Text style={styles.tooltipLabel}>{s.label}</Text>
                  <Text style={[styles.tooltipValue, { color: s.color }]}>
                    {formatTooltipValue(s, slicedData[tooltip.index])}
                  </Text>
                </View>
              ))}
            </View>
          )}
        </View>
        <View style={{ height: 20 }} />
      </ScrollView>

      {/* 날짜 필터 모달 */}
      <Modal visible={showFilterModal} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>사용자 지정 기간 설정</Text>
            <Text style={styles.modalSub}>YYYY-MM-DD 형식 (숫자만 입력 시 자동 변환)</Text>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>시작 날짜</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="ex) 2026-03-01"
                value={startDate}
                onChangeText={(t) => handleDateInput(t, setStartDate)}
                keyboardType="numeric"
                maxLength={10}
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>종료 날짜</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="ex) 2026-03-31"
                value={endDate}
                onChangeText={(t) => handleDateInput(t, setEndDate)}
                keyboardType="numeric"
                maxLength={10}
              />
            </View>

            <View style={styles.modalBtnRow}>
              <TouchableOpacity style={styles.modalBtnCancel} onPress={() => setShowFilterModal(false)}>
                <Text style={styles.modalBtnTextCancel}>취소</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modalBtnApply}
                onPress={() => { setRange('custom'); setShowFilterModal(false); }}
              >
                <Text style={styles.modalBtnTextApply}>그래프 적용</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* 차트 가로/세로 전체화면 확대 모달 */}
      <Modal visible={showFullscreen} animationType="slide" onRequestClose={() => setShowFullscreen(false)}>
        <View style={styles.fsRoot}>
          <View style={[styles.fsHeader, { paddingTop: Platform.OS === 'ios' ? insets.top + 5 : 15 }]}>
            <Text style={styles.fsTitle}>상세 차트 분석</Text>
            <TouchableOpacity onPress={() => setShowFullscreen(false)} style={styles.fsCloseBtn}>
              <Text style={styles.fsCloseText}>✕ 닫기</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.fsBody}>
            <Text style={styles.chartSubtitle}>{dateRange} 세부 동향</Text>

            <View style={styles.legendRow}>
              {currentSeries.map(s => {
                const isActive = visibleSeries[s.key];
                return (
                  <Pressable
                    key={s.key}
                    style={[styles.legendItem, !isActive && { opacity: 0.3 }]}
                    onPress={() => setVisibleSeries(prev => ({ ...prev, [s.key]: !prev[s.key] }))}
                  >
                    <View style={[styles.legendDot, { backgroundColor: s.color }]} />
                    <Text style={[styles.legendText, !isActive && { textDecorationLine: 'line-through' }]}>
                      {s.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            <ScrollView horizontal showsHorizontalScrollIndicator={true} bounces={false}>
              {renderLineChart(fsChartWidth, SCREEN_H * 0.65, true)}
            </ScrollView>
          </View>
        </View>
      </Modal>

    </View>
  );
}

// ── StyleSheet ─────────────────────────────────────────────────
const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: COLORS.screenBg },

  // Header
  header: { backgroundColor: COLORS.headerBg, paddingHorizontal: 16, paddingBottom: 12 },
  headerTop: { marginBottom: 12 },
  headerTitle: { fontSize: 17, fontWeight: '700', color: COLORS.headerText },
  headerSub: { fontSize: 10, color: COLORS.headerAccent, marginTop: 2 },

  // Tabs
  tabRow: { flexDirection: 'row', gap: 8, marginBottom: 10 },
  tabBtn: { borderRadius: 20, paddingHorizontal: 16, paddingVertical: 5, borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)' },
  tabBtnActive: { backgroundColor: COLORS.white },
  tabBtnText: { fontSize: 12, color: 'rgba(255,255,255,0.65)' },
  tabBtnTextActive: { color: COLORS.headerBg, fontWeight: '700' },

  // Range chips
  rangeRow: { flexDirection: 'row', gap: 8 },
  rangeChip: { borderRadius: 14, paddingHorizontal: 12, paddingVertical: 4, borderWidth: 1, borderColor: 'rgba(255,255,255,0.15)' },
  rangeChipActive: { borderColor: 'rgba(255,255,255,0.5)', backgroundColor: 'rgba(255,255,255,0.1)' },
  rangeChipText: { fontSize: 11, color: 'rgba(255,255,255,0.5)' },
  rangeChipTextActive: { color: 'rgba(255,255,255,1)' },

  // Body
  body: { padding: 14 },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 14 },
  statCell: {
    flex: 1, minWidth: '45%', backgroundColor: COLORS.white, borderRadius: 14, padding: 14,
    ...Platform.select({ ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 6 }, android: { elevation: 1 } }),
  },
  statLabel: { fontSize: 11, color: COLORS.textMuted, marginBottom: 4 },
  statValue: { fontSize: 18, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 2, flexShrink: 1 },
  statSub: { fontSize: 11, color: COLORS.textMuted },

  // Chart
  chartCard: {
    backgroundColor: COLORS.white, borderRadius: 14, padding: 14,
    ...Platform.select({ ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 8 }, android: { elevation: 2 } }),
  },
  chartTitle: { fontSize: 13, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 2 },
  chartSubtitle: { fontSize: 10, color: COLORS.textMuted, marginBottom: 12 },
  expandBtn: { backgroundColor: '#F3F4F6', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8 },
  expandBtnText: { fontSize: 11, fontWeight: '700', color: COLORS.textPrimary },
  legendRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 12 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 6, paddingHorizontal: 10, backgroundColor: '#F3F4F6', borderRadius: 8 },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  legendText: { fontSize: 12, color: COLORS.textPrimary, fontWeight: '600' },
  chartNote: { fontSize: 10, color: COLORS.textLight, marginTop: 4 },
  hitOverlay: {
    ...StyleSheet.absoluteFillObject,
    flexDirection: 'row',
  },
  hitArea: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    backgroundColor: 'transparent',
  },

  // Tooltip panel
  tooltipPanel: {
    marginTop: 12,
    backgroundColor: '#F8F9FF',
    borderRadius: 10,
    padding: 10,
    borderWidth: 1,
    borderColor: '#E8EAFE',
  },
  tooltipPanelHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  tooltipDate:  { fontSize: 12, fontWeight: '700', color: COLORS.textPrimary },
  tooltipClose: { fontSize: 14, color: COLORS.textMuted, padding: 2 },
  tooltipRow:   { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 },
  tooltipLabel: { flex: 1, fontSize: 11, color: COLORS.textMuted },
  tooltipValue: { fontSize: 12, fontWeight: '700' },

  // Filter Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalContent: {
    width: '100%', maxWidth: 320, backgroundColor: COLORS.white, borderRadius: 16, padding: 20,
    ...Platform.select({ ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.1, shadowRadius: 10 }, android: { elevation: 4 } })
  },
  modalTitle: { fontSize: 16, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 4 },
  modalSub: { fontSize: 11, color: COLORS.textMuted, marginBottom: 16 },
  inputGroup: { marginBottom: 12 },
  inputLabel: { fontSize: 11, color: COLORS.textMuted, marginBottom: 4, fontWeight: '600' },
  modalInput: { borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 14, color: COLORS.textPrimary, backgroundColor: '#F9FAFB' },
  modalBtnRow: { flexDirection: 'row', justifyContent: 'flex-end', gap: 8, marginTop: 10 },
  modalBtnCancel: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: 8 },
  modalBtnTextCancel: { fontSize: 14, color: COLORS.textMuted, fontWeight: '600' },
  modalBtnApply: { backgroundColor: COLORS.headerBg, paddingHorizontal: 16, paddingVertical: 10, borderRadius: 8 },
  modalBtnTextApply: { fontSize: 14, color: COLORS.white, fontWeight: '700' },

  // Fullscreen Modal
  fsRoot: { flex: 1, backgroundColor: COLORS.white },
  fsHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: COLORS.headerBg, paddingHorizontal: 16, paddingBottom: 16 },
  fsTitle: { fontSize: 18, fontWeight: '700', color: COLORS.white },
  fsCloseBtn: { padding: 8, backgroundColor: 'rgba(255,255,255,0.2)', borderRadius: 8 },
  fsCloseText: { fontSize: 13, fontWeight: '700', color: COLORS.white },
  fsBody: { flex: 1, padding: 20, paddingTop: 30 },
});
