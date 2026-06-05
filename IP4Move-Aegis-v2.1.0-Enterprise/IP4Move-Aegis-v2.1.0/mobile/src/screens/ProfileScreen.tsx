import React, { useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Path, Circle } from 'react-native-svg';

import { Card } from '@/components/Card';
import { Toggle } from '@/components/Toggle';
import { tokenStore } from '@/api/client';
import { useAppStore } from '@/store';
import { colors, spacing } from '@/theme';

const SecHead: React.FC<{ title: string }> = ({ title }) => (
  <Text style={styles.secTitle}>{title}</Text>
);

const Row: React.FC<{ icon: React.ReactNode; title: React.ReactNode; detail: string; right?: React.ReactNode }> = ({
  icon, title, detail, right,
}) => (
  <View style={styles.row}>
    <View style={styles.iconBox}>{icon}</View>
    <View style={{ flex: 1 }}>
      <Text style={styles.rowTitle}>{title}</Text>
      <Text style={styles.rowDetail}>{detail}</Text>
    </View>
    {right}
  </View>
);

export const ProfileScreen: React.FC = () => {
  const showToast = useAppStore((s) => s.showToast);
  const setAuthed = useAppStore((s) => s.setAuthed);

  const [settings, setSettings] = useState({
    antiProbe: true,
    pqc: true,
    dp: true,
    emergency: false,
  });

  const upd = (k: keyof typeof settings) => (v: boolean) => {
    setSettings((s) => ({ ...s, [k]: v }));
    showToast(v ? '已启用' : '已停用');
  };

  const onLogout = () => {
    Alert.alert('退出登录', '吊销所有会话令牌？', [
      { text: '取消', style: 'cancel' },
      {
        text: '退出',
        style: 'destructive',
        onPress: async () => {
          await tokenStore.clear();
          setAuthed(false);
          showToast('已退出');
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.profileCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>LX</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.profileName}>林雪 · 高级分析师</Text>
            <Text style={styles.profileId}>uid: a3f8-9b2e-7d4c-1f6a</Text>
            <View style={styles.trustRow}>
              <View style={styles.trustBar}>
                <View style={[styles.trustFill, { width: '92%' }]} />
              </View>
              <Text style={styles.trustNum}>信任 92%</Text>
            </View>
          </View>
        </View>

        <View style={{ marginTop: 22 }}><SecHead title="安全设置" /></View>
        <Card>
          <Row
            icon={<Svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke={colors.teal} strokeWidth={2}><Path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></Svg>}
            title="抗主动探测"
            detail="PoW 挑战 · 协议一致性"
            right={<Toggle value={settings.antiProbe} onChange={upd('antiProbe')} />}
          />
          <View style={styles.divider} />
          <Row
            icon={<Svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke={colors.teal} strokeWidth={2}><Path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3" /></Svg>}
            title="后量子加密"
            detail="ML-KEM-768 · liboqs"
            right={<Toggle value={settings.pqc} onChange={upd('pqc')} />}
          />
          <View style={styles.divider} />
          <Row
            icon={<Svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke={colors.teal} strokeWidth={2}><Circle cx={12} cy={12} r={3} /><Path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6" /></Svg>}
            title="差分隐私指标"
            detail="拉普拉斯噪声 · 时间分箱"
            right={<Toggle value={settings.dp} onChange={upd('dp')} />}
          />
          <View style={styles.divider} />
          <Row
            icon={<Svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke={colors.amber} strokeWidth={2}><Path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /></Svg>}
            title="紧急通道"
            detail="低延迟 <50ms"
            right={<Toggle value={settings.emergency} onChange={upd('emergency')} />}
          />
        </Card>

        <View style={{ marginTop: 22 }}><SecHead title="系统" /></View>
        <Card>
          <Row
            icon={<Svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke={colors.ink2} strokeWidth={2}><Circle cx={12} cy={12} r={3} /><Path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></Svg>}
            title="偏好设置"
            detail="通知 · 主题 · 语言"
            right={<Text style={{ color: colors.ink4 }}>›</Text>}
          />
          <View style={styles.divider} />
          <Row
            icon={<Svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke={colors.ink2} strokeWidth={2}><Path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><Path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" /></Svg>}
            title="操作日志"
            detail="2,847 条事件 · 30 天"
            right={<Text style={{ color: colors.ink4 }}>›</Text>}
          />
          <View style={styles.divider} />
          <Row
            icon={<Svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke={colors.red} strokeWidth={2}><Path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" /></Svg>}
            title={<Text style={{ color: colors.red }}>退出登录</Text>}
            detail="吊销所有会话令牌"
            right={null}
          />
        </Card>

        <Text style={styles.build} onPress={onLogout}>
          AEGIS v2.1.0 · BUILD 2026.05.31
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.void },
  scroll: { paddingHorizontal: spacing.lg, paddingBottom: 120 },
  profileCard: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: colors.panel, borderRadius: 20,
    borderWidth: 1, borderColor: colors.line, padding: spacing.lg,
  },
  avatar: { width: 56, height: 56, borderRadius: 14, backgroundColor: colors.teal, alignItems: 'center', justifyContent: 'center' },
  avatarText: { color: colors.void, fontWeight: '800', fontSize: 22 },
  profileName: { color: colors.ink1, fontSize: 16, fontWeight: '700' },
  profileId: { color: colors.ink3, fontSize: 10, marginTop: 3, fontVariant: ['tabular-nums'] },
  trustRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 },
  trustBar: { flex: 1, height: 4, backgroundColor: colors.void2, borderRadius: 2, overflow: 'hidden' },
  trustFill: { height: '100%', backgroundColor: colors.teal },
  trustNum: { color: colors.teal, fontSize: 11, fontWeight: '700' },

  secTitle: { color: colors.ink1, fontWeight: '700', fontSize: 14, marginBottom: 12 },
  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12 },
  iconBox: {
    width: 36, height: 36, borderRadius: 10,
    backgroundColor: colors.void2, borderWidth: 1, borderColor: colors.line,
    alignItems: 'center', justifyContent: 'center', marginRight: 12,
  },
  rowTitle: { color: colors.ink1, fontSize: 13, fontWeight: '600' },
  rowDetail: { color: colors.ink3, fontSize: 10, marginTop: 3, fontVariant: ['tabular-nums'] },
  divider: { height: 1, backgroundColor: colors.line },

  build: { color: colors.ink4, fontSize: 10, textAlign: 'center', paddingVertical: 24, letterSpacing: 1.5, fontVariant: ['tabular-nums'] },
});
