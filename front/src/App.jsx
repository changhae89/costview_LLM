// App.jsx — Root Navigator (Bottom Tab) + Splash
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, View, Image, ActivityIndicator, Animated, Easing } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import * as SplashScreen from 'expo-splash-screen';
import AsyncStorage from '@react-native-async-storage/async-storage';

import DashboardScreen from './screens/DashboardScreen';
import NewsListScreen from './screens/NewsListScreen';
import PredictionListScreen from './screens/PredictionListScreen';
import RiskScreen from './screens/RiskScreen';
import SettingsScreen from './screens/SettingsScreen';
import { COLORS } from './constants/colors';

SplashScreen.preventAutoHideAsync();

const Tab = createBottomTabNavigator();
const DUMMY_AUTH_KEY = 'costview:dummy-auth';

// ── 탭 아이콘 (SVG 없이 텍스트 이모지 + 인디케이터) ──────────
function TabIcon({ label, focused }) {
  const icons = {
    '뉴스': '📰',
    '품목 예측': '📈',
    '대시보드': '📊',
    '리스크': '🕐',
    '설정': '⚙️',
  };
  return (
    <View style={tabStyles.iconWrap}>
      <Text style={[tabStyles.iconText, !focused && tabStyles.iconInactive]}>
        {icons[label] ?? '●'}
      </Text>
      <Text 
        numberOfLines={1}
        adjustsFontSizeToFit
        style={[tabStyles.label, focused ? tabStyles.labelActive : tabStyles.labelInactive]}
      >
        {label}
      </Text>
      {focused && <View style={tabStyles.indicator} />}
    </View>
  );
}

export default function App() {
  const [appIsReady, setAppIsReady] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [profile, setProfile] = useState(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState('');
  const [showToast, setShowToast] = useState(false);
  const toastOpacity = useRef(new Animated.Value(0)).current;
  const toastTranslateY = useRef(new Animated.Value(-18)).current;
  const toastTimerRef = useRef(null);

  useEffect(() => {
    async function prepare() {
      try {
        const raw = await AsyncStorage.getItem(DUMMY_AUTH_KEY);
        if (raw) {
          const parsed = JSON.parse(raw);
          if (parsed?.email) {
            setProfile(parsed);
            setIsLoggedIn(true);
          }
        }
        await new Promise(resolve => setTimeout(resolve, 2500)); // 2.5초 대기
      } catch (e) {
        console.warn(e);
      } finally {
        setIsAuthLoading(false);
        setAppIsReady(true);
      }
    }
    prepare();
  }, []);

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current);
      }
    };
  }, []);

  const showWelcomeToast = (name) => {
    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current);
    }

    setToastMessage(`${name}님, 환영합니다!`);
    setShowToast(true);

    toastOpacity.setValue(0);
    toastTranslateY.setValue(-18);

    Animated.parallel([
      Animated.timing(toastOpacity, {
        toValue: 1,
        duration: 220,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.spring(toastTranslateY, {
        toValue: 0,
        friction: 8,
        tension: 80,
        useNativeDriver: true,
      }),
    ]).start();

    toastTimerRef.current = setTimeout(() => {
      Animated.parallel([
        Animated.timing(toastOpacity, {
          toValue: 0,
          duration: 180,
          easing: Easing.in(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.timing(toastTranslateY, {
          toValue: -12,
          duration: 180,
          useNativeDriver: true,
        }),
      ]).start(({ finished }) => {
        if (finished) {
          setShowToast(false);
        }
      });
    }, 1700);
  };

  const handleLogin = async ({ email }) => {
    const nextProfile = {
      email,
      name: email.split('@')[0] || 'guest',
      loginType: 'Admin Account',
      lastLoginAt: Date.now(),
    };

    await AsyncStorage.setItem(DUMMY_AUTH_KEY, JSON.stringify(nextProfile));
    setProfile(nextProfile);
    setIsLoggedIn(true);
    showWelcomeToast(nextProfile.name);
  };

  const handleLogout = async () => {
    await AsyncStorage.removeItem(DUMMY_AUTH_KEY);
    setProfile(null);
    setIsLoggedIn(false);
  };

  const onLayoutRootView = useCallback(async () => {
    if (appIsReady) {
      await SplashScreen.hideAsync();
    }
  }, [appIsReady]);

  if (!appIsReady) {
    return (
      <View style={styles.loadingContainer}>
        <Image 
          source={require('../logo/logo1.png')} 
          style={styles.logo}
          resizeMode="contain"
        />
        <ActivityIndicator size="large" color={COLORS.headerBg} style={{ marginTop: 20 }} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1 }} onLayout={onLayoutRootView}>
      <SafeAreaProvider>
        <NavigationContainer>
          {!isLoggedIn ? (
            <SettingsScreen
              isLoggedIn={false}
              profile={null}
              isAuthLoading={isAuthLoading}
              onLogin={handleLogin}
              onLogout={handleLogout}
              loginOnlyMode
            />
          ) : (
            <Tab.Navigator
              initialRouteName="Dashboard"
              screenOptions={{
                headerShown: false,
                tabBarStyle: tabStyles.tabBar,
                tabBarShowLabel: false,
              }}
            >
              <Tab.Screen
                name="News"
                component={NewsListScreen}
                options={{ tabBarIcon: ({ focused }) => <TabIcon label="뉴스" focused={focused} /> }}
              />
              <Tab.Screen
                name="Prediction"
                component={PredictionListScreen}
                options={{ tabBarIcon: ({ focused }) => <TabIcon label="품목 예측" focused={focused} /> }}
              />
              <Tab.Screen
                name="Dashboard"
                component={DashboardScreen}
                options={{ tabBarIcon: ({ focused }) => <TabIcon label="대시보드" focused={focused} /> }}
              />
              <Tab.Screen
                name="Risk"
                component={RiskScreen}
                options={{ tabBarIcon: ({ focused }) => <TabIcon label="리스크" focused={focused} /> }}
              />
              <Tab.Screen
                name="Settings"
                options={{ tabBarIcon: ({ focused }) => <TabIcon label="설정" focused={focused} /> }}
              >
                {() => (
                  <SettingsScreen
                    isLoggedIn={isLoggedIn}
                    profile={profile}
                    isAuthLoading={isAuthLoading}
                    onLogin={handleLogin}
                    onLogout={handleLogout}
                  />
                )}
              </Tab.Screen>
            </Tab.Navigator>
          )}
        </NavigationContainer>
        {showToast ? (
          <Animated.View
            pointerEvents="none"
            style={[
              styles.toastContainer,
              {
                opacity: toastOpacity,
                transform: [{ translateY: toastTranslateY }],
              },
            ]}
          >
            <Text style={styles.toastText}>{toastMessage}</Text>
          </Animated.View>
        ) : null}
      </SafeAreaProvider>
    </View>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  logo: {
    width: 200,
    height: 200,
  },
  toastContainer: {
    position: 'absolute',
    top: 56,
    left: 16,
    right: 16,
    backgroundColor: '#111827',
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.2,
    shadowRadius: 12,
    elevation: 8,
  },
  toastText: {
    color: '#F9FAFB',
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
});

const tabStyles = StyleSheet.create({
  tabBar: {
    height: 83,
    backgroundColor: COLORS.white,
    borderTopWidth: 0.5,
    borderTopColor: COLORS.border,
    paddingTop: 4,
  },
  iconWrap: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 4,
    width: 65, // 텍스트 폭 확보
  },
  iconText: {
    fontSize: 22,
    marginBottom: 2,
  },
  iconInactive: {
    opacity: 0.4,
  },
  label: {
    fontSize: 10,
    fontWeight: '600',
    width: '100%',
    textAlign: 'center',
  },
  labelActive: {
    color: COLORS.tabActive,
    fontWeight: '700',
  },
  labelInactive: {
    color: COLORS.tabInactive,
  },
  indicator: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: COLORS.tabActive,
    marginTop: 3,
  },
});
