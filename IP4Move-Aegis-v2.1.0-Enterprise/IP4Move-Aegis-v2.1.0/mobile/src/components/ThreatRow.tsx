import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '@/theme';
import { formatTimeAgo } from '@/utils/format';
import type { Threat } from '@/api/threats';

interface Props {
  threat: Threat;
  onPress?: () => void;
}

const sevColor = {
  critical: colors.red,
  high: colors.amber,
  medium: colors.violet,
  low: colors.ink4,
};

export const ThreatRow: React.FC<Props> = ({ threat, onPress }) => {
  const c = sevColor[threat.severity];
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.row, pressed && { opacity: 0.85 }]}
    >
      <View style={[styles.bar, { backgroundColor: c }]} />
      <View style={{ flex: 1 }}>
        <Text style={styles.title} numberOfLines={2}>
          {threat.title}
        </Text>
        <Text style={styles.ioc} numberOfLines={1}>
          {threat.ioc}
        </Text>
        <Text style={styles.meta}>
          {formatTimeAgo(threat.observedAt)} · {threat.source} · 置信度{' '}
          {(threat.confidence * 100).toFixed(0)}
        </Text>
      </View>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: spacing.md,
    paddingVertical: spacing.md,
  },
  bar: { width: 3, borderRadius: 2 },
  title: { color: colors.ink1, fontSize: 13, fontWeight: '600' },
  ioc: {
    color: colors.teal,
    fontSize: 11,
    fontVariant: ['tabular-nums'],
    marginTop: 4,
    backgroundColor: colors.void2,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: radius.sm,
    alignSelf: 'flex-start',
  },
  meta: { color: colors.ink3, fontSize: 10, marginTop: 6 },
});
