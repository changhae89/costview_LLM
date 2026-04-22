// components/DirectionDot.jsx
import { View } from 'react-native';
import { DIRECTION_MAP } from '../constants/category';

export default function DirectionDot({ direction, size = 8 }) {
  const info = DIRECTION_MAP[direction] ?? DIRECTION_MAP.neutral;
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        backgroundColor: info.dotColor,
        marginRight: 8,
      }}
    />
  );
}
