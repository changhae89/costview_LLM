import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View, Text, StyleSheet, StatusBar, TextInput, TouchableOpacity, Alert, ActivityIndicator, Animated, Easing } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { COLORS } from '../constants/colors';

export default function SettingsScreen({
  isLoggedIn = false,
  profile = null,
  isAuthLoading = false,
  onLogin = async () => {},
  onLogout = async () => {},
  loginOnlyMode = false,
}) {
  const insets = useSafeAreaInsets();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const displayEmail = profile?.email ?? email;
  const cardOpacity = useRef(new Animated.Value(0)).current;
  const cardTranslateY = useRef(new Animated.Value(14)).current;

  useEffect(() => {
    if (profile?.email) {
      setEmail(profile.email);
    }
  }, [profile]);

  useEffect(() => {
    cardOpacity.setValue(0);
    cardTranslateY.setValue(14);
    Animated.parallel([
      Animated.timing(cardOpacity, {
        toValue: 1,
        duration: 240,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.timing(cardTranslateY, {
        toValue: 0,
        duration: 240,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
    ]).start();
  }, [isLoggedIn, cardOpacity, cardTranslateY]);

  const formattedLastLogin = useMemo(() => {
    if (!profile?.lastLoginAt) {
      return '방금 전';
    }
    const date = new Date(profile.lastLoginAt);
    return new Intl.DateTimeFormat('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  }, [profile]);

  const validateInput = () => {
    if (!email || !password) {
      Alert.alert('알림', '이메일과 비밀번호를 입력해주세요.');
      return false;
    }
    if (!email.includes('@')) {
      Alert.alert('알림', '올바른 이메일 형식을 입력해주세요.');
      return false;
    }
    if (password.length < 4) {
      Alert.alert('알림', '비밀번호는 4자 이상 입력해주세요.');
      return false;
    }
    return true;
  };

  const handleLogin = async () => {
    if (!validateInput() || isSubmitting) {
      return;
    }

    const normalizedEmail = email.trim().toLowerCase();

    setIsSubmitting(true);
    setStatusMessage('로그인 확인 중...');
    await new Promise((resolve) => setTimeout(resolve, 900));
    try {
      await onLogin({ email: normalizedEmail, password });
      setEmail(normalizedEmail);
      setStatusMessage('로그인 성공');
    } catch (error) {
      Alert.alert('오류', '로그인 처리 중 문제가 발생했습니다.');
      setStatusMessage('로그인 실패');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = async () => {
    if (isSubmitting) {
      return;
    }
    setIsSubmitting(true);
    setStatusMessage('로그아웃 중...');
    await new Promise((resolve) => setTimeout(resolve, 450));
    await onLogout();
    setEmail('');
    setPassword('');
    setStatusMessage('로그아웃 완료');
    setIsSubmitting(false);
  };

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.headerBg} />
      <View style={[styles.header, { paddingTop: insets.top + 10 }]}>
        <Text style={styles.headerTitle}>{loginOnlyMode ? '로그인' : '설정'}</Text>
      </View>
      <View style={styles.body}>
        {isAuthLoading ? (
          <View style={styles.loadingBox}>
            <ActivityIndicator size="small" color={COLORS.headerBg} />
            <Text style={styles.loadingText}>로그인 상태를 불러오는 중...</Text>
          </View>
        ) : null}

        {!isLoggedIn ? (
          <Animated.View
            style={[
              styles.loginContainer,
              {
                opacity: cardOpacity,
                transform: [{ translateY: cardTranslateY }],
              },
            ]}
          >
            <Text style={styles.sectionTitle}>로그인</Text>
            <Text style={styles.sectionSub}>Cost-Vue의 모든 기능을 이용해보세요</Text>
            
            <TextInput
              style={styles.input}
              placeholder="이메일"
              placeholderTextColor={COLORS.textMuted}
              keyboardType="email-address"
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
            />
            <TextInput
              style={styles.input}
              placeholder="비밀번호"
              placeholderTextColor={COLORS.textMuted}
              secureTextEntry
              value={password}
              onChangeText={setPassword}
            />
            
            <TouchableOpacity
              style={[styles.loginButton, (isSubmitting || isAuthLoading) && styles.buttonDisabled]}
              onPress={handleLogin}
              disabled={isSubmitting || isAuthLoading}
            >
              {isSubmitting ? <ActivityIndicator size="small" color={COLORS.white} /> : null}
              <Text style={styles.loginButtonText}>{isSubmitting ? '로그인 중...' : '로그인'}</Text>
            </TouchableOpacity>
            <Text style={styles.hintText}>이메일 예시: cost@view.ai / 1234</Text>
          </Animated.View>
        ) : (
          <Animated.View
            style={[
              styles.profileContainer,
              {
                opacity: cardOpacity,
                transform: [{ translateY: cardTranslateY }],
              },
            ]}
          >
            <View style={styles.profileAvatar}>
              <Text style={styles.profileAvatarText}>{(displayEmail?.charAt(0) || '?').toUpperCase()}</Text>
            </View>
            <Text style={styles.profileEmail}>{displayEmail}</Text>
            <Text style={styles.sessionMeta}>계정 유형: {profile?.loginType ?? 'Dummy Account'}</Text>
            <Text style={styles.sessionMeta}>마지막 로그인: {formattedLastLogin}</Text>
            <TouchableOpacity
              style={[styles.logoutButton, isSubmitting && styles.buttonDisabled]}
              onPress={handleLogout}
              disabled={isSubmitting}
            >
              <Text style={styles.logoutButtonText}>{isSubmitting ? '로그아웃 중...' : '로그아웃'}</Text>
            </TouchableOpacity>
          </Animated.View>
        )}
        
        <View style={styles.footerContainer}>
          {statusMessage ? <Text style={styles.statusMessage}>{statusMessage}</Text> : null}
          <Text style={styles.text}>버전 1.0.0</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: COLORS.screenBg },
  header: {
    backgroundColor: COLORS.headerBg,
    paddingHorizontal: 16,
    paddingBottom: 14,
  },
  headerTitle: { fontSize: 17, fontWeight: '700', color: COLORS.headerText },
  body: {
    flex: 1,
    padding: 20,
  },
  loadingBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#EFF6FF',
    borderColor: '#BFDBFE',
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 12,
    marginBottom: 12,
  },
  loadingText: {
    fontSize: 13,
    color: COLORS.textPrimary,
    fontWeight: '500',
  },
  loginContainer: {
    backgroundColor: COLORS.white,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 6,
    elevation: 2,
    marginTop: 10,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 4,
  },
  sectionSub: {
    fontSize: 12,
    color: COLORS.textMuted,
    marginBottom: 20,
  },
  input: {
    backgroundColor: '#F3F4F6',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 12,
    fontSize: 14,
    color: COLORS.textPrimary,
  },
  loginButton: {
    backgroundColor: COLORS.headerBg,
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: 8,
    marginTop: 8,
  },
  loginButtonText: {
    color: COLORS.white,
    fontSize: 15,
    fontWeight: '600',
  },
  profileContainer: {
    backgroundColor: COLORS.white,
    padding: 24,
    borderRadius: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 6,
    elevation: 2,
    marginTop: 10,
  },
  profileAvatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: COLORS.headerBg,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  profileAvatarText: {
    color: COLORS.white,
    fontSize: 24,
    fontWeight: '700',
  },
  profileEmail: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.textPrimary,
    marginBottom: 12,
  },
  sessionMeta: {
    fontSize: 13,
    color: COLORS.textMuted,
    marginBottom: 6,
  },
  logoutButton: {
    backgroundColor: '#FEE2E2',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
  },
  logoutButtonText: {
    color: '#EF4444',
    fontSize: 14,
    fontWeight: '600',
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  hintText: {
    marginTop: 12,
    color: COLORS.textMuted,
    fontSize: 12,
  },
  footerContainer: {
    flex: 1,
    justifyContent: 'flex-end',
    alignItems: 'center',
    paddingBottom: 20,
  },
  text: {
    fontSize: 13,
    color: COLORS.textMuted,
  },
  statusMessage: {
    marginBottom: 6,
    fontSize: 12,
    color: COLORS.headerBg,
  },
});
