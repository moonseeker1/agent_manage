# 智能体管理系统 - 完整使用指南

## 目录

1. [系统部署](#1-系统部署)
2. [基础使用](#2-基础使用)
3. [功能详解](#3-功能详解)
4. [API 调用](#4-api-调用)
5. [监控配置](#5-监控配置)
6. [常见问题](#6-常见问题)

---

## 1. 系统部署

### 1.1 环境要求

| 组件 | 版本要求 |
|------|---------|
| Python | 3.9+ |
| Node.js | 18+ |
| PostgreSQL | 14+ |
| Redis | 6+ |

### 1.2 Docker 部署（推荐）

```bash
# 克隆项目
git clone https://github.com/moonseeker1/agent_manage.git
cd agent_manage

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

服务地址：
- 前端：http://localhost:5173
- 后端：http://localhost:8000
- API文档：http://localhost:8000/docs

### 1.3 手动部署

#### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 配置数据库连接

# 初始化数据库
alembic upgrade head

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 前端

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

### 1.4 Nginx 配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端
    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    # API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 2. 基础使用

### 2.1 注册账号

1. 访问系统首页
2. 点击"注册"标签
3. 填写用户名、邮箱、密码
4. 点击"注册"按钮

### 2.2 登录系统

1. 使用注册的用户名和密码登录
2. 登录成功后跳转到仪表盘

### 2.3 界面导航

```
┌─────────────────────────────────────────────────────┐
│  智能体管理                    [用户名 ▼]            │
├────────────┬────────────────────────────────────────┤
│            │                                        │
│  仪表盘    │          主内容区域                    │
│            │                                        │
│  智能体管理 │                                        │
│            │                                        │
│  智能体群组 │                                        │
│            │                                        │
│  执行记录  │                                        │
│            │                                        │
│  实时监控  │                                        │
│            │                                        │
└────────────┴────────────────────────────────────────┘
```

---

## 3. 功能详解

### 3.1 智能体管理

#### 创建智能体

1. 点击左侧菜单"智能体管理"
2. 点击"新建智能体"按钮
3. 填写信息：

| 字段 | 说明 | 示例 |
|------|------|------|
| 名称 | Agent 名称 | GPT-4 代码助手 |
| 描述 | 功能描述 | 用于代码审查和建议 |
| 类型 | Agent 类型 | openai / anthropic / mcp / custom |
| 配置 | JSON 配置 | 见下方示例 |

**OpenAI 配置示例：**
```json
{
  "api_key": "sk-xxx",
  "model": "gpt-4-turbo-preview",
  "temperature": 0.7,
  "max_tokens": 2000,
  "system_prompt": "你是一个代码助手"
}
```

**Anthropic Claude 配置示例：**
```json
{
  "api_key": "sk-ant-xxx",
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 4096,
  "temperature": 0.7,
  "system_prompt": "你是一个有帮助的AI助手"
}
```

#### 启用/禁用智能体

- 点击列表中的开关按钮即可切换状态
- 禁用后该 Agent 不会被执行

### 3.2 智能体群组

#### 创建群组

1. 点击"智能体群组"菜单
2. 点击"新建群组"
3. 填写群组名称和描述
4. 添加成员 Agent
5. 设置执行模式：
   - **顺序执行**：按优先级依次执行
   - **并行执行**：同时执行所有成员

#### 使用场景

- 代码审查群组：代码格式化 → 代码检查 → 安全扫描
- 内容生成群组：大纲生成 → 内容撰写 → 内容校对

### 3.3 执行记录

查看所有 Agent 的执行历史：

- 执行状态（运行中/成功/失败）
- 输入参数
- 输出结果
- 执行时长
- 详细日志

### 3.4 实时监控

监控正在执行的 Agent：

1. 选择正在运行的执行记录
2. 查看实时日志滚动
3. WebSocket 自动更新状态

### 3.5 配置导入导出

点击右上角用户头像：

- **导出配置**：下载所有 Agent 和群组配置
- **导入配置**：上传 JSON 文件恢复配置

---

## 4. API 调用

### 4.1 认证

```bash
# 登录获取 Token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 响应
{"access_token": "eyJ...", "token_type": "bearer"}
```

### 4.2 智能体操作

```bash
# 设置 Token
TOKEN="eyJ..."

# 获取智能体列表
curl http://localhost:8000/api/agents \
  -H "Authorization: Bearer $TOKEN"

# 创建智能体
curl -X POST http://localhost:8000/api/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Agent",
    "description": "Test agent",
    "agent_type": "openai",
    "config": {"model": "gpt-4"}
  }'

# 执行智能体
curl -X POST http://localhost:8000/api/executions/agents/{agent_id}/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_data": {"message": "Hello"}}'
```

### 4.3 查看执行结果

```bash
# 获取执行状态
curl http://localhost:8000/api/executions/{execution_id} \
  -H "Authorization: Bearer $TOKEN"

# 获取执行日志
curl http://localhost:8000/api/executions/{execution_id}/logs \
  -H "Authorization: Bearer $TOKEN"
```

---

## 5. 监控配置

### 5.1 WebSocket 连接

```javascript
// 连接全局 WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => console.log('Connected');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};

// 连接特定执行
const execWs = new WebSocket('ws://localhost:8000/ws/executions/{execution_id}');
```

### 5.2 消息类型

| 类型 | 说明 |
|------|------|
| `execution_update` | 执行状态更新 |
| `log_update` | 新日志条目 |
| `metric_update` | 指标更新 |

---

## 6. 常见问题

### Q: 忘记密码怎么办？

A: 目前需要联系管理员重置，或直接操作数据库。

### Q: Agent 执行超时怎么办？

A: 检查网络连接和 API Key 是否有效，查看后端日志排查问题。

### Q: 如何添加新的 Agent 类型？

A: 在 `backend/app/services/agent_executor.py` 中添加新的执行器类。

### Q: 数据库迁移怎么做？

A:
```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Q: 如何备份数据？

A:
```bash
# PostgreSQL 备份
pg_dump agent_db > backup.sql

# 或使用导出配置功能
```

---

## 技术支持

- GitHub: https://github.com/moonseeker1/agent_manage
- 问题反馈: GitHub Issues
