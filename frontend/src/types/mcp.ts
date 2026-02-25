// MCP Server types

export type MCPServerType = 'stdio' | 'sse' | 'http';

export interface MCPTool {
  id: string;
  server_id: string;
  name: string;
  description?: string;
  input_schema: Record<string, any>;
  is_enabled: boolean;
  created_at: string;
}

export interface MCPServer {
  id: string;
  name: string;
  code: string;
  description?: string;
  server_type: MCPServerType;
  command?: string;
  args?: string[];
  url?: string;
  env?: Record<string, string>;
  headers?: Record<string, string>;
  enabled: boolean;
  tools_cache?: Record<string, any>[];
  resources_cache?: Record<string, any>[];
  last_sync_at?: string;
  sync_error?: string;
  created_at: string;
  updated_at: string;
  tools?: MCPTool[];
}

export interface MCPServerCreate {
  name: string;
  code: string;
  description?: string;
  server_type: MCPServerType;
  command?: string;
  args?: string[];
  url?: string;
  env?: Record<string, string>;
  headers?: Record<string, string>;
  enabled?: boolean;
}

export interface MCPServerUpdate {
  name?: string;
  description?: string;
  command?: string;
  args?: string[];
  url?: string;
  env?: Record<string, string>;
  headers?: Record<string, string>;
  enabled?: boolean;
}

export interface MCPServerSyncResponse {
  server_id: string;
  tools_count: number;
  resources_count: number;
  error?: string;
}
