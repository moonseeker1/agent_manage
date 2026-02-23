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
        message.success('群组更新成功');
      } else {
        await createGroup(data);
        message.success('群组创建成功');
      }

      setModalOpen(false);
      form.resetFields();
      setSelectedAgents([]);
    } catch (error: any) {
      if (error.errorFields) return;
      message.error(error.message || '操作失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteGroup(id);
      message.success('群组删除成功');
    } catch (error: any) {
      message.error(error.message || '删除失败');
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
      message.success('群组执行已启动');
      setExecuteModalOpen(false);
    } catch (error: any) {
      if (error.errorFields) return;
      message.error(error.message || '执行失败');
    }
  };

  const agentOptions = agents.map((agent) => ({
    key: agent.id,
    title: agent.name,
  }));

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '执行模式',
      dataIndex: 'execution_mode',
      key: 'execution_mode',
      render: (mode: string) => (
        <Tag color={mode === 'parallel' ? 'blue' : 'green'}>
          {mode === 'parallel' ? '并行' : '顺序'}
        </Tag>
      ),
    },
    {
      title: '成员',
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
      title: '操作',
      key: 'actions',
      render: (_: any, record: AgentGroup) => (
        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            size="small"
            onClick={() => handleExecute(record)}
          >
            执行
          </Button>
          <Button
            icon={<EditOutlined />}
            size="small"
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="确定删除此群组？"
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
        <Title level={2}>智能体群组</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          创建群组
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
        title={editingGroup ? '编辑群组' : '创建群组'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入群组名称' }]}
          >
            <Input placeholder="群组名称" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="群组描述" />
          </Form.Item>

          <Form.Item name="execution_mode" label="执行模式">
            <Select>
              <Select.Option value="sequential">顺序执行</Select.Option>
              <Select.Option value="parallel">并行执行</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label="选择智能体">
            <Transfer
              dataSource={agentOptions}
              titles={['可选智能体', '已选智能体']}
              targetKeys={selectedAgents}
              onChange={(keys) => setSelectedAgents(keys as string[])}
              render={(item) => item.title}
              listStyle={{ width: 280, height: 300 }}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`执行群组: ${executingGroup?.name}`}
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
              placeholder='{"message": "你好，智能体们！"}'
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default GroupsList;
