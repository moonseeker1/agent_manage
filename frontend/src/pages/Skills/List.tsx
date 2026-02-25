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
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { skillsApi, agentsApi } from '@/services/api';
import type { Skill, Agent } from '@/types';

const { Title } = Typography;
const { TextArea } = Input;

const SkillsList: React.FC = () => {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [bindModalOpen, setBindModalOpen] = useState(false);
  const [editingSkill, setEditingSkill] = useState<Skill | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [form] = Form.useForm();
  const [bindForm] = Form.useForm();

  useEffect(() => {
    loadSkills();
    loadAgents();
  }, []);

  const loadSkills = async () => {
    setLoading(true);
    try {
      const data = await skillsApi.list();
      setSkills(data.items || []);
    } catch (error) {
      message.error('加载技能列表失败');
    }
    setLoading(false);
  };

  const loadAgents = async () => {
    try {
      const data = await agentsApi.list();
      setAgents(data.items || []);
    } catch (error) {
      console.error('加载智能体列表失败', error);
    }
  };

  const handleCreate = () => {
    setEditingSkill(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true });
    setModalOpen(true);
  };

  const handleEdit = (skill: Skill) => {
    setEditingSkill(skill);
    form.setFieldsValue(skill);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (editingSkill) {
        await skillsApi.update(editingSkill.id, values);
        message.success('技能更新成功');
      } else {
        await skillsApi.create(values);
        message.success('技能创建成功');
      }

      setModalOpen(false);
      form.resetFields();
      loadSkills();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await skillsApi.delete(id);
      message.success('技能删除成功');
      loadSkills();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleBindModal = (skill: Skill) => {
    setSelectedSkill(skill);
    bindForm.resetFields();
    setBindModalOpen(true);
  };

  const handleBindSkill = async () => {
    try {
      const values = await bindForm.validateFields();
      await skillsApi.bindToAgent(values.agent_id, selectedSkill!.id, {
        agent_id: values.agent_id,
        skill_id: selectedSkill!.id,
        priority: values.priority || 100,
        config: values.config || {},
      });
      message.success('技能绑定成功');
      setBindModalOpen(false);
      bindForm.resetFields();
    } catch (error: any) {
      message.error(error.message || '绑定失败');
    }
  };

  const columns = [
    {
      title: '技能名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      render: (code: string) => <Tag color="blue">{code}</Tag>,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => category || '-',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>
          {active ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: Skill) => (
        <Space>
          <Button
            icon={<LinkOutlined />}
            size="small"
            onClick={() => handleBindModal(record)}
          >
            绑定
          </Button>
          <Button
            icon={<EditOutlined />}
            size="small"
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="确定删除此技能？"
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
        <Title level={2}>技能管理</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          创建技能
        </Button>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={skills}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* 创建/编辑技能弹窗 */}
      <Modal
        title={editingSkill ? '编辑技能' : '创建技能'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="技能名称"
            rules={[{ required: true, message: '请输入技能名称' }]}
          >
            <Input placeholder="如：代码生成" />
          </Form.Item>

          <Form.Item
            name="code"
            label="技能代码"
            rules={[{ required: true, message: '请输入技能代码' }]}
            extra="唯一标识，如：code_generation"
          >
            <Input placeholder="code_generation" disabled={!!editingSkill} />
          </Form.Item>

          <Form.Item name="category" label="分类">
            <Select placeholder="选择分类" allowClear>
              <Select.Option value="开发">开发</Select.Option>
              <Select.Option value="分析">分析</Select.Option>
              <Select.Option value="系统">系统</Select.Option>
              <Select.Option value="集成">集成</Select.Option>
              <Select.Option value="其他">其他</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="技能描述" />
          </Form.Item>

          <Form.Item name="config" label="配置（JSON格式）">
            <TextArea rows={4} placeholder='{"max_tokens": 4096}' />
          </Form.Item>
        </Form>
      </Modal>

      {/* 绑定到智能体弹窗 */}
      <Modal
        title={`绑定技能: ${selectedSkill?.name}`}
        open={bindModalOpen}
        onOk={handleBindSkill}
        onCancel={() => setBindModalOpen(false)}
        width={500}
      >
        <Form form={bindForm} layout="vertical">
          <Form.Item
            name="agent_id"
            label="选择智能体"
            rules={[{ required: true, message: '请选择智能体' }]}
          >
            <Select placeholder="选择要绑定到的智能体">
              {agents.filter(a => a.enabled).map(agent => (
                <Select.Option key={agent.id} value={agent.id}>
                  {agent.name} ({agent.agent_type})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="priority"
            label="优先级"
            extra="数字越小优先级越高"
            initialValue={100}
          >
            <Input type="number" placeholder="100" />
          </Form.Item>

          <Form.Item name="config" label="绑定配置（JSON格式）">
            <TextArea rows={3} placeholder='{"max_rows": 1000}' />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SkillsList;
