# 核心代码说明

## 项目架构

```
├── frontend/                    # React 前端
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   ├── components/         # 公共组件
│   │   ├── services/           # API 服务
│   │   ├── stores/             # 状态管理 (Zustand)
│   │   └── types/              # TypeScript 类型
│   └── vite.config.ts          # Vite 配置
│
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/endpoints/   # API 路由
│   │   ├── models/             # 数据库模型
│   │   ├── schemas/            # Pydantic 验证
│   │   ├── services/           # 业务逻辑
│   │   └── core/               # 核心配置
│   └── requirements.txt
│
└── docs/                        # 文档
```

---

## 1. 后端核心代码

### 1.1 数据库模型 (`backend/app/models/`)

#### Agent 模型

```python
# backend/app/models/agent.py

class AgentType:
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MCP = "mcp"
    CUSTOM = "custom"

class Agent(Base):
    """智能体模型"""
    __tablename__ = "agents"

    id = Column(UUID, primary_key=True)
    name = Column(String(255))           # 名称
    description = Column(Text)           # 描述
    agent_type = Column(String(50))      # 类型
    config = Column(JSONB)               # 配置 (JSON)
    enabled = Column(Boolean)            # 是否启用

    # 关系
    executions = relationship("Execution")
    groups = relationship("AgentGroupMember")
```

#### Execution 模型

```python
# backend/app/models/execution.py

class Execution(Base):
    """执行记录模型"""
    __tablename__ = "executions"

    id = Column(UUID, primary_key=True)
    agent_id = Column(UUID, ForeignKey("agents.id"))
    status = Column(String(50))          # pending/running/completed/failed
    input_data = Column(JSONB)           # 输入数据
    output_data = Column(JSONB)          # 输出数据
    error_message = Column(Text)         # 错误信息
    started_at = Column(DateTime)        # 开始时间
    completed_at = Column(DateTime)      # 完成时间

    # 关系
    logs = relationship("ExecutionLog")
```

### 1.2 API 路由 (`backend/app/api/v1/endpoints/`)

#### Agents 路由

```python
# backend/app/api/v1/endpoints/agents.py

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.get("")
async def list_agents(
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取智能体列表"""
    service = AgentService(db)
    agents, total = await service.get_agents(page, page_size)
    return {"items": agents, "total": total}

@router.post("")
async def create_agent(
    data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建智能体"""
    service = AgentService(db)
    return await service.create_agent(data)
```

### 1.3 业务服务 (`backend/app/services/`)

#### Agent 执行器

```python
# backend/app/services/agent_executor.py

class AnthropicExecutor(BaseExecutor):
    """Claude 执行器"""

    async def execute(self, input_data: dict) -> dict:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.api_key)

        response = await client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": input_data["message"]}]
        )

        return {"response": response.content[0].text}
```

---

## 2. 前端核心代码

### 2.1 状态管理 (`frontend/src/stores/`)

#### Auth Store

```typescript
// frontend/src/stores/authStore.ts

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      setAuth: (token, user) => set({ token, user, isAuthenticated: true }),
      logout: () => set({ token: null, user: null, isAuthenticated: false }),
    }),
    { name: 'auth-storage' }
  )
);
```

### 2.2 API 服务 (`frontend/src/services/`)

```typescript
// frontend/src/services/api.ts

const api = axios.create({
  baseURL: '/agent/api',
});

// 请求拦截器 - 添加 Token
api.interceptors.request.use((config) => {
  const authStorage = localStorage.getItem('auth-storage');
  if (authStorage) {
    const { state } = JSON.parse(authStorage);
    if (state?.token) {
      config.headers.Authorization = `Bearer ${state.token}`;
    }
  }
  return config;
});

// Agents API
export const agentsApi = {
  list: (params) => api.get('/agents', { params }),
  create: (data) => api.post('/agents', data),
  execute: (id, inputData) => api.post(`/executions/agents/${id}/execute`, inputData),
};
```

### 2.3 WebSocket 服务

```typescript
// frontend/src/services/websocket.ts

class WebSocketService {
  connect(url = `ws://${location.host}/agent/ws`) {
    this.ws = new WebSocket(url);

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
  }

  subscribe(type: string, handler: Function) {
    // 订阅特定类型的消息
  }
}
```

---

## 3. 关键流程

### 3.1 用户登录流程

```
用户输入 → Login组件 → API /auth/login
                          ↓
                    验证用户名密码
                          ↓
                    生成 JWT Token
                          ↓
                    返回 Token → 存储到 Zustand
                          ↓
                    跳转到仪表盘
```

### 3.2 Agent 执行流程

```
用户点击执行 → API /executions/agents/{id}/execute
                    ↓
              创建 Execution 记录 (status: pending)
                    ↓
              获取 Agent 配置
                    ↓
              选择对应 Executor (OpenAI/Anthropic/MCP)
                    ↓
              执行并记录日志
                    ↓
              更新 Execution 状态 (completed/failed)
                    ↓
              WebSocket 推送更新到前端
```

### 3.3 实时监控流程

```
前端连接 WebSocket → 订阅执行更新
                           ↓
                    后端执行 Agent
                           ↓
                    每条日志通过 WebSocket 推送
                           ↓
                    前端实时显示日志
```

---

## 4. 配置文件说明

### 4.1 后端环境变量

```env
# backend/.env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/agent_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
DEBUG=true
OPENAI_API_KEY=sk-xxx
```

### 4.2 前端配置

```typescript
// frontend/vite.config.ts
export default defineConfig({
  base: '/agent/',  // 部署路径
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000' },
      '/ws': { target: 'ws://localhost:8000', ws: true },
    }
  }
});
```

---

## 5. 扩展开发

### 5.1 添加新的 Agent 类型

1. 在 `agent_executor.py` 添加新执行器：

```python
class MyCustomExecutor(BaseExecutor):
    async def execute(self, input_data: dict) -> dict:
        # 实现执行逻辑
        pass
```

2. 在 `get_executor()` 函数中注册：

```python
executors = {
    ...
    "my_custom": MyCustomExecutor,
}
```

### 5.2 添加新的 API 端点

1. 在 `endpoints/` 创建路由文件
2. 在 `__init__.py` 中注册路由
3. 添加对应的 Schema 和 Service

---

## 6. 数据库关系图

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   agents    │────<│ agent_group_members│>────│ agent_groups│
└─────────────┘     └──────────────────┘     └─────────────┘
       │
       │
       ▼
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│ executions  │────<│ execution_logs  │     │   metrics   │
└─────────────┘     └─────────────────┘     └─────────────┘
       │                                            │
       └────────────────────────────────────────────┘

┌─────────────┐
│   users     │
└─────────────┘
```
