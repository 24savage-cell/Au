# IP4Move-Aegis v2.1.0 企业部署指南

🚀 **一键部署** | 🔒 **国密合规** | 📊 **监控就绪**

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/your-org/ip4move-aegis.git
cd ip4move-aegis
```

### 2. 一键部署

```bash
# Docker Compose部署 (推荐)
./deploy.sh deploy-docker

# Kubernetes部署
./deploy.sh deploy-k8s
```

### 3. 验证部署

```bash
# 查看状态
./deploy.sh status

# 查看日志
./deploy.sh logs
```

---

## 部署选项

### 选项1: Docker Compose (推荐中小企业)

**适用场景**: 单节点或少量节点部署

```bash
# 部署
./deploy.sh deploy-docker

# 访问地址
- API: http://localhost:8080
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
```

**配置**:
```bash
# 编辑 .env 文件
vim .env

# 关键配置
AEGIS_MASTER_SECRET=your-secret-key
CORS_ORIGINS=https://your-domain.com
```

### 选项2: Kubernetes (推荐大规模)

**适用场景**: 多节点、自动扩缩容

```bash
# 部署
./deploy.sh deploy-k8s

# 查看Pod
kubectl get pods -n ip4move

# 查看服务
kubectl get svc -n ip4move
```

**特性**:
- 自动扩缩容 (HPA)
- 滚动更新
- PodDisruptionBudget保证可用性
- NetworkPolicy网络隔离

---

## 国密SM2/SM3/SM4配置

### 安装国密支持

```bash
pip install gmssl
```

### 代码中使用

```python
from src.crypto.sm_crypto import (
    SM2Crypto, SM3Hash, SM4Cipher,
    generate_sm2_keypair, check_sm_support
)

# 检查支持状态
print(check_sm_support())

# SM2密钥对
keypair = generate_sm2_keypair()

# SM2签名
sm2 = SM2Crypto(keypair)
signature = sm2.sign(b"message")
assert sm2.verify(b"message", signature)

# SM3哈希
digest = SM3Hash.hash(b"message")

# SM4加密
cipher = SM4Cipher(key=b"1234567890abcdef")
ciphertext, iv = cipher.encrypt(b"plaintext")
plaintext = cipher.decrypt(ciphertext, iv)
```

### 配置国密优先

```python
from src.crypto.sm_crypto import SMSelector

# 使用国密
selector = SMSelector(use_sm=True)
hash_func = selector.get_hash()  # SM3
cipher = selector.get_cipher(key)  # SM4
```

---

## 生产环境配置

### 1. 生成密钥

```bash
# 自动生成
./deploy.sh init

# 或手动生成
openssl rand -hex 32
```

### 2. 配置HTTPS

**Docker Compose**:
```yaml
# docker-compose.yml 添加
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./ssl:/etc/nginx/ssl:ro
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
```

**Kubernetes**:
```yaml
# 使用 cert-manager
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
    - hosts:
        - your-domain.com
      secretName: aegis-tls
```

### 3. 配置监控告警

**Prometheus告警规则**:
```yaml
# monitoring/alert_rules.yml
groups:
  - name: aegis-alerts
    rules:
      - alert: AegisHighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Aegis错误率过高"
```

**Grafana仪表板**:
- 访问 http://localhost:3000
- 默认账号: admin / (自动生成的密码见.env)

---

## 运维命令

```bash
# 查看状态
./deploy.sh status

# 查看日志
./deploy.sh logs

# 更新服务
./deploy.sh update

# 停止服务
./deploy.sh stop

# 清理资源 (危险!)
./deploy.sh cleanup
```

---

## 故障排查

### 服务无法启动

```bash
# 检查日志
docker-compose logs -f
# 或
kubectl logs -f deployment/aegis -n ip4move

# 检查配置
./deploy.sh init
```

### 健康检查失败

```bash
# 手动检查
curl http://localhost:8080/health/live
curl http://localhost:8080/health/ready
```

### 性能问题

```bash
# 查看资源使用
docker stats
# 或
kubectl top pods -n ip4move
```

---

## 安全加固

### 1. 网络安全

- 使用NetworkPolicy限制Pod间通信
- 配置防火墙规则
- 使用私有网络

### 2. 密钥管理

- 生产环境使用KMS/Vault
- 定期轮换密钥
- 启用审计日志

### 3. 监控告警

- 配置异常流量告警
- 监控节点健康状态
- 设置SLA监控

---

## 升级指南

### v2.0 → v2.1

```bash
# 备份数据
cp -r data data.backup

# 拉取新版本
git pull origin main

# 更新部署
./deploy.sh update

# 验证
./deploy.sh status
```

---

## 技术支持

- 文档: https://docs.ip4move.io
- 问题: https://github.com/your-org/ip4move-aegis/issues
- 邮箱: support@ip4move.io

---

## 许可证

MIT License - 企业商用友好
