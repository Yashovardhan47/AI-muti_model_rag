export type User = { id: string; email: string; role: 'admin' | 'user' }
export type StoredFile = { id: string; name: string; mime_type: string; size: number; status: string; error: string | null; tags: string; created_at: string }
export type Citation = { number: number; file_id: string; file_name: string; chunk_id: string; location: string; excerpt: string; score: number; modality?: string }
export type Answer = { session_id: string; answer: string; citations: Citation[]; confidence: string; grounded: boolean }
export type Message = { id?: string; role: 'user'|'assistant'; content: string; citations?: Citation[]; created_at?: string }
