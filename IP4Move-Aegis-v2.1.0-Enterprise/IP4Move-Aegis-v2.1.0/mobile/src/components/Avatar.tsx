import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors, radius } from '@/theme';

interface Props {
  name: string;
  id?: string;
  size?: 'sm' | 'md' | 'lg';
  trustScore?: number;
}

export const Avatar: React.FC<Props> = ({ name, id, size = 'md', trustScore }) => {
  const initials = name
    .split(' ')
    .map((s) => s[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  const dim = size === 'lg' ? 56 : size === 'sm' ? 32 : 44;
  const fontSize = size === 'lg' ? 20 : size === 'sm' ? 12 : 16;

  return (
    <View>
      <View
        style={[
          styles.box,
          {
            width: dim,
            height: dim,
            borderRadius: radius.md,
          },
        ]}
      >
        <Text style={[styles.text, { fontSize }]}>{initials}</Text>
      </View>
      {typeof trustScore === 'number' && (
        <View style={styles.trust}>
          <Text style={styles.trustNum}>{trustScore}</Text>
        </View>
      )}
      {id && <Text style={styles.id}>{id}</Text>}
    </View>
  );
};

const styles = StyleSheet.create({
  box: {
    backgroundColor: colors.teal,
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: { color: colors.void, fontWeight: '800' },
  trust: {
    marginTop: 6,
    backgroundColor: colors.void2,
    borderRadius: radius.sm,
    paddingHorizontal: 6,
    paddingVertical: 2,
    alignSelf: 'flex-start',
  },
  trustNum: { color: colors.teal, fontSize: 11, fontWeight: '700', fontVariant: ['tabular-nums'] },
  id: { color: colors.ink3, fontSize: 10, marginTop: 4, fontVariant: ['tabular-nums'] },
});
