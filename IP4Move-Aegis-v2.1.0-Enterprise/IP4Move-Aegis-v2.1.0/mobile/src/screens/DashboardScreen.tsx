import React, { useEffect, useState } from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Svg, { Circle, Path } from 'react-native-svg';

import { tunnelsApi, type Tunnel } from '@/api/tunnels';
import { threatsApi, type Threat } from '@/api/threats';
import { useAppStore } from '@/store';
import { Card } from '@/components/Card';
import { TunnelRow } from '@/components/TunnelRow';
import { ThreatRow } from '@/components/ThreatRow';
import { BarChart } from '@/components/BarChart';
import { colors, radius, spacing } from '@/theme';
import { formatBytes } from '@/utils/format';

const Header: React.FC = () => (
  <View style={styles.header}>
    <View style={styles.brand}>
      <View style={styles.brandMark}>
        <Svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke={colors.void} strokeWidth={2.5}>
          <Path d="M12 2L3 6v6c0 5 4 9 9 10 5-1 9-5 9-10V6l-9-4z" />
          <Path d="M9 12l2 2 4-4" />
        </Svg>
      </View>
      <View>
        <Text style={styles.brandT1}>AEGIS</Text>
        <Text style={styles.brandT2}>v2.1.0 · SECURE</Text>
      </View>
    </View>
    <View style={styles.livePill}>
      <View style={styles.liveDot} />
      <Text style={styles.liveText}>LIVE</Text>
    </View>
  </View>
);

const Hero: React.FC<{ tunnels: Tunnel[]; trafficIn: number; trafficOut: number; uptime: number }> = ({
  tunnels,
  trafficIn,
  trafficOut,
  uptime,
}) => {
  const active = tunnels.filter((t) => t.enabled).length;
  return (
    <Card variant="hero" style={styles.heroCard}>
      <Text style={styles.heroGreeting}>// OPS-7 · 态势感知</Text>
      <Text style={styles.heroTitle}>
        系统<Text style={{ color: colors.teal }}>在线</Text>
        {'\n'}威胁等级：中
      </Text>

      <View style={styles.statRow}>
        <Stat num={`${active}/${tunnels.length}`} label="ACTIVE" />
        <Stat num={formatBytes(trafficOut)} label="EGRESS" />
        <Stat num={`${uptime.toFixed(0)}%`} label="UPTIME" />
      </View>
    </Card>
  );
};

const Stat: React.FC<{ num: string; label: string }> = ({ num, label }) => (
  <View style={styles.stat}>
    <Text style={styles.statNum}>{num}</Text>
    <Text style={styles.statLabel}>{label}</Text>
  </View>
);

const SecHead: React.FC<{ title: string; meta?: string; action?: string; onAction?: () => void }> = ({
  title,
  meta,
  action,
  onAction,
}) => (
  <View style={styles.secHead}>
    <Text style={styles.secTitle}>{title}</Text>
    {action ? (
      <Text style={styles.secAction} onPress={onAction}>
        {action}
      </Text>
    ) : meta ? (
      <Text style={styles.secMeta}>{meta}</Text>
    ) : null}
  </View>
);

export const DashboardScreen: React.FC = () => {
  const showToast = useAppStore((s) => s.showToast);
  const qc = useQueryClient();

  const tunnelsQ = useQuery({
    queryKey: ['tunnels'],
    queryFn: tunnelsApi.list,
    // Fallback mock for offline first-run
    placeholderData: mockTunnels,
  });

  const trafficQ = useQuery({
    queryKey: ['traffic', '24h'],
    queryFn: () => tunnelsApi.traffic('24h'),
    placeholderData: mockTraffic,
  });

  const threatsQ = useQuery({
    queryKey: ['threats', 'feed', 3],
    queryFn: () => threatsApi.feed(3),
    placeholderData: mockThreats,
  });

  const [series, setSeries] = useState<number[]>([]);

  useEffect(() => {
    if (trafficQ.data) {
      setSeries(trafficQ.data.map((p) => p.outBytes));
    }
  }, [trafficQ.data]);

  const onRefresh = () => {
    qc.invalidateQueries({ queryKey: ['tunnels'] });
    qc.invalidateQueries({ queryKey: ['traffic'] });
    qc.invalidateQueries({ queryKey: ['threats'] });
    showToast('数据已刷新');
  };

  const trafficIn = trafficQ.data?.reduce((s, p) => s + p.inBytes, 0) ?? 0;
  const trafficOut = trafficQ.data?.reduce((s, p) => s + p.outBytes, 0) ?? 0;
  const uptime = 98 + Math.random() * 1.5;

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <Header />
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={false} onRefresh={onRefresh} tintColor={colors.teal} />}
      >
        <Hero tunnels={tunnelsQ.data ?? []} trafficIn={trafficIn} trafficOut={trafficOut} uptime={uptime} />

        <SecHead title="流量监控" meta="24H · LIVE" />
        <Card>
          {trafficQ.isLoading && !trafficQ.data ? (
            <ActivityIndicator color={colors.teal} />
          ) : (
            <BarChart data={series} height={120} />
          )}
          <View style={styles.axis}>
            {['00', '06', '12', '18', 'NOW'].map((h) => (
              <Text key={h} style={styles.axisText}>{h}</Text>
            ))}
          </View>
          <View style={styles.legend}>
            <Text style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: colors.teal }]} /> 出站
            </Text>
            <Text style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: colors.ink4 }]} /> 入站
            </Text>
          </View>
        </Card>

        <SecHead title="活跃隧道" action="查看全部 →" />
        {(tunnelsQ.data ?? []).slice(0, 3).map((t) => (
          <TunnelRow
            key={t.id}
            tunnel={t}
            onToggle={(enabled) => {
              tunnelsApi.toggle(t.id, enabled).catch(() => showToast('切换失败'));
              showToast(enabled ? '已启用' : '已停用');
            }}
          />
        ))}

        <SecHead title="最近威胁" action="实时源 →" />
        <Card>
          {(threatsQ.data ?? []).map((th) => (
            <ThreatRow key={th.id} threat={th} />
          ))}
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
};

const mockTunnels: Tunnel[] = [
  { id: '1', name: 'mix-node-01', country: 'NL · 阿姆斯特丹', location: 'NL', ip: '142.93.4.21', latencyMs: 23, throughputGbps: 1.2, protocol: 'DoH', status: 'active', enabled: true },
  { id: '2', name: 'mix-node-02', country: 'CH · 苏黎世',     location: 'CH', ip: '203.0.113.47', latencyMs: 41, throughputGbps: 0.9, protocol: 'PQC', status: 'rebuilding', enabled: false },
  { id: '3', name: 'mix-node-03', country: 'JP · 东京',        location: 'JP', ip: '198.51.100.6', latencyMs: 19, throughputGbps: 0.8, protocol: 'WebRTC', status: 'active', enabled: true },
];

const mockTraffic = Array.from({ length: 24 }, (_, i) => {
  const peak = 14;
  const dist = Math.abs(i - peak);
  const out = Math.max(0.2, 1 - dist * dist * 0.008) * (1 + Math.sin(i * 1.3) * 0.2);
  const inn = out * (0.4 + Math.sin(i * 0.5) * 0.2);
  return { t: new Date().toISOString(), inBytes: inn, outBytes: out };
});

const mockThreats: Threat[] = [
  { id: 't1', title: 'C2 服务器活动', ioc: '185.220.101.4', severity: 'critical', source: 'MISP', confidence: 0.96, observedAt: new Date().toISOString() },
  { id: 't2', title: '恶意软件分发', ioc: 'malicious-cdn.example.io', severity: 'high', source: 'OpenCTI', confidence: 0.88, observedAt: new Date(Date.now() - 1500e3).toISOString() },
  { id: 't3', title: '钓鱼域名注册', ioc: 'secure-bank-update.cn', severity: 'medium', source: 'OSINT', confidence: 0.71, observedAt: new Date(Date.now() - 3600e3).toISOString() },
];

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.void },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: spacing.lg, paddingVertical: spacing.md,
  },
  brand: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  brandMark: {
    width: 30, height: 30, backgroundColor: colors.teal,
    transform: [{ rotate: '0deg' }],
    alignItems: 'center', justifyContent: 'center',
    borderRadius: 6,
  },
  brandT1: { color: colors.ink1, fontWeight: '800', fontSize: 15, letterSpacing: 0.5 },
  brandT2: { color: colors.teal, fontSize: 9, letterSpacing: 1.5, marginTop: 2, fontVariant: ['tabular-nums'] },
  livePill: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    paddingHorizontal: 10, paddingVertical: 5, borderRadius: radius.pill,
    borderWidth: 1, borderColor: colors.line, backgroundColor: colors.panel,
  },
  liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.teal },
  liveText: { color: colors.ink2, fontSize: 10, fontWeight: '600', letterSpacing: 1.2 },

  scroll: { paddingHorizontal: spacing.lg, paddingBottom: 120 },
  heroCard: { marginBottom: spacing.lg, position: 'relative', overflow: 'hidden' },
  heroGreeting: { color: colors.teal, fontSize: 10, letterSpacing: 2, fontWeight: '600' },
  heroTitle: { color: colors.ink1, fontSize: 26, fontWeight: '800', lineHeight: 32, marginTop: 6, letterSpacing: -0.5 },
  statRow: { flexDirection: 'row', gap: 8, marginTop: 18 },
  stat: { flex: 1, backgroundColor: 'rgba(0,0,0,0.3)', borderWidth: 1, borderColor: colors.line, borderRadius: 10, paddingVertical: 10, alignItems: 'center' },
  statNum: { color: colors.ink1, fontWeight: '700', fontSize: 18, fontVariant: ['tabular-nums'] },
  statLabel: { color: colors.ink3, fontSize: 9, letterSpacing: 1.2, marginTop: 4 },

  secHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 22, marginBottom: 12 },
  secTitle: { color: colors.ink1, fontWeight: '700', fontSize: 14 },
  secAction: { color: colors.teal, fontSize: 12, fontWeight: '600' },
  secMeta: { color: colors.ink3, fontSize: 10, letterSpacing: 1 },

  axis: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 },
  axisText: { color: colors.ink4, fontSize: 9, fontVariant: ['tabular-nums'] },
  legend: { flexDirection: 'row', gap: 16, marginTop: 10 },
  legendItem: { color: colors.ink2, fontSize: 10, flexDirection: 'row', alignItems: 'center' },
  legendDot: { width: 8, height: 8, borderRadius: 2, marginRight: 4, display: 'none' },
});
