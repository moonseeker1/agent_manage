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
    label: '仪表盘',
  },
  {
    key: '/agents',
    icon: <RobotOutlined />,
    label: '智能体管理',
  },
  {
    key: '/groups',
    icon: <TeamOutlined />,
    label: '智能体群组',
  },
  {
    key: '/executions',
    icon: <PlayCircleOutlined />,
    label: '执行记录',
  },
  {
    key: '/monitor',
    icon: <MonitorOutlined />,
    label: '实时监控',
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
      message.success('配置导出成功');
    } catch (error) {
      message.error('配置导出失败');
    }
  };

  const handleImport = async (file: File) => {
    try {
      const result = await configApi.import(file);
      message.success(
        `导入完成: 创建了 ${result.agents_created} 个智能体, ${result.groups_created} 个群组`
      );
      if (result.errors.length > 0) {
        message.warning(`导入过程中发生 ${result.errors.length} 个错误`);
      }
      window.location.reload();
    } catch (error) {
      message.error('配置导入失败');
    }
  };

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: user?.username || '用户',
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'export',
      icon: <DownloadOutlined />,
      label: '导出配置',
      onClick: handleExport,
    },
    {
      key: 'import',
      icon: <UploadOutlined />,
      label: '导入配置',
      onClick: () => fileInputRef.current?.click(),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
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
          {collapsed ? '智' : '智能体管理'}
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
