// screens/NewsListScreen.jsx — SCR-002 뉴스 목록 & 상세
import { useEffect, useState } from 'react';
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
  TextInput,
  TouchableOpacity,
  View,
  ActivityIndicator,
  RefreshControl,
  FlatList,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import DirectionDot from '../components/DirectionDot';
import ReliabilityBadge from '../components/ReliabilityBadge';
import { CATEGORY_MAP, DIRECTION_MAP, MAGNITUDE_MAP, formatCategory } from '../constants/category';
import { COLORS } from '../constants/colors';
import { formatDateTime } from '../lib/helpers';
import NewsDetailView from '../components/NewsDetailView';
import { useNews } from '../hooks/useNews';

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

// (기존 getNewsDateFromRawNews 제거됨 — 공용 헬퍼 또는 내부 로직으로 대체 가능)

function NewsCard({ item, onPress }) {
  const mainChain = item.causal_chains?.[0];
  const dateStr = formatDateTime(item.raw_news?.origin_published_at ?? item.created_at);

  return (
    <Pressable onPress={() => onPress(item)} style={styles.newsCard}>
      <View style={styles.newsCardTop}>
        <DirectionDot direction={mainChain?.direction ?? 'neutral'} size={7} />
        <Text style={styles.newsCardTitle} numberOfLines={2}>{item.summary}</Text>
        <ReliabilityBadge reliability={item.reliability} />
      </View>
      <Text style={styles.newsCardEn} numberOfLines={1}>{item.raw_news?.title ?? ''}</Text>
      <Text style={styles.newsCardDate}>{dateStr}</Text>
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
        {(item.raw_news?.keyword ?? []).map(k => (
          <View key={k} style={styles.tagGray}>
            <Text style={styles.tagGrayText}>{k}</Text>
          </View>
        ))}
      </View>
    </Pressable>
  );
}

// NewsListScreen logic...


// ── 목록 메인 ─────────────────────────────────────────────────
export default function NewsListScreen() {
  const insets = useSafeAreaInsets();
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState('');
  const [dirFilter, setDirFilter] = useState('');
  const [catFilter, setCatFilter] = useState('');
  const [sortAsc, setSortAsc] = useState(false);
  const [showSearch, setShowSearch] = useState(false);

  // useNews 훅에 필터 값들을 넘겨서 서버사이드 필터링 및 페이징 수행
  const { newsList, totalCount, loading, refreshing, loadingMore, loadMore, refetch } = useNews({
    query, dirFilter, catFilter, sortAsc
  });

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

  if (selected) {
    return (
      <NewsDetailView
        item={selected}
        onClose={() => setSelected(null)}
        topInset={insets.top}
      />
    );
  }

  const renderFooter = () => {
    if (!loadingMore) return <View style={{ height: 20 }} />;
    return <ActivityIndicator color={COLORS.primary} style={{ marginVertical: 20 }} />;
  };

  return (
    <View style={styles.root}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.headerBg} />

      {/* 헤더 */}
      <View style={[styles.header, { paddingTop: insets.top + 10 }]}>
        <View style={[styles.headerTop, { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }]}>
          <View>
            <Text style={styles.headerTitle}>뉴스</Text>
            <Text style={styles.headerSub}>실시간 뉴스 분석</Text>
          </View>
          <TouchableOpacity onPress={() => setShowSearch(!showSearch)} style={{ padding: 5 }}>
            <Text style={{ fontSize: 18, color: COLORS.primary }}>🔍</Text>
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

      {/* 리스크 바 */}
      <View style={styles.listBar}>
        <Text style={styles.listCount}>총 {totalCount}건</Text>
        <TouchableOpacity onPress={() => setSortAsc(!sortAsc)}>
          <Text style={styles.sortBtn}>{sortAsc ? '오래된순 ↕' : '최신순 ↕'}</Text>
        </TouchableOpacity>
      </View>

      {loading && newsList.length === 0 ? (
        <ActivityIndicator color={COLORS.primary} style={{ marginBottom: 12, marginTop: 20 }} />
      ) : !loading && newsList.length === 0 ? (
        <Text style={styles.emptyText}>조건에 맞는 뉴스가 없습니다.</Text>
      ) : (
        <FlatList
          data={newsList}
          keyExtractor={(item, index) => item.id ? item.id.toString() : index.toString()}
          renderItem={({ item }) => <NewsCard item={item} onPress={setSelected} />}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          onEndReached={loadMore}
          onEndReachedThreshold={0.5}
          ListFooterComponent={renderFooter}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={refetch}
              tintColor={COLORS.primary}
              colors={[COLORS.primary]}
            />
          }
        />
      )}

      {/* 뉴스 상세 화면 공용 컴포넌트 */}
      {selected && (
        <NewsDetailView 
          item={selected} 
          onClose={() => setSelected(null)} 
          topInset={insets.top}
          customBackText="뉴스 목록"
        />
      )}
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
    backgroundColor: '#F9FAFB',
    borderRadius: 10, marginHorizontal: 16, marginBottom: 10,
    paddingHorizontal: 10, paddingVertical: 7,
  },
  searchIcon:  { fontSize: 14, marginRight: 6 },
  searchInput: { flex: 1, fontSize: 13, color: COLORS.headerText },

  // Chips
  chipRow: { paddingHorizontal: 16, paddingBottom: 8, gap: 8 },
  chip: {
    borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5,
    borderWidth: 1, borderColor: COLORS.border,
  },
  chipActive:     { backgroundColor: COLORS.white },
  chipText:       { fontSize: 11, color: COLORS.textMuted },
  chipTextActive: { color: COLORS.primary, fontWeight: '700' },

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
  newsCardBottom: { marginLeft: 15, marginTop: 2 },
  newsCardDate: { fontSize: 10, color: COLORS.textLight, marginBottom: 6 },
  tagScroll:    { marginLeft: 0 },
  tagRow:    { flexDirection: 'row', flexWrap: 'wrap', gap: 4, alignItems: 'center', marginTop: 6 },
  tag:       { borderRadius: 4, paddingHorizontal: 5, paddingVertical: 2 },
  tagText:   { fontSize: 10, fontWeight: '600' },
  tagGray:   { backgroundColor: '#F3F4F6', borderRadius: 4, paddingHorizontal: 5, paddingVertical: 2 },
  tagGrayText: { fontSize: 10, color: COLORS.textMuted },
  errorBox: { backgroundColor: '#FEF2F2', borderRadius: 12, padding: 14, marginBottom: 12, borderWidth: 1, borderColor: '#FECACA' },
  errorText: { fontSize: 13, fontWeight: '700', color: '#991B1B', marginBottom: 4 },
  errorSub: { fontSize: 11, color: '#B91C1C' },
  emptyText: { padding: 24, fontSize: 13, color: COLORS.textMuted, textAlign: 'center' },
});
