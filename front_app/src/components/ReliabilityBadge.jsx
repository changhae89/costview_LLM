// components/ReliabilityBadge.jsx
import { StyleSheet, Text, View } from 'react-native';
import { getReliabilityBadge } from '../constants/category';

export default function ReliabilityBadge({ reliability }) {
  const badge = getReliabilityBadge(reliability);
  if (!badge) return null;
  return (
    <View style={[styles.badge, { backgroundColor: badge.bg }]}>
      <Text style={[styles.text, { color: badge.color }]}>{badge.label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  text: {
    fontSize: 10,
    fontWeight: '600',
  },
});
