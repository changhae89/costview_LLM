// components/NewsDetailView.jsx
import React, { useEffect, useRef } from 'react';
import {
  Animated,
  Dimensions,
  Easing,
  Linking,
  Platform,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import DirectionDot from './DirectionDot';
import ReliabilityBadge from './ReliabilityBadge';
import { formatCategory, DIRECTION_MAP } from '../constants/category';
import { COLORS } from '../constants/colors';
import { formatDateTime } from '../lib/helpers';

const { width: SCREEN_W } = Dimensions.get('window');

export default function NewsDetailView({ item, onClose, topInset, customBackText }) {
  const slideAnim = useRef(new Animated.Value(SCREEN_W)).current;

  useEffect(() => {
    Animated.timing(slideAnim, {
      toValue: 0,
      duration: 300,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();
  }, [slideAnim]);

  const handleClose = () => {
    Animated.timing(slideAnim, {
      toValue: SCREEN_W,
      duration: 250,
      easing: Easing.in(Easing.cubic),
      useNativeDriver: true,
    }).start(() => onClose());
  };

  const mainChain = item.causal_chains?.[0];
  const dir = DIRECTION_MAP[mainChain?.direction] ?? DIRECTION_MAP.neutral;
  const dateStr = formatDateTime(item.raw_news?.origin_published_at ?? item.created_at);

  return (
    <Animated.View style={[styles.root, { transform: [{ translateX: slideAnim }] }]}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.headerBg} />
      
      {/* 헤더 */}
      <View style={[styles.header, { paddingTop: topInset + 10 }]}>
        <TouchableOpacity onPress={handleClose} style={styles.backBtn} hitSlop={15}>
          <Text style={styles.backText}>← {customBackText ?? '목록으로 돌아가기'}</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>뉴스 상세 분석</Text>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.body}>
        {/* 뉴스 기본 정보 */}
        <View style={styles.newsCard}>
          <View style={styles.reliabilityRow}>
             <ReliabilityBadge reliability={item.reliability} />
             <Text style={styles.dateText}>{dateStr}</Text>
          </View>
          
          <Text style={styles.summaryTitle}>{item.summary}</Text>
          <Text style={styles.originalTitle}>{item.raw_news?.title}</Text>
          
          <View style={styles.impactRow}>
            <DirectionDot direction={mainChain?.direction} size={8} />
            <Text style={[styles.impactText, { color: dir.color }]}>
              {formatCategory(mainChain?.category)} 가격 {dir.label} 영향
            </Text>
          </View>
        </View>

        {/* AI 분석 요약 */}
        <Text style={styles.sectionLabel}>AI 분석 요약</Text>
        <View style={styles.detailCard}>
          <Text style={styles.detailText}>{item.summary_detail || '상세 분석 내용이 없습니다.'}</Text>
        </View>

        {/* 인과관계 상세 */}
        {mainChain && (
          <>
            <Text style={styles.sectionLabel}>추론 메커니즘</Text>
            <View style={styles.detailCard}>
              <View style={styles.chainRow}>
                <View style={styles.chainDot} />
                <View style={styles.chainContent}>
                  <Text style={styles.chainLabel}>원인 (Event)</Text>
                  <Text style={styles.chainValue}>{mainChain.event || '정보 없음'}</Text>
                </View>
              </View>
              <View style={styles.chainLine} />
              <View style={styles.chainRow}>
                <View style={styles.chainDot} />
                <View style={styles.chainContent}>
                  <Text style={styles.chainLabel}>영향 경로 (Mechanism)</Text>
                  <Text style={styles.chainValue}>{mainChain.mechanism || '정보 없음'}</Text>
                </View>
              </View>
            </View>
          </>
        )}

        {/* 키워드 */}
        {item.raw_news?.keyword && item.raw_news.keyword.length > 0 && (
          <>
            <Text style={styles.sectionLabel}>관련 키워드</Text>
            <View style={styles.tagRow}>
              {item.raw_news.keyword.map(k => (
                <View key={k} style={styles.tagGray}>
                  <Text style={styles.tagGrayText}>#{k}</Text>
                </View>
              ))}
            </View>
          </>
        )}

        {/* 원문 링크 */}
        {item.raw_news?.news_url ? (
          <TouchableOpacity 
            style={styles.linkBtn}
            onPress={() => Linking.openURL(item.raw_news.news_url).catch(() => {})}
          >
            <Text style={styles.linkText}>뉴스 원문 읽기 ↗</Text>
          </TouchableOpacity>
        ) : null}

        <View style={{ height: 40 }} />
      </ScrollView>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  root: {
    position: 'absolute',
    top: 0, bottom: 0, left: 0, right: 0,
    backgroundColor: COLORS.screenBg,
    zIndex: 1000,
  },
  header: {
    backgroundColor: COLORS.headerBg,
    paddingHorizontal: 16,
    paddingBottom: 16,
  },
  backBtn: {
    marginBottom: 8,
  },
  backText: {
    fontSize: 13,
    color: COLORS.textPrimary,
    fontWeight: '600',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: COLORS.headerText,
  },
  body: {
    padding: 16,
  },
  newsCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    ...Platform.select({
      ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.1, shadowRadius: 12 },
      android: { elevation: 3 },
    }),
  },
  reliabilityRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  dateText: {
    fontSize: 11,
    color: COLORS.textLight,
  },
  summaryTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: COLORS.textPrimary,
    lineHeight: 26,
    marginBottom: 8,
  },
  originalTitle: {
    fontSize: 13,
    color: COLORS.textMuted,
    lineHeight: 20,
    marginBottom: 16,
  },
  impactRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
  },
  impactText: {
    fontSize: 14,
    fontWeight: '700',
  },
  sectionLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 10,
    marginLeft: 4,
  },
  detailCard: {
    backgroundColor: COLORS.white,
    borderRadius: 14,
    padding: 16,
    marginBottom: 20,
  },
  detailText: {
    fontSize: 14,
    color: COLORS.textPrimary,
    lineHeight: 22,
  },
  chainRow: {
    flexDirection: 'row',
    gap: 12,
  },
  chainDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: COLORS.primary,
    marginTop: 6,
  },
  chainLabel: {
    fontSize: 11,
    color: COLORS.textMuted,
    marginBottom: 2,
  },
  chainValue: {
    fontSize: 14,
    color: COLORS.textPrimary,
    fontWeight: '600',
    lineHeight: 20,
  },
  chainLine: {
    width: 1,
    height: 20,
    backgroundColor: COLORS.border,
    marginLeft: 3.5,
    marginVertical: 4,
  },
  tagRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 24,
  },
  tagGray: {
    backgroundColor: '#E5E7EB',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
  },
  tagGrayText: {
    fontSize: 12,
    color: COLORS.textMuted,
    fontWeight: '500',
  },
  linkBtn: {
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 10,
  },
  linkText: {
    color: COLORS.white,
    fontSize: 15,
    fontWeight: '700',
  },
});
