import React, { useEffect, useState } from 'react';
import { Table, Tag, Button, Space, Modal, Typography, Card, Descriptions } from 'antd';
import { EyeOutlined, CloseOutlined } from '@ant-design/icons';
import { useAgentStore } from '@/stores';
import type { Execution, ExecutionStatus } from '@/types';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const { Title } = Typography;

const statusColors: Record<ExecutionStatus, string> = {
  pending: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
  cancelled: 'warning',
};

const statusLabels: Record<ExecutionStatus, string> = {
  pending: '等待中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
};

const ExecutionsList: React.FC = () => {
  const { executions, loading, fetchExecutions, fetchExecution, cancelExecution } = useAgentStore();
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null);

  useEffect(() => {
    fetchExecutions({ page_size: 100 });
    // 每5秒刷新一次运行中的执行
    const interval = setInterval(() => {
      fetchExecutions({ page_size: 100 });
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleViewDetail = async (execution: Execution) => {
    await fetchExecution(execution.id);
    setSelectedExecution(execution);
    setDetailModalOpen(true);
  };

  const handleCancel = async (id: string) => {
    await cancelExecution(id);
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      render: (id: string) => id.substring(0, 8),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: ExecutionStatus) => (
        <Tag color={statusColors[status]}>{statusLabels[status]}</Tag>
      ),
    },
    {
      title: '智能体/群组',
      key: 'target',
      render: (_: any, record: Execution) => (
        <span>
          {record.agent_id ? `智能体: ${record.agent_id.substring(0, 8)}` : ''}
          {record.group_id ? `群组: ${record.group_id.substring(0, 8)}` : ''}
        </span>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).fromNow(),
    },
    {
      title: '耗时',
      dataIndex: 'duration',
      key: 'duration',
      render: (duration: number | null) =>
        duration ? `${duration.toFixed(2)}秒` : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: Execution) => (
        <Space>
          <Button
            icon={<EyeOutlined />}
            size="small"
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          {record.status === 'running' && (
            <Button
              icon={<CloseOutlined />}
              size="small"
              danger
              onClick={() => handleCancel(record.id)}
            >
              取消
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={2}>执行记录</Title>

      <Card>
        <Table
          columns={columns}
          dataSource={executions}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
        />
      </Card>

      <Modal
        title="执行详情"
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={null}
        width={800}
      >
        {selectedExecution && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="ID" span={2}>
              {selectedExecution.id}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={statusColors[selectedExecution.status]}>
                {statusLabels[selectedExecution.status]}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="耗时">
              {selectedExecution.duration
                ? `${selectedExecution.duration.toFixed(2)}秒`
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {dayjs(selectedExecution.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="开始时间">
              {selectedExecution.started_at
                ? dayjs(selectedExecution.started_at).format('YYYY-MM-DD HH:mm:ss')
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="完成时间">
              {selectedExecution.completed_at
                ? dayjs(selectedExecution.completed_at).format('YYYY-MM-DD HH:mm:ss')
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="智能体ID">
              {selectedExecution.agent_id || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="输入数据" span={2}>
              <pre style={{ margin: 0, maxHeight: 150, overflow: 'auto' }}>
                {JSON.stringify(selectedExecution.input_data, null, 2)}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="输出数据" span={2}>
              <pre style={{ margin: 0, maxHeight: 150, overflow: 'auto' }}>
                {JSON.stringify(selectedExecution.output_data, null, 2)}
              </pre>
            </Descriptions.Item>
            {selectedExecution.error_message && (
              <Descriptions.Item label="错误信息" span={2}>
                <pre style={{ margin: 0, color: 'red' }}>
                  {selectedExecution.error_message}
                </pre>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default ExecutionsList;
