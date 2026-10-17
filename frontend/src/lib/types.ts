export interface User {
  id: string;
  email: string;
}

export interface Session {
  user_id: string;
  expires_in: number;
}

export interface NoteSummary {
  id: string;
  title: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface Note extends NoteSummary {
  owner_id: string;
  body: string;
}

export interface NotePayload {
  title: string;
  body: string;
  tags?: string[];
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface SearchHit {
  id: string;
  owner_id: string;
  title: string;
  tags: string[];
  updated_at: string;
  rank: number;
}

export interface Tag {
  id: string;
  name: string;
  note_count: number;
}

export interface NoteRef {
  id: string;
  title: string;
}

export interface Suggestion {
  id: string;
  source_note: NoteRef;
  target_note: NoteRef;
  similarity_score: number;
  explanation: string;
  created_at: string;
}

export interface NoteLink {
  id: string;
  source_note: NoteRef;
  target_note: NoteRef;
  created_at: string;
}

export interface GraphNode {
  id: string;
  owner_id: string;
  title: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  created_at: string;
}

export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  max_nodes: number;
  is_capped: boolean;
  message: string | null;
}
