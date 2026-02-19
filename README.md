# 🤖 智能体管理系统 (Agent Management System)

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18+-blue.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.109+-green.svg)](https://fastapi.tiangolo.com/)

一个功能完善的智能体(Agent)管理与监控系统，支持 MCP Server、OpenAI API 和自定义 Agent 的统一管理与调度。

## ✨ 功能特性

### 核心功能
- 🔐 **用户认证** - JWT Token 认证，支持用户注册/登录
- 🤖 **智能体管理** - 创建、配置、启用/禁用智能体
- 👥 **智能体群组** - 将多个智能体组合，支持顺序/并行执行
- 📊 **执行监控** - 实时监控智能体执行状态和日志
- 📈 **数据统计** - 执行次数、成功率、响应时间等指标

### Agent 类型
- **OpenAI** - 支持 GPT-4、GPT-3.5 等模型
- **MCP Server** - Model Context Protocol 服务集成
- **Custom** - 自定义 Webhook 或代码执行

### 高级功能
- 📋 **预设模板** - 快速创建常用类型智能体
- 📥 **配置导入/导出** - 一键备份和恢复配置
- 🔄 **批量操作** - 批量启用/禁用/删除智能体
- 🌐 **WebSocket 实时推送** - 执行状态实时更新

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Ant Design 5 + Vite |
| 后端 | Python 3.9+ + FastAPI + SQLAlchemy (async) |
| 数据库 | PostgreSQL 14+ |
| 缓存 | Redis |
| 认证 | JWT (python-jose) |

## 📦 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 克隆仓库
git clone https://github.com/moonseeker1/agent_manage.git
cd agent_manage

# 启动所有服务
docker-compose up -d

# 访问应用
# 前端: http://localhost:5173
# 后端: http://localhost:8000
# API文档: http://localhost:8000/docs
```

### 方式二：手动部署

#### 环境要求
- Python 3.9+
- Node.js 18+
- PostgreSQL 14+
- Redis

#### 后端部署

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库连接等

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 前端部署

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

#### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name _;

    # 前端
    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    # 后端 API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
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

## 📁 项目结构

```
.
├── frontend/                    # React 前端
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   │   ├── Dashboard/      # 仪表盘
│   │   │   ├── Agents/         # 智能体管理
│   │   │   ├── Groups/         # 群组管理
│   │   │   ├── Executions/     # 执行记录
│   │   │   ├── Monitor/        # 实时监控
│   │   │   └── Login/          # 登录注册
│   │   ├── components/         # 公共组件
│   │   ├── services/           # API 和 WebSocket 服务
│   │   ├── stores/             # Zustand 状态管理
│   │   └── types/              # TypeScript 类型定义
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── api/                # API 路由
│   │   │   └── v1/endpoints/   # 各接口实现
│   │   ├── models/             # SQLAlchemy 数据库模型
│   │   ├── schemas/            # Pydantic 验证模型
│   │   ├── services/           # 业务逻辑层
│   │   ├── core/               # 核心配置
│   │   │   ├── config.py       # 配置管理
│   │   │   ├── database.py     # 数据库连接
│   │   │   ├── security.py     # 密码和JWT
│   │   │   └── deps.py         # 依赖注入
│   │   └── main.py             # 应用入口
│   ├── tests/                  # 单元测试
│   ├── requirements.txt
│   └── .env.example
│
├── docker-compose.yml          # Docker 编排
├── nginx.conf                  # Nginx 配置示例
├── start.sh                    # 启动脚本
└── README.md
```

## 🔌 API 接口

### 认证相关
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| GET | `/api/auth/me` | 获取当前用户信息 |
| PUT | `/api/auth/me` | 更新用户信息 |

### 智能体管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/agents` | 获取智能体列表 |
| POST | `/api/agents` | 创建智能体 |
| GET | `/api/agents/{id}` | 获取智能体详情 |
| PUT | `/api/agents/{id}` | 更新智能体 |
| DELETE | `/api/agents/{id}` | 删除智能体 |
| POST | `/api/agents/{id}/enable` | 启用智能体 |
| POST | `/api/agents/{id}/disable` | 禁用智能体 |

### 群组管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/groups` | 获取群组列表 |
| POST | `/api/groups` | 创建群组 |
| GET | `/api/groups/{id}` | 获取群组详情 |
| PUT | `/api/groups/{id}` | 更新群组 |
| DELETE | `/api/groups/{id}` | 删除群组 |
| POST | `/api/groups/{id}/members` | 添加成员 |
| DELETE | `/api/groups/{id}/members/{agent_id}` | 移除成员 |

### 执行管理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/executions/agents/{id}/execute` | 执行智能体 |
| POST | `/api/executions/groups/{id}/execute` | 执行群组 |
| GET | `/api/executions` | 获取执行列表 |
| GET | `/api/executions/{id}` | 获取执行详情 |
| GET | `/api/executions/{id}/logs` | 获取执行日志 |
| POST | `/api/executions/{id}/cancel` | 取消执行 |

### 配置管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config/export` | 导出配置 |
| POST | `/api/config/import` | 导入配置 |
| POST | `/api/config/agents/batch-delete` | 批量删除 |
| POST | `/api/config/agents/batch-toggle` | 批量切换状态 |

### WebSocket
| 路径 | 说明 |
|------|------|
| `/ws` | 全局状态推送 |
| `/ws/executions/{id}` | 单个执行状态推送 |

## 📝 Agent 配置示例

### OpenAI 类型
```json
{
  "name": "GPT-4 助手",
  "description": "基于 GPT-4 的通用助手",
  "agent_type": "openai",
  "config": {
    "api_key": "sk-xxx",
    "model": "gpt-4-turbo-preview",
    "temperature": 0.7,
    "max_tokens": 2000,
    "system_prompt": "你是一个有帮助的AI助手。"
  }
}
```

### MCP Server 类型
```json
{
  "name": "文件系统助手",
  "description": "MCP 文件系统服务",
  "agent_type": "mcp",
  "config": {
    "server_url": "http://localhost:3001",
    "server_command": "node server.js",
    "tools": ["read_file", "write_file", "list_directory"]
  }
}
```

### 自定义类型
```json
{
  "name": "自定义 Webhook",
  "description": "调用自定义服务",
  "agent_type": "custom",
  "config": {
    "webhook_url": "https://your-service.com/execute",
    "timeout": 30,
    "headers": {
      "Authorization": "Bearer xxx"
    }
  }
}
```

## 🧪 测试

```bash
# 后端测试
cd backend
pytest

# 前端代码检查
cd frontend
npm run lint
```

## 📄 环境变量

### 后端 (.env)
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/agent_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
DEBUG=true
OPENAI_API_KEY=sk-xxx
CORS_ORIGINS=["http://localhost:5173"]
```

## 📸 界面预览

### 登录页面
- 支持用户注册和登录
- 中文界面

### 仪表盘
- 智能体统计概览
- 执行记录图表
- 快速操作入口

### 智能体管理
- 列表展示所有智能体
- 支持搜索和筛选
- 快速启用/禁用

### 实时监控
- 执行状态实时更新
- 日志实时滚动显示
- WebSocket 实时通信

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📜 许可证

[MIT License](LICENSE)

---

**作者**: Agent Manager Team
**仓库**: https://github.com/moonseeker1/agent_manage
