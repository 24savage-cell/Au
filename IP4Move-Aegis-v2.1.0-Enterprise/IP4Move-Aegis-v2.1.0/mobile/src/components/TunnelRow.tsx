import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Badge } from './Badge';
import { Toggle } from './Toggle';
import { colors, radius, spacing } from '@/theme';
import type { Tunnel } from '@/api/tunnels';

interface Props {
  tunnel: Tunnel;
  onToggle: (enabled: boolean) => void;
  onPress?: () => void;
}

const protocolTone: Record<Tunnel['protocol'], 'teal' | 'amber' | 'red' | 'mute'> = {
  DoH: 'teal',
  QUIC: 'teal',
  WebRTC: 'teal',
  PQC: 'amber',
};

export const TunnelRow: React.FC<Props> = ({ tunnel, onToggle, onPress }) => {
  const isWarn = tunnel.status === 'rebuilding' || tunnel.status === 'connecting';
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [styles.row, pressed && styles.pressed]}>
      <View
        style={[
          styles.icon,
          { borderColor: isWarn ? 'rgba(245,165,36,0.25)' : 'rgba(77,212,196,0.25)' },
        ]}
      >
        <View
          style={[
            styles.iconDot,
            { backgroundColor: isWarn ? colors.amber : colors.teal },
          ]}
        />
      </View>

      <View style={{ flex: 1 }}>
        <View style={styles.titleRow}>
          <Text style={styles.name}>{tunnel.name}</Text>
          <Badge label={tunnel.protocol} tone={protocolTone[tunnel.protocol]} />
        </View>
        <Text style={styles.meta}>
          {tunnel.country} · {tunnel.latencyMs} ms · {tunnel.throughputGbps.toFixed(1)} Gbps
        </Text>
      </View>

      <Toggle value={tunnel.enabled} onChange={onToggle} />
    </Pressable>
  );
};

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    backgroundColor: colors.panel,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.line,
    marginBottom: spacing.sm,
  },
  pressed: { opacity: 0.85 },
  icon: {
    width: 40,
    height: 40,
    borderRadius: radius.md,
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconDot: { width: 10, height: 10, borderRadius: 5 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  name: { color: colors.ink1, fontSize: 14, fontWeight: '600' },
  meta: { color: colors.ink3, fontSize: 11, marginTop: 3, fontVariant: ['tabular-nums'] },
});
