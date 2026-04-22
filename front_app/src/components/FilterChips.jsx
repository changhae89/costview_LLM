// components/FilterChips.jsx
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

export function Chip({ label, active, onPress }) {
  return (
    <Pressable onPress={onPress} style={[styles.chip, active && styles.chipActive]}>
      <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
    </Pressable>
  );
}

export function FilterChipRow({ chips, activeValue, onSelect, style }) {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={[styles.row, style]}
    >
      {chips.map(c => (
        <Chip
          key={c.value}
          label={c.label}
          active={activeValue === c.value}
          onPress={() => onSelect(c.value)}
        />
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 6, paddingHorizontal: 14, paddingVertical: 8 },
  chip: {
    paddingHorizontal: 12, paddingVertical: 6,
    borderRadius: 20, borderWidth: 1,
    borderColor: '#D1D5DB', backgroundColor: '#FFF',
  },
  chipActive: { backgroundColor: '#1E3A5F', borderColor: '#1E3A5F' },
  chipText: { fontSize: 12, color: '#374151', fontWeight: '500' },
  chipTextActive: { color: '#FFF', fontWeight: '600' },
});
