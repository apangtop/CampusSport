# CampusSport 校园运动会管理系统

## 技术栈
- **后端**：Django 3.2 LTS + Django REST Framework + JWT 认证
- **前端**：Vue 3 + Vite + Element Plus + Pinia
- **数据库**：MySQL（Docker 使用 8.0）

## 项目结构
```
CampusSport/
├── CampusSport/        # Django 后端项目
│   ├── accounts/       # 用户认证与角色管理
│   ├── events/         # 运动会、比赛项目、赛程
│   ├── registration/   # 报名管理、学生信息
│   ├── scores/         # 成绩录入、排名、积分
│   ├── reports/        # 秩序册/成绩报表导出
│   └── requirements.txt
└── frontend/           # Vue 3 前端
```

## 环境要求
- Python 3.9+
- Node.js 18+
- MySQL 8.0（Docker 默认配置）

## 快速启动

### 1. 后端启动
```bash
cd CampusSport

# 安装依赖
pip install -r requirements.txt

# 数据库迁移（首次运行）
python manage.py migrate

# 初始化学校与管理员（首次空库使用，密码由终端交互输入）
python manage.py bootstrap_school --school "你的学校全称" --username school_admin

# 启动服务
python manage.py runserver 0.0.0.0:8000
```

### 2. 前端启动
```bash
cd frontend
npm install
npm run dev
```

### 3. 访问地址
| 地址 | 说明 |
|------|------|
| http://localhost:5173 | 前端页面 |
| http://localhost:8000/api | 后端 API |
| http://localhost:8000/admin | Django 管理后台 |

## 学校初始化

正式安装没有通用默认账号。使用 `bootstrap_school` 设置学校名称并创建应用管理员，密码不会写入命令参数或文档。该管理员用于系统前端；如需 Django 管理后台，另用 `createsuperuser` 创建维护账号。

登录后先进入「学校设置」配置班级与年级，再在「账号管理」创建班主任和裁判。小学、初中、高中及自定义班级名称均可配置；旧的 `2028级1班` 格式仍可使用。

按每校独立部署交付，每校使用独立数据库、密钥和文件目录。详见 [学校交付说明](SCHOOL_DELIVERY.md)。

## 主要功能

### P0 核心功能
- **用户登录**：三种角色（体育老师/班主任/裁判）统一登录，自动跳转对应界面
- **运动会管理**：创建、编辑、状态流转（筹备中→报名中→进行中→已结束）
- **比赛项目管理**：径赛/田赛/趣味/对抗/接力，支持多阶段赛制
- **报名管理**：班主任为本班学生报名，体育老师审核，报名上限自动校验
- **秩序册生成**：一键导出 Word，含封面/赛程总览/各项目参赛名单

### P1 重要功能
- **成绩录入**：裁判按项目录入成绩，自动计算排名和积分
- **拔河录入**：逐局录入胜负，自动判定最终胜者
- **积分榜**：实时班级总积分排名，金银铜牌统计

### P2 增值功能
- **历届数据查询**：历届运动会、积分榜、项目历史最佳、学生参赛历史
- **学生管理**：支持 Excel 批量导入学生名单

## 学生导入 Excel 格式
| 姓名* | 性别(男/女)* | 学号 | 年级 |
|-------|-------------|------|------|
| 张三 | 男 | 2024001 | 初一 |
