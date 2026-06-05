import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import * as Haptics from 'expo-haptics';
import { colors, radius } from '@/theme';

interface Props {
  value: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}

export const Toggle: React.FC<Props> = ({ value, onChange, disabled }) => {
  const handle = () => {
    if (disabled) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onChange(!value);
  };

  return (
    <Pressable
      onPress={handle}
      hitSlop={12}
      style={[styles.track, value && styles.on, disabled && styles.disabled]}
    >
      <View style={[styles.thumb, value && styles.thumbOn]} />
    </Pressable>
  );
};

const styles = StyleSheet.create({
  track: {
    width: 48,
    height: 28,
    borderRadius: radius.pill,
    backgroundColor: colors.line,
    padding: 3,
    justifyContent: 'center',
  },
  on: { backgroundColor: colors.tealDim },
  disabled: { opacity: 0.4 },
  thumb: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.ink2,
  },
  thumbOn: {
    backgroundColor: colors.teal,
    transform: [{ translateX: 20 }],
  },
});
