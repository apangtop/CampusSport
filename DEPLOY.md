# 校园运动会管理系统 — 服务器部署指南

## 架构说明

```
┌──────────────────────────────────────────────────┐
│  宿主机 (CentOS)                                   │
│  ┌──────────────────┐  ┌──────────────────────┐  │
│  │ 已有项目          │  │ 本项目 (Docker)       │  │
│  │ Nginx :80        │  │ Frontend Nginx :8080 │  │
│  │ Django :8000      │  │ Backend  :8000(内部)│  │
│  │ MySQL  :3306      │  │ MySQL    :3307      │  │
│  └──────────────────┘  └──────────────────────┘  │
└──────────────────────────────────────────────────┘
```

端口不冲突，两个项目可同时运行。

## 前置条件

1. CentOS 服务器已安装 Docker 和 Docker Compose
2. 确保以下端口未被占用：**8080、3307**

```bash
# 检查端口占用
ss -tlnp | grep -E '8080|3307'
```

## 第一步：上传项目到服务器

```bash
# 在本地打包项目（排除 node_modules 等）
cd /path/to/CampusSport
tar --exclude='node_modules' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='db.sqlite3' --exclude='.git' --exclude='frontend/dist' \
    -czf campussport.tar.gz .

# 上传到服务器
scp campussport.tar.gz root@你的服务器IP:/opt/

# 在服务器上解压
ssh root@你的服务器IP
mkdir -p /opt/campussport
cd /opt/campussport
tar -xzf /opt/campussport.tar.gz
```

## 第二步：修改环境变量

```bash
cd /opt/campussport

# 编辑 .env 文件，修改密码和关键配置
vi .env
```

**务必修改：**
- `DB_PASSWORD` — 设置一个安全的 MySQL root 密码
- `SECRET_KEY` — 生成一个随机字符串
- `ALLOWED_HOSTS` — 改为服务器 IP 或域名，如 `你的IP,你的域名`

```bash
# 生成随机 SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

## 第三步：启动服务

```bash
cd /opt/campussport

# 构建并启动所有容器（后台运行）
docker compose up -d --build

# 查看启动日志
docker compose logs -f

# 按 Ctrl+C 退出日志查看
```

启动后会自动：
- 等待 MySQL 就绪
- 执行数据库迁移（migrate）
- 收集静态文件（collectstatic）

## 第四步：检查服务状态

```bash
# 确认三个容器都在运行
docker compose ps

# 预期输出：
# campussport-db-1        mysql:8.0     Up (healthy)
# campussport-backend-1   ...            Up
# campussport-frontend-1  nginx:alpine   Up
```

## 第五步：导入测试数据

```bash
# 进入后端容器
docker compose exec backend python manage.py seed_data --clear
```

这会创建：
- 1 届运动会（第三届田径运动会）
- 2 个年级共 7 个班级的学生
- 70 个比赛项目及赛程
- 预设账号：admin、teacher_*/referee*

## 第六步：配置外网访问

```bash
# 放行 8080 端口
firewall-cmd --add-port=8080/tcp --permanent
firewall-cmd --reload
```

访问：`http://你的服务器IP:8080`

## 第七步：对接已有 Nginx（可选）

如果希望通过 80 端口访问，在已有 Nginx 中添加反向代理：

```nginx
# 在 /etc/nginx/conf.d/ 下新建 campussport.conf
server {
    listen 80;
    server_name sport.你的域名.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
nginx -t && nginx -s reload
```

## 日常管理

```bash
# 查看日志
docker compose logs -f backend        # 后端日志
docker compose logs -f frontend       # 前端日志

# 重启某个服务
docker compose restart backend
docker compose restart frontend

# 更新代码后重新部署
docker compose up -d --build

# 停止所有服务
docker compose down

# 停止并删除数据卷（⚠️ 会清除数据库数据）
docker compose down -v

# 进入后端容器
docker compose exec backend bash
```

## 数据备份

```bash
# 备份 MySQL 数据库
docker compose exec db mysqldump -u root -p campussport > backup_$(date +%Y%m%d).sql

# 备份上传的文件
tar -czf media_backup.tar.gz -C /var/lib/docker/volumes campussport_media_data
```

## 数据恢复

```bash
# 恢复数据库
docker compose exec -T db mysql -u root -p campussport < backup_20260512.sql

# 恢复后重新导入数据
docker compose exec backend python manage.py seed_data --clear
```
