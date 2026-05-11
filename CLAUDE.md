# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

校园运动会管理系统 — Django REST Framework 后端 + Vue 3 前端，支持体育老师（管理）、班主任（报名）、裁判（成绩录入）三种角色。

## 开发命令

```bash
# 后端（CampusSport/ 目录）
python manage.py migrate              # 执行数据库迁移
python manage.py runserver 8000       # 启动 Django 开发服务器
python manage.py seed_data --clear    # 重新生成全套测试数据（清空旧数据 + 创建账号/学生/运动会/成绩）

# 前端（frontend/ 目录）
npm run dev                           # 启动 Vite 开发服务器（端口 5173，API 代理到 localhost:8000）
npm run build                         # 生产构建
```

## 架构

### 后端：Django REST Framework（5 个 App）

- **`accounts`** — 自定义 User 模型，JWT 认证（simplejwt，8h access / 7d refresh）。登录返回 user 对象含 `role`。权限基类 `IsAdmin`、`IsAdminOrTeacher`、`IsAdminOrReferee` 在各 app 的 views.py 中独立定义（未抽取到公共模块）。
- **`events`** — `SportsMeet`（状态流转：preparing → registration → ongoing → finished）→ `Event`（径赛/田赛/趣味/接力/对抗，支持 1-3 阶段赛制）→ `Schedule`（按阶段+组次编排）
- **`registration`** — `Student` + `Registration`（个人报名）+ `TeamRegistration`（团体报名）。`Registration` 有 `unique_together('event', 'student')`。每人报名上限在 `SportsMeet.max_events_per_person` 和 `Event.max_per_person` 两级控制。
- **`scores`** — `Score`（个人成绩）+ `TeamScore`（团体成绩）+ `ConfrontationRound`（对抗赛 BO3/BO5 局次）+ `ClassPoints`（班级积分汇总）。`calculate_rank_and_points()` 根据项目类型决定排序方向（田赛远度类 desc，径赛时间类 asc），`recalculate_class_points()` 汇总班级总积分/奖牌/排名。
- **`reports`** — `Report` 模型 + 秩序册 Word 生成（`python-docx`）+ 成绩报表 Excel 生成（`openpyxl`）。`generators.py` 中是旧版 Excel 版秩序册（通过文件系统保存），`views.py` 中直接返回内存流下载，后者是当前实际使用的。

API 路由通过 DRF `DefaultRouter` 注册，URL 前缀统一为 `/api/`。跨域全部开放（`CORS_ALLOW_ALL_ORIGINS = True`）。

### 前端：Vue 3 + Element Plus + Pinia

- **路由** (`router/index.js`) — 三个角色面板：`/admin/`、`/teacher/`、`/referee/`，每个有独立 Layout。路由守卫按 `meta.role` 校验，未登录跳 `/login`。
- **状态管理** (`stores/auth.js`) — `useAuthStore` 存 token + user 对象到 localStorage，`isAdmin`/`isTeacher`/`isReferee` 三个 getter。
- **API 层** (`api/request.js`) — axios 实例，自动附加 `Bearer` token，401 时清除登录态并跳转，blob 响应返回完整 response 供下载。
- **布局组件** — `AdminLayout`、`TeacherLayout`、`RefereeLayout` 各含侧边导航菜单。
- **组件** — `ClassSelector` 是班级选择器通用组件，全局注册。

### 关键约束

- **成绩排序方向**：track/relay 类型按 `result_numeric` 升序（时间越短越好）；field/fun_individual 按单位判断 — `meter`/`count` 降序，`second` 升序。
- **积分倍率**：团体项目（relay/team_confrontation）积分 ×2.0，在 `Event.score_multiplier` 中配置。
- **班主任权限边界**：只能操作 `class_name` 匹配的本班学生；裁判只能操作分配给自己项目的成绩。
- **数据库**：当前配置为 MySQL（`campussport` 库），但含有 `db.sqlite3` 文件。`settings.py` 中的数据库密码是硬编码的测试凭据。
- **中文环境**：`LANGUAGE_CODE = 'zh-hans'`，`TIME_ZONE = 'Asia/Shanghai'`。Element Plus 使用 zh-cn 语言包。Word 生成字体设为微软雅黑。

### 测试账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 体育老师（管理员） |
| teacher_2028_1 ~ teacher_2027_3 | teacher123 | 班主任 |
| referee1 ~ referee4 | referee123 | 裁判 |
