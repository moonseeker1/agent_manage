import React, { useState, useEffect } from 'react';
import {
  Table,
  Card,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  message,
  Popconfirm,
  Progress,
  Drawer,
  Descriptions,
  Tooltip,
  Badge,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  SendOutlined,
  ReloadOutlined,
  StopOutlined,
  EyeOutlined,
  DeleteOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

import { commandsApi, agentsApi } from '@/services/api';
import type {
  AgentCommand,
  CommandCreate,
  CommandStatus,
  CommandStatsResponse,
} from '@/types/command';
import {
  COMMAND_TYPE_LABELS,
  COMMAND_STATUS_LABELS,
  COMMAND_STATUS_COLORS,
} from '@/types/command';
import type { Agent } from '@/types';

const CommandsPage: React.FC = () => {
  const [commands, setCommands] = useState<AgentCommand[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<CommandStatsResponse | null>(null);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });
  const [filters, setFilters] = useState<{
    agent_id?: string;
    status?: CommandStatus;
    command_type?: string;
  }>({});
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [selectedCommand, setSelectedCommand] = useState<AgentCommand | null>(null);
  const [form] = Form.useForm();

  // 加载指令列表
  const loadCommands = async () => {
    setLoading(true);
    try {
      const response = await commandsApi.list({
        ...filters,
        page: pagination.current,
        page_size: pagination.pageSize,
      });
      setCommands(response.items);
      setPagination((prev) => ({ ...prev, total: response.total }));
    } catch (error) {
      message.error('加载指令列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 加载统计数据
  const loadStats = async () => {
    try {
      const response = await commandsApi.getStats(filters.agent_id);
      setStats(response);
    } catch (error) {
      console.error('加载统计数据失败', error);
    }
  };

  // 加载 Agent 列表
  const loadAgents = async () => {
    try {
      const response = await agentsApi.list({ page_size: 100 });
      setAgents(response.items || []);
    } catch (error) {
      console.error('加载 Agent 列表失败', error);
    }
  };

  useEffect(() => {
    loadCommands();
    loadStats();
  }, [pagination.current, pagination.pageSize, filters]);

  useEffect(() => {
    loadAgents();
  }, []);

  // 创建指令
  const handleCreate = async (values: any) => {
    try {
      const data: CommandCreate = {
        type: values.command_type,
        content: values.content ? JSON.parse(values.content) : {},
        priority: values.priority || 0,
        timeout: values.timeout || 300,
      };
      await commandsApi.send(values.agent_id, data);
      message.success('指令已发送');
      setCreateModalVisible(false);
      form.resetFields();
      loadCommands();
      loadStats();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '发送指令失败');
    }
  };

  // 重试指令
  const handleRetry = async (commandId: string) => {
    try {
      await commandsApi.retry(commandId);
      message.success('指令已重新入队');
      loadCommands();
      loadStats();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '重试失败');
    }
  };

  // 取消指令
  const handleCancel = async (commandId: string) => {
    try {
      await commandsApi.cancel(commandId);
      message.success('指令已取消');
      loadCommands();
      loadStats();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '取消失败');
    }
  };

  // 查看详情
  const handleViewDetail = (command: AgentCommand) => {
    setSelectedCommand(command);
    setDetailDrawerVisible(true);
  };

  // 状态渲染
  const renderStatus = (status: CommandStatus) => {
    const icons: Record<CommandStatus, React.ReactNode> = {
      pending: <ClockCircleOutlined />,
      executing: <SyncOutlined spin />,
      success: <CheckCircleOutlined />,
      error: <ExclamationCircleOutlined />,
      timeout: <ExclamationCircleOutlined />,
      cancelled: <StopOutlined />,
    };

    return (
      <Tag icon={icons[status]} color={COMMAND_STATUS_COLORS[status]}>
        {COMMAND_STATUS_LABELS[status]}
      </Tag>
    );
  };

  const columns: ColumnsType<AgentCommand> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
      render: (id: string) => (
        <Tooltip title={id}>
          <span style={{ fontFamily: 'monospace' }}>{id.slice(0, 8)}...</span>
        </Tooltip>
      ),
    },
    {
      title: 'Agent',
      dataIndex: 'agent_id',
      key: 'agent_id',
      width: 150,
      render: (agentId: string) => {
        const agent = agents.find((a) => a.id === agentId);
        return agent?.name || agentId.slice(0, 8);
      },
    },
    {
      title: '类型',
      dataIndex: 'command_type',
      key: 'command_type',
      width: 100,
      render: (type: string) => COMMAND_TYPE_LABELS[type as keyof typeof COMMAND_TYPE_LABELS] || type,
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      sorter: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: renderStatus,
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 120,
      render: (progress: number, record: AgentCommand) => {
        if (record.status === 'executing') {
          return <Progress percent={progress} size="small" />;
        }
        return '-';
      },
    },
    {
      title: '重试',
      dataIndex: 'retry_count',
      key: 'retry_count',
      width: 80,
      render: (count: number, record: AgentCommand) => (
        <span>
          {count}/{record.max_retries}
        </span>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          {['error', 'timeout'].includes(record.status) && record.retry_count < record.max_retries && (
            <Button
              type="link"
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => handleRetry(record.id)}
            >
              重试
            </Button>
          )}
          {['pending', 'executing'].includes(record.status) && (
            <Popconfirm
              title="确定取消此指令？"
              onConfirm={() => handleCancel(record.id)}
            >
              <Button type="link" size="small" danger icon={<StopOutlined />}>
                取消
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card>
            <Statistic
              title="待处理"
              value={stats?.status_counts?.pending || 0}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="执行中"
              value={stats?.status_counts?.executing || 0}
              prefix={<SyncOutlined spin />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="成功"
              value={stats?.status_counts?.success || 0}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="失败"
              value={(stats?.status_counts?.error || 0) + (stats?.status_counts?.timeout || 0)}
              valueStyle={{ color: '#cf1322' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="队列中"
              value={stats?.pending_in_redis || 0}
              prefix={<Badge status="processing" />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="总计" value={stats?.total || 0} />
          </Card>
        </Col>
      </Row>

      {/* 主表格 */}
      <Card
        title="指令管理"
        extra={
          <Space>
            <Select
              allowClear
              placeholder="选择 Agent"
              style={{ width: 150 }}
              onChange={(value) => setFilters((f) => ({ ...f, agent_id: value }))}
            >
              {agents.map((agent) => (
                <Select.Option key={agent.id} value={agent.id}>
                  {agent.name}
                </Select.Option>
              ))}
            </Select>
            <Select
              allowClear
              placeholder="状态"
              style={{ width: 100 }}
              onChange={(value) => setFilters((f) => ({ ...f, status: value }))}
            >
              {Object.entries(COMMAND_STATUS_LABELS).map(([key, label]) => (
                <Select.Option key={key} value={key}>
                  {label}
                </Select.Option>
              ))}
            </Select>
            <Button icon={<ReloadOutlined />} onClick={() => { loadCommands(); loadStats(); }}>
              刷新
            </Button>
            <Button type="primary" icon={<SendOutlined />} onClick={() => setCreateModalVisible(true)}>
              发送指令
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={commands}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => setPagination((p) => ({ ...p, current: page, pageSize })),
          }}
        />
      </Card>

      {/* 创建指令弹窗 */}
      <Modal
        title="发送指令"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        onOk={() => form.submit()}
        width={500}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="agent_id" label="目标 Agent" rules={[{ required: true }]}>
            <Select placeholder="选择 Agent">
              {agents.map((agent) => (
                <Select.Option key={agent.id} value={agent.id}>
                  {agent.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="command_type" label="指令类型" rules={[{ required: true }]}>
            <Select placeholder="选择类型">
              <Select.Option value="task">任务</Select.Option>
              <Select.Option value="pause">暂停</Select.Option>
              <Select.Option value="cancel">取消</Select.Option>
              <Select.Option value="config_reload">重载配置</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="content" label="指令内容 (JSON)">
            <Input.TextArea rows={4} placeholder='{"command": "check logs"}' />
          </Form.Item>
          <Form.Item name="priority" label="优先级 (0-100)" initialValue={0}>
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="timeout" label="超时时间 (秒)" initialValue={300}>
            <InputNumber min={10} max={3600} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 详情抽屉 */}
      <Drawer
        title="指令详情"
        placement="right"
        width={600}
        onClose={() => setDetailDrawerVisible(false)}
        open={detailDrawerVisible}
      >
        {selectedCommand && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="ID">{selectedCommand.id}</Descriptions.Item>
            <Descriptions.Item label="Agent ID">{selectedCommand.agent_id}</Descriptions.Item>
            <Descriptions.Item label="类型">
              {COMMAND_TYPE_LABELS[selectedCommand.command_type as keyof typeof COMMAND_TYPE_LABELS]}
            </Descriptions.Item>
            <Descriptions.Item label="状态">{renderStatus(selectedCommand.status)}</Descriptions.Item>
            <Descriptions.Item label="优先级">{selectedCommand.priority}</Descriptions.Item>
            <Descriptions.Item label="超时">{selectedCommand.timeout} 秒</Descriptions.Item>
            <Descriptions.Item label="进度">
              {selectedCommand.status === 'executing' ? (
                <Progress percent={selectedCommand.progress} />
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="内容">
              <pre>{JSON.stringify(selectedCommand.content, null, 2)}</pre>
            </Descriptions.Item>
            <Descriptions.Item label="输出">
              {selectedCommand.output ? (
                <pre style={{ maxHeight: 200, overflow: 'auto' }}>{selectedCommand.output}</pre>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="错误信息">
              {selectedCommand.error_message ? (
                <span style={{ color: 'red' }}>{selectedCommand.error_message}</span>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="重试次数">
              {selectedCommand.retry_count} / {selectedCommand.max_retries}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {new Date(selectedCommand.created_at).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="开始时间">
              {selectedCommand.started_at ? new Date(selectedCommand.started_at).toLocaleString() : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="完成时间">
              {selectedCommand.completed_at ? new Date(selectedCommand.completed_at).toLocaleString() : '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default CommandsPage;
