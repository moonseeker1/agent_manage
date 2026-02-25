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
  Switch,
  Tooltip,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SyncOutlined,
  ApiOutlined,
  ToolOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { mcpServersApi } from '@/services/api';
import type { MCPServer, MCPTool } from '@/types/mcp';

const { Title, Text } = Typography;
const { TextArea } = Input;

const MCPServersPage: React.FC = () => {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [toolsModalOpen, setToolsModalOpen] = useState(false);
  const [editingServer, setEditingServer] = useState<MCPServer | null>(null);
  const [selectedServer, setSelectedServer] = useState<MCPServer | null>(null);
  const [serverTools, setServerTools] = useState<MCPTool[]>([]);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [form] = Form.useForm();
  const [serverTypes, setServerTypes] = useState<{value: string, label: string}[]>([]);

  useEffect(() => {
    loadServers();
    loadServerTypes();
  }, []);

  const loadServers = async () => {
    setLoading(true);
    try {
      const data = await mcpServersApi.list({ page: 1, page_size: 100 });
      setServers(data.items || []);
    } catch (error) {
      message.error('加载MCP服务器列表失败');
    } finally {
      setLoading(false);
    }
  };

  const loadServerTypes = async () => {
    try {
      const types = await mcpServersApi.getTypes();
      setServerTypes(types);
    } catch (error) {
      console.error('加载服务器类型失败', error);
    }
  };

  const handleCreate = () => {
    setEditingServer(null);
    form.resetFields();
    form.setFieldsValue({ server_type: 'stdio', enabled: true, args: [], env: {} });
    setModalOpen(true);
  };

  const handleEdit = (server: MCPServer) => {
    setEditingServer(server);
    form.setFieldsValue({
      ...server,
      args: server.args?.join('\n') || '',
      env: JSON.stringify(server.env || {}, null, 2),
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      // Parse args and env
      const submitData = {
        ...values,
        args: values.args ? values.args.split('\n').filter((a: string) => a.trim()) : [],
        env: values.env ? JSON.parse(values.env) : {},
      };

      if (editingServer) {
        await mcpServersApi.update(editingServer.id, submitData);
        message.success('更新成功');
      } else {
        await mcpServersApi.create(submitData);
        message.success('创建成功');
      }

      setModalOpen(false);
      loadServers();
    } catch (error: any) {
      if (error.message) {
        message.error(error.message);
      }
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await mcpServersApi.delete(id);
      message.success('删除成功');
      loadServers();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleSync = async (server: MCPServer) => {
    setSyncing(server.id);
    try {
      const result = await mcpServersApi.sync(server.id);
      if (result.error) {
        message.error(`同步失败: ${result.error}`);
      } else {
        message.success(`同步成功，发现 ${result.tools_count} 个工具`);
        loadServers();
      }
    } catch (error: any) {
      message.error(`同步失败: ${error.message}`);
    } finally {
      setSyncing(null);
    }
  };

  const handleViewTools = async (server: MCPServer) => {
    setSelectedServer(server);
    try {
      const tools = await mcpServersApi.getTools(server.id);
      setServerTools(tools);
    } catch (error) {
      setServerTools([]);
    }
    setToolsModalOpen(true);
  };

  const handleToggleTool = async (toolId: string, enabled: boolean) => {
    try {
      await mcpServersApi.toggleTool(toolId, enabled);
      message.success(enabled ? '已启用工具' : '已禁用工具');
      // Refresh tools
      if (selectedServer) {
        const tools = await mcpServersApi.getTools(selectedServer.id);
        setServerTools(tools);
      }
    } catch (error) {
      message.error('操作失败');
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: MCPServer) => (
        <Space>
          <ApiOutlined />
          <span>{name}</span>
          {record.enabled ? (
            <Tag color="green">启用</Tag>
          ) : (
            <Tag color="red">禁用</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      render: (code: string) => <Tag color="blue">{code}</Tag>,
    },
    {
      title: '类型',
      dataIndex: 'server_type',
      key: 'server_type',
      render: (type: string) => {
        const typeMap: Record<string, { color: string; label: string }> = {
          stdio: { color: 'purple', label: 'STDIO' },
          sse: { color: 'cyan', label: 'SSE' },
          http: { color: 'orange', label: 'HTTP' },
        };
        const config = typeMap[type] || { color: 'default', label: type };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '连接信息',
      key: 'connection',
      render: (_: any, record: MCPServer) => (
        <Text code ellipsis style={{ maxWidth: 200 }}>
          {record.server_type === 'stdio' ? record.command : record.url}
        </Text>
      ),
    },
    {
      title: '工具数量',
      key: 'tools_count',
      render: (_: any, record: MCPServer) => {
        const count = record.tools?.length || record.tools_cache?.length || 0;
        return (
          <Badge count={count} showZero color="blue">
            <Button
              icon={<ToolOutlined />}
              size="small"
              onClick={() => handleViewTools(record)}
            >
              工具
            </Button>
          </Badge>
        );
      },
    },
    {
      title: '同步状态',
      key: 'sync_status',
      render: (_: any, record: MCPServer) => {
        if (record.sync_error) {
          return (
            <Tooltip title={record.sync_error}>
              <ExclamationCircleOutlined style={{ color: 'red' }} />
            </Tooltip>
          );
        }
        if (record.last_sync_at) {
          return (
            <Tooltip title={`最后同步: ${new Date(record.last_sync_at).toLocaleString()}`}>
              <CheckCircleOutlined style={{ color: 'green' }} />
            </Tooltip>
          );
        }
        return <Text type="secondary">未同步</Text>;
      },
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: MCPServer) => (
        <Space>
          <Tooltip title="同步工具">
            <Button
              icon={<SyncOutlined spin={syncing === record.id} />}
              size="small"
              onClick={() => handleSync(record)}
              loading={syncing === record.id}
            />
          </Tooltip>
          <Button
            icon={<EditOutlined />}
            size="small"
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="确定要删除此MCP服务器吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button icon={<DeleteOutlined />} size="small" danger />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const toolColumns = [
    {
      title: '工具名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => <Tag color="geekblue">{name}</Tag>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      render: (enabled: boolean, record: MCPTool) => (
        <Switch
          checked={enabled}
          onChange={(checked) => handleToggleTool(record.id, checked)}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <Title level={4} style={{ margin: 0 }}>
            <ApiOutlined /> MCP服务器管理
          </Title>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            添加服务器
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={servers}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* 创建/编辑服务器弹窗 */}
      <Modal
        title={editingServer ? '编辑MCP服务器' : '添加MCP服务器'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width={600}
        okText="确定"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="服务器名称"
            rules={[{ required: true, message: '请输入服务器名称' }]}
          >
            <Input placeholder="例如：Agent Manager" />
          </Form.Item>

          <Form.Item
            name="code"
            label="服务器代码"
            rules={[
              { required: true, message: '请输入服务器代码' },
              { pattern: /^[a-z][a-z0-9_]*$/, message: '只能包含小写字母、数字和下划线，以字母开头' },
            ]}
          >
            <Input placeholder="例如：agent_manager" disabled={!!editingServer} />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="服务器描述" />
          </Form.Item>

          <Form.Item
            name="server_type"
            label="连接类型"
            rules={[{ required: true, message: '请选择连接类型' }]}
          >
            <Select options={serverTypes} />
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prev, curr) => prev.server_type !== curr.server_type}
          >
            {({ getFieldValue }) => {
              const type = getFieldValue('server_type');
              if (type === 'stdio') {
                return (
                  <>
                    <Form.Item
                      name="command"
                      label="执行命令"
                      rules={[{ required: true, message: '请输入执行命令' }]}
                    >
                      <Input placeholder="例如：python3 或 /path/to/executable" />
                    </Form.Item>
                    <Form.Item name="args" label="命令参数（每行一个）">
                      <TextArea
                        rows={3}
                        placeholder={'例如：\n/path/to/script.py\n--config\nconfig.json'}
                      />
                    </Form.Item>
                  </>
                );
              } else {
                return (
                  <Form.Item
                    name="url"
                    label="服务器URL"
                    rules={[{ required: true, message: '请输入服务器URL' }]}
                  >
                    <Input placeholder="例如：http://localhost:8080/mcp" />
                  </Form.Item>
                );
              }
            }}
          </Form.Item>

          <Form.Item name="env" label="环境变量（JSON格式）">
            <TextArea
              rows={3}
              placeholder={'例如：\n{\n  "API_KEY": "xxx",\n  "DEBUG": "true"\n}'}
            />
          </Form.Item>

          <Form.Item name="enabled" label="启用状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 查看工具弹窗 */}
      <Modal
        title={
          <Space>
            <ToolOutlined />
            {selectedServer?.name} - 工具列表
          </Space>
        }
        open={toolsModalOpen}
        onCancel={() => setToolsModalOpen(false)}
        footer={null}
        width={700}
      >
        <Table
          columns={toolColumns}
          dataSource={serverTools}
          rowKey="id"
          pagination={false}
          size="small"
          locale={{ emptyText: '暂无工具，请先同步' }}
        />
      </Modal>
    </div>
  );
};

export default MCPServersPage;
