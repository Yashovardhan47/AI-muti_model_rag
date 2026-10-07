export type User = { id: string; email: string; role: 'admin' | 'user' }
export type StoredFile = { id: string; name: string; mime_type: string; size: number; status: string; error: string | null; tags: string; created_at: string }
export type Citation = { number: number; file_id: string; file_name: string; chunk_id: string; location: string; excerpt: string; score: number; modality?: string; source_sha256?: string | null; available?: boolean }
export type EvidenceAudit = { status: 'source_excerpts' | 'citation_checked' | 'withheld' | 'insufficient'; abstained: boolean; checks: { text: string; citation_numbers: number[]; status: string; issues: string[] }[]; warnings: string[] }
export type Answer = { session_id: string; answer: string; citations: Citation[]; confidence: string; grounded: boolean; audit: EvidenceAudit }
export type Message = { id?: string; role: 'user'|'assistant'; content: string; citations?: Citation[]; audit?: EvidenceAudit; created_at?: string }
