import { useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, LinearProgress } from '@mui/material'
import { FileText, RefreshCw, Trash2, UploadCloud, ExternalLink, Tag, GitCompare, Users } from 'lucide-react'
import { api, errorText, previewFile } from '../lib/api'
import { Empty, Heading } from '../components/Layout'
import EvidencePreview from '../components/EvidencePreview'
import type { Citation, StoredFile } from '../lib/types'

type Grant = { user_id: string; email: string; created_at: string }
type ChangedValue = { value: string; chunk_id: string; location: string }
type Difference = { record: string; field: string; left: ChangedValue; right: ChangedValue; interpretation: string }
type TextChange = { text: string; chunk_id: string; location: string }
type Comparison = { left: { id: string; name: string; version: number }; right: { id: string; name: string; version: number }; changes: Difference[]; text_added: TextChange[]; text_removed: TextChange[]; totals: Record<string, number>; note: string }

export default function Upload() {
  const input = useRef<HTMLInputElement>(null), replacementInput = useRef<HTMLInputElement>(null), client = useQueryClient()
  const [drag, setDrag] = useState(false), [method, setMethod] = useState('document'), [ocrLanguages, setOcrLanguages] = useState('eng')
  const [message, setMessage] = useState(''), [failure, setFailure] = useState(''), [replacement, setReplacement] = useState('')
  const [sharing, setSharing] = useState(''), [email, setEmail] = useState(''), [grants, setGrants] = useState<Grant[]>([])
  const [left, setLeft] = useState(''), [right, setRight] = useState(''), [comparison, setComparison] = useState<Comparison | null>(null)
  const [evidence, setEvidence] = useState<Citation | null>(null), [busy, setBusy] = useState(false)
  const { data: files = [], isLoading } = useQuery<StoredFile[]>({ queryKey: ['files'], queryFn: async () => (await api.get('/files/list')).data, refetchInterval: 3000 })
  const refresh = () => { client.invalidateQueries({ queryKey: ['files'] }); client.invalidateQueries({ queryKey: ['dashboard'] }) }

  const upload = async (selected: FileList | File[], replaceId = '') => {
    setBusy(true); setFailure(''); let duplicates = 0
    try {
      const selectedFiles = Array.from(selected)
      if (replaceId && selectedFiles.length !== 1) throw new Error('Choose one replacement file')
      for (const file of selectedFiles) {
        const body = new FormData()
        body.append('file', file); body.append('chunk_method', method); body.append('ocr_languages', ocrLanguages)
        if (replaceId) body.append('replace_file_id', replaceId)
        const response = await api.post('/files/upload', body)
        if (response.data.duplicate) duplicates++
      }
      refresh(); setMessage(duplicates ? `${duplicates} identical upload(s) reused; others accepted.` : 'Upload accepted. Indexing will begin shortly.')
    } catch (exception) { setFailure(errorText(exception)) }
    finally { setBusy(false); setReplacement('') }
  }
  const remove = async (id: string) => {
    if (!window.confirm('Delete this source and its indexed content?')) return
    try { await api.delete(`/files/${id}`); refresh() } catch (exception) { setFailure(errorText(exception)) }
  }
  const editTags = async (file: StoredFile) => {
    const value = window.prompt('Tags, separated by commas', file.tags)
    if (value === null) return
    try { await api.patch(`/files/${file.id}/tags`, value.split(',').map(tag => tag.trim()).filter(Boolean)); refresh() }
    catch (exception) { setFailure(errorText(exception)) }
  }
  const retry = async (id: string) => {
    try { await api.post(`/files/${id}/process`, null, { params: { chunk_method: method } }); refresh() }
    catch (exception) { setFailure(errorText(exception)) }
  }
  const openSharing = async (id: string) => {
    setSharing(id); setEmail('')
    try { setGrants((await api.get(`/files/${id}/access`)).data) } catch (exception) { setFailure(errorText(exception)) }
  }
  const grant = async () => {
    try { await api.post(`/files/${sharing}/access`, { email }); setEmail(''); await openSharing(sharing); setMessage('Read access granted across this source’s versions.') }
    catch (exception) { setFailure(errorText(exception)) }
  }
  const revoke = async (id: string) => {
    try { await api.delete(`/files/${sharing}/access/${id}`); await openSharing(sharing); setMessage('Read access revoked.') }
    catch (exception) { setFailure(errorText(exception)) }
  }
  const compare = async () => {
    setFailure(''); setComparison(null)
    try { setComparison((await api.get('/files/compare', { params: { left_id: left, right_id: right } })).data) }
    catch (exception) { setFailure(errorText(exception)) }
  }
  const inspect = (fileId: string, fileName: string, value: ChangedValue | TextChange) =>
    setEvidence({ number: 1, file_id: fileId, file_name: fileName, chunk_id: value.chunk_id,
      excerpt: 'text' in value ? value.text : value.value, location: value.location, score: 0 })

  return <>
    <Heading eyebrow="Source library" title="Upload center" description="Index private files, preserve revisions, and share read access with registered users."/>
    <div className="grid lg:grid-cols-[1.5fr_1fr] gap-5">
      <div className={`surface border-dashed border-2 p-10 text-center transition ${drag ? '!border-teal-300 bg-teal-300/5' : ''}`}
        onDragOver={event => { event.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)}
        onDrop={event => { event.preventDefault(); setDrag(false); if (event.dataTransfer.files.length) upload(event.dataTransfer.files) }}>
        <div className="w-18 h-18 mx-auto rounded-2xl bg-teal-300/12 text-teal-300 grid place-items-center mb-5"><UploadCloud size={32}/></div>
        <h2 className="text-xl font-bold">Drop your files here</h2><p className="muted text-sm mt-2">or choose files from your device</p>
        <input ref={input} type="file" multiple className="hidden" accept=".pdf,.docx,.pptx,.xlsx,.csv,.png,.jpg,.jpeg,.webp,.mp3,.wav,.m4a,.mp4,.mov,.txt,.log,.json,.jsonl"
          onChange={event => { if (event.target.files?.length) upload(event.target.files); event.target.value = '' }}/>
        <input ref={replacementInput} type="file" className="hidden" accept=".pdf,.docx,.pptx,.xlsx,.csv,.png,.jpg,.jpeg,.webp,.mp3,.wav,.m4a,.mp4,.mov,.txt,.log,.json,.jsonl"
          onChange={event => { if (event.target.files?.length) upload(event.target.files, replacement); event.target.value = '' }}/>
        <button className="action mt-6" onClick={() => input.current?.click()} disabled={busy}>Browse files</button>
        <p className="muted text-xs mt-5">PDF, Office, images, audio, video, text, logs · up to 30 MB by default</p>{busy && <LinearProgress className="mt-5"/>}
      </div>
      <div className="surface p-7"><h3 className="font-bold text-lg mb-3">Indexing options</h3>
        <label className="text-sm">Chunking strategy<select className="field mt-2" value={method} onChange={event => setMethod(event.target.value)}>
          <option value="document">Document aware</option><option value="recursive">Recursive</option><option value="fixed">Fixed</option><option value="semantic">Semantic</option></select></label>
        <label className="text-sm block mt-5">OCR languages<select className="field mt-2" value={ocrLanguages} onChange={event => setOcrLanguages(event.target.value)}>
          <option value="eng">English</option><option value="hin">Hindi</option><option value="tel">Telugu</option>
          <option value="eng+hin">English + Hindi</option><option value="eng+tel">English + Telugu</option><option value="eng+hin+tel">All three</option></select></label>
        <p className="muted text-xs mt-3">Install the selected Tesseract language packs on the worker. Choose multilingual E5 for cross-language semantic search.</p>
      </div>
    </div>
    {message && <Alert severity="success" className="mt-5" onClose={() => setMessage('')}>{message}</Alert>}
    {failure && <Alert severity="error" className="mt-5" onClose={() => setFailure('')}>{failure}</Alert>}
    <div className="flex items-center justify-between mt-10 mb-4"><h2 className="text-xl font-bold">Sources <span className="muted font-normal">({files.length})</span></h2><span className="muted text-sm">Updates every 3 seconds</span></div>
    {!isLoading && !files.length ? <Empty title="No files yet" detail="Upload a source to start building your knowledge base."/> : <div className="surface overflow-hidden">
      {files.map(file => <div key={file.id} className="flex flex-wrap items-center gap-4 p-4 md:px-6 border-b last:border-b-0" style={{ borderColor: 'var(--line)' }}>
        <div className="w-11 h-11 rounded-xl bg-indigo-400/12 text-indigo-300 grid place-items-center"><FileText size={21}/></div>
        <div className="flex-1 min-w-45"><p className="font-medium truncate">{file.name} <span className="tag ml-1">v{file.version}</span>{file.read_only && <span className="tag ml-1">shared read only</span>}{!file.is_current && <span className="tag ml-1">older version</span>}</p>
          <p className="muted text-xs mt-1">{(file.size / 1024).toFixed(1)} KB · {new Date(file.created_at).toLocaleString()} · OCR {file.ocr_languages}</p>
          {file.error && <p className="text-red-400 text-xs mt-1">{file.error}</p>}</div>
        <span className={`tag ${file.status === 'failed' ? '!text-red-400 !border-red-400/30' : ''}`}>{file.status}</span>
        <button className="outline !p-2" onClick={() => previewFile(file.id).catch(exception => setFailure(errorText(exception)))} aria-label={`Preview ${file.name}`}><ExternalLink size={17}/></button>
        {!file.read_only && <>
          <button className="outline !p-2" onClick={() => editTags(file)} aria-label={`Edit tags for ${file.name}`}><Tag size={17}/></button>
          <button className="outline !p-2" onClick={() => openSharing(file.id)} aria-label={`Share ${file.name}`}><Users size={17}/></button>
          {file.is_current && <button className="outline !p-2" disabled={busy} onClick={() => { setReplacement(file.id); replacementInput.current?.click() }} aria-label={`Upload new version of ${file.name}`} title="Upload a new version"><GitCompare size={17}/></button>}
          {file.status === 'failed' && <button className="outline !p-2" onClick={() => retry(file.id)} aria-label={`Retry ${file.name}`}><RefreshCw size={17}/></button>}
          <button className="outline !p-2 hover:!text-red-400" onClick={() => remove(file.id)} aria-label={`Delete ${file.name}`}><Trash2 size={17}/></button>
        </>}
      </div>)}
    </div>}
    {sharing && <section className="surface p-5 mt-6"><h2 className="font-semibold">Read access</h2><p className="muted text-xs mt-1">Granted users can search and cite all versions of this source. Revocation removes saved answers that cited it.</p>
      <div className="flex gap-2 mt-4"><input type="email" className="field" placeholder="Registered user's email" value={email} onChange={event => setEmail(event.target.value)}/><button className="action" disabled={!email} onClick={grant}>Grant</button><button className="outline" onClick={() => setSharing('')}>Close</button></div>
      <div className="space-y-2 mt-4">{grants.map(grant => <div className="flex items-center justify-between raised p-3" key={grant.user_id}><span>{grant.email}</span><button className="outline text-xs" onClick={() => revoke(grant.user_id)}>Revoke</button></div>)}</div>
    </section>}
    <section className="surface p-5 mt-8"><h2 className="font-semibold">Compare indexed sources</h2><p className="muted text-xs mt-1">Exact table fields and changed passages are shown with links to both sources. Differences require human interpretation.</p>
      <div className="flex flex-wrap gap-3 mt-4"><select className="field !w-auto flex-1" aria-label="Earlier source" value={left} onChange={event => setLeft(event.target.value)}><option value="">First source</option>{files.filter(file => file.status === 'ready').map(file => <option key={file.id} value={file.id}>{file.name} v{file.version}</option>)}</select>
        <select className="field !w-auto flex-1" aria-label="Later source" value={right} onChange={event => setRight(event.target.value)}><option value="">Second source</option>{files.filter(file => file.status === 'ready').map(file => <option key={file.id} value={file.id}>{file.name} v{file.version}</option>)}</select>
        <button className="action" disabled={!left || !right || left === right} onClick={compare}>Compare</button></div>
      {comparison && <div className="mt-5 space-y-4"><p className="muted text-sm">{comparison.note} · {comparison.totals.changes} changed values · {comparison.totals.text_added} added lines · {comparison.totals.text_removed} removed lines.</p>
        {comparison.changes.map((change, index) => <div key={index} className="raised p-3 text-sm"><p className="font-semibold">{change.record} · {change.field}</p><div className="flex flex-wrap gap-3 mt-2"><button className="outline" onClick={() => inspect(comparison.left.id, comparison.left.name, change.left)}>Earlier: {change.left.value}</button><button className="outline" onClick={() => inspect(comparison.right.id, comparison.right.name, change.right)}>Later: {change.right.value}</button></div></div>)}
        {comparison.text_removed.map((entry, index) => <button className="outline block w-full text-left" key={`r${index}`} onClick={() => inspect(comparison.left.id, comparison.left.name, entry)}>Removed: {entry.text}</button>)}
        {comparison.text_added.map((entry, index) => <button className="outline block w-full text-left" key={`a${index}`} onClick={() => inspect(comparison.right.id, comparison.right.name, entry)}>Added: {entry.text}</button>)}
      </div>}
    </section>
    <EvidencePreview citation={evidence} onClose={() => setEvidence(null)}/>
  </>
}
