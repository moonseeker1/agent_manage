/**
 * Command Types
 * 指令相关类型定义
 */

export type CommandType = 'pause' | 'cancel' | 'task' | 'config_reload' | 'status_check';
export type CommandStatus = 'pending' | 'executing' | 'success' | 'error' | 'timeout' | 'cancelled';

export interface AgentCommand {
  id: string;
  agent_id: string;
  command_type: CommandType;
  content: Record<string, unknown>;
  status: CommandStatus;
  priority: number;
  timeout: number;
  output?: string;
  progress: number;
  progress_message?: string;
  error_message?: string;
  retry_count: number;
  max_retries: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  updated_at?: string;
}

export interface CommandCreate {
  type: CommandType;
  content: Record<string, unknown>;
  priority?: number;
  timeout?: number;
  max_retries?: number;
}

export interface CommandResultSubmit {
  output?: string;
  status: 'success' | 'error';
  error_message?: string;
}

export interface CommandProgressUpdate {
  progress: number;
  message?: string;
}

export interface CommandQuery {
  agent_id?: string;
  status?: CommandStatus;
  command_type?: CommandType;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}

export interface CommandListResponse {
  items: AgentCommand[];
  total: number;
  page: number;
  page_size: number;
}

export interface CommandStatsResponse {
  status_counts: Record<CommandStatus, number>;
  pending_in_redis: number;
  total: number;
}

export interface CommandSimpleResponse {
  success: boolean;
  message?: string;
  data?: Record<string, unknown>;
}

export const COMMAND_TYPE_LABELS: Record<CommandType, string> = {
  pause: '暂停',
  cancel: '取消',
  task: '任务',
  config_reload: '重载配置',
  status_check: '状态检查',
};

export const COMMAND_STATUS_LABELS: Record<CommandStatus, string> = {
  pending: '待处理',
  executing: '执行中',
  success: '成功',
  error: '失败',
  timeout: '超时',
  cancelled: '已取消',
};

export const COMMAND_STATUS_COLORS: Record<CommandStatus, string> = {
  pending: 'default',
  executing: 'processing',
  success: 'success',
  error: 'error',
  timeout: 'warning',
  cancelled: 'default',
};
