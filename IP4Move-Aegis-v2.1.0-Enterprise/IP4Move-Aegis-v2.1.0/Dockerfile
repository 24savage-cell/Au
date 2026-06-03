# IP4Move-Aegis v2.1.0 企业版 Dockerfile
# 多阶段构建，生产优化

# ============================================================================
# 构建阶段
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 安装国密支持 (可选)
RUN pip install --no-cache-dir gmssl || echo "gmssl安装失败，将使用回退"

# 安装PQC支持 (可选)
RUN pip install --no-cache-dir liboqs-python || echo "liboqs安装失败，将使用回退"

# ============================================================================
# 生产阶段
# ============================================================================
FROM python:3.11-slim as production

LABEL maintainer="IP4Move Security Team"
LABEL version="2.1.0"
LABEL description="IP4Move-Aegis Enterprise Anonymous Network System"

WORKDIR /app

# 创建非root用户
RUN groupadd -r aegis && useradd -r -g aegis aegis

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY src/ ./src/
COPY start.py .
COPY .env.example .
COPY README.md .

# 创建数据目录
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R aegis:aegis /app

# 切换到非root用户
USER aegis

# 暴露端口
EXPOSE 8080 9050

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/live')" || exit 1

# 启动命令
ENTRYPOINT ["python", "start.py"]
CMD ["--prod"]
