// screens/PredictionListScreen.jsx — SCR-003 품목별 물가 예측
import { useEffect, useRef, useState } from 'react';
import {
  Animated,
  BackHandler,
  Dimensions,
  Easing,
  Platform,
  Pressable,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ActivityIndicator,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { CATEGORY_MAP, DIRECTION_MAP, MAGNITUDE_MAP } from '../constants/category';
import { COLORS } from '../constants/colors';
import { fetchPredictions } from '../lib/supabase';

const { width: SCREEN_W } = Dimensions.get('window');



const FILTER_CHIPS = [
  { label: '전체',       value: '',        type: 'all' },
  { label: '▲ 상승',    value: 'up',      type: 'dir' },
  { label: '▼ 하락',    value: 'down',    type: 'dir' },
  { label: '연료·에너지', value: 'fuel',   type: 'cat' },
  { label: '교통·여행',  value: 'travel',  type: 'cat' },
  { label: '전기·가스',  value: 'utility', type: 'cat' },
  { label: '식음료',     value: 'dining',  type: 'cat' },
];

function Chip({ label, active, onPress }) {
  return (
    <Pressable onPress={onPress} style={[styles.chip, active && styles.chipActive]}>
      <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
    </Pressable>
  );
}

// ── 예측 카드 ─────────────────────────────────────────────────
function PredictionCard({ item, onPress }) {
  const dir    = DIRECTION_MAP[item.direction] ?? DIRECTION_MAP.neutral;
  const mag    = MAGNITUDE_MAP[item.magnitude] ?? MAGNITUDE_MAP.low;
  const catName = CATEGORY_MAP[item.category] ?? item.category;
  const count  = item.news_analyses?.length ?? 0;

  const topBorderColor =
    item.direction === 'up'   ? COLORS.up :
    item.direction === 'down' ? COLORS.down : '#E5E7EB';

  let rangeText = '';
  if (item.direction === 'neutral') {
    rangeText = '─ 중립';
  } else {
    const sign = item.change_pct_min > 0 ? '+' : '';
    if (item.change_pct_min === item.change_pct_max) {
      rangeText = `${dir.label} 약${sign}${item.change_pct_min}%`;
    } else {
      const sign2 = item.change_pct_max > 0 ? '+' : '';
      rangeText = `${dir.label} ${sign}${item.change_pct_min} ~ ${sign2}${item.change_pct_max}%`;
    }
  }

  const magBadge = {
    high:   { bg: COLORS.highBg,  color: COLORS.highText },
    medium: { bg: COLORS.medBg,   color: COLORS.medText  },
    low:    { bg: COLORS.lowBg,   color: COLORS.lowText  },
  }[item.magnitude] ?? { bg: COLORS.lowBg, color: COLORS.lowText };

  const previewText = item.news_analyses?.[0]?.summary ?? '';

  return (
    <Pressable
      onPress={() => onPress(item)}
      style={[styles.predCard, { borderTopColor: topBorderColor }]}
    >
      <View style={styles.predCardTop}>
        <View style={{ flex: 1 }}>
          <Text style={styles.predCatEn}>{item.category}</Text>
          <Text style={styles.predCatKo}>{catName}</Text>
          <Text style={[styles.predRange, { color: dir.color }]}>{rangeText}</Text>
          <Text style={styles.predDesc} numberOfLines={1}>{item.result}</Text>
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

      <View style={styles.predDivider} />
      <View style={styles.predPreview}>
        <Text style={styles.predPreviewText} numberOfLines={1}>{previewText}</Text>
        <View style={styles.predCountBadge}>
          <Text style={styles.predCountText}>{count}건</Text>
        </View>
      </View>
    </Pressable>
  );
}

// ── 품목 상세 (슬라이드 전환) ─────────────────────────────────
function PredictionDetailView({ item, onClose, topInset }) {
  const slideAnim = useRef(new Animated.Value(SCREEN_W)).current;

  useEffect(() => {
    Animated.timing(slideAnim, {
      toValue: 0, duration: 280,
      easing: Easing.bezier(0.4, 0, 0.2, 1),
      useNativeDriver: true,
    }).start();
  }, []);

  const handleClose = () => {
    Animated.timing(slideAnim, {
      toValue: SCREEN_W, duration: 280,
      easing: Easing.bezier(0.4, 0, 0.2, 1),
      useNativeDriver: true,
    }).start(() => onClose());
  };

  const dir    = DIRECTION_MAP[item.direction] ?? DIRECTION_MAP.neutral;
  const mag    = MAGNITUDE_MAP[item.magnitude] ?? MAGNITUDE_MAP.low;
  const catName = CATEGORY_MAP[item.category] ?? item.category;
  const count  = item.news_analyses?.length ?? 0;

  let rangeText = '';
  if (item.direction === 'neutral') {
    rangeText = '─ 중립';
  } else {
    const sign = item.change_pct_min > 0 ? '+' : '';
    if (item.change_pct_min === item.change_pct_max) {
      rangeText = `${dir.label} 약${sign}${item.change_pct_min}%`;
    } else {
      const sign2 = item.change_pct_max > 0 ? '+' : '';
      rangeText = `${dir.label} ${sign}${item.change_pct_min} ~ ${sign2}${item.change_pct_max}%`;
    }
  }

  const magBadge = {
    high:   { bg: COLORS.highBg,  color: COLORS.highText },
    medium: { bg: COLORS.medBg,   color: COLORS.medText  },
    low:    { bg: COLORS.lowBg,   color: COLORS.lowText  },
  }[item.magnitude] ?? { bg: COLORS.lowBg, color: COLORS.lowText };

  const resultNodeBg    = item.direction === 'up'   ? COLORS.tagUpBg   : COLORS.tagDownBg;
  const resultNodeColor = item.direction === 'up'   ? COLORS.tagUpText : COLORS.tagDownText;

  return (
    <Animated.View style={[styles.detailRoot, { transform: [{ translateX: slideAnim }] }]}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.headerBg} />

      {/* 상세 헤더 */}
      <View style={[styles.detailHeader, { paddingTop: topInset + 10 }]}>
        <TouchableOpacity onPress={handleClose} style={styles.backBtn}>
          <Text style={styles.backText}>← 품목 예측</Text>
        </TouchableOpacity>
        <Text style={styles.detailCatName}>{catName}</Text>
        <Text style={[styles.detailRange, { color: item.direction === 'up' ? '#FF8A7A' : item.direction === 'down' ? '#6EE7B7' : '#B4B2A9' }]}>
          {rangeText}
        </Text>
        <View style={styles.detailMetaRow}>
          <View style={[styles.magBadge, { backgroundColor: magBadge.bg }]}>
            <Text style={[styles.magBadgeText, { color: magBadge.color }]}>{mag.label}</Text>
          </View>
          <Text style={styles.detailCountText}>{count}건의 인과관계</Text>
        </View>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.detailBody}>
        {/* 인과관계 체인 */}
        <Text style={styles.sectionLabel}>인과관계 체인</Text>
        <View style={styles.detailCard}>
          {/* 첫 번째 체인 행 */}
          <View style={styles.flowRow}>
            <View style={styles.flowEventNode}>
              <Text style={styles.flowEventText} numberOfLines={2}>{item.event}</Text>
            </View>
            <Text style={styles.flowArrow}>→</Text>
            <View style={[styles.flowResultNode, { backgroundColor: resultNodeBg }]}>
              <Text style={[styles.flowResultText, { color: resultNodeColor }]} numberOfLines={2}>
                {item.result}
              </Text>
            </View>
          </View>
          <Text style={styles.mechanismText} numberOfLines={2}>{item.mechanism}</Text>

          {/* 추가 뉴스 분석 */}
          {(item.news_analyses ?? []).slice(1).map((na) => (
            <View key={na.id}>
              <View style={styles.chainDivider} />
              <View style={styles.flowRow}>
                <View style={styles.flowEventNode}>
                  <Text style={styles.flowEventText} numberOfLines={1}>{na.summary}</Text>
                </View>
                <Text style={styles.flowArrow}>→</Text>
                <View style={[styles.flowResultNode, { backgroundColor: resultNodeBg }]}>
                  <Text style={[styles.flowResultText, { color: resultNodeColor }]}>{item.result}</Text>
                </View>
              </View>
            </View>
          ))}
        </View>

        {/* 요약 */}
        <Text style={[styles.sectionLabel, { marginTop: 14 }]}>요약</Text>
        <View style={styles.detailCard}>
          <Text style={styles.summaryText}>{item.result}</Text>
          <Text style={styles.summarySubText}>총 {count}건의 뉴스 분석</Text>
        </View>

        <View style={{ height: 30 }} />
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

  useEffect(() => {
    fetchPredictions()
      .then(data => { if (data?.length > 0) setPredictions(data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

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
          <Text style={styles.headerSub}>카테고리별 가격 변동</Text>
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

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.listContent}>
        <Text style={styles.listSectionLabel}>카테고리별 예측 ({filtered.length}건)</Text>
        {loading && <ActivityIndicator color={COLORS.headerBg} style={{ marginBottom: 12, marginTop: 10 }} />}
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
  headerSub:   { fontSize: 10, color: COLORS.headerAccent, marginTop: 2 },
  chipRow:     { paddingHorizontal: 16, paddingBottom: 8, gap: 8 },
  chip: {
    borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5,
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)',
  },
  chipActive:     { backgroundColor: COLORS.white },
  chipText:       { fontSize: 11, color: 'rgba(255,255,255,0.65)' },
  chipTextActive: { color: COLORS.headerBg, fontWeight: '700' },

  // List
  listContent:      { padding: 10 },
  listSectionLabel: {
    fontSize: 11, fontWeight: '500', color: COLORS.textMuted,
    letterSpacing: 0.3, marginBottom: 10, paddingHorizontal: 4,
  },

  // Prediction card
  predCard: {
    backgroundColor: COLORS.white, borderRadius: 14,
    borderTopWidth: 3, marginBottom: 12, overflow: 'hidden',
    ...Platform.select({
      ios:     { shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 8 },
      android: { elevation: 2 },
    }),
  },
  predCardTop:  { flexDirection: 'row', padding: 14, paddingBottom: 10 },
  predCatEn:    { fontSize: 10, color: COLORS.textMuted, marginBottom: 2 },
  predCatKo:    { fontSize: 14, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 4 },
  predRange:    { fontSize: 20, fontWeight: '700', marginBottom: 4 },
  predDesc:     { fontSize: 11, color: COLORS.textMuted },
  predRight:    { alignItems: 'flex-end', justifyContent: 'center' },
  magBadge:     { borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3, marginBottom: 6 },
  magBadgeText: { fontSize: 10, fontWeight: '600' },
  magDots:      { flexDirection: 'row', gap: 4 },
  magDot:       { width: 8, height: 8, borderRadius: 4 },
  predDivider:  { height: 0.5, backgroundColor: COLORS.border, marginHorizontal: 14 },
  predPreview:  { flexDirection: 'row', alignItems: 'center', padding: 10, paddingHorizontal: 14 },
  predPreviewText: { flex: 1, fontSize: 11, color: COLORS.textMuted },
  predCountBadge: { backgroundColor: '#F3F4F6', borderRadius: 6, paddingHorizontal: 6, paddingVertical: 2 },
  predCountText:  { fontSize: 10, color: COLORS.textMuted },

  // Detail
  sectionLabel: {
    fontSize: 11, fontWeight: '500', color: COLORS.textMuted,
    letterSpacing: 0.3, marginBottom: 8,
  },
  detailRoot:   { ...StyleSheet.absoluteFillObject, backgroundColor: COLORS.screenBg, zIndex: 100 },
  detailHeader: { backgroundColor: COLORS.headerBg, paddingHorizontal: 16, paddingBottom: 14 },
  backBtn:      { marginBottom: 10 },
  backText:     { fontSize: 13, color: COLORS.headerAccent },
  detailCatName: { fontSize: 15, color: COLORS.headerText, marginBottom: 4 },
  detailRange:   { fontSize: 26, fontWeight: '700', marginBottom: 8 },
  detailMetaRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  detailCountText: { fontSize: 11, color: COLORS.headerMuted },
  detailBody:    { padding: 14 },
  detailCard: {
    backgroundColor: COLORS.white, borderRadius: 14, padding: 14, marginBottom: 8,
    ...Platform.select({
      ios:     { shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 6 },
      android: { elevation: 1 },
    }),
  },

  // Flow nodes
  flowRow:        { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: 6, marginBottom: 8 },
  flowEventNode:  { backgroundColor: COLORS.highBg, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4, maxWidth: '40%' },
  flowEventText:  { fontSize: 11, color: COLORS.highText },
  flowArrow:      { fontSize: 11, color: COLORS.textMuted },
  flowResultNode: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4, maxWidth: '40%' },
  flowResultText: { fontSize: 11, fontWeight: '700' },
  mechanismText:  { fontSize: 11, color: COLORS.textMuted, lineHeight: 17 },
  chainDivider:   { height: 0.5, backgroundColor: COLORS.border, marginVertical: 10 },

  // Summary
  summaryText:    { fontSize: 14, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 4 },
  summarySubText: { fontSize: 11, color: COLORS.textMuted },
});
