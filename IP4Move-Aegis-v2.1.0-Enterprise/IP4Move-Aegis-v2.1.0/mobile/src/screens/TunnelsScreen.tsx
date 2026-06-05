import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { tunnelsApi, type Tunnel } from '@/api/tunnels';
import { TunnelRow } from '@/components/TunnelRow';
import { Toggle } from '@/components/Toggle';
import { Card } from '@/components/Card';
import { useAppStore } from '@/store';
import { colors, spacing } from '@/theme';

const SecHead: React.FC<{ title: string; meta?: string; action?: string }> = ({ title, meta, action }) => (
  <View style={styles.secHead}>
    <Text style={styles.secTitle}>{title}</Text>
    <Text style={meta ? styles.secMeta : styles.secAction}>{meta ?? action}</Text>
  </View>
);

export const TunnelsScreen: React.FC = () => {
  const showToast = useAppStore((s) => s.showToast);
  const qc = useQueryClient();

  const tunnelsQ = useQuery({
    queryKey: ['tunnels'],
    queryFn: tunnelsApi.list,
    placeholderData: mockTunnels,
  });

  const disguiseQ = useQuery({
    queryKey: ['disguise'],
    queryFn: tunnelsApi.disguise,
    placeholderData: { doh: true, webrtc: true, dynamicBatch: true, emergency: false },
  });

  const toggleM = useMutation({
    mutationFn: (id: string) => tunnelsApi.toggle(id, true),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tunnels'] }),
  });

  const disguiseM = useMutation({
    mutationFn: tunnelsApi.setDisguise,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['disguise'] }),
  });

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>
          {(tunnelsQ.data ?? []).filter((t) => t.enabled).length} 个<Text style={{ color: colors.teal }}>活跃</Text>隧道
        </Text>
        <Text style={styles.subtitle}>
          总出口带宽{' '}
          {(tunnelsQ.data ?? [])
            .filter((t) => t.enabled)
            .reduce((s, t) => s + t.throughputGbps, 0)
            .toFixed(1)}{' '}
          Gbps · 平均延迟 27 ms
        </Text>

        <SecHead title="出站节点" action="+ 新建" />
        {(tunnelsQ.data ?? []).map((t) => (
          <TunnelRow
            key={t.id}
            tunnel={t}
            onToggle={(enabled) => {
              tunnelsApi.toggle(t.id, enabled).catch(() => {});
              showToast(enabled ? '已启用' : '已停用');
            }}
          />
        ))}

        <SecHead title="流量伪装" meta="DISGUISE" />
        <Card>
          {[
            { key: 'doh', label: 'DoH over HTTPS', detail: '通过 1.1.1.1 隧道 DNS 查询' },
            { key: 'webrtc', label: 'WebRTC DataChannel', detail: 'P2P 媒体流伪装' },
            { key: 'dynamicBatch', label: '动态批处理', detail: '8-128 自适应' },
            { key: 'emergency', label: '紧急通道', detail: '低延迟 <50ms' },
          ].map((row, idx, arr) => (
            <View key={row.key}>
              <View style={styles.settingRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.settingLabel}>{row.label}</Text>
                  <Text style={styles.settingDetail}>{row.detail}</Text>
                </View>
                <Toggle
                  value={(disguiseQ.data as any)?.[row.key] ?? false}
                  onChange={(v) => {
                    disguiseM.mutate({ [row.key]: v } as any);
                    showToast(v ? '已启用' : '已停用');
                  }}
                />
              </View>
              {idx < arr.length - 1 && <View style={styles.divider} />}
            </View>
          ))}
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
};

const mockTunnels: Tunnel[] = [
  { id: '1', name: 'mix-node-01', country: 'NL · 阿姆斯特丹', location: 'NL', ip: '142.93.4.21', latencyMs: 23, throughputGbps: 1.2, protocol: 'DoH', status: 'active', enabled: true },
  { id: '2', name: 'mix-node-02', country: 'CH · 苏黎世',     location: 'CH', ip: '203.0.113.47', latencyMs: 31, throughputGbps: 0.9, protocol: 'QUIC', status: 'active', enabled: true },
  { id: '3', name: 'mix-node-03', country: 'IS · 雷克雅未克', location: 'IS', ip: '', latencyMs: 41, throughputGbps: 0, protocol: 'PQC', status: 'rebuilding', enabled: false },
  { id: '4', name: 'mix-node-04', country: 'JP · 东京',        location: 'JP', ip: '198.51.100.6', latencyMs: 19, throughputGbps: 0.8, protocol: 'WebRTC', status: 'active', enabled: true },
];

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.void },
  scroll: { paddingHorizontal: spacing.lg, paddingBottom: 120 },
  title: { color: colors.ink1, fontSize: 26, fontWeight: '800', letterSpacing: -0.5 },
  subtitle: { color: colors.ink3, fontSize: 11, marginTop: 6, fontVariant: ['tabular-nums'] },
  secHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 24, marginBottom: 12 },
  secTitle: { color: colors.ink1, fontWeight: '700', fontSize: 14 },
  secMeta: { color: colors.ink3, fontSize: 10, letterSpacing: 1 },
  secAction: { color: colors.teal, fontSize: 12, fontWeight: '600' },
  settingRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12 },
  settingLabel: { color: colors.ink1, fontSize: 13, fontWeight: '600' },
  settingDetail: { color: colors.ink3, fontSize: 10, marginTop: 3, fontVariant: ['tabular-nums'] },
  divider: { height: 1, backgroundColor: colors.line },
});
