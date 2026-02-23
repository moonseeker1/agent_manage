import React, { useEffect, useState, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Typography,
  Tag,
  List,
  Input,
  Button,
  Space,
  Select,
  message,
} from 'antd';
import { SendOutlined, ClearOutlined } from '@ant-design/icons';
import { useAgentStore } from '@/stores';
import { wsService } from '@/services/websocket';
import type { Execution, ExecutionStatus } from '@/types';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { TextArea } = Input;

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

const Monitor: React.FC = () => {
  const { executions, agents, fetchExecutions, fetchAgents } = useAgentStore();
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [testInput, setTestInput] = useState('');
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchExecutions({ page_size: 50, status: 'running' });
    fetchAgents({ page_size: 100 });

    // 连接 WebSocket
    wsService.connect();

    // 订阅更新
    const unsubUpdate = wsService.subscribe('execution_update', (data) => {
      message.info(`执行 ${data.execution_id}: ${data.status}`);
      fetchExecutions({ page_size: 50 });
    });

    const unsubLog = wsService.subscribe('log_update', (data) => {
      if (selectedExecutionId === data.execution_id) {
        setLogs((prev) => [...prev, data.log]);
      }
    });

    return () => {
      unsubUpdate();
      unsubLog();
      wsService.disconnect();
    };
  }, [selectedExecutionId]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleSelectExecution = (executionId: string) => {
    setSelectedExecutionId(executionId);
    wsService.connectToExecution(executionId);
    // 加载已有日志
    setLogs([]);
  };

  const handleClearLogs = () => {
    setLogs([]);
  };

  const handleTestAgent = async () => {
    if (!selectedAgentId || !testInput.trim()) {
      message.warning('请选择智能体并输入内容');
      return;
    }

    try {
      const { executeAgent } = useAgentStore.getState();
      const execution = await executeAgent(selectedAgentId, { message: testInput });
      handleSelectExecution(execution.id);
      setTestInput('');
      message.success('执行已启动');
    } catch (error: any) {
      message.error(error.message || '启动执行失败');
    }
  };

  const runningExecutions = executions.filter((e) => e.status === 'running');

  return (
    <div>
      <Title level={2}>实时监控</Title>

      <Row gutter={16}>
        <Col xs={24} lg={8}>
          <Card title="运行中的任务" style={{ marginBottom: 16 }}>
            <List
              dataSource={runningExecutions}
              renderItem={(item: Execution) => (
                <List.Item
                  onClick={() => handleSelectExecution(item.id)}
                  style={{
                    cursor: 'pointer',
                    backgroundColor:
                      selectedExecutionId === item.id ? '#f0f0f0' : 'transparent',
                  }}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        <Text code>{item.id.substring(0, 8)}</Text>
                        <Tag color={statusColors[item.status]}>
                          {statusLabels[item.status]}
                        </Tag>
                      </Space>
                    }
                    description={dayjs(item.created_at).format('HH:mm:ss')}
                  />
                </List.Item>
              )}
              locale={{ emptyText: '暂无运行中的任务' }}
            />
          </Card>

          <Card title="快速测试">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Select
                placeholder="选择智能体"
                style={{ width: '100%' }}
                onChange={setSelectedAgentId}
                value={selectedAgentId}
              >
                {agents
                  .filter((a) => a.enabled)
                  .map((agent) => (
                    <Select.Option key={agent.id} value={agent.id}>
                      {agent.name} ({agent.agent_type})
                    </Select.Option>
                  ))}
              </Select>
              <TextArea
                rows={4}
                placeholder="输入测试消息..."
                value={testInput}
                onChange={(e) => setTestInput(e.target.value)}
              />
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleTestAgent}
                block
              >
                执行
              </Button>
            </Space>
          </Card>
        </Col>

        <Col xs={24} lg={16}>
          <Card
            title={
              <Space>
                <span>执行日志</span>
                {selectedExecutionId && (
                  <Text code>{selectedExecutionId.substring(0, 8)}</Text>
                )}
              </Space>
            }
            extra={
              <Button icon={<ClearOutlined />} onClick={handleClearLogs}>
                清空
              </Button>
            }
          >
            <div
              style={{
                height: 500,
                overflow: 'auto',
                backgroundColor: '#1e1e1e',
                padding: 16,
                borderRadius: 4,
                fontFamily: 'monospace',
              }}
            >
              {logs.length === 0 ? (
                <Text style={{ color: '#666' }}>
                  选择一个执行任务查看日志...
                </Text>
              ) : (
                logs.map((log, index) => (
                  <div
                    key={index}
                    style={{
                      marginBottom: 4,
                      color:
                        log.level === 'error'
                          ? '#ff4d4f'
                          : log.level === 'warning'
                          ? '#faad14'
                          : '#52c41a',
                    }}
                  >
                    <span style={{ color: '#666', marginRight: 8 }}>
                      [{dayjs(log.created_at).format('HH:mm:ss')}]
                    </span>
                    <span style={{ marginRight: 8 }}>[{log.level.toUpperCase()}]</span>
                    <span>{log.message}</span>
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Monitor;
