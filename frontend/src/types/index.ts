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

// Permission types
export interface Permission {
  id: string;
  name: string;
  code: string;
  description?: string;
  resource: string;
  action: string;
  created_at: string;
}

export interface PermissionCreate {
  name: string;
  code: string;
  description?: string;
  resource: string;
  action: string;
}

export interface PermissionUpdate {
  name?: string;
  description?: string;
  resource?: string;
  action?: string;
}

// Role types
export interface Role {
  id: string;
  name: string;
  code: string;
  description?: string;
  is_system: boolean;
  is_active: boolean;
  permissions: Permission[];
  created_at: string;
}

export interface RoleCreate {
  name: string;
  code: string;
  description?: string;
  is_active?: boolean;
  permission_ids?: string[];
}

export interface RoleUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
  permission_ids?: string[];
}

// Skill types
export interface Skill {
  id: string;
  name: string;
  code: string;
  description?: string;
  category?: string;
  config?: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SkillCreate {
  name: string;
  code: string;
  description?: string;
  category?: string;
  config?: Record<string, any>;
  is_active?: boolean;
  permission_ids?: string[];
}

export interface SkillUpdate {
  name?: string;
  description?: string;
  category?: string;
  config?: Record<string, any>;
  is_active?: boolean;
  permission_ids?: string[];
}

export interface AgentSkillBinding {
  id: string;
  agent_id: string;
  skill_id: string;
  skill_name: string;
  skill_code: string;
  config: Record<string, any>;
  priority: number;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface AgentSkillBindingCreate {
  agent_id: string;
  skill_id: string;
  config?: Record<string, any>;
  priority?: number;
  is_enabled?: boolean;
}
