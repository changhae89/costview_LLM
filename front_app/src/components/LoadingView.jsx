// components/LoadingView.jsx
import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { COLORS } from '../constants/colors';

export default function LoadingView({ loading, hasError, onRetry, children }) {
  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }
  if (hasError) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>데이터를 불러오지 못했습니다.</Text>
        {onRetry && (
          <TouchableOpacity style={styles.retryBtn} onPress={onRetry}>
            <Text style={styles.retryText}>다시 시도</Text>
          </TouchableOpacity>
        )}
      </View>
    );
  }
  return children;
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 80 },
  errorText: { color: '#6B7280', fontSize: 14, marginBottom: 12 },
  retryBtn: { backgroundColor: COLORS.primary, paddingHorizontal: 20, paddingVertical: 10, borderRadius: 8 },
  retryText: { color: '#FFF', fontSize: 14, fontWeight: '600' },
});
