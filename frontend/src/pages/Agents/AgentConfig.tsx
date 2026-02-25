import React, { useEffect, useState } from 'react';
import {
  Card,
  Tabs,
  Form,
  Switch,
  Input,
  Button,
  Space,
  message,
  Spin,
  Tag,
  Table,
  Select,
  Popconfirm,
  InputNumber,
  Row,
  Col,
  Divider,
} from 'antd';
import {
  SaveOutlined,
  PlusOutlined,
  DeleteOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import api from '@/services/api';

const { TabPane } = Tabs;
const { TextArea } = Input;

interface MCPBinding {
  id: string;
  mcp_server_id: string;
  server_name: string;
  server_code: string;
  enabled_tools: string[];
  is_enabled: boolean;
  priority: number;
}

interface SkillBinding {
  id: string;
  skill_id: string;
  skill_name: string;
  priority: number;
  is_enabled: boolean;
}

interface MCPServer {
  id: string;
  name: string;
  code: string;
  tools?: { name: string; description?: string }[];
}

interface Skill {
  id: string;
  name: string;
  code: string;
}

interface AgentConfigProps {
  agentId: string;
}

const AgentConfig: React.FC<AgentConfigProps> = ({ agentId }) => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [mcpBindings, setMcpBindings] = useState<MCPBinding[]>([]);
  const [skillBindings, setSkillBindings] = useState<SkillBinding[]>([]);
  const [mcpServers, setMcpServers] = useState<MCPServer[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [activeTab, setActiveTab] = useState('permission');
  const [permissionForm] = Form.useForm();
  const [selectedMcpServer, setSelectedMcpServer] = useState<string>('');
  const [selectedSkill, setSelectedSkill] = useState<string>('');

  useEffect(() => {
    loadData();
  }, [agentId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      // Load permission
      const permRes = await api.get(`/agents/${agentId}/permission`, { headers });
      permissionForm.setFieldsValue(permRes.data);

      // Load MCP bindings
      const mcpRes = await api.get(`/agents/${agentId}/mcp-bindings`, { headers });
      setMcpBindings(mcpRes.data);

      // Load skill bindings
      const skillRes = await api.get(`/rbac/agents/${agentId}/skills`, { headers });
      setSkillBindings(skillRes.data || []);

      // Load available MCP servers
      const serversRes = await api.get('/mcp/servers', { headers });
      setMcpServers(serversRes.data.items || []);

      // Load available skills
      const skillsRes = await api.get('/rbac/skills', { headers });
      setSkills(skillsRes.data.items || []);
    } catch (error) {
      console.error('加载配置失败', error);
    } finally {
      setLoading(false);
    }
  };

  const savePermission = async () => {
    setSaving(true);
    try {
      const values = await permissionForm.validateFields();
      const token = localStorage.getItem('token');

      // Convert comma-separated strings to arrays
      const data = {
        ...values,
        allowed_paths: values.allowed_paths?.split('\n').filter((p: string) => p.trim()) || [],
        blocked_paths: values.blocked_paths?.split('\n').filter((p: string) => p.trim()) || [],
        allowed_commands: values.allowed_commands?.split('\n').filter((c: string) => c.trim()) || [],
        blocked_commands: values.blocked_commands?.split('\n').filter((c: string) => c.trim()) || [],
      };

      await api.put(`/agents/${agentId}/permission`, data, {
        headers: { Authorization: `Bearer ${token}` }
      });
      message.success('权限配置已保存');
    } catch (error) {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  const addMcpBinding = async () => {
    if (!selectedMcpServer) {
      message.warning('请选择MCP服务器');
      return;
    }
    try {
      const token = localStorage.getItem('token');
      await api.post(
        `/agents/${agentId}/mcp-bindings`,
        { mcp_server_id: selectedMcpServer, is_enabled: true, priority: 100 },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      message.success('MCP服务已绑定');
      setSelectedMcpServer('');
      loadData();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '绑定失败');
    }
  };

  const removeMcpBinding = async (bindingId: string) => {
    try {
      const token = localStorage.getItem('token');
      await api.delete(`/agents/${agentId}/mcp-bindings/${bindingId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      message.success('已解除绑定');
      loadData();
    } catch (error) {
      message.error('解除绑定失败');
    }
  };

  const addSkillBinding = async () => {
    if (!selectedSkill) {
      message.warning('请选择技能');
      return;
    }
    try {
      const token = localStorage.getItem('token');
      await api.post(
        `/rbac/agents/${agentId}/skills/${selectedSkill}`,
        { priority: 100, is_enabled: true },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      message.success('技能已绑定');
      setSelectedSkill('');
      loadData();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '绑定失败');
    }
  };

  const removeSkillBinding = async (skillId: string) => {
    try {
      const token = localStorage.getItem('token');
      await api.delete(`/rbac/agents/${agentId}/skills/${skillId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      message.success('已解除绑定');
      loadData();
    } catch (error) {
      message.error('解除绑定失败');
    }
  };

  const mcpColumns = [
    {
      title: 'MCP服务器',
      dataIndex: 'server_name',
      key: 'server_name',
      render: (name: string, record: MCPBinding) => (
        <Space>
          <ApiOutlined />
          <span>{name}</span>
          <Tag color="blue">{record.server_code}</Tag>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'green' : 'red'}>{enabled ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: MCPBinding) => (
        <Popconfirm
          title="确定要解除绑定吗？"
          onConfirm={() => removeMcpBinding(record.id)}
          okText="确定"
          cancelText="取消"
        >
          <Button icon={<DeleteOutlined />} size="small" danger />
        </Popconfirm>
      ),
    },
  ];

  const skillColumns = [
    {
      title: '技能',
      dataIndex: 'skill_name',
      key: 'skill_name',
      render: (name: string) => (
        <Space>
          <ThunderboltOutlined />
          <span>{name}</span>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'green' : 'red'}>{enabled ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: SkillBinding) => (
        <Popconfirm
          title="确定要解除绑定吗？"
          onConfirm={() => removeSkillBinding(record.skill_id)}
          okText="确定"
          cancelText="取消"
        >
          <Button icon={<DeleteOutlined />} size="small" danger />
        </Popconfirm>
      ),
    },
  ];

  // Filter out already bound servers
  const availableMcpServers = mcpServers.filter(
    server => !mcpBindings.some(b => b.mcp_server_id === server.id)
  );
  const availableSkills = skills.filter(
    skill => !skillBindings.some(b => b.skill_id === skill.id)
  );

  if (loading) {
    return <Spin />;
  }

  return (
    <Card>
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        {/* 权限配置 */}
        <TabPane
          tab={<span><SafetyOutlined /> 操作权限</span>}
          key="permission"
        >
          <Form form={permissionForm} layout="vertical">
            <Row gutter={24}>
              <Col span={12}>
                <Card title="工具权限" size="small">
                  <Form.Item name="allow_bash" label="允许执行Bash命令" valuePropName="checked">
                    <Switch checkedChildren="允许" unCheckedChildren="禁止" />
                  </Form.Item>
                  <Form.Item name="allow_read" label="允许读取文件" valuePropName="checked">
                    <Switch checkedChildren="允许" unCheckedChildren="禁止" />
                  </Form.Item>
                  <Form.Item name="allow_write" label="允许写入文件" valuePropName="checked">
                    <Switch checkedChildren="允许" unCheckedChildren="禁止" />
                  </Form.Item>
                  <Form.Item name="allow_edit" label="允许编辑文件" valuePropName="checked">
                    <Switch checkedChildren="允许" unCheckedChildren="禁止" />
                  </Form.Item>
                  <Form.Item name="allow_web" label="允许访问网络" valuePropName="checked">
                    <Switch checkedChildren="允许" unCheckedChildren="禁止" />
                  </Form.Item>
                </Card>
              </Col>
              <Col span={12}>
                <Card title="执行限制" size="small">
                  <Form.Item name="max_execution_time" label="最大执行时间(秒)">
                    <InputNumber min={1} max={3600} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item name="max_output_size" label="最大输出大小(KB)">
                    <InputNumber min={1} max={100000} style={{ width: '100%' }} />
                  </Form.Item>
                </Card>
              </Col>
            </Row>

            <Divider />

            <Row gutter={24}>
              <Col span={12}>
                <Card title="路径限制" size="small">
                  <Form.Item name="allowed_paths" label="允许访问的路径（每行一个）">
                    <TextArea rows={4} placeholder="/home/user&#10;/tmp" />
                  </Form.Item>
                  <Form.Item name="blocked_paths" label="禁止访问的路径（每行一个）">
                    <TextArea rows={4} placeholder="/etc/passwd&#10;/root" />
                  </Form.Item>
                </Card>
              </Col>
              <Col span={12}>
                <Card title="命令限制" size="small">
                  <Form.Item name="allowed_commands" label="允许执行的命令（每行一个）">
                    <TextArea rows={4} placeholder="ls&#10;cat&#10;grep" />
                  </Form.Item>
                  <Form.Item name="blocked_commands" label="禁止执行的命令（每行一个）">
                    <TextArea rows={4} placeholder="rm -rf&#10;sudo" />
                  </Form.Item>
                </Card>
              </Col>
            </Row>

            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={savePermission}>
                保存权限配置
              </Button>
            </div>
          </Form>
        </TabPane>

        {/* 技能绑定 */}
        <TabPane
          tab={<span><ThunderboltOutlined /> 技能绑定</span>}
          key="skills"
        >
          <div style={{ marginBottom: 16 }}>
            <Space>
              <Select
                style={{ width: 200 }}
                placeholder="选择技能"
                value={selectedSkill}
                onChange={setSelectedSkill}
                options={availableSkills.map(s => ({ value: s.id, label: s.name }))}
              />
              <Button type="primary" icon={<PlusOutlined />} onClick={addSkillBinding}>
                绑定技能
              </Button>
            </Space>
          </div>
          <Table
            columns={skillColumns}
            dataSource={skillBindings}
            rowKey="id"
            pagination={false}
            size="small"
            locale={{ emptyText: '暂未绑定任何技能' }}
          />
        </TabPane>

        {/* MCP绑定 */}
        <TabPane
          tab={<span><ApiOutlined /> MCP服务</span>}
          key="mcp"
        >
          <div style={{ marginBottom: 16 }}>
            <Space>
              <Select
                style={{ width: 250 }}
                placeholder="选择MCP服务器"
                value={selectedMcpServer}
                onChange={setSelectedMcpServer}
                options={availableMcpServers.map(s => ({ value: s.id, label: `${s.name} (${s.code})` }))}
              />
              <Button type="primary" icon={<PlusOutlined />} onClick={addMcpBinding}>
                绑定MCP服务
              </Button>
            </Space>
          </div>
          <Table
            columns={mcpColumns}
            dataSource={mcpBindings}
            rowKey="id"
            pagination={false}
            size="small"
            locale={{ emptyText: '暂未绑定任何MCP服务' }}
          />
        </TabPane>
      </Tabs>
    </Card>
  );
};

export default AgentConfig;
