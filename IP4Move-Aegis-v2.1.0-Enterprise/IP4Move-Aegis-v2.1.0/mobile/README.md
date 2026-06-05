# AEGIS Mobile — 真正能在真机上运行的原生 App

> 基于 **Expo SDK 52 + React Native 0.76 (New Architecture)** 构建的原生 iOS / Android 应用。
> 不是浏览器模拟，不是 Web 套壳。是真正的 Native 组件、真正的 Hermes/JSC 引擎、真正的 iOS Bundle / Android APK。

---

## 项目结构

```
mobile/
├── App.tsx                          # 根组件 (GestureHandler + SafeArea + Query)
├── index.js                         # Expo 注册入口
├── app.json                         # Expo 配置 (iOS BundleId / Android Package / 图标)
├── eas.json                         # EAS Build 云打包配置
├── package.json                     # 依赖 (React Navigation、Reanimated、SVG…)
├── babel.config.js                  # 含路径别名 @/* → src/*
├── metro.config.js                  # Metro + SVG 支持
├── tsconfig.json                    # TS 严格模式
└── src/
    ├── theme/                       # 颜色 / 字体 / 间距常量
    ├── components/                  # 通用组件 (Card/Toggle/Badge/BarChart/…)
    ├── screens/                     # 5 个原生 Tab 页面
    ├── navigation/RootNavigator.tsx # 底部 Tab 导航 (原生 Bottom Tabs)
    ├── api/                         # 真实后端 API 客户端 (Axios + SecureStore)
    ├── store/index.ts               # Zustand 全局状态
    └── utils/format.ts              # 时间/字节格式化
```

---

## 在真机上跑起来（三种方式，从易到难）

### 方式 ① Expo Go（最快，2 分钟）

**适合**：开发调试、即时预览、QR 扫码即用

```bash
cd mobile
npm install
npx expo start
# 控制台会输出 QR 码
# iPhone  → 相机扫码
# Android → Expo Go App 内 "Scan QR Code"
```

要求：
- iPhone 安装 [Expo Go](https://apps.apple.com/app/expo-go/id982107779) (iOS 14+)
- Android 安装 [Expo Go](https://play.google.com/store/apps/details?id=host.exp.exponent) (Android 11+)
- 手机和电脑在同一 WiFi

### 方式 ② EAS Build（出 .apk / .ipa 装到任意真机）

**适合**：分发测试版给团队、上传 TestFlight / Internal Testing

```bash
# 第一次需要登录 Expo 账号
npm install -g eas-cli
eas login

# 配置项目 (首次)
eas init    # 会自动更新 app.json 里的 projectId

# 构建 Android APK（可在任意 Android 手机上直接安装）
eas build -p android --profile preview

# 构建 iOS IPA（需 Apple Developer 账号）
eas build -p ios --profile preview
```

构建完成后控制台会给出下载链接，扫描 / 点击即可安装到真机。

### 方式 ③ 本地原生构建（彻底脱离 Expo Go）

```bash
# 预编译原生工程
npx expo prebuild --platform ios --platform android

# iOS (需 macOS + Xcode)
cd ios && pod install && cd ..
npx expo run:ios --device

# Android (需 Android SDK)
npx expo run:android --device
```

---

## 后端对接

默认 API 地址在 [app.json](app.json) 的 `extra.apiBaseUrl`：

```json
"extra": { "apiBaseUrl": "https://api.aegis.ip4move.io" }
```

开发时改成本地后端：

```json
"extra": { "apiBaseUrl": "http://192.168.1.100:8080" }
```

后端需实现以下端点（与 IP4Move-Aegis FastAPI 对接）：

| Method | Path | 说明 |
|--------|------|------|
| POST | `/auth/login` | 登录 → 返回 access + refresh |
| POST | `/auth/refresh` | 刷新 token |
| GET | `/me` | 当前用户档案 |
| GET | `/me/mfa` | MFA 因子列表 |
| POST | `/me/mfa/:method/toggle` | 切换 MFA 因子 |
| GET | `/me/devices` | 已注册设备 |
| GET | `/me/sessions` | 活跃会话 |
| DELETE | `/me/sessions/:id` | 吊销单个会话 |
| POST | `/me/sessions/revoke-all` | 吊销全部 |
| GET | `/tunnels` | 隧道列表 |
| POST | `/tunnels/:id/toggle` | 启停隧道 |
| GET | `/tunnels/traffic?range=24h` | 流量时序 |
| GET | `/tunnels/disguise` | 流量伪装配置 |
| POST | `/tunnels/disguise` | 更新伪装配置 |
| GET | `/threats/feed?limit=50` | 威胁流 |
| GET | `/threats/reputation?target=...` | IOC 信誉查询 |

API 客户端：[src/api/](src/api/)
- `client.ts` — Axios 实例 + Bearer 注入 + 401 自动刷新 + SecureStore 持久化
- `tunnels.ts` / `threats.ts` / `identity.ts` — 各模块端点

---

## 已使用的能力（真机原生）

| 能力 | 库 | 用途 |
|------|----|----|
| 触觉反馈 | `expo-haptics` | 切换开关、按钮反馈 |
| 安全存储 | `expo-secure-store` | 访问令牌、刷新令牌加密存储 (Keychain / EncryptedSharedPreferences) |
| 推送通知 | `expo-notifications` | 威胁告警推送 |
| 启动屏 | `expo-splash-screen` | 原生闪屏 |
| 生物识别 | `expo-local-authentication` (需安装) | FaceID / 指纹解锁 |
| 链接跳转 | `expo-linking` | 通用链接 (applinks://aegis.ip4move.io) |
| 真 SVG | `react-native-svg` | 所有图标都是矢量绘制，0 倍图 |
| 手势 | `react-native-gesture-handler` | 原生手势栈 |
| 动画 | `react-native-reanimated` | 60fps UI 线程动画 |
| 网络 | `axios` | 真实 HTTP 调用 |
| 状态 | `zustand` + `react-query` | 客户端状态 + 服务端缓存 |

---

## 当前版本

**AEGIS v2.1.0 · BUILD 2026.05.31**
- React Native 0.76 (New Architecture 默认开启)
- Expo SDK 52
- TypeScript strict
- iOS 14+ / Android 7+

---

## 下一步可选

- [ ] 接 WebAuthn / FaceID 实现真正的无密码登录
- [ ] 加 react-native-mmkv 做本地威胁 IOC 缓存
- [ ] 加 react-native-mqtt 订阅实时威胁流 (替代轮询)
- [ ] 接 react-native-ble 或 react-native-wifi 做内网隧道扫描
- [ ] 国际化 (i18next + 多语言)
- [ ] CI/CD：GitHub Actions 自动 EAS Build
