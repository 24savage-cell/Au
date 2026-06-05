import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { identityApi } from '@/api/identity';
import { useAppStore } from '@/store';
import { Card } from '@/components/Card';
import { Avatar } from '@/components/Avatar';
import { Toggle } from '@/components/Toggle';
import { colors, radius, spacing } from '@/theme';
import { formatTimeAgo, formatExpiresIn } from '@/utils/format';

const SecHead: React.FC<{ title: string; meta?: string; action?: string }> = ({ title, meta, action }) => (
  <View style={styles.secHead}>
    <Text style={styles.secTitle}>{title}</Text>
    {meta && <Text style={styles.secMeta}>{meta}</Text>}
    {action && <Text style={styles.secAction}>{action}</Text>}
  </View>
);

const RiskPill: React.FC<{ risk: 'low' | 'medium' | 'high' }> = ({ risk }) => {
  const map = {
    low: { bg: 'rgba(77,212,196,0.12)', fg: colors.teal, label: '低' },
    medium: { bg: 'rgba(245,165,36,0.12)', fg: colors.amber, label: '中' },
    high: { bg: 'rgba(229,72,77,0.12)', fg: colors.red, label: '高' },
  } as const;
  const m = map[risk];
  return (
    <View style={[styles.pill, { backgroundColor: m.bg }]}>
      <Text style={[styles.pillText, { color: m.fg }]}>{m.label}</Text>
    </View>
  );
};

export const IdentityScreen: React.FC = () => {
  const showToast = useAppStore((s) => s.showToast);
  const qc = useQueryClient();

  const meQ = useQuery({ queryKey: ['me'], queryFn: identityApi.me, placeholderData: mockProfile });
  const mfaQ = useQuery({ queryKey: ['mfa'], queryFn: identityApi.mfa, placeholderData: mockMfa });
  const devQ = useQuery({ queryKey: ['devices'], queryFn: identityApi.devices, placeholderData: mockDevices });
  const sessQ = useQuery({ queryKey: ['sessions'], queryFn: identityApi.sessions, placeholderData: mockSessions });

  const mfaM = useMutation({
    mutationFn: ({ method, enabled }: { method: string; enabled: boolean }) =>
      identityApi.toggleMfa(method as any, enabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mfa'] }),
  });

  const revokeM = useMutation({
    mutationFn: (id: string) => identityApi.revokeSession(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sessions'] });
      showToast('会话已吊销');
    },
  });

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        {/* profile */}
        <View style={styles.profileCard}>
          <Avatar name={meQ.data?.name ?? 'LX'} size="lg" />
          <View style={{ flex: 1, marginLeft: 14 }}>
            <Text style={styles.profileName}>{meQ.data?.name}</Text>
            <Text style={styles.profileId}>uid: {meQ.data?.uid}</Text>
            <View style={styles.trustRow}>
              <View style={styles.trustBar}>
                <View style={[styles.trustFill, { width: `${meQ.data?.trustScore ?? 0}%` }]} />
              </View>
              <Text style={styles.trustNum}>{meQ.data?.trustScore}</Text>
            </View>
          </View>
        </View>

        <SecHead title="多因素认证" meta={`MFA · ${(mfaQ.data ?? []).filter((m) => m.enabled).length}/4`} />
        <Card>
          {(mfaQ.data ?? []).map((m, idx, arr) => (
            <View key={m.method}>
              <View style={styles.row}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.rowTitle}>{m.label}</Text>
                  <Text style={styles.rowDetail}>{m.detail}</Text>
                </View>
                <Toggle
                  value={m.enabled}
                  onChange={(v) => {
                    mfaM.mutate({ method: m.method, enabled: v });
                    showToast(v ? '已启用' : '已停用');
                  }}
                />
              </View>
              {idx < arr.length - 1 && <View style={styles.divider} />}
            </View>
          ))}
        </Card>

        <SecHead title="已注册设备" action="+ 添加" />
        <Card>
          {(devQ.data ?? []).map((d, idx, arr) => (
            <View key={d.id}>
              <View style={styles.row}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.rowTitle}>{d.name}</Text>
                  <Text style={styles.rowDetail}>
                    {[d.os, d.browser].filter(Boolean).join(' · ')}
                    {d.geo && ` · ${d.geo}`}
                  </Text>
                </View>
                <View style={[styles.pill, { backgroundColor: d.suspicious ? 'rgba(245,165,36,0.12)' : 'rgba(77,212,196,0.12)' }]}>
                  <Text style={[styles.pillText, { color: d.suspicious ? colors.amber : colors.teal }]}>
                    {d.suspicious ? '审查' : d.current ? '当前' : '信任'}
                  </Text>
                </View>
              </View>
              {idx < arr.length - 1 && <View style={styles.divider} />}
            </View>
          ))}
        </Card>

        <SecHead title="活跃会话" meta={`${(sessQ.data ?? []).length} SESSIONS`} />
        <Card>
          {(sessQ.data ?? []).map((s, idx, arr) => (
            <View key={s.id}>
              <View style={styles.row}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.rowTitle}>{s.label}</Text>
                  <Text style={styles.rowDetail}>
                    {s.detail} · 剩 {formatExpiresIn(s.expiresIn)}
                  </Text>
                </View>
                <RiskPill risk={s.risk} />
              </View>
              {idx < arr.length - 1 && <View style={styles.divider} />}
            </View>
          ))}
          <Text style={styles.revokeAll} onPress={() => identityApi.revokeAll().then(() => showToast('全部已吊销'))}>
            吊销所有会话
          </Text>
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
};

const mockProfile = { uid: 'a3f8-9b2e-7d4c-1f6a', name: '林雪 · 高级分析师', role: 'analyst', trustScore: 92 };
const mockMfa = [
  { method: 'totp' as const, enabled: true, label: 'TOTP · Google Authenticator', detail: '已启用 · 30s 刷新' },
  { method: 'webauthn' as const, enabled: true, label: 'WebAuthn · YubiKey 5C', detail: '已注册 · FIDO2' },
  { method: 'sms' as const, enabled: true, label: 'SMS 备用', detail: '+86 ****8829' },
  { method: 'push' as const, enabled: false, label: 'Push 通知', detail: '未配置' },
];
const mockDevices = [
  { id: 'd1', name: 'MacBook Pro · M3', os: 'macOS 14.4', browser: 'Chrome 124', trusted: true, lastSeen: new Date().toISOString(), current: false, geo: '北京' },
  { id: 'd2', name: 'iPhone 15 Pro', os: 'iOS 17.5', trusted: true, lastSeen: new Date().toISOString(), current: true, geo: '北京' },
  { id: 'd3', name: '未知 Android 设备', os: 'Android 14', trusted: false, lastSeen: new Date(Date.now() - 3600e3).toISOString(), current: false, geo: '北京', suspicious: true },
];
const mockSessions = [
  { id: 's1', type: 'control' as const, label: '控制台会话', detail: '噪声协议 · 已加密', expiresIn: 3600 * 6, risk: 'low' as const },
  { id: 's2', type: 'data' as const, label: 'API 数据面', detail: '7 天令牌 · 持续认证', expiresIn: 3600 * 24 * 4, risk: 'low' as const },
  { id: 's3', type: 'micro' as const, label: '微隧道 · 控制面', detail: '6 小时令牌 · 北京', expiresIn: 3600 * 1.5, risk: 'medium' as const },
];

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.void },
  scroll: { paddingHorizontal: spacing.lg, paddingBottom: 120 },
  profileCard: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: colors.panel, borderRadius: 20,
    borderWidth: 1, borderColor: colors.line, padding: spacing.lg,
  },
  profileName: { color: colors.ink1, fontSize: 16, fontWeight: '700' },
  profileId: { color: colors.ink3, fontSize: 10, marginTop: 3, fontVariant: ['tabular-nums'] },
  trustRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 },
  trustBar: { flex: 1, height: 4, backgroundColor: colors.void2, borderRadius: 2, overflow: 'hidden' },
  trustFill: { height: '100%', backgroundColor: colors.teal },
  trustNum: { color: colors.teal, fontSize: 11, fontWeight: '700', fontVariant: ['tabular-nums'] },

  secHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 22, marginBottom: 12 },
  secTitle: { color: colors.ink1, fontWeight: '700', fontSize: 14 },
  secMeta: { color: colors.ink3, fontSize: 10, letterSpacing: 1 },
  secAction: { color: colors.teal, fontSize: 12, fontWeight: '600' },

  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12 },
  rowTitle: { color: colors.ink1, fontSize: 13, fontWeight: '600' },
  rowDetail: { color: colors.ink3, fontSize: 10, marginTop: 3, fontVariant: ['tabular-nums'] },
  divider: { height: 1, backgroundColor: colors.line },
  pill: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4 },
  pillText: { fontSize: 11, fontWeight: '600' },

  revokeAll: { color: colors.red, fontSize: 12, fontWeight: '600', textAlign: 'center', paddingTop: 12 },
});
