export const colors = {
  // Surface
  void: '#0A0B0D',
  void2: '#0E1014',
  panel: '#14171C',
  panel2: '#1A1E24',
  line: '#232932',
  line2: '#2D343E',

  // Ink
  ink1: '#E6E9EE',
  ink2: '#A6ADB8',
  ink3: '#6B7280',
  ink4: '#454B55',

  // Accent
  teal: '#4DD4C4',
  tealDim: '#2A8C82',
  tealGlow: 'rgba(77, 212, 196, 0.18)',
  amber: '#F5A524',
  amberDim: '#B07A1A',
  red: '#E5484D',
  redDim: '#A93236',
  violet: '#A78BFA',
} as const;

export type ColorKey = keyof typeof colors;
