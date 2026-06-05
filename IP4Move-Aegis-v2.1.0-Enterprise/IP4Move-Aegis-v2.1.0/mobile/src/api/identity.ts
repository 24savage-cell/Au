import { api } from './client';

export type MfaMethod = 'totp' | 'webauthn' | 'sms' | 'push';

export interface MfaConfig {
  method: MfaMethod;
  enabled: boolean;
  label: string;
  detail: string;
}

export interface Device {
  id: string;
  name: string;
  os: string;
  browser?: string;
  trusted: boolean;
  lastSeen: string;
  current?: boolean;
  geo?: string;
  suspicious?: boolean;
}

export interface Session {
  id: string;
  type: 'control' | 'data' | 'micro';
  label: string;
  detail: string;
  expiresIn: number; // seconds
  risk: 'low' | 'medium' | 'high';
}

export interface IdentityProfile {
  uid: string;
  name: string;
  role: string;
  trustScore: number; // 0~100
}

export const identityApi = {
  me: () => api.get<IdentityProfile>('/me').then((r) => r.data),
  mfa: () => api.get<MfaConfig[]>('/me/mfa').then((r) => r.data),
  toggleMfa: (method: MfaMethod, enabled: boolean) =>
    api.post(`/me/mfa/${method}/toggle`, { enabled }).then((r) => r.data),
  devices: () => api.get<Device[]>('/me/devices').then((r) => r.data),
  sessions: () => api.get<Session[]>('/me/sessions').then((r) => r.data),
  revokeSession: (id: string) => api.delete(`/me/sessions/${id}`).then((r) => r.data),
  revokeAll: () => api.post('/me/sessions/revoke-all').then((r) => r.data),
};
