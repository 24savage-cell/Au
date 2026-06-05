import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '@/theme';

type Tone = 'teal' | 'amber' | 'red' | 'mute';

const toneStyles = {
  teal: { bg: 'rgba(77,212,196,0.12)', fg: colors.teal, border: 'rgba(77,212,196,0.25)' },
  amber: { bg: 'rgba(245,165,36,0.12)', fg: colors.amber, border: 'rgba(245,165,36,0.25)' },
  red: { bg: 'rgba(229,72,77,0.12)', fg: colors.red, border: 'rgba(229,72,77,0.25)' },
  mute: { bg: 'rgba(255,255,255,0.04)', fg: colors.ink3, border: colors.line },
} as const;

interface Props {
  label: string;
  tone?: Tone;
}

export const Badge: React.FC<Props> = ({ label, tone = 'teal' }) => {
  const t = toneStyles[tone];
  return (
    <View style={[styles.box, { backgroundColor: t.bg, borderColor: t.border }]}>
      <Text style={[styles.text, { color: t.fg }]}>{label}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  box: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radius.sm,
    borderWidth: 1,
    alignSelf: 'flex-start',
  },
  text: { fontSize: 10, fontWeight: '700', letterSpacing: 0.8 },
});
