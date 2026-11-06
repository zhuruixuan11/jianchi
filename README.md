# 习惯/健身打卡追踪器

基于《习惯健身打卡追踪器-完整系统设计》实现的健身追踪与管理平台，覆盖学员、教练、管理员三类角色。

## 技术栈

- 后端：Python 3.12+ / FastAPI / Uvicorn
- 数据库：MySQL 8.0（PyMySQL 原生 SQL，参数化查询防注入）
- 缓存：Redis 7（排行榜/热点数据缓存，不可用时自动降级内存缓存）
- 认证：JWT（PyJWT）+ bcrypt
- 前端：原生 HTML5 + CSS3 + JavaScript（Chart.js + ECharts，深色科技风 UI）

## 快速启动

### 1. 初始化数据库

```bash
mysql -uroot -p < sql/init.sql
```

脚本会创建数据库、账号、全部表结构及演示数据（管理员/教练/学员账号）。

### 2. 配置环境

按需修改 `.env`（数据库、Redis、JWT 密钥、上传限制）。

### 3. 安装依赖并启动

```bash
conda create -n fitness_tracker python=3.14 -y
conda activate fitness_tracker
pip install -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问

- 前端界面：http://localhost:8000/
- OpenAPI 文档：http://localhost:8000/docs

## 演示账号

| 角色   | 用户名     | 密码       |
| ------ | ---------- | ---------- |
| 管理员 | admin      | Admin@123  |
| 教练   | coach_li   | Coach@123  |
| 学员   | student_wx | Student@123 |

## 目录结构

```
fitness-tracker/
├── app/
│   ├── main.py              # FastAPI 入口 + WebSocket
│   ├── config.py            # 环境变量与配置
│   ├── database.py          # PyMySQL 线程安全连接池
│   ├── redis_client.py      # Redis 连接（含内存降级）
│   ├── auth/                # JWT + bcrypt 认证与角色依赖
│   ├── routers/             # auth/student/coach/admin/upload 路由
│   ├── services/            # 打卡/计划/视频/统计/成就/消息业务逻辑
│   ├── models/              # Pydantic 数据模型
│   └── utils/               # 工具函数
├── static/                  # 前端（学员端/教练端/管理员端 SPA）
├── uploads/                 # 打卡媒体/教学视频/头像
├── sql/init.sql             # 数据库初始化脚本
├── .env
└── requirements.txt
```

## 核心功能

- **训练营（营期闭环）**：教练创建营期（21天/6周）→ 学员凭邀请码入营 → 以模板计划一键为全员生成营期计划（日期自动对齐开营日）→ 营内排行榜（打卡天数/训练量，尊重匿名设置）→ 营内实时群聊（WebSocket，系统消息自动记录入营/开营/结营）→ 营期看板（打卡率趋势、未打卡名单一键催打卡、低活跃预警）→ 结营自动生成报告（打卡率/人均训练量/平均体重变化/徽章数/Top3）
- **学员端**：图文/视频打卡（关联训练计划）、连续天数与断签补签（教练审批）、打卡日历热力图、体重/体脂/围度趋势（Chart.js）、每周训练量/时长（ECharts 柱线混合）、教学视频库（分类/搜索/笔记/倍速播放）、动作级训练数据（组数/次数/重量/RPE/心率）、成就徽章（7/30/100/365 天）、周/月排行榜（可匿名）、WebSocket 实时消息
- **教练端**：学员列表与打卡监控（一键催打卡）、训练计划制定（动作库/复制历史计划）、打卡评论指导、补签审批、视频上传与可见范围管理、批量消息与模板、学员数据看板（30 天打卡率/低活跃预警/CSV 导出）
- **管理员端**：用户管理（启禁/角色/重置密码）、教练资质审核、视频审核、公告管理（置顶/定向）、热门计划推荐、运营数据看板（7/30/90 天趋势）、系统参数配置、操作日志（保留 90 天）

## 训练营模块（2026-08-27 新增）

数据模型：`camps`（营期，含邀请码与状态机 draft→recruiting→ongoing→ended）、`camp_members`（营员）、`camp_messages`（营内群聊），`training_plans` 新增可空 `camp_id` 列（已有 1v1 计划零影响）。

```bash
# 初始化/升级数据库（幂等，可重复执行）
python migrate_20260827.py
```

关键接口（前缀 `/api/camps`）：

| 端点 | 角色 | 说明 |
| --- | --- | --- |
| `POST /api/camps` | 教练 | 创建营期（自动生成 8 位邀请码） |
| `POST /api/camps/join` | 学员 | 凭邀请码入营 |
| `POST /api/camps/{id}/transition?action=start/open/finish` | 教练 | 发布招生 / 开营 / 结营（自动生成报告） |
| `POST /api/camps/{id}/generate-plans` | 教练 | 以模板计划为全员批量生成营期计划 |
| `GET /api/camps/{id}/leaderboard` | 成员 | 营内排行榜 |
| `GET /api/camps/{id}/dashboard` | 教练 | 营期看板（趋势/未打卡/低活跃） |
| `WS {"type":"camp","camp_id":N,"content":"..."}` | 成员/教练 | 营内实时群聊（仅 ongoing 状态） |
| `GET /api/camps/{id}/report` | 成员 | 结营报告 |

## 安全要点

- 所有 SQL 使用 %s 参数化占位符
- 密码 bcrypt 哈希（work factor 12）
- JWT 仅通过 Authorization: Bearer 头传递
- 上传文件校验 MIME/扩展名并重命名 UUID，路径不含用户输入
- 管理员操作全部落库审计
