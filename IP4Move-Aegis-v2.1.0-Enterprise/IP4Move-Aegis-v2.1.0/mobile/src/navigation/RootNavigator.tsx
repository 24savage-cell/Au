import React from 'react';
import { Platform, StyleSheet, Text, View } from 'react-native';
import { NavigationContainer, DarkTheme } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import Svg, { Path, Circle, Polyline } from 'react-native-svg';

import { DashboardScreen } from '@/screens/DashboardScreen';
import { TunnelsScreen } from '@/screens/TunnelsScreen';
import { ThreatsScreen } from '@/screens/ThreatsScreen';
import { IdentityScreen } from '@/screens/IdentityScreen';
import { ProfileScreen } from '@/screens/ProfileScreen';
import { colors, radius, spacing } from '@/theme';

const Tab = createBottomTabNavigator();

const Icon = {
  Home: ({ color }: { color: string }) => (
    <Svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <Path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <Path d="M9 22V12h6v10" />
    </Svg>
  ),
  Tunnel: ({ color }: { color: string }) => (
    <Svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <Path d="M2 12h6l3-9 4 18 3-9h4" />
    </Svg>
  ),
  Shield: ({ color }: { color: string }) => (
    <Svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <Path d="M12 9v4M12 17h.01" />
      <Path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    </Svg>
  ),
  User: ({ color }: { color: string }) => (
    <Svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <Path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <Circle cx="12" cy="7" r="4" />
    </Svg>
  ),
  Gear: ({ color }: { color: string }) => (
    <Svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <Circle cx="12" cy="12" r="3" />
      <Path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </Svg>
  ),
};

const navTheme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: colors.void,
    card: colors.void2,
    text: colors.ink1,
    border: colors.line,
    primary: colors.teal,
    notification: colors.red,
  },
};

export const RootNavigator: React.FC = () => {
  return (
    <NavigationContainer theme={navTheme}>
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarStyle: styles.tabBar,
          tabBarActiveTintColor: colors.teal,
          tabBarInactiveTintColor: colors.ink3,
          tabBarLabelStyle: styles.tabLabel,
          tabBarItemStyle: styles.tabItem,
          tabBarIcon: ({ color }) => {
            switch (route.name) {
              case '总览': return <Icon.Home color={color} />;
              case '隧道': return <Icon.Tunnel color={color} />;
              case '威胁': return <Icon.Shield color={color} />;
              case '身份': return <Icon.User color={color} />;
              case '设置': return <Icon.Gear color={color} />;
              default: return null;
            }
          },
        })}
      >
        <Tab.Screen name="总览" component={DashboardScreen} />
        <Tab.Screen name="隧道" component={TunnelsScreen} />
        <Tab.Screen name="威胁" component={ThreatsScreen} />
        <Tab.Screen name="身份" component={IdentityScreen} />
        <Tab.Screen name="设置" component={ProfileScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
};

const styles = StyleSheet.create({
  tabBar: {
    position: 'absolute',
    backgroundColor: 'rgba(20, 23, 28, 0.92)',
    borderTopWidth: 1,
    borderTopColor: colors.line,
    height: Platform.select({ ios: 84, android: 64 }),
    paddingTop: 6,
    paddingBottom: Platform.select({ ios: 24, android: 6 }),
  },
  tabLabel: { fontSize: 10, fontWeight: '600', letterSpacing: 0.3 },
  tabItem: { paddingVertical: 4 },
});
