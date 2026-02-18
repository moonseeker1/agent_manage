import axios from 'axios';
import type {
  Agent,
  AgentCreate,
  AgentUpdate,
  AgentGroup,
  AgentGroupCreate,
  AgentGroupUpdate,
  Execution,
  ExecutionLog,
  AgentMetricsSummary,
  ExecutionMetricsSummary,
  PaginatedResponse,
} from '@/types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const authStorage = localStorage.getItem('auth-storage');
    if (authStorage) {
      try {
        const { state } = JSON.parse(authStorage);
        if (state?.token) {
          config.headers.Authorization = `Bearer ${state.token}`;
        }
      } catch (e) {
        // Ignore parse errors
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth and redirect to login
      localStorage.removeItem('auth-storage');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Agents API
export const agentsApi = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    agent_type?: string;
    enabled?: boolean;
    search?: string;
  }) => {
    const response = await api.get<PaginatedResponse<Agent>>('/agents', { params });
    return response.data;
  },

  get: async (id: string) => {
    const response = await api.get<Agent>(`/agents/${id}`);
    return response.data;
  },

  create: async (data: AgentCreate) => {
    const response = await api.post<Agent>('/agents', data);
    return response.data;
  },

  update: async (id: string, data: AgentUpdate) => {
    const response = await api.put<Agent>(`/agents/${id}`, data);
    return response.data;
  },

  delete: async (id: string) => {
    await api.delete(`/agents/${id}`);
  },

  enable: async (id: string) => {
    const response = await api.post<Agent>(`/agents/${id}/enable`);
    return response.data;
  },

  disable: async (id: string) => {
    const response = await api.post<Agent>(`/agents/${id}/disable`);
    return response.data;
  },

  execute: async (id: string, inputData?: Record<string, any>) => {
    const response = await api.post<Execution>(`/executions/agents/${id}/execute`, {
      input_data: inputData,
    });
    return response.data;
  },

  batchDelete: async (ids: string[]) => {
    const response = await api.post<{ deleted: number; failed: number }>(
      '/config/agents/batch-delete',
      ids
    );
    return response.data;
  },

  batchToggle: async (ids: string[], enabled: boolean) => {
    const response = await api.post<{ updated: number; failed: number }>(
      '/config/agents/batch-toggle',
      ids,
      { params: { enabled } }
    );
    return response.data;
  },
};

// Agent Groups API
export const groupsApi = {
  list: async (params?: { page?: number; page_size?: number; search?: string }) => {
    const response = await api.get<PaginatedResponse<AgentGroup>>('/groups', { params });
    return response.data;
  },

  get: async (id: string) => {
    const response = await api.get<AgentGroup>(`/groups/${id}`);
    return response.data;
  },

  create: async (data: AgentGroupCreate) => {
    const response = await api.post<AgentGroup>('/groups', data);
    return response.data;
  },

  update: async (id: string, data: AgentGroupUpdate) => {
    const response = await api.put<AgentGroup>(`/groups/${id}`, data);
    return response.data;
  },

  delete: async (id: string) => {
    await api.delete(`/groups/${id}`);
  },

  addMember: async (groupId: string, agentId: string, priority: number = 0) => {
    const response = await api.post(`/groups/${groupId}/members`, {
      agent_id: agentId,
      priority,
    });
    return response.data;
  },

  removeMember: async (groupId: string, agentId: string) => {
    await api.delete(`/groups/${groupId}/members/${agentId}`);
  },

  execute: async (id: string, inputData?: Record<string, any>) => {
    const response = await api.post<Execution>(`/executions/groups/${id}/execute`, {
      input_data: inputData,
    });
    return response.data;
  },
};

// Executions API
export const executionsApi = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    agent_id?: string;
    group_id?: string;
    status?: string;
  }) => {
    const response = await api.get<PaginatedResponse<Execution>>('/executions', { params });
    return response.data;
  },

  get: async (id: string) => {
    const response = await api.get<Execution>(`/executions/${id}`);
    return response.data;
  },

  getLogs: async (id: string) => {
    const response = await api.get<{ items: ExecutionLog[]; total: number }>(
      `/executions/${id}/logs`
    );
    return response.data;
  },

  cancel: async (id: string) => {
    const response = await api.post<Execution>(`/executions/${id}/cancel`);
    return response.data;
  },
};

// Metrics API
export const metricsApi = {
  getExecutionMetrics: async (days: number = 7) => {
    const response = await api.get<ExecutionMetricsSummary>('/metrics/executions', {
      params: { days },
    });
    return response.data;
  },

  getAgentMetrics: async (agentId: string) => {
    const response = await api.get<AgentMetricsSummary>(`/metrics/agents/${agentId}`);
    return response.data;
  },

  getAllAgentMetrics: async () => {
    const response = await api.get<{ agents: AgentMetricsSummary[] }>('/metrics/agents');
    return response.data.agents;
  },
};

// Templates API
export const templatesApi = {
  list: async () => {
    const response = await api.get<{ templates: any[] }>('/templates');
    return response.data.templates;
  },

  get: async (id: string) => {
    const response = await api.get(`/templates/${id}`);
    return response.data;
  },
};

// Config API
export const configApi = {
  export: async () => {
    const response = await api.get('/config/export');
    return response.data;
  },

  import: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/config/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

export default api;
