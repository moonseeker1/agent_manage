# 龙虾养殖场 - OpenClaw 管理案例

## 概念说明

把 **OpenClaw** 比作"龙虾"，**智能体管理系统**就是"龙虾养殖场"。

```
┌──────────────────────────────────────────────────────────────┐
│                     🦞 龙虾养殖场 🦞                          │
│                  (Agent Management System)                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   🦞 龙虾池1        🦞 龙虾池2        🦞 龙虾池3             │
│   (代码助手)        (文档助手)       (测试助手)              │
│                                                              │
│   🦞 龙虾群组: 全能工作流                                     │
│   (多个龙虾协同工作)                                          │
│                                                              │
│   📊 监控面板: 查看所有龙虾的工作状态                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 第一步：创建龙虾池（智能体）

### 龙虾1：代码审查助手

```json
{
  "name": "🦞 代码审查龙虾",
  "description": "负责代码质量检查和改进建议",
  "agent_type": "openai",
  "config": {
    "api_key": "sk-xxx",
    "model": "gpt-4-turbo-preview",
    "system_prompt": "你是一个专业的代码审查专家。分析代码质量，提出改进建议。",
    "temperature": 0.3
  }
}
```

### 龙虾2：文档生成助手

```json
{
  "name": "🦞 文档龙虾",
  "description": "负责生成和维护项目文档",
  "agent_type": "anthropic",
  "config": {
    "api_key": "sk-ant-xxx",
    "model": "claude-3-5-sonnet-20241022",
    "system_prompt": "你是一个技术文档专家。根据代码生成清晰的文档。",
    "max_tokens": 4096
  }
}
```

### 龙虾3：测试用例生成

```json
{
  "name": "🦞 测试龙虾",
  "description": "负责生成单元测试和集成测试",
  "agent_type": "anthropic",
  "config": {
    "api_key": "sk-ant-xxx",
    "model": "claude-3-5-sonnet-20241022",
    "system_prompt": "你是一个测试工程师。为代码生成完整的测试用例。"
  }
}
```

---

## 第二步：创建龙虾群组

### 群组：全能工作流

将多只龙虾组合成一条流水线：

```json
{
  "name": "🦞 全能工作流群组",
  "description": "代码审查 → 文档生成 → 测试用例",
  "execution_mode": "sequential",
  "agent_ids": [
    "代码审查龙虾的ID",
    "文档龙虾的ID",
    "测试龙虾的ID"
  ]
}
```

**执行流程：**
```
输入代码
    ↓
🦞 代码审查龙虾 → 输出审查报告
    ↓
🦞 文档龙虾 → 输出API文档
    ↓
🦞 测试龙虾 → 输出测试用例
    ↓
完成！
```

---

## 第三步：通过 API 操作龙虾

### 登录获取 Token

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 创建龙虾

```bash
# 创建代码审查龙虾
curl -X POST http://localhost:8000/api/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "🦞 代码审查龙虾",
    "description": "负责代码质量检查",
    "agent_type": "anthropic",
    "config": {
      "api_key": "sk-ant-xxx",
      "model": "claude-3-5-sonnet-20241022",
      "system_prompt": "你是代码审查专家"
    }
  }'
```

### 派龙虾干活

```bash
# 让代码审查龙虾审查代码
curl -X POST http://localhost:8000/api/executions/agents/{龙虾ID}/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input_data": {
      "message": "请审查以下代码：\n```python\ndef hello():\n    print(\"hello\")\n```"
    }
  }'
```

### 查看龙虾工作结果

```bash
# 获取执行结果
curl http://localhost:8000/api/executions/{执行ID} \
  -H "Authorization: Bearer $TOKEN"

# 获取工作日志
curl http://localhost:8000/api/executions/{执行ID}/logs \
  -H "Authorization: Bearer $TOKEN"
```

---

## 第四步：监控龙虾状态

### 前端监控

访问 http://localhost:8000/agent/monitor

可以看到：
- 🟢 正在工作的龙虾
- 📊 每只龙虾的工作次数
- ⏱️ 平均工作时间
- ❌ 失败率统计

### WebSocket 实时监控

```javascript
// 连接监控
const ws = new WebSocket('ws://localhost:8000/agent/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'execution_update') {
    console.log(`🦞 ${data.agent_name} 状态: ${data.status}`);
  }

  if (data.type === 'log_update') {
    console.log(`📝 ${data.log.message}`);
  }
};
```

---

## 完整示例：Python 脚本管理龙虾

```python
"""
龙虾养殖场管理脚本
"""
import requests

BASE_URL = "http://localhost:8000/api"
TOKEN = "your-jwt-token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 1. 创建龙虾
def create_crawfish(name, description, config):
    response = requests.post(
        f"{BASE_URL}/agents",
        headers=headers,
        json={
            "name": name,
            "description": description,
            "agent_type": "anthropic",
            "config": config
        }
    )
    return response.json()

# 2. 派龙虾干活
def send_crawfish_to_work(agent_id, task):
    response = requests.post(
        f"{BASE_URL}/executions/agents/{agent_id}/execute",
        headers=headers,
        json={"input_data": {"message": task}}
    )
    return response.json()

# 3. 查看工作结果
def check_work_result(execution_id):
    response = requests.get(
        f"{BASE_URL}/executions/{execution_id}",
        headers=headers
    )
    return response.json()

# 使用示例
if __name__ == "__main__":
    # 创建一只代码龙虾
    crawfish = create_crawfish(
        name="🦞 代码龙虾",
        description="代码审查专家",
        config={
            "api_key": "sk-ant-xxx",
            "model": "claude-3-5-sonnet-20241022",
            "system_prompt": "你是代码审查专家"
        }
    )
    print(f"创建龙虾: {crawfish['id']}")

    # 派它去工作
    execution = send_crawfish_to_work(
        crawfish["id"],
        "请审查这段代码: def add(a, b): return a + b"
    )
    print(f"开始执行: {execution['id']}")

    # 查看结果
    import time
    time.sleep(5)  # 等待执行完成
    result = check_work_result(execution["id"])
    print(f"执行状态: {result['status']}")
    print(f"输出结果: {result['output_data']}")
```

---

## 养殖场运营技巧

### 1. 分类管理龙虾

| 类型 | 用途 | 推荐模型 |
|------|------|---------|
| 🔍 审查龙虾 | 代码审查 | GPT-4 / Claude |
| 📝 文档龙虾 | 文档生成 | Claude |
| 🧪 测试龙虾 | 测试用例 | GPT-4 |
| 🎨 设计龙虾 | UI/UX | DALL-E |
| 🔧 运维龙虾 | 部署脚本 | GPT-4 |

### 2. 群组协作

创建专业团队：
- **前端团队**：审查 → 文档 → 测试
- **后端团队**：API设计 → 代码 → 文档
- **全栈团队**：设计 → 前端 → 后端 → 测试

### 3. 监控健康度

- Token 消耗量
- 响应时间
- 成功率
- 错误日志

### 4. 批量操作

```bash
# 批量启用所有龙虾
curl -X POST http://localhost:8000/api/config/agents/batch-toggle \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '["id1", "id2", "id3"]&enabled=true'
```

---

## 总结

**龙虾养殖场 = 智能体管理系统**
- 🦞 龙虾 = Agent（智能体）
- 🏊 龙虾池 = Agent 配置
- 🦐 龙虾群 = Agent Group（群组）
- 📊 监控 = Dashboard + WebSocket
- 🎣 派活 = Execute API

开始养你的龙虾吧！🦞
