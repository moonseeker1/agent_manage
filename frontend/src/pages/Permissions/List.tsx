import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
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
  Transfer,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  KeyOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { permissionsApi, rolesApi } from '@/services/api';

const { Title } = Typography;
const { TextArea } = Input;

interface Permission {
  id: string;
  name: string;
  code: string;
  description: string;
  resource: string;
  action: string;
  created_at: string;
}

interface Role {
  id: string;
  name: string;
  code: string;
  description: string;
  is_system: boolean;
  is_active: boolean;
  permissions: Permission[];
  created_at: string;
}

const PermissionsPage: React.FC = () => {
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(false);

  // 权限弹窗
  const [permModalOpen, setPermModalOpen] = useState(false);
  const [editingPerm, setEditingPerm] = useState<Permission | null>(null);
  const [permForm] = Form.useForm();

  // 角色弹窗
  const [roleModalOpen, setRoleModalOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [roleForm] = Form.useForm();
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<string[]>([]);

  useEffect(() => {
    loadPermissions();
    loadRoles();
  }, []);

  const loadPermissions = async () => {
    try {
      const data = await permissionsApi.list();
      setPermissions(data);
    } catch (error) {
      message.error('加载权限列表失败');
    }
  };

  const loadRoles = async () => {
    setLoading(true);
    try {
      const data = await rolesApi.list({ page_size: 100 });
      setRoles(data.items || []);
    } catch (error) {
      message.error('加载角色列表失败');
    }
    setLoading(false);
  };

  // ============== 权限管理 ==============

  const handleCreatePerm = () => {
    setEditingPerm(null);
    permForm.resetFields();
    setPermModalOpen(true);
  };

  const handleEditPerm = (perm: Permission) => {
    setEditingPerm(perm);
    permForm.setFieldsValue(perm);
    setPermModalOpen(true);
  };

  const handleSubmitPerm = async () => {
    try {
      const values = await permForm.validateFields();

      if (editingPerm) {
        await permissionsApi.update(editingPerm.id, values);
        message.success('权限更新成功');
      } else {
        await permissionsApi.create(values);
        message.success('权限创建成功');
      }

      setPermModalOpen(false);
      permForm.resetFields();
      loadPermissions();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleDeletePerm = async (id: string) => {
    try {
      await permissionsApi.delete(id);
      message.success('权限删除成功');
      loadPermissions();
    } catch (error) {
      message.error('删除失败');
    }
  };

  // ============== 角色管理 ==============

  const handleCreateRole = () => {
    setEditingRole(null);
    setSelectedPermissionIds([]);
    roleForm.resetFields();
    roleForm.setFieldsValue({ is_active: true });
    setRoleModalOpen(true);
  };

  const handleEditRole = (role: Role) => {
    setEditingRole(role);
    setSelectedPermissionIds(role.permissions?.map(p => p.id) || []);
    roleForm.setFieldsValue(role);
    setRoleModalOpen(true);
  };

  const handleSubmitRole = async () => {
    try {
      const values = await roleForm.validateFields();
      const data = {
        ...values,
        permission_ids: selectedPermissionIds,
      };

      if (editingRole) {
        await rolesApi.update(editingRole.id, data);
        message.success('角色更新成功');
      } else {
        await rolesApi.create(data);
        message.success('角色创建成功');
      }

      setRoleModalOpen(false);
      roleForm.resetFields();
      setSelectedPermissionIds([]);
      loadRoles();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleDeleteRole = async (id: string) => {
    try {
      await rolesApi.delete(id);
      message.success('角色删除成功');
      loadRoles();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const permissionColumns = [
    {
      title: '权限名称',
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
      title: '资源',
      dataIndex: 'resource',
      key: 'resource',
      render: (resource: string) => <Tag color="geekblue">{resource}</Tag>,
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      render: (action: string) => <Tag color="orange">{action}</Tag>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: Permission) => (
        <Space>
          <Button
            icon={<EditOutlined />}
            size="small"
            onClick={() => handleEditPerm(record)}
          />
          <Popconfirm
            title="确定删除此权限？"
            onConfirm={() => handleDeletePerm(record.id)}
          >
            <Button icon={<DeleteOutlined />} size="small" danger />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const roleColumns = [
    {
      title: '角色名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Role) => (
        <Space>
          {name}
          {record.is_system && <Tag color="purple">系统</Tag>}
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
      title: '权限数量',
      key: 'perm_count',
      render: (_: any, record: Role) => (
        <Tag color="green">{record.permissions?.length || 0} 个权限</Tag>
      ),
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
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: Role) => (
        <Space>
          <Button
            icon={<EditOutlined />}
            size="small"
            onClick={() => handleEditRole(record)}
            disabled={record.is_system}
          >
            编辑
          </Button>
          {!record.is_system && (
            <Popconfirm
              title="确定删除此角色？"
              onConfirm={() => handleDeleteRole(record.id)}
            >
              <Button icon={<DeleteOutlined />} size="small" danger />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  const permissionOptions = permissions.map(p => ({
    key: p.id,
    title: `${p.name} (${p.code})`,
  }));

  return (
    <div>
      <Title level={2}>权限管理</Title>

      <Row gutter={16}>
        {/* 权限列表 */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <KeyOutlined />
                <span>权限列表</span>
              </Space>
            }
            extra={
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreatePerm}>
                创建权限
              </Button>
            }
            style={{ marginBottom: 16 }}
          >
            <Table
              columns={permissionColumns}
              dataSource={permissions}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10 }}
              size="small"
            />
          </Card>
        </Col>

        {/* 角色列表 */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <TeamOutlined />
                <span>角色列表</span>
              </Space>
            }
            extra={
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateRole}>
                创建角色
              </Button>
            }
          >
            <Table
              columns={roleColumns}
              dataSource={roles}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10 }}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      {/* 创建/编辑权限弹窗 */}
      <Modal
        title={editingPerm ? '编辑权限' : '创建权限'}
        open={permModalOpen}
        onOk={handleSubmitPerm}
        onCancel={() => setPermModalOpen(false)}
        width={500}
      >
        <Form form={permForm} layout="vertical">
          <Form.Item
            name="name"
            label="权限名称"
            rules={[{ required: true, message: '请输入权限名称' }]}
          >
            <Input placeholder="如：创建智能体" />
          </Form.Item>

          <Form.Item
            name="code"
            label="权限代码"
            rules={[{ required: true, message: '请输入权限代码' }]}
            extra="格式：resource:action，如 agent:create"
          >
            <Input placeholder="agent:create" />
          </Form.Item>

          <Form.Item name="resource" label="资源">
            <Select placeholder="选择资源类型">
              <Select.Option value="agent">智能体</Select.Option>
              <Select.Option value="skill">技能</Select.Option>
              <Select.Option value="role">角色</Select.Option>
              <Select.Option value="permission">权限</Select.Option>
              <Select.Option value="execution">执行</Select.Option>
              <Select.Option value="user">用户</Select.Option>
              <Select.Option value="system">系统</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="action" label="操作">
            <Select placeholder="选择操作类型">
              <Select.Option value="create">创建</Select.Option>
              <Select.Option value="read">查看</Select.Option>
              <Select.Option value="update">更新</Select.Option>
              <Select.Option value="delete">删除</Select.Option>
              <Select.Option value="execute">执行</Select.Option>
              <Select.Option value="manage">管理</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="权限描述" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 创建/编辑角色弹窗 */}
      <Modal
        title={editingRole ? '编辑角色' : '创建角色'}
        open={roleModalOpen}
        onOk={handleSubmitRole}
        onCancel={() => setRoleModalOpen(false)}
        width={700}
      >
        <Form form={roleForm} layout="vertical">
          <Form.Item
            name="name"
            label="角色名称"
            rules={[{ required: true, message: '请输入角色名称' }]}
          >
            <Input placeholder="如：开发者" />
          </Form.Item>

          <Form.Item
            name="code"
            label="角色代码"
            rules={[{ required: true, message: '请输入角色代码' }]}
            extra="唯一标识，如：developer"
          >
            <Input placeholder="developer" disabled={!!editingRole} />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="角色描述" />
          </Form.Item>

          <Form.Item label="分配权限">
            <Transfer
              dataSource={permissionOptions}
              titles={['可用权限', '已分配权限']}
              targetKeys={selectedPermissionIds}
              onChange={(keys) => setSelectedPermissionIds(keys as string[])}
              render={(item) => item.title}
              listStyle={{ width: 280, height: 300 }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default PermissionsPage;
