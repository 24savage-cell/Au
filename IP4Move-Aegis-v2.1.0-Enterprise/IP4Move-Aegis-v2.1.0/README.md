# IP4Move-Aegis v2.1.0 完整修复版

🛡️ **企业级匿名网络系统** - 深度修复版 | 架构优化 | 生产就绪

## ✨ 版本更新 (v2.0 → v2.1)

### 🔴 紧急安全修复

#### 1. PQC侧信道攻击防护
- **问题**: 纯Python PQC存在时序攻击风险
- **修复**: 集成liboqs (NIST FIPS 203/204/205认证)
- **文件**: `src/pqc/liboqs_provider.py`
- **使用**:
  ```python
  from src.pqc.liboqs_provider import LiboqsKEM, KEMAlgorithm
  
  kem = LiboqsKEM(KEMAlgorithm.ML_KEM_768)
  pub, priv = kem.keygen()
  ```

#### 2. DHT节点ID Sybil攻击防护
- **问题**: 节点ID随机生成，可低成本伪造大量节点
- **修复**: 节点ID = SHA256(公钥)[:20] + 可选PoW
- **文件**: `src/dht_v2/secure_node_id.py`

### 🟡 性能优化

#### 3. Mixnet动态批处理
- **问题**: 固定BATCH_SIZE=64是流量特征
- **修复**: 动态自适应批大小 + 指数分布延迟 + 紧急通道
- **文件**: `src/mixnet/optimized_mixnet.py`
- **改进**:
  - 批大小根据队列长度自适应 (8-128)
  - 指数分布延迟更符合真实网络
  - 实时流量走紧急通道 (延迟<50ms)

#### 4. 流量伪装真实传输
- **问题**: simulate_doh_query是模拟，不是真实传输
- **修复**: 实现真实DoH/WebRTC传输
- **文件**: `src/traffic_disguise_v2/real_transport.py`
- **改进**:
  - 真实HTTPS请求到DoH服务器
  - 数据编码为DNS查询域名
  - 完全合法的TLS流量

### 🟢 功能增强

#### 5. 分级API认证
- **问题**: 6小时统一token，用户体验差
- **修复**: 控制面短token(6h) + 数据面长token(7d) + 无感刷新
- **文件**: `src/api/tiered_auth.py`

#### 6. Crypto-Agility
- **问题**: 算法硬编码，无法热切换
- **修复**: 密码敏捷架构，支持运行时切换
- **文件**: `src/pqc/liboqs_provider.py` (CryptoAgilityManager)

#### 7. 抗审查设计
- **问题**: 无主动探测防御
- **修复**: 探测检测 + 协议一致性验证 + 连接前PoW
- **文件**: `src/security/anti_censorship.py`

#### 8. 差分隐私指标
- **问题**: Prometheus指标暴露流量模式
- **修复**: 拉普拉斯噪声 + 本地聚合 + 时间分箱
- **文件**: `src/metrics/dp_metrics.py`

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt

# 生产环境额外依赖
pip install liboqs-python>=0.15.0  # PQC
pip install httpx                   # 真实DoH
pip install PyJWT                   # 分级认证
```

### 2. 启动服务

```bash
python start.py                    # 开发模式
python start.py --prod             # 生产模式
python start.py --port 9000        # 自定义端口
```

---

## 📁 新增文件

| 文件 | 说明 |
|------|------|
| `src/pqc/liboqs_provider.py` | liboqs集成 + Crypto-Agility |
| `src/mixnet/optimized_mixnet.py` | 动态批处理 + 紧急通道 |
| `src/traffic_disguise_v2/real_transport.py` | 真实DoH/WebRTC传输 |
| `src/dht_v2/secure_node_id.py` | 安全节点ID + Sybil防护 |
| `src/api/tiered_auth.py` | 分级Token认证 |
| `src/security/anti_censorship.py` | 抗审查设计 |
| `src/metrics/dp_metrics.py` | 差分隐私指标 |

---

## 🔧 配置说明

### PQC配置

```python
# 使用liboqs (生产)
from src.pqc.liboqs_provider import get_global_manager

manager = get_global_manager()
kem = manager.get_kem()  # 默认ML-KEM-768

# 切换算法
manager.switch_default_kem("hybrid")  # X25519+Kyber混合
```

### Mixnet配置

```python
from src.mixnet.optimized_mixnet import OptimizedMixnetConfig, OptimizedMixNode

config = OptimizedMixnetConfig(
    node_id="mix-1",
    # 动态批处理
    batch=DynamicBatchConfig(
        min_batch_size=8,
        max_batch_size=128,
    ),
    # 指数延迟
    delay=ExponentialDelayConfig(
        max_delay_ms=2000,  # 从5秒降到2秒
    ),
    # 紧急通道
    express=ExpressChannelConfig(enabled=True),
)

node = OptimizedMixNode(config)
```

### 认证配置

```python
from src.api.tiered_auth import TieredTokenManager, TokenConfig

config = TokenConfig(
    control_access_ttl=6*3600,    # 控制面6小时
    data_access_ttl=7*24*3600,    # 数据面7天
    device_binding_enabled=True,  # 设备绑定
)

manager = TieredTokenManager(secret_key, config)

# 创建控制面token
control_tokens = manager.create_control_tokens(user_id, device)

# 创建数据面token
data_tokens = manager.create_data_tokens(user_id, device)
```

---

## 🔒 安全改进总结

| 问题 | 修复 | 影响 |
|------|------|------|
| PQC时序攻击 | liboqs集成 | 恒定时间操作 |
| Sybil攻击 | 公钥绑定+PoW | 增加伪造成本 |
| 流量特征 | 动态批处理 | 消除固定模式 |
| 伪装识别 | 真实DoH | 完全合法流量 |
| Token滥用 | 设备绑定 | 防盗用 |
| 主动探测 | PoW挑战 | 防探测 |
| 元数据泄露 | 差分隐私 | 保护统计信息 |

---

## 📊 性能改进

- **Mixnet延迟**: 最大延迟从5秒降到2秒
- **实时流量**: 紧急通道延迟<50ms
- **批处理效率**: 动态调整提高吞吐
- **DoH传输**: 真实HTTPS，无特征

---

## ⚠️ 重要提醒

### 生产环境必须

1. **安装liboqs**: `pip install liboqs-python>=0.15.0`
2. **设置密钥**: `export AEGIS_MASTER_SECRET=$(openssl rand -hex 32)`
3. **启用PoW**: 增加Sybil攻击成本
4. **配置设备绑定**: 防止Token盗用

### 不适合生产

- 纯Python PQC实现 (侧信道风险)
- 模拟流量伪装 (可被识别)
- 无设备绑定的认证

---

## 📝 变更日志

### v2.1.0 (2026-05-31)

**安全修复**
- 集成liboqs实现生产级PQC
- 添加PQC安全警告
- 修复DHT节点ID Sybil攻击漏洞

**性能优化**
- 实现动态批处理消除流量特征
- 指数分布延迟更真实
- 添加紧急通道支持实时通信

**功能增强**
- 实现真实DoH/WebRTC传输
- 分级Token认证系统
- Crypto-Agility架构
- 抗审查设计
- 差分隐私指标保护

---

## 📄 许可证

MIT License
