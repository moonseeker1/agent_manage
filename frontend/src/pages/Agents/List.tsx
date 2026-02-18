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
} from '@ant-design/icons';
import { useAgentStore } from '@/stores';
import type { Agent, AgentType } from '@/types';

const { Title } = Typography;
const { TextArea } = Input;

const agentTypeColors: Record<AgentType, string> = {
  mcp: 'blue',
  openai: 'green',
  custom: 'orange',
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
        message.success('Agent updated successfully');
      } else {
        await createAgent(data);
        message.success('Agent created successfully');
      }

      setModalOpen(false);
      form.resetFields();
    } catch (error: any) {
      if (error.errorFields) return;
      message.error(error.message || 'Operation failed');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteAgent(id);
      message.success('Agent deleted successfully');
    } catch (error: any) {
      message.error(error.message || 'Delete failed');
    }
  };

  const handleToggle = async (id: string, enabled: boolean) => {
    await toggleAgent(id, enabled);
    message.success(`Agent ${enabled ? 'enabled' : 'disabled'}`);
  };

  const handleExecute = (agent: Agent) => {
    setExecutingAgent(agent);
    executeForm.resetFields();
    setExecuteModalOpen(true);
  };

  const handleExecuteSubmit = async () => {
    try {
      const values = await executeForm.validateFields();
      const inputData = values.input_data
        ? JSON.parse(values.input_data)
        : undefined;

      await executeAgent(executingAgent!.id, inputData);
      message.success('Execution started');
      setExecuteModalOpen(false);
    } catch (error: any) {
      if (error.errorFields) return;
      message.error(error.message || 'Execution failed');
    }
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Agent) => (
        <Space>
          {name}
          {!record.enabled && <Tag color="red">Disabled</Tag>}
        </Space>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'agent_type',
      key: 'agent_type',
      render: (type: AgentType) => (
        <Tag color={agentTypeColors[type]}>{type.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Enabled',
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
      title: 'Actions',
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
            Execute
          </Button>
          <Button
            icon={<EditOutlined />}
            size="small"
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="Delete agent?"
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
        <Title level={2}>Agents</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          Create Agent
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
        title={editingAgent ? 'Edit Agent' : 'Create Agent'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: 'Please enter agent name' }]}
          >
            <Input placeholder="Agent name" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <TextArea rows={2} placeholder="Agent description" />
          </Form.Item>

          <Form.Item
            name="agent_type"
            label="Type"
            rules={[{ required: true }]}
          >
            <Select disabled={!!editingAgent}>
              <Select.Option value="openai">OpenAI</Select.Option>
              <Select.Option value="mcp">MCP Server</Select.Option>
              <Select.Option value="custom">Custom</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="enabled" label="Enabled" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item
            name="config"
            label="Configuration (JSON)"
            extra="Enter configuration as JSON object"
          >
            <TextArea
              rows={6}
              placeholder='{"api_key": "...", "model": "gpt-4"}'
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`Execute Agent: ${executingAgent?.name}`}
        open={executeModalOpen}
        onOk={handleExecuteSubmit}
        onCancel={() => setExecuteModalOpen(false)}
      >
        <Form form={executeForm} layout="vertical">
          <Form.Item
            name="input_data"
            label="Input Data (JSON)"
            extra="Enter input data as JSON object"
          >
            <TextArea
              rows={6}
              placeholder='{"message": "Hello, agent!"}'
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AgentsList;
