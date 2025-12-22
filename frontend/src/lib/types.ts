export interface Project {
  id: number;
  path: string;
  name: string;
  project_type: string;
  description: string;
  readme_content: string;
  readme_translated: string;
  tags: string[];
  last_modified: string;
  detected_at: string;
  metadata: Record<string, unknown>;
}

export interface Stats {
  total: number;
  by_type: Record<string, number>;
  last_scan: string;
}

export interface AskResponse {
  answer: string;
  project_ids: number[];
  fallback: boolean;
}
