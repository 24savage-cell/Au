export * from './colors';
export { colors as default } from './colors';

export const fonts = {
  display: {
    fontFamily: 'System',
    fontWeight: '800' as const,
  },
  body: {
    fontFamily: 'System',
    fontWeight: '500' as const,
  },
  mono: {
    fontFamily: 'Courier',
    fontWeight: '500' as const,
  },
};

export const sizes = {
  xs: 10,
  sm: 12,
  md: 14,
  lg: 16,
  xl: 18,
  xxl: 22,
  hero: 28,
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 28,
} as const;

export const radius = {
  sm: 6,
  md: 10,
  lg: 14,
  xl: 18,
  pill: 999,
} as const;
