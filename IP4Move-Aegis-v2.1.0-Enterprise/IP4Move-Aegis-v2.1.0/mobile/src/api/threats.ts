import { api } from './client';

export type ThreatSeverity = 'critical' | 'high' | 'medium' | 'low';

export interface Threat {
  id: string;
  title: string;
  ioc: string;
  severity: ThreatSeverity;
  source: 'MISP' | 'OpenCTI' | 'TAXII' | 'OSINT';
  confidence: number; // 0~1
  observedAt: string;
}

export interface ReputationResult {
  target: string;
  score: number; // 0~100
  grade: 'A' | 'B' | 'C' | 'F';
  risk: 'low' | 'medium' | 'high' | 'critical';
  tags: string[];
  sources: number;
}

export const threatsApi = {
  feed: (limit = 50) =>
    api.get<Threat[]>('/threats/feed', { params: { limit } }).then((r) => r.data),
  reputation: (target: string) =>
    api
      .get<ReputationResult>('/threats/reputation', { params: { target } })
      .then((r) => r.data),
};
