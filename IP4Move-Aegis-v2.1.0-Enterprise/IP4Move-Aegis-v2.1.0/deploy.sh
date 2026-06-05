#!/bin/bash
# IP4Move-Aegis v2.1.0 企业版一键部署脚本
# 支持: Docker Compose / Kubernetes

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 版本信息
VERSION="2.1.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 打印横幅
print_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║           IP4Move-Aegis v2.1.0 - 企业版部署脚本                  ║
║                                                                  ║
║     国密SM2/SM3/SM4 | Docker/K8s | 生产就绪                      ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        echo "安装命令: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装"
        exit 1
    fi
    
    # 检查kubectl (K8s模式)
    if [ "$DEPLOY_MODE" == "k8s" ]; then
        if ! command -v kubectl &> /dev/null; then
            log_error "kubectl未安装"
            exit 1
        fi
    fi
    
    log_info "依赖检查通过"
}

# 生成密钥
generate_secrets() {
    log_info "生成密钥..."
    
    if [ -f "$SCRIPT_DIR/.env" ]; then
        log_warn ".env文件已存在，是否覆盖? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log_info "跳过密钥生成"
            return
        fi
    fi
    
    # 生成主密钥
    MASTER_SECRET=$(openssl rand -hex 32)
    
    # 生成Grafana密码
    GRAFANA_PASSWORD=$(openssl rand -base64 12)
    
    cat > "$SCRIPT_DIR/.env" << EOF
# IP4Move-Aegis v2.1.0 生产环境配置
# 生成时间: $(date)

# ==================== 核心配置 ====================
IP4MOVE_ENV=production
HOST=0.0.0.0
PORT=8080
WORKERS=4

# 主密钥 (必须保密!)
AEGIS_MASTER_SECRET=$MASTER_SECRET

# ==================== 日志配置 ====================
LOG_LEVEL=INFO
JSON_LOGS=true

# ==================== 监控配置 ====================
METRICS_ENABLED=true
METRICS_PATH=/metrics
HEALTH_PATH=/health

# Grafana管理员密码
GRAFANA_ADMIN_PASSWORD=$GRAFANA_PASSWORD

# ==================== 网络配置 ====================
CORS_ORIGINS=https://your-domain.com

# ==================== 可选: Redis配置 ====================
# REDIS_URL=redis://redis:6379/0

# ==================== 可选: 数据库配置 ====================
# DATABASE_URL=postgresql://user:pass@db:5432/aegis
EOF
    
    log_info "密钥已生成到 .env 文件"
    log_warn "请编辑 .env 文件，配置您的域名和其他参数"
}

# Docker Compose部署
deploy_docker() {
    log_info "使用Docker Compose部署..."
    
    cd "$SCRIPT_DIR"
    
    # 构建镜像
    log_info "构建Docker镜像..."
    docker-compose build
    
    # 启动服务
    log_info "启动服务..."
    docker-compose up -d
    
    # 等待服务就绪
    log_info "等待服务就绪..."
    sleep 10
    
    # 检查健康状态
    if curl -s http://localhost:8080/health/live > /dev/null; then
        log_info "服务部署成功!"
        echo ""
        echo -e "${GREEN}访问地址:${NC}"
        echo "  - API服务: http://localhost:8080"
        echo "  - Prometheus: http://localhost:9090"
        echo "  - Grafana: http://localhost:3000 (admin/$GRAFANA_PASSWORD)"
    else
        log_error "服务健康检查失败"
        docker-compose logs
        exit 1
    fi
}

# Kubernetes部署
deploy_k8s() {
    log_info "使用Kubernetes部署..."
    
    cd "$SCRIPT_DIR"
    
    # 创建命名空间
    kubectl apply -f k8s/namespace.yaml 2>/dev/null || true
    
    # 应用配置
    log_info "应用K8s配置..."
    kubectl apply -f k8s/
    
    # 等待部署就绪
    log_info "等待部署就绪..."
    kubectl rollout status deployment/aegis -n ip4move --timeout=300s
    
    # 获取访问信息
    NODE_PORT=$(kubectl get svc aegis-nodeport -n ip4move -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "30080")
    
    log_info "K8s部署成功!"
    echo ""
    echo -e "${GREEN}访问地址:${NC}"
    echo "  - API服务: http://<node-ip>:$NODE_PORT"
    echo "  - 查看Pod: kubectl get pods -n ip4move"
    echo "  - 查看日志: kubectl logs -f deployment/aegis -n ip4move"
}

# 查看状态
show_status() {
    if [ "$DEPLOY_MODE" == "docker" ]; then
        echo -e "${BLUE}=== Docker Compose 状态 ===${NC}"
        docker-compose ps
        echo ""
        echo -e "${BLUE}=== 资源使用 ===${NC}"
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || true
    else
        echo -e "${BLUE}=== K8s Pod 状态 ===${NC}"
        kubectl get pods -n ip4move
        echo ""
        echo -e "${BLUE}=== K8s 服务 ===${NC}"
        kubectl get svc -n ip4move
    fi
}

# 查看日志
show_logs() {
    if [ "$DEPLOY_MODE" == "docker" ]; then
        docker-compose logs -f --tail=100
    else
        kubectl logs -f deployment/aegis -n ip4move --tail=100
    fi
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    
    if [ "$DEPLOY_MODE" == "docker" ]; then
        docker-compose down
    else
        kubectl delete -f k8s/ 2>/dev/null || true
    fi
    
    log_info "服务已停止"
}

# 更新服务
update_services() {
    log_info "更新服务..."
    
    if [ "$DEPLOY_MODE" == "docker" ]; then
        docker-compose pull
        docker-compose up -d --build
    else
        kubectl rollout restart deployment/aegis -n ip4move
        kubectl rollout status deployment/aegis -n ip4move
    fi
    
    log_info "服务已更新"
}

# 清理资源
cleanup() {
    log_warn "这将删除所有数据! 确定吗? (yes/no)"
    read -r response
    if [ "$response" != "yes" ]; then
        log_info "取消清理"
        return
    fi
    
    if [ "$DEPLOY_MODE" == "docker" ]; then
        docker-compose down -v
        docker volume prune -f
    else
        kubectl delete namespace ip4move
    fi
    
    log_info "资源已清理"
}

# 使用说明
show_usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  deploy-docker     使用Docker Compose部署"
    echo "  deploy-k8s        使用Kubernetes部署"
    echo "  status            查看服务状态"
    echo "  logs              查看服务日志"
    echo "  stop              停止服务"
    echo "  update            更新服务"
    echo "  cleanup           清理所有资源"
    echo "  init              仅初始化配置"
    echo ""
    echo "示例:"
    echo "  $0 deploy-docker   # Docker部署"
    echo "  $0 deploy-k8s      # K8s部署"
    echo "  $0 status          # 查看状态"
}

# 主函数
main() {
    print_banner
    
    # 默认部署模式
    DEPLOY_MODE="${DEPLOY_MODE:-docker}"
    
    case "${1:-}" in
        deploy-docker)
            DEPLOY_MODE="docker"
            check_dependencies
            generate_secrets
            deploy_docker
            ;;
        deploy-k8s)
            DEPLOY_MODE="k8s"
            check_dependencies
            generate_secrets
            deploy_k8s
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        stop)
            stop_services
            ;;
        update)
            update_services
            ;;
        cleanup)
            cleanup
            ;;
        init)
            generate_secrets
            log_info "初始化完成，请编辑 .env 文件"
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
