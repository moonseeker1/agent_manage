import React, { useState, useRef } from 'react';
import { Layout, Menu, theme, Dropdown, Avatar, Space, Button, Upload, message } from 'antd';
import {
  DashboardOutlined,
  RobotOutlined,
  TeamOutlined,
  PlayCircleOutlined,
  MonitorOutlined,
  UserOutlined,
  LogoutOutlined,
  DownloadOutlined,
  UploadOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { configApi } from '@/services/api';

const { Sider, Content, Header } = Layout;

interface MainLayoutProps {
  children: React.ReactNode;
}

const menuItems = [
  {
    key: '/',
    icon: <DashboardOutlined />,
    label: 'Dashboard',
  },
  {
    key: '/agents',
    icon: <RobotOutlined />,
    label: 'Agents',
  },
  {
    key: '/groups',
    icon: <TeamOutlined />,
    label: 'Groups',
  },
  {
    key: '/executions',
    icon: <PlayCircleOutlined />,
    label: 'Executions',
  },
  {
    key: '/monitor',
    icon: <MonitorOutlined />,
    label: 'Monitor',
  },
];

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleExport = async () => {
    try {
      const config = await configApi.export();
      const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'agent_config.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      message.success('Configuration exported successfully');
    } catch (error) {
      message.error('Failed to export configuration');
    }
  };

  const handleImport = async (file: File) => {
    try {
      const result = await configApi.import(file);
      message.success(
        `Import completed: ${result.agents_created} agents, ${result.groups_created} groups created`
      );
      if (result.errors.length > 0) {
        message.warning(`${result.errors.length} errors occurred during import`);
      }
      window.location.reload();
    } catch (error) {
      message.error('Failed to import configuration');
    }
  };

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: user?.username || 'User',
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'export',
      icon: <DownloadOutlined />,
      label: 'Export Config',
      onClick: handleExport,
    },
    {
      key: 'import',
      icon: <UploadOutlined />,
      label: 'Import Config',
      onClick: () => fileInputRef.current?.click(),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
      onClick: handleLogout,
      danger: true,
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: 'none' }}
        accept=".json"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            handleImport(file);
          }
        }}
      />
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={(value) => setCollapsed(value)}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div
          style={{
            height: 32,
            margin: 16,
            background: 'rgba(255, 255, 255, 0.2)',
            borderRadius: borderRadiusLG,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 'bold',
          }}
        >
          {collapsed ? 'AM' : 'Agent Manager'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.2s' }}>
        <Header
          style={{
            padding: '0 24px',
            background: colorBgContainer,
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
          }}
        >
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Space style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
              <span>{user?.username}</span>
            </Space>
          </Dropdown>
        </Header>
        <Content style={{ margin: '24px 16px 0', overflow: 'initial' }}>
          <div
            style={{
              padding: 24,
              background: colorBgContainer,
              borderRadius: borderRadiusLG,
              minHeight: 'calc(100vh - 112px)',
            }}
          >
            {children}
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
