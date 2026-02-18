import React, { useEffect, useState } from 'react';
import { Table, Tag, Button, Space, Modal, Typography, Card, Descriptions } from 'antd';
import { EyeOutlined, CloseOutlined } from '@ant-design/icons';
import { useAgentStore } from '@/stores';
import type { Execution, ExecutionStatus } from '@/types';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

const { Title } = Typography;

const statusColors: Record<ExecutionStatus, string> = {
  pending: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
  cancelled: 'warning',
};

const ExecutionsList: React.FC = () => {
  const { executions, loading, fetchExecutions, fetchExecution, cancelExecution } = useAgentStore();
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null);

  useEffect(() => {
    fetchExecutions({ page_size: 100 });
    // Refresh every 5 seconds for running executions
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
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: ExecutionStatus) => (
        <Tag color={statusColors[status]}>{status.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Agent/Group',
      key: 'target',
      render: (_: any, record: Execution) => (
        <span>
          {record.agent_id ? `Agent: ${record.agent_id.substring(0, 8)}` : ''}
          {record.group_id ? `Group: ${record.group_id.substring(0, 8)}` : ''}
        </span>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).fromNow(),
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
      render: (duration: number | null) =>
        duration ? `${duration.toFixed(2)}s` : '-',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: Execution) => (
        <Space>
          <Button
            icon={<EyeOutlined />}
            size="small"
            onClick={() => handleViewDetail(record)}
          >
            Detail
          </Button>
          {record.status === 'running' && (
            <Button
              icon={<CloseOutlined />}
              size="small"
              danger
              onClick={() => handleCancel(record.id)}
            >
              Cancel
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={2}>Executions</Title>

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
        title="Execution Detail"
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
            <Descriptions.Item label="Status">
              <Tag color={statusColors[selectedExecution.status]}>
                {selectedExecution.status.toUpperCase()}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Duration">
              {selectedExecution.duration
                ? `${selectedExecution.duration.toFixed(2)}s`
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Created">
              {dayjs(selectedExecution.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="Started">
              {selectedExecution.started_at
                ? dayjs(selectedExecution.started_at).format('YYYY-MM-DD HH:mm:ss')
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Completed">
              {selectedExecution.completed_at
                ? dayjs(selectedExecution.completed_at).format('YYYY-MM-DD HH:mm:ss')
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Agent ID">
              {selectedExecution.agent_id || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Input Data" span={2}>
              <pre style={{ margin: 0, maxHeight: 150, overflow: 'auto' }}>
                {JSON.stringify(selectedExecution.input_data, null, 2)}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="Output Data" span={2}>
              <pre style={{ margin: 0, maxHeight: 150, overflow: 'auto' }}>
                {JSON.stringify(selectedExecution.output_data, null, 2)}
              </pre>
            </Descriptions.Item>
            {selectedExecution.error_message && (
              <Descriptions.Item label="Error" span={2}>
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
