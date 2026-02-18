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
  message,
  Popconfirm,
  Typography,
  Card,
  Transfer,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import { useAgentStore } from '@/stores';
import type { AgentGroup } from '@/types';

const { Title } = Typography;
const { TextArea } = Input;

const GroupsList: React.FC = () => {
  const {
    groups,
    agents,
    loading,
    fetchGroups,
    fetchAgents,
    createGroup,
    updateGroup,
    deleteGroup,
    executeGroup,
  } = useAgentStore();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<AgentGroup | null>(null);
  const [form] = Form.useForm();
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [executeModalOpen, setExecuteModalOpen] = useState(false);
  const [executingGroup, setExecutingGroup] = useState<AgentGroup | null>(null);
  const [executeForm] = Form.useForm();

  useEffect(() => {
    fetchGroups({ page_size: 100 });
    fetchAgents({ page_size: 100 });
  }, []);

  const handleCreate = () => {
    setEditingGroup(null);
    setSelectedAgents([]);
    form.resetFields();
    form.setFieldsValue({
      execution_mode: 'sequential',
    });
    setModalOpen(true);
  };

  const handleEdit = (group: AgentGroup) => {
    setEditingGroup(group);
    setSelectedAgents(group.members.map((m) => m.agent_id));
    form.setFieldsValue({
      name: group.name,
      description: group.description,
      execution_mode: group.execution_mode,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      const data = {
        name: values.name,
        description: values.description,
        execution_mode: values.execution_mode,
        agent_ids: selectedAgents,
      };

      if (editingGroup) {
        await updateGroup(editingGroup.id, data);
        message.success('Group updated successfully');
      } else {
        await createGroup(data);
        message.success('Group created successfully');
      }

      setModalOpen(false);
      form.resetFields();
      setSelectedAgents([]);
    } catch (error: any) {
      if (error.errorFields) return;
      message.error(error.message || 'Operation failed');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteGroup(id);
      message.success('Group deleted successfully');
    } catch (error: any) {
      message.error(error.message || 'Delete failed');
    }
  };

  const handleExecute = (group: AgentGroup) => {
    setExecutingGroup(group);
    executeForm.resetFields();
    setExecuteModalOpen(true);
  };

  const handleExecuteSubmit = async () => {
    try {
      const values = await executeForm.validateFields();
      const inputData = values.input_data
        ? JSON.parse(values.input_data)
        : undefined;

      await executeGroup(executingGroup!.id, inputData);
      message.success('Group execution started');
      setExecuteModalOpen(false);
    } catch (error: any) {
      if (error.errorFields) return;
      message.error(error.message || 'Execution failed');
    }
  };

  const agentOptions = agents.map((agent) => ({
    key: agent.id,
    title: agent.name,
  }));

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Execution Mode',
      dataIndex: 'execution_mode',
      key: 'execution_mode',
      render: (mode: string) => (
        <Tag color={mode === 'parallel' ? 'blue' : 'green'}>
          {mode.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Members',
      dataIndex: 'members',
      key: 'members',
      render: (members: any[]) => (
        <Space wrap>
          {members.map((m) => (
            <Tag key={m.agent_id}>{m.agent_name}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: AgentGroup) => (
        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            size="small"
            onClick={() => handleExecute(record)}
          >
            Execute
          </Button>
          <Button
            icon={<EditOutlined />}
            size="small"
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="Delete group?"
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
        <Title level={2}>Agent Groups</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          Create Group
        </Button>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={groups}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={editingGroup ? 'Edit Group' : 'Create Group'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: 'Please enter group name' }]}
          >
            <Input placeholder="Group name" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <TextArea rows={2} placeholder="Group description" />
          </Form.Item>

          <Form.Item name="execution_mode" label="Execution Mode">
            <Select>
              <Select.Option value="sequential">Sequential</Select.Option>
              <Select.Option value="parallel">Parallel</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label="Select Agents">
            <Transfer
              dataSource={agentOptions}
              titles={['Available Agents', 'Selected Agents']}
              targetKeys={selectedAgents}
              onChange={setSelectedAgents}
              render={(item) => item.title}
              listStyle={{ width: 280, height: 300 }}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`Execute Group: ${executingGroup?.name}`}
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
              placeholder='{"message": "Hello, agents!"}'
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default GroupsList;
