import { create } from 'zustand';
import type { IdentityProfile, MfaConfig, Device, Session } from '@/api/identity';

interface AppState {
  // auth
  isAuthed: boolean;
  setAuthed: (v: boolean) => void;

  // identity
  profile: IdentityProfile | null;
  setProfile: (p: IdentityProfile | null) => void;

  mfa: MfaConfig[];
  setMfa: (m: MfaConfig[]) => void;

  devices: Device[];
  setDevices: (d: Device[]) => void;

  sessions: Session[];
  setSessions: (s: Session[]) => void;

  // ui
  toast: string | null;
  showToast: (m: string) => void;
  clearToast: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  isAuthed: false,
  setAuthed: (v) => set({ isAuthed: v }),

  profile: null,
  setProfile: (profile) => set({ profile }),

  mfa: [],
  setMfa: (mfa) => set({ mfa }),

  devices: [],
  setDevices: (devices) => set({ devices }),

  sessions: [],
  setSessions: (sessions) => set({ sessions }),

  toast: null,
  showToast: (toast) => {
    set({ toast });
    setTimeout(() => set({ toast: null }), 2200);
  },
  clearToast: () => set({ toast: null }),
}));
