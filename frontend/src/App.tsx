import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { MainLayout } from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import { AgentsList } from '@/pages/Agents';
import { GroupsList } from '@/pages/Groups';
import { ExecutionsList } from '@/pages/Executions';
import Monitor from '@/pages/Monitor';
import Login from '@/pages/Login';
import SkillsList from '@/pages/Skills/List';
import PermissionsPage from '@/pages/Permissions/List';
import MCPServersPage from '@/pages/MCP/List';
import { useAuthStore } from '@/stores/authStore';

// Protected Route component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <ConfigProvider locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#1890ff',
        },
      }}
    >
      <BrowserRouter basename="/agent">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <MainLayout>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/agents" element={<AgentsList />} />
                    <Route path="/groups" element={<GroupsList />} />
                    <Route path="/executions" element={<ExecutionsList />} />
                    <Route path="/monitor" element={<Monitor />} />
                    <Route path="/skills" element={<SkillsList />} />
                    <Route path="/permissions" element={<PermissionsPage />} />
                    <Route path="/mcp" element={<MCPServersPage />} />
                  </Routes>
                </MainLayout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
