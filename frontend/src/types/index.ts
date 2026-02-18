// Agent types
export type AgentType = 'mcp' | 'openai' | 'custom';

export interface Agent {
  id: string;
  name: string;
  description?: string;
  agent_type: AgentType;
  config: Record<string, any>;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface AgentCreate {
  name: string;
  description?: string;
  agent_type: AgentType;
  config: Record<string, any>;
  enabled?: boolean;
}

export interface AgentUpdate {
  name?: string;
  description?: string;
  config?: Record<string, any>;
  enabled?: boolean;
}

// Agent Group types
export interface AgentGroupMember {
  id: string;
  agent_id: string;
  agent_name: string;
  priority: number;
}

export interface AgentGroup {
  id: string;
  name: string;
  description?: string;
  execution_mode: 'sequential' | 'parallel' | 'round_robin';
  created_at: string;
  updated_at: string;
  members: AgentGroupMember[];
}

export interface AgentGroupCreate {
  name: string;
  description?: string;
  execution_mode?: string;
  agent_ids?: string[];
}

export interface AgentGroupUpdate {
  name?: string;
  description?: string;
  execution_mode?: string;
}

// Execution types
export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface Execution {
  id: string;
  agent_id?: string;
  group_id?: string;
  status: ExecutionStatus;
  input_data?: Record<string, any>;
  output_data?: Record<string, any>;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  duration?: number;
}

export interface ExecutionLog {
  id: string;
  execution_id: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  message: string;
  metadata?: Record<string, any>;
  created_at: string;
}

// Metrics types
export interface AgentMetricsSummary {
  agent_id: string;
  agent_name: string;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  success_rate: number;
  avg_duration?: number;
  total_tokens_used: number;
}

export interface ExecutionMetricsSummary {
  total_executions: number;
  running_executions: number;
  completed_executions: number;
  failed_executions: number;
  avg_duration?: number;
  executions_per_day: Array<{ date: string; count: number }>;
}

// API Response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
