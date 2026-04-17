// screens/NewsListScreen.jsx — SCR-002 뉴스 목록 & 상세
import { useEffect, useState } from 'react';
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
  TextInput,
  TouchableOpacity,
  View,
  ActivityIndicator,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import DirectionDot from '../components/DirectionDot';
import ReliabilityBadge from '../components/ReliabilityBadge';
import { CATEGORY_MAP, DIRECTION_MAP, MAGNITUDE_MAP } from '../constants/category';
import { COLORS } from '../constants/colors';
import { fetchNewsList } from '../lib/supabase';

const { width: SCREEN_W } = Dimensions.get('window');


const DIR_CHIPS = [
  { label: '전체',   value: '' },
  { label: '▲ 상승', value: 'up' },
  { label: '▼ 하락', value: 'down' },
];
const CAT_CHIPS = [
  { label: '연료·에너지', value: 'fuel' },
  { label: '교통·여행',   value: 'travel' },
  { label: '전기·가스',   value: 'utility' },
  { label: '식음료',      value: 'dining' },
  { label: '신뢰도 高',   value: '__high__' },
];

// ── 필터 칩 ───────────────────────────────────────────────────
function Chip({ label, active, onPress }) {
  return (
    <Pressable onPress={onPress} style={[styles.chip, active && styles.chipActive]}>
      <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
    </Pressable>
  );
}

function getNewsDateFromRawNews(rawNews, createdAt) {
  const published = rawNews?.origin_published_at ?? rawNews?.published_date ?? '';
  if (published) return published.slice(0, 10);

  const rawId = rawNews?.id;
  if (rawId !== null && rawId !== undefined) {
    const idStr = String(rawId).trim();
    const match = idStr.match(/^(\d{4})[-_]?(\d{2})[-_]?(\d{2})/);
    if (match) return `${match[1]}-${match[2]}-${match[3]}`;
  }

  return createdAt?.slice(0, 10) ?? '';
}

function NewsCard({ item, onPress }) {
  const mainChain = item.causal_chains?.[0];
  const dateStr = getNewsDateFromRawNews(item.raw_news, item.created_at);

  return (
    <Pressable onPress={() => onPress(item)} style={styles.newsCard}>
      <View style={styles.newsCardTop}>
        <DirectionDot direction={mainChain?.direction ?? 'neutral'} size={7} />
        <Text style={styles.newsCardTitle} numberOfLines={2}>{item.summary}</Text>
        <ReliabilityBadge reliability={item.reliability} />
      </View>
      <Text style={styles.newsCardEn} numberOfLines={1}>{item.raw_news?.title ?? ''}</Text>
      <View style={styles.newsCardBottom}>
        <Text style={styles.newsCardDate}>{dateStr}</Text>
        <View style={styles.tagRow}>
          {(item.raw_news?.increased_items ?? []).map(k => (
            <View key={k} style={[styles.tag, { backgroundColor: COLORS.tagUpBg }]}>
              <Text style={[styles.tagText, { color: COLORS.tagUpText }]}>▲{k}</Text>
            </View>
          ))}
          {(item.raw_news?.keyword ?? []).slice(0, 2).map(k => (
            <View key={k} style={styles.tagGray}>
              <Text style={styles.tagGrayText}>{k}</Text>
            </View>
          ))}
        </View>
      </View>
    </Pressable>
  );
}

// ── 뉴스 상세 (슬라이드 전환) ─────────────────────────────────
function NewsDetailView({ item, onClose, topInset }) {
  const [slideAnim] = useState(() => new Animated.Value(SCREEN_W));

  useEffect(() => {
    Animated.timing(slideAnim, {
      toValue: 0,
      duration: 280,
      easing: Easing.bezier(0.4, 0, 0.2, 1),
      useNativeDriver: true,
    }).start();
  }, [slideAnim]);

  const handleClose = () => {
    Animated.timing(slideAnim, {
      toValue: SCREEN_W,
      duration: 280,
      easing: Easing.bezier(0.4, 0, 0.2, 1),
      useNativeDriver: true,
    }).start(() => onClose());
  };

  const mainChain  = item.causal_chains?.[0];
  const dir        = mainChain ? (DIRECTION_MAP[mainChain.direction] ?? DIRECTION_MAP.neutral) : DIRECTION_MAP.neutral;
  const catName    = mainChain ? (CATEGORY_MAP[mainChain.category] ?? mainChain.category) : '';
  const dateStr    = getNewsDateFromRawNews(item.raw_news, item.created_at);
  const reliabilityPct = Math.round((item.reliability ?? 0) * 100);

  return (
    <Animated.View style={[styles.detailRoot, { transform: [{ translateX: slideAnim }] }]}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.headerBg} />

      {/* 상세 헤더 */}
      <View style={[styles.detailHeader, { paddingTop: topInset + 10 }]}>
        <TouchableOpacity onPress={handleClose} style={styles.backBtn}>
          <Text style={styles.backText}>← 뉴스 목록</Text>
        </TouchableOpacity>
        <Text style={styles.detailTitle} numberOfLines={3}>{item.summary}</Text>
        <Text style={styles.detailTitleEn} numberOfLines={2}>{item.raw_news?.title ?? ''}</Text>
        <View style={styles.detailMetaRow}>
          <Text style={styles.detailDate}>{dateStr}</Text>
          <ReliabilityBadge reliability={item.reliability} />
          <View style={styles.dirBadge}>
            <Text style={[styles.dirBadgeText, { color: dir.dotColor === '#D85A30' ? '#FF8A7A' : '#6EE7B7' }]}>
              {dir.label}
            </Text>
          </View>
          {catName ? (
            <View style={styles.catBadge}>
              <Text style={styles.catBadgeText}>{catName}</Text>
            </View>
          ) : null}
        </View>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.detailBody}>
        {/* AI 분석 요약 */}
        <Text style={styles.sectionLabel}>AI 분석 요약</Text>
        <View style={styles.detailCard}>
          <Text style={styles.detailCardText}>{item.summary}</Text>
          <View style={styles.reliabilityRow}>
            <Text style={styles.relaLabel}>신뢰도</Text>
            <View style={styles.relaBar}>
              <View style={[styles.relaFill, { width: `${reliabilityPct}%` }]} />
            </View>
            <Text style={styles.relaPct}>{reliabilityPct}%</Text>
          </View>
        </View>

        {/* 관련 지표 */}
        {mainChain?.event ? (
          <>
            <Text style={[styles.sectionLabel, { marginTop: 14 }]}>관련 지표</Text>
            <View style={styles.detailCard}>
              <View style={styles.relatedTag}>
                <Text style={styles.relatedTagText}>{mainChain.event}</Text>
              </View>
            </View>
          </>
        ) : null}

        {/* 영향 품목 */}
        <Text style={[styles.sectionLabel, { marginTop: 14 }]}>영향 품목</Text>
        <View style={styles.detailCard}>
          <View style={styles.impactRow}>
            <View style={styles.impactCol}>
              <Text style={styles.impactHeader}>▲ 급등</Text>
              {(item.raw_news?.increased_items ?? []).length > 0
                ? (item.raw_news.increased_items.map(k => (
                    <View key={k} style={[styles.impactTag, { backgroundColor: COLORS.tagUpBg }]}>
                      <Text style={{ fontSize: 11, color: COLORS.tagUpText, fontWeight: '600' }}>{k}</Text>
                    </View>
                  )))
                : <Text style={styles.impactNone}>없음</Text>
              }
            </View>
            <View style={styles.impactDivider} />
            <View style={styles.impactCol}>
              <Text style={styles.impactHeader}>▼ 급락</Text>
              {(item.raw_news?.decreased_items ?? []).length > 0
                ? (item.raw_news.decreased_items.map(k => (
                    <View key={k} style={[styles.impactTag, { backgroundColor: COLORS.tagDownBg }]}>
                      <Text style={{ fontSize: 11, color: COLORS.tagDownText, fontWeight: '600' }}>{k}</Text>
                    </View>
                  )))
                : <Text style={styles.impactNone}>없음</Text>
              }
            </View>
          </View>
        </View>

        {/* 키워드 */}
        <Text style={[styles.sectionLabel, { marginTop: 14 }]}>키워드</Text>
        <View style={styles.detailCard}>
          <View style={styles.keywordRow}>
            {(item.raw_news?.keyword ?? []).map(k => (
              <View key={k} style={styles.keywordTag}>
                <Text style={styles.keywordText}>{k}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* CTA */}
        <TouchableOpacity style={styles.ctaBtn} activeOpacity={0.85}>
          <Text style={styles.ctaText}>→ 인과관계 상세 보기</Text>
        </TouchableOpacity>

        <View style={{ height: 30 }} />
      </ScrollView>
    </Animated.View>
  );
}

// ── 목록 메인 ─────────────────────────────────────────────────
export default function NewsListScreen() {
  const insets = useSafeAreaInsets();
  const [newsList, setNewsList] = useState([]);
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState('');
  const [dirFilter, setDirFilter] = useState('');
  const [catFilter, setCatFilter] = useState('');
  const [sortAsc, setSortAsc] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchNewsList()
      .then(data => { if (data?.length > 0) setNewsList(data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // 안드로이드 하드웨어 뒤로가기 대응
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

  const filtered = newsList.filter(item => {
    const chain = item.causal_chains?.[0];
    if (dirFilter && chain?.direction !== dirFilter) return false;
    if (catFilter === '__high__' && item.reliability < 0.8) return false;
    else if (catFilter && catFilter !== '__high__' && chain?.category !== catFilter) return false;
    if (query) {
      const q = query.toLowerCase();
      const inTitle = item.summary?.toLowerCase().includes(q);
      const inKeyword = (item.raw_news?.keyword ?? []).some(k => k.toLowerCase().includes(q));
      if (!inTitle && !inKeyword) return false;
    }
    return true;
  }).sort((a, b) => {
    const da = new Date(getNewsDateFromRawNews(a.raw_news, a.created_at) ?? 0);
    const db = new Date(getNewsDateFromRawNews(b.raw_news, b.created_at) ?? 0);
    return sortAsc ? da - db : db - da;
  });

  if (selected) {
    return (
      <NewsDetailView
        item={selected}
        onClose={() => setSelected(null)}
        topInset={insets.top}
      />
    );
  }

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.headerBg} />

      {/* 헤더 */}
      <View style={[styles.header, { paddingTop: insets.top + 10 }]}>
        <View style={[styles.headerTop, { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }]}>
          <View>
            <Text style={styles.headerTitle}>뉴스</Text>
            <Text style={styles.headerSub}>실시간 뉴스 분석</Text>
          </View>
          <TouchableOpacity onPress={() => setShowSearch(!showSearch)} style={{ padding: 5 }}>
            <Text style={{ fontSize: 18, color: COLORS.white }}>🔍</Text>
          </TouchableOpacity>
        </View>

        {/* 검색 */}
        {showSearch && (
          <View style={styles.searchBox}>
            <Text style={styles.searchIcon}>🔍</Text>
            <TextInput
              style={styles.searchInput}
              placeholder="뉴스·키워드 검색"
              placeholderTextColor={COLORS.headerMuted}
              value={query}
              onChangeText={setQuery}
              returnKeyType="search"
            />
          </View>
        )}

        {/* 필터 칩 */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
          {DIR_CHIPS.map(c => (
            <Chip
              key={c.value}
              label={c.label}
              active={dirFilter === c.value && c.value !== ''}
              onPress={() => setDirFilter(dirFilter === c.value ? '' : c.value)}
            />
          ))}
          {CAT_CHIPS.map(c => (
            <Chip
              key={c.value}
              label={c.label}
              active={catFilter === c.value}
              onPress={() => setCatFilter(catFilter === c.value ? '' : c.value)}
            />
          ))}
        </ScrollView>
      </View>

      {/* 리스트 바 */}
      <View style={styles.listBar}>
        <Text style={styles.listCount}>{filtered.length}건</Text>
        <TouchableOpacity onPress={() => setSortAsc(!sortAsc)}>
          <Text style={styles.sortBtn}>{sortAsc ? '오래된순 ↕' : '최신순 ↕'}</Text>
        </TouchableOpacity>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.listContent}>
        {loading && <ActivityIndicator color={COLORS.headerBg} style={{ marginBottom: 12, marginTop: 20 }} />}
        {filtered.map(item => (
          <NewsCard key={item.id} item={item} onPress={setSelected} />
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

  // Search
  searchBox: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderRadius: 10, marginHorizontal: 16, marginBottom: 10,
    paddingHorizontal: 10, paddingVertical: 7,
  },
  searchIcon:  { fontSize: 14, marginRight: 6 },
  searchInput: { flex: 1, fontSize: 13, color: COLORS.headerText },

  // Chips
  chipRow: { paddingHorizontal: 16, paddingBottom: 8, gap: 8 },
  chip: {
    borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5,
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)',
  },
  chipActive:     { backgroundColor: COLORS.white },
  chipText:       { fontSize: 11, color: 'rgba(255,255,255,0.65)' },
  chipTextActive: { color: COLORS.headerBg, fontWeight: '700' },

  // List bar
  listBar: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 14, paddingVertical: 8,
    backgroundColor: COLORS.white,
    borderBottomWidth: 0.5, borderBottomColor: COLORS.border,
  },
  listCount: { fontSize: 12, fontWeight: '600', color: COLORS.textPrimary },
  sortBtn:   { fontSize: 12, color: COLORS.textMuted },

  // News card
  listContent: { padding: 10 },
  newsCard: {
    backgroundColor: COLORS.white, borderRadius: 14,
    padding: 12, marginBottom: 10,
    ...Platform.select({
      ios:     { shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 6 },
      android: { elevation: 2 },
    }),
  },
  newsCardTop:  { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 4 },
  newsCardTitle:{ flex: 1, fontSize: 12, fontWeight: '700', color: COLORS.textPrimary, marginRight: 8 },
  newsCardEn:   { fontSize: 11, color: COLORS.textMuted, marginBottom: 8, marginLeft: 15 },
  newsCardBottom: { flexDirection: 'row', alignItems: 'center', marginLeft: 15, gap: 8 },
  newsCardDate: { fontSize: 10, color: COLORS.textLight },
  tagRow:    { flexDirection: 'row', gap: 4, flexWrap: 'wrap' },
  tag:       { borderRadius: 4, paddingHorizontal: 5, paddingVertical: 2 },
  tagText:   { fontSize: 10, fontWeight: '600' },
  tagGray:   { backgroundColor: '#F3F4F6', borderRadius: 4, paddingHorizontal: 5, paddingVertical: 2 },
  tagGrayText: { fontSize: 10, color: COLORS.textMuted },

  // Detail
  sectionLabel: {
    fontSize: 11, fontWeight: '500', color: COLORS.textMuted,
    letterSpacing: 0.3, marginBottom: 8,
  },
  detailRoot:   { ...StyleSheet.absoluteFillObject, backgroundColor: COLORS.screenBg, zIndex: 100 },
  detailHeader: { backgroundColor: COLORS.headerBg, paddingHorizontal: 16, paddingBottom: 14 },
  backBtn:      { marginBottom: 10 },
  backText:     { fontSize: 13, color: COLORS.headerAccent },
  detailTitle:  { fontSize: 14, fontWeight: '700', color: COLORS.headerText, lineHeight: 20, marginBottom: 4 },
  detailTitleEn: { fontSize: 10, color: 'rgba(255,255,255,0.5)', fontStyle: 'italic', marginBottom: 8 },
  detailMetaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, alignItems: 'center' },
  detailDate:   { fontSize: 10, color: COLORS.headerMuted },
  dirBadge:     { backgroundColor: 'rgba(255,255,255,0.12)', borderRadius: 6, paddingHorizontal: 6, paddingVertical: 2 },
  dirBadgeText: { fontSize: 10, fontWeight: '600' },
  catBadge:     { backgroundColor: 'rgba(255,255,255,0.12)', borderRadius: 6, paddingHorizontal: 6, paddingVertical: 2 },
  catBadgeText: { fontSize: 10, color: COLORS.headerText },
  detailBody:   { padding: 14 },
  detailCard: {
    backgroundColor: COLORS.white, borderRadius: 14, padding: 14, marginBottom: 8,
    ...Platform.select({
      ios:     { shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 6 },
      android: { elevation: 1 },
    }),
  },
  detailCardText: { fontSize: 13, color: COLORS.textPrimary, lineHeight: 20, marginBottom: 12 },
  reliabilityRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  relaLabel:      { fontSize: 11, color: COLORS.textMuted, width: 36 },
  relaBar:        { flex: 1, height: 4, backgroundColor: '#E5E7EB', borderRadius: 2 },
  relaFill:       { height: 4, backgroundColor: COLORS.headerBg, borderRadius: 2 },
  relaPct:        { fontSize: 11, fontWeight: '600', color: COLORS.textPrimary, width: 30, textAlign: 'right' },
  relatedTag:     { backgroundColor: COLORS.highBg, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4, alignSelf: 'flex-start' },
  relatedTagText: { fontSize: 11, color: COLORS.highText, fontWeight: '600' },
  impactRow:      { flexDirection: 'row' },
  impactCol:      { flex: 1 },
  impactDivider:  { width: 0.5, backgroundColor: COLORS.border, marginHorizontal: 12 },
  impactHeader:   { fontSize: 11, fontWeight: '700', color: COLORS.textMuted, marginBottom: 8 },
  impactTag:      { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4, marginBottom: 6, alignSelf: 'flex-start' },
  impactNone:     { fontSize: 11, color: COLORS.textLight },
  keywordRow:     { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  keywordTag:     { backgroundColor: '#F3F4F6', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4 },
  keywordText:    { fontSize: 11, color: COLORS.textMuted },
  ctaBtn: {
    backgroundColor: COLORS.headerBg, borderRadius: 12,
    padding: 14, alignItems: 'center', marginTop: 6,
  },
  ctaText: { fontSize: 14, fontWeight: '700', color: COLORS.white },
});
