import axios, { AxiosError, AxiosInstance } from 'axios';
import * as SecureStore from 'expo-secure-store';
import Constants from 'expo-constants';

const API_BASE_URL =
  (Constants.expoConfig?.extra as any)?.apiBaseUrl ?? 'https://api.aegis.ip4move.io';

const TOKEN_KEY = 'aegis.access_token';
const REFRESH_KEY = 'aegis.refresh_token';

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// 请求拦截：注入 Bearer token
api.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截：401 自动刷新 + 统一错误
api.interceptors.response.use(
  (res) => res,
  async (err: AxiosError) => {
    const original: any = err.config;
    if (err.response?.status === 401 && !original?._retry) {
      original._retry = true;
      try {
        const refresh = await SecureStore.getItemAsync(REFRESH_KEY);
        if (refresh) {
          const r = await axios.post(`${API_BASE_URL}/auth/refresh`, { refresh });
          await SecureStore.setItemAsync(TOKEN_KEY, r.data.access);
          original.headers.Authorization = `Bearer ${r.data.access}`;
          return api.request(original);
        }
      } catch {
        await SecureStore.deleteItemAsync(TOKEN_KEY);
        await SecureStore.deleteItemAsync(REFRESH_KEY);
      }
    }
    return Promise.reject(err);
  },
);

export const tokenStore = {
  set: (access: string, refresh: string) =>
    Promise.all([
      SecureStore.setItemAsync(TOKEN_KEY, access),
      SecureStore.setItemAsync(REFRESH_KEY, refresh),
    ]),
  clear: () =>
    Promise.all([
      SecureStore.deleteItemAsync(TOKEN_KEY),
      SecureStore.deleteItemAsync(REFRESH_KEY),
    ]),
  get: () => SecureStore.getItemAsync(TOKEN_KEY),
};
