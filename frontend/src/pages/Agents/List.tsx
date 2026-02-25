import React, { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  message,
  Popconfirm,
  Typography,
  Card,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useAgentStore } from '@/stores';
import type { Agent, AgentType } from '@/types';
import AgentConfig from './AgentConfig';

const { Title } = Typography;
const { TextArea } = Input;

const agentTypeColors: Record<AgentType, string> = {
  mcp: 'blue',
  openai: 'green',
  custom: 'orange',
};

const agentTypeLabels: Record<AgentType, string> = {
  mcp: 'MCP服务',
  openai: 'OpenAI',
  custom: '自定义',
};

const AgentsList: React.FC = () => {
  const {
    agents,
    loading,
    fetchAgents,
    createAgent,
    updateAgent,
    deleteAgent,
    toggleAgent,
    executeAgent,
  } = useAgentStore();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [form] = Form.useForm();
  const [executeModalOpen, setExecuteModalOpen] = useState(false);
  const [executingAgent, setExecutingAgent] = useState<Agent | null>(null);
  const [executeForm] = Form.useForm();
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [configuringAgent, setConfiguringAgent] = useState<Agent | null>(null);

  useEffect(() => {
    fetchAgents({ page_size: 100 });
  }, []);

  const handleCreate = () => {
    setEditingAgent(null);
    form.resetFields();
    form.setFieldsValue({
      agent_type: 'openai',
      enabled: true,
      config: {},
    });
    setModalOpen(true);
  };

  const handleEdit = (agent: Agent) => {
    setEditingAgent(agent);
    form.setFieldsValue({
      name: agent.name,
      description: agent.description,
      agent_type: agent.agent_type,
      enabled: agent.enabled,
      config: JSON.stringify(agent.config, null, 2),
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const config = values.config
        ? JSON.parse(values.config)
        : {};

      const data = {
        name: values.name,
        description: values.description,
        agent_type: values.agent_type,
        enabled: values.enabled,
        config,
      };

      if (editingAgent) {
        await updateAgent(editingAgent.id, data);
        message.success('智能体更新成功');
      } else {
        await createAgent(data);
        message.success('智能体创建成功');
      }

      setModalOpen(false);
      form.resetFields();
    } catch (error: any) {
      if (error.errorFields) return;
      message.error(error.message || '操作失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteAgent(id);
      message.success('智能体删除成功');
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleToggle = async (id: string, enabled: boolean) => {
    await toggleAgent(id, enabled);
    message.success(`智能体已${enabled ? '启用' : '禁用'}`);
  };

  const handleExecute = (agent: Agent) => {
    setExecutingAgent(agent);
    executeForm.resetFields();
    setExecuteModalOpen(true);
  };

  const handleConfig = (agent: Agent) => {
    setConfiguringAgent(agent);
    setConfigModalOpen(true);
  };

  const handleExecuteSubmit = async () => {
    try {
      const values = await executeForm.validateFields();
      const inputData = values.input_data
        ? JSON.parse(values.input_data)
        : undefined;

      await executeAgent(executingAgent!.id, inputData);
      message.success('执行任务已启动');
      setExecuteModalOpen(false);
    } catch (error: any) {
      if (error.errorFields) return;
      message.error(error.message || '执行失败');
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Agent) => (
        <Space>
          {name}
          {!record.enabled && <Tag color="red">已禁用</Tag>}
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'agent_type',
      key: 'agent_type',
      render: (type: AgentType) => (
        <Tag color={agentTypeColors[type]}>{agentTypeLabels[type]}</Tag>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean, record: Agent) => (
        <Switch
          checked={enabled}
          onChange={(checked) => handleToggle(record.id, checked)}
        />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: Agent) => (
        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            size="small"
            onClick={() => handleExecute(record)}
            disabled={!record.enabled}
          >
            执行
          </Button>
          <Button
            icon={<SettingOutlined />}
            size="small"
            onClick={() => handleConfig(record)}
            title="配置权限、技能和MCP"
          >
            配置
          </Button>
          <Button
            icon={<EditOutlined />}
            size="small"
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="确定删除此智能体？"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button icon={<DeleteOutlined />} size="small" danger />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={2}>智能体管理</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          创建智能体
        </Button>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={agents}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={editingAgent ? '编辑智能体' : '创建智能体'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入智能体名称' }]}
          >
            <Input placeholder="智能体名称" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="智能体描述" />
          </Form.Item>

          <Form.Item
            name="agent_type"
            label="类型"
            rules={[{ required: true }]}
          >
            <Select disabled={!!editingAgent}>
              <Select.Option value="openai">OpenAI</Select.Option>
              <Select.Option value="mcp">MCP服务</Select.Option>
              <Select.Option value="custom">自定义</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item
            name="config"
            label="配置（JSON格式）"
            extra="请输入JSON格式的配置对象"
          >
            <TextArea
              rows={6}
              placeholder='{"api_key": "...", "model": "gpt-4"}'
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`执行智能体: ${executingAgent?.name}`}
        open={executeModalOpen}
        onOk={handleExecuteSubmit}
        onCancel={() => setExecuteModalOpen(false)}
      >
        <Form form={executeForm} layout="vertical">
          <Form.Item
            name="input_data"
            label="输入数据（JSON格式）"
            extra="请输入JSON格式的输入数据"
          >
            <TextArea
              rows={6}
              placeholder='{"message": "你好，智能体！"}'
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`配置智能体: ${configuringAgent?.name}`}
        open={configModalOpen}
        onCancel={() => setConfigModalOpen(false)}
        footer={null}
        width={900}
      >
        {configuringAgent && <AgentConfig agentId={configuringAgent.id} />}
      </Modal>
    </div>
  );
};

export default AgentsList;
