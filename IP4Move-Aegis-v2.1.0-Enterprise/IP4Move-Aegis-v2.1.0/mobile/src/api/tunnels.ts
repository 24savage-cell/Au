import { api } from './client';

export type TunnelStatus = 'active' | 'connecting' | 'rebuilding' | 'offline';
export type TunnelProtocol = 'DoH' | 'QUIC' | 'PQC' | 'WebRTC';

export interface Tunnel {
  id: string;
  name: string;
  location: string;
  country: string;
  ip: string;
  latencyMs: number;
  throughputGbps: number;
  protocol: TunnelProtocol;
  status: TunnelStatus;
  enabled: boolean;
}

export interface TrafficPoint {
  t: string; // ISO timestamp
  inBytes: number;
  outBytes: number;
}

export const tunnelsApi = {
  list: () => api.get<Tunnel[]>('/tunnels').then((r) => r.data),
  toggle: (id: string, enabled: boolean) =>
    api.post<Tunnel>(`/tunnels/${id}/toggle`, { enabled }).then((r) => r.data),
  traffic: (range: '24h' | '7d' | '30d' = '24h') =>
    api.get<TrafficPoint[]>(`/tunnels/traffic`, { params: { range } }).then((r) => r.data),
  disguise: () =>
    api
      .get<{ doh: boolean; webrtc: boolean; dynamicBatch: boolean; emergency: boolean }>(
        '/tunnels/disguise',
      )
      .then((r) => r.data),
  setDisguise: (body: { doh?: boolean; webrtc?: boolean; dynamicBatch?: boolean }) =>
    api.post('/tunnels/disguise', body).then((r) => r.data),
};
