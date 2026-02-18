import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Typography } from 'antd';
import {
  RobotOutlined,
  TeamOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { Column } from '@ant-design/plots';
import { useAgentStore } from '@/stores';
import { metricsApi } from '@/services/api';
import type { ExecutionMetricsSummary, AgentMetricsSummary } from '@/types';

const { Title } = Typography;

const Dashboard: React.FC = () => {
  const { agents, groups, executions, fetchAgents, fetchGroups, fetchExecutions } = useAgentStore();
  const [metrics, setMetrics] = useState<ExecutionMetricsSummary | null>(null);
  const [agentMetrics, setAgentMetrics] = useState<AgentMetricsSummary[]>([]);

  useEffect(() => {
    fetchAgents({ page_size: 100 });
    fetchGroups({ page_size: 100 });
    fetchExecutions({ page_size: 100 });
    loadMetrics();
  }, []);

  const loadMetrics = async () => {
    try {
      const [execMetrics, agentMetricsData] = await Promise.all([
        metricsApi.getExecutionMetrics(7),
        metricsApi.getAllAgentMetrics(),
      ]);
      setMetrics(execMetrics);
      setAgentMetrics(agentMetricsData);
    } catch (error) {
      console.error('Failed to load metrics:', error);
    }
  };

  const runningExecutions = executions.filter((e) => e.status === 'running').length;
  const enabledAgents = agents.filter((a) => a.enabled).length;

  const columnConfig = {
    data: metrics?.executions_per_day || [],
    xField: 'date',
    yField: 'count',
    label: {
      position: 'top' as const,
    },
    xAxis: {
      label: {
        autoHide: false,
        autoRotate: false,
      },
    },
  };

  const agentColumns = [
    {
      title: 'Agent Name',
      dataIndex: 'agent_name',
      key: 'agent_name',
    },
    {
      title: 'Total Executions',
      dataIndex: 'total_executions',
      key: 'total_executions',
    },
    {
      title: 'Success Rate',
      dataIndex: 'success_rate',
      key: 'success_rate',
      render: (rate: number) => `${rate.toFixed(1)}%`,
    },
    {
      title: 'Avg Duration',
      dataIndex: 'avg_duration',
      key: 'avg_duration',
      render: (duration: number | null) =>
        duration ? `${duration.toFixed(2)}s` : 'N/A',
    },
  ];

  return (
    <div>
      <Title level={2}>Dashboard</Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Agents"
              value={agents.length}
              prefix={<RobotOutlined />}
              suffix={<span style={{ fontSize: 14 }}>/ {enabledAgents} enabled</span>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Agent Groups"
              value={groups.length}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Running Executions"
              value={runningExecutions}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Executions (7d)"
              value={metrics?.total_executions || 0}
              prefix={<PlayCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="Executions per Day (Last 7 Days)">
            <Column {...columnConfig} height={250} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Execution Status">
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="Completed"
                  value={metrics?.completed_executions || 0}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Failed"
                  value={metrics?.failed_executions || 0}
                  prefix={<CloseCircleOutlined />}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Avg Duration"
                  value={metrics?.avg_duration?.toFixed(2) || 'N/A'}
                  suffix={metrics?.avg_duration ? 's' : ''}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="Agent Performance">
            <Table
              columns={agentColumns}
              dataSource={agentMetrics}
              rowKey="agent_id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
