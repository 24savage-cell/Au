import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StyleSheet, Text, View } from 'react-native';

import { RootNavigator } from '@/navigation/RootNavigator';
import { colors } from '@/theme';
import { useAppStore } from '@/store';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

const ToastHost: React.FC = () => {
  const toast = useAppStore((s) => s.toast);
  if (!toast) return null;
  return (
    <View pointerEvents="none" style={styles.toastWrap}>
      <View style={styles.toast}>
        <Text style={styles.toastText}>{toast}</Text>
      </View>
    </View>
  );
};

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1, backgroundColor: colors.void }}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <StatusBar style="light" backgroundColor={colors.void} />
          <RootNavigator />
          <ToastHost />
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  toastWrap: {
    position: 'absolute',
    top: 60,
    left: 0,
    right: 0,
    alignItems: 'center',
    zIndex: 999,
  },
  toast: {
    backgroundColor: colors.panel2,
    borderColor: colors.teal,
    borderWidth: 1,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 10,
  },
  toastText: { color: colors.ink1, fontSize: 13, fontWeight: '500' },
});
