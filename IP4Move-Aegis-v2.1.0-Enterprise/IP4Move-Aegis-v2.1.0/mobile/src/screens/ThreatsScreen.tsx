import React, { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useMutation, useQuery } from '@tanstack/react-query';

import { threatsApi, type ReputationResult } from '@/api/threats';
import { Card } from '@/components/Card';
import { ThreatRow } from '@/components/ThreatRow';
import { useAppStore } from '@/store';
import { colors, radius, spacing } from '@/theme';

const SecHead: React.FC<{ title: string; meta?: string }> = ({ title, meta }) => (
  <View style={styles.secHead}>
    <Text style={styles.secTitle}>{title}</Text>
    {meta && <Text style={styles.secMeta}>{meta}</Text>}
  </View>
);

const gradeColor = (g: ReputationResult['grade']) => {
  if (g === 'A' || g === 'B') return colors.teal;
  if (g === 'C') return colors.amber;
  return colors.red;
};

const riskLabel = (r: ReputationResult['risk']) => ({
  low: '低', medium: '中', high: '高', critical: '极高',
}[r]);

export const ThreatsScreen: React.FC = () => {
  const [input, setInput] = useState('');
  const [result, setResult] = useState<ReputationResult | null>(null);
  const showToast = useAppStore((s) => s.showToast);

  const feedQ = useQuery({
    queryKey: ['threats', 'feed', 50],
    queryFn: () => threatsApi.feed(50),
    refetchInterval: 10_000,
  });

  const lookupM = useMutation({
    mutationFn: (target: string) => threatsApi.reputation(target),
    onSuccess: (data) => {
      setResult(data);
      showToast('信誉评分已更新');
    },
    onError: () => showToast('查询失败'),
  });

  const submit = () => {
    const v = input.trim();
    if (!v) {
      showToast('请输入要查询的指标');
      return;
    }
    lookupM.mutate(v);
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Card>
          <Text style={styles.label}>IOC 查询</Text>
          <View style={styles.searchBox}>
            <TextInput
              style={styles.input}
              placeholder="IP / 域名 / 哈希 / URL"
              placeholderTextColor={colors.ink4}
              value={input}
              onChangeText={setInput}
              onSubmitEditing={submit}
              autoCapitalize="none"
              autoCorrect={false}
              returnKeyType="search"
            />
            <Text style={styles.searchBtn} onPress={submit}>
              {lookupM.isPending ? <ActivityIndicator size="small" color={colors.void} /> : '查询'}
            </Text>
          </View>

          {result && (
            <View
              style={[
                styles.resultBox,
                { borderLeftColor: gradeColor(result.grade) },
              ]}
            >
              <View style={styles.resultHead}>
                <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 8 }}>
                  <Text style={[styles.resultNum, { color: gradeColor(result.grade) }]}>
                    {result.score}
                  </Text>
                  <Text style={styles.resultGrade}>等级 {result.grade}</Text>
                </View>
                <View
                  style={[
                    styles.riskPill,
                    {
                      backgroundColor:
                        result.score >= 60 ? 'rgba(77,212,196,0.12)' : 'rgba(229,72,77,0.12)',
                    },
                  ]}
                >
                  <Text
                    style={{
                      color: result.score >= 60 ? colors.teal : colors.red,
                      fontSize: 11,
                      fontWeight: '600',
                    }}
                  >
                    {riskLabel(result.risk)}
                  </Text>
                </View>
              </View>
              <Text style={styles.resultTarget}>{result.target}</Text>
              <View style={styles.tagsRow}>
                {result.tags.map((t) => (
                  <View key={t} style={styles.tag}>
                    <Text style={styles.tagText}>{t}</Text>
                  </View>
                ))}
              </View>
            </View>
          )}
        </Card>

        <SecHead title="实时威胁流" meta="STIX · MISP · OSINT" />
        <Card>
          {feedQ.isLoading && !feedQ.data ? (
            <ActivityIndicator color={colors.teal} />
          ) : (
            (feedQ.data ?? []).map((t) => <ThreatRow key={t.id} threat={t} />)
          )}
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.void },
  scroll: { paddingHorizontal: spacing.lg, paddingBottom: 120 },
  label: {
    color: colors.ink3, fontSize: 10, letterSpacing: 1.5, fontWeight: '600',
    marginBottom: 12,
  },
  searchBox: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: colors.void2, borderRadius: 10,
    borderWidth: 1, borderColor: colors.line, paddingHorizontal: 12, paddingVertical: 4,
  },
  input: { flex: 1, color: colors.ink1, fontSize: 13, paddingVertical: 8, fontVariant: ['tabular-nums'] },
  searchBtn: {
    backgroundColor: colors.teal, color: colors.void, paddingHorizontal: 12, paddingVertical: 6,
    borderRadius: 6, fontSize: 11, fontWeight: '700', overflow: 'hidden',
  },
  resultBox: {
    marginTop: 14, padding: 14, backgroundColor: colors.void2, borderRadius: 10,
    borderLeftWidth: 3,
  },
  resultHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  resultNum: { fontSize: 32, fontWeight: '700', fontVariant: ['tabular-nums'], letterSpacing: -1 },
  resultGrade: { color: colors.ink2, fontSize: 14, fontWeight: '800' },
  resultTarget: { color: colors.ink2, fontSize: 11, marginTop: 4, fontVariant: ['tabular-nums'] },
  riskPill: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4 },
  tagsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 10 },
  tag: {
    paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4,
    backgroundColor: 'rgba(77,212,196,0.1)', borderWidth: 1, borderColor: 'rgba(77,212,196,0.2)',
  },
  tagText: { color: colors.teal, fontSize: 10, fontWeight: '600' },

  secHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 22, marginBottom: 12 },
  secTitle: { color: colors.ink1, fontWeight: '700', fontSize: 14 },
  secMeta: { color: colors.ink3, fontSize: 10, letterSpacing: 1 },
});
