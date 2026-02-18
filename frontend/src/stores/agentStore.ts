import { create } from 'zustand';
import type { Agent, AgentGroup, Execution, ExecutionLog } from '@/types';
import { agentsApi, groupsApi, executionsApi } from '@/services/api';

interface AgentStore {
  // State
  agents: Agent[];
  groups: AgentGroup[];
  executions: Execution[];
  currentExecution: Execution | null;
  executionLogs: ExecutionLog[];
  loading: boolean;
  error: string | null;

  // Agent actions
  fetchAgents: (params?: any) => Promise<void>;
  createAgent: (data: any) => Promise<Agent>;
  updateAgent: (id: string, data: any) => Promise<Agent>;
  deleteAgent: (id: string) => Promise<void>;
  toggleAgent: (id: string, enabled: boolean) => Promise<void>;

  // Group actions
  fetchGroups: (params?: any) => Promise<void>;
  createGroup: (data: any) => Promise<AgentGroup>;
  updateGroup: (id: string, data: any) => Promise<AgentGroup>;
  deleteGroup: (id: string) => Promise<void>;

  // Execution actions
  fetchExecutions: (params?: any) => Promise<void>;
  fetchExecution: (id: string) => Promise<void>;
  fetchExecutionLogs: (id: string) => Promise<void>;
  executeAgent: (id: string, inputData?: any) => Promise<Execution>;
  executeGroup: (id: string, inputData?: any) => Promise<Execution>;
  cancelExecution: (id: string) => Promise<void>;

  // Utility
  clearError: () => void;
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  // Initial state
  agents: [],
  groups: [],
  executions: [],
  currentExecution: null,
  executionLogs: [],
  loading: false,
  error: null,

  // Agent actions
  fetchAgents: async (params) => {
    set({ loading: true, error: null });
    try {
      const response = await agentsApi.list(params);
      set({ agents: response.items, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createAgent: async (data) => {
    set({ loading: true, error: null });
    try {
      const agent = await agentsApi.create(data);
      const { agents } = get();
      set({ agents: [agent, ...agents], loading: false });
      return agent;
    } catch (error: any) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  updateAgent: async (id, data) => {
    set({ loading: true, error: null });
    try {
      const agent = await agentsApi.update(id, data);
      const { agents } = get();
      set({
        agents: agents.map((a) => (a.id === id ? agent : a)),
        loading: false,
      });
      return agent;
    } catch (error: any) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  deleteAgent: async (id) => {
    set({ loading: true, error: null });
    try {
      await agentsApi.delete(id);
      const { agents } = get();
      set({ agents: agents.filter((a) => a.id !== id), loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  toggleAgent: async (id, enabled) => {
    try {
      const agent = enabled ? await agentsApi.enable(id) : await agentsApi.disable(id);
      const { agents } = get();
      set({
        agents: agents.map((a) => (a.id === id ? agent : a)),
      });
    } catch (error: any) {
      set({ error: error.message });
    }
  },

  // Group actions
  fetchGroups: async (params) => {
    set({ loading: true, error: null });
    try {
      const response = await groupsApi.list(params);
      set({ groups: response.items, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createGroup: async (data) => {
    set({ loading: true, error: null });
    try {
      const group = await groupsApi.create(data);
      const { groups } = get();
      set({ groups: [group, ...groups], loading: false });
      return group;
    } catch (error: any) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  updateGroup: async (id, data) => {
    set({ loading: true, error: null });
    try {
      const group = await groupsApi.update(id, data);
      const { groups } = get();
      set({
        groups: groups.map((g) => (g.id === id ? group : g)),
        loading: false,
      });
      return group;
    } catch (error: any) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  deleteGroup: async (id) => {
    set({ loading: true, error: null });
    try {
      await groupsApi.delete(id);
      const { groups } = get();
      set({ groups: groups.filter((g) => g.id !== id), loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  // Execution actions
  fetchExecutions: async (params) => {
    set({ loading: true, error: null });
    try {
      const response = await executionsApi.list(params);
      set({ executions: response.items, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchExecution: async (id) => {
    set({ loading: true, error: null });
    try {
      const execution = await executionsApi.get(id);
      set({ currentExecution: execution, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchExecutionLogs: async (id) => {
    try {
      const response = await executionsApi.getLogs(id);
      set({ executionLogs: response.items });
    } catch (error: any) {
      set({ error: error.message });
    }
  },

  executeAgent: async (id, inputData) => {
    set({ loading: true, error: null });
    try {
      const execution = await agentsApi.execute(id, inputData);
      const { executions } = get();
      set({
        executions: [execution, ...executions],
        currentExecution: execution,
        loading: false,
      });
      return execution;
    } catch (error: any) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  executeGroup: async (id, inputData) => {
    set({ loading: true, error: null });
    try {
      const execution = await groupsApi.execute(id, inputData);
      const { executions } = get();
      set({
        executions: [execution, ...executions],
        currentExecution: execution,
        loading: false,
      });
      return execution;
    } catch (error: any) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  cancelExecution: async (id) => {
    try {
      const execution = await executionsApi.cancel(id);
      const { executions, currentExecution } = get();
      set({
        executions: executions.map((e) => (e.id === id ? execution : e)),
        currentExecution:
          currentExecution?.id === id ? execution : currentExecution,
      });
    } catch (error: any) {
      set({ error: error.message });
    }
  },

  // Utility
  clearError: () => set({ error: null }),
}));
