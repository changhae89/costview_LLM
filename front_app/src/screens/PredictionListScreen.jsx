// screens/PredictionListScreen.jsx — SCR-003 품목별 물가 예측 (v3 리팩토링)
import { useEffect, useState } from 'react';
import {
  BackHandler, Platform, Pressable, RefreshControl,
  ScrollView, StatusBar, StyleSheet, Text, View, ActivityIndicator,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { COLORS } from '../constants/colors';
import { usePredictions } from '../hooks/usePredictions';
import PredictionCard from '../components/PredictionCard';
import PredictionDetailView from '../components/PredictionDetailView';

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

export default function PredictionListScreen() {
  const insets = useSafeAreaInsets();
  const { predictions, loading, refreshing, hasError, refetch } = usePredictions();
  const [selected, setSelected] = useState(null);
  const [dirFilter, setDirFilter] = useState('');
  const [catFilter, setCatFilter] = useState('');

  useEffect(() => {
    const onBackPress = () => {
      if (selected) { setSelected(null); return true; }
      return false;
    };
    const sub = BackHandler.addEventListener('hardwareBackPress', onBackPress);
    return () => sub.remove();
  }, [selected]);

  if (selected) {
    return (
      <PredictionDetailView
        item={selected}
        onClose={() => setSelected(null)}
        topInset={insets.top}
      />
    );
  }

  const isAllActive = dirFilter === '' && catFilter === '';
  const filtered = predictions.filter(item => {
    if (dirFilter && item.direction !== dirFilter) return false;
    if (catFilter && item.category !== catFilter) return false;
    return true;
  });

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
            const active = c.type === 'all' ? isAllActive
              : c.type === 'dir' ? dirFilter === c.value
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
          <RefreshControl refreshing={refreshing} onRefresh={refetch} tintColor={COLORS.headerBg} colors={[COLORS.headerBg]} />
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

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: COLORS.screenBg },
  header: { backgroundColor: COLORS.headerBg, paddingBottom: 10 },
  headerTop: { paddingHorizontal: 16, marginBottom: 10 },
  headerTitle: { fontSize: 17, fontWeight: '700', color: COLORS.headerText },
  headerSub: { fontSize: 10, color: COLORS.headerAccent, marginTop: 2 },
  chipRow: { paddingHorizontal: 16, paddingBottom: 8, gap: 8 },
  chip: { borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5, borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)' },
  chipActive: { backgroundColor: COLORS.white },
  chipText: { fontSize: 11, color: 'rgba(255,255,255,0.65)' },
  chipTextActive: { color: COLORS.headerBg, fontWeight: '700' },
  listContent: { padding: 12 },
  listSectionLabel: { fontSize: 11, fontWeight: '600', color: COLORS.textMuted, letterSpacing: 0.5, marginBottom: 12, paddingHorizontal: 4, textTransform: 'uppercase' },
  errorBox: { backgroundColor: '#FEF2F2', borderRadius: 12, padding: 14, marginBottom: 12, borderWidth: 1, borderColor: '#FECACA' },
  errorText: { fontSize: 13, fontWeight: '700', color: '#991B1B', marginBottom: 4 },
  errorSub: { fontSize: 11, color: '#B91C1C' },
  emptyText: { padding: 24, fontSize: 13, color: COLORS.textMuted, textAlign: 'center' },
});
