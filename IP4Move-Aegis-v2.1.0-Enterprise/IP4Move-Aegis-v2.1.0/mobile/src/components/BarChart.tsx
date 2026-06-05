import React, { useMemo } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '@/theme';

interface Props {
  data: number[]; // values 0~1
  height?: number;
  outColor?: string;
  inColor?: string;
}

export const BarChart: React.FC<Props> = ({
  data,
  height = 120,
  outColor = colors.teal,
  inColor = colors.ink4,
}) => {
  const bars = useMemo(
    () =>
      data.map((v, i) => {
        const out = Math.max(0.04, Math.min(1, v));
        const inn = Math.max(0.04, out * (0.35 + Math.sin(i * 0.5) * 0.2));
        return { out, inn, key: i };
      }),
    [data],
  );

  return (
    <View style={[styles.row, { height }]}>
      {bars.map((b) => (
        <View key={b.key} style={styles.col}>
          <View style={[styles.bar, { height: `${b.out * 100}%`, backgroundColor: outColor }]} />
          <View style={[styles.bar, { height: `${b.inn * 100}%`, backgroundColor: inColor }]} />
        </View>
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'flex-end', gap: 3 },
  col: { flex: 1, justifyContent: 'flex-end', gap: 2 },
  bar: {
    width: '100%',
    borderRadius: radius.sm,
    opacity: 0.85,
  },
});
