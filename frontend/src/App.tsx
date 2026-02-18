import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { MainLayout } from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import { AgentsList } from '@/pages/Agents';
import { GroupsList } from '@/pages/Groups';
import { ExecutionsList } from '@/pages/Executions';
import Monitor from '@/pages/Monitor';

const App: React.FC = () => {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1890ff',
        },
      }}
    >
      <BrowserRouter>
        <MainLayout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/agents" element={<AgentsList />} />
            <Route path="/groups" element={<GroupsList />} />
            <Route path="/executions" element={<ExecutionsList />} />
            <Route path="/monitor" element={<Monitor />} />
          </Routes>
        </MainLayout>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
