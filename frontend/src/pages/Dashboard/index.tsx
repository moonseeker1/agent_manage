import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Typography } from 'antd';
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
      console.error('加载指标失败:', error);
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
      title: '智能体名称',
      dataIndex: 'agent_name',
      key: 'agent_name',
    },
    {
      title: '执行次数',
      dataIndex: 'total_executions',
      key: 'total_executions',
    },
    {
      title: '成功率',
      dataIndex: 'success_rate',
      key: 'success_rate',
      render: (rate: number) => `${rate.toFixed(1)}%`,
    },
    {
      title: '平均耗时',
      dataIndex: 'avg_duration',
      key: 'avg_duration',
      render: (duration: number | null) =>
        duration ? `${duration.toFixed(2)}秒` : '暂无',
    },
  ];

  return (
    <div>
      <Title level={2}>控制台</Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="智能体总数"
              value={agents.length}
              prefix={<RobotOutlined />}
              suffix={<span style={{ fontSize: 14 }}>/ {enabledAgents} 启用</span>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="智能体群组"
              value={groups.length}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="运行中任务"
              value={runningExecutions}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="7天执行总数"
              value={metrics?.total_executions || 0}
              prefix={<PlayCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="每日执行量（最近7天）">
            <Column {...columnConfig} height={250} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="执行状态统计">
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="已完成"
                  value={metrics?.completed_executions || 0}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="失败"
                  value={metrics?.failed_executions || 0}
                  prefix={<CloseCircleOutlined />}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="平均耗时"
                  value={metrics?.avg_duration?.toFixed(2) || '暂无'}
                  suffix={metrics?.avg_duration ? '秒' : ''}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="智能体性能">
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
