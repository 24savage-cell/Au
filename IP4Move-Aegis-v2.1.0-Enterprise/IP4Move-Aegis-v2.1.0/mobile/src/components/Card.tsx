import React, { PropsWithChildren } from 'react';
import { StyleSheet, View, ViewStyle } from 'react-native';
import { colors, radius, spacing } from '@/theme';

interface Props {
  style?: ViewStyle;
  variant?: 'default' | 'hero';
}

export const Card: React.FC<PropsWithChildren<Props>> = ({ children, style, variant = 'default' }) => (
  <View style={[styles.base, variant === 'hero' && styles.hero, style]}>{children}</View>
);

const styles = StyleSheet.create({
  base: {
    backgroundColor: colors.panel,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.line,
    padding: spacing.lg,
  },
  hero: {
    backgroundColor: colors.void2,
    borderRadius: radius.xl,
    padding: spacing.xl,
  },
});
