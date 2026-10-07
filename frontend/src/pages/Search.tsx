import { useState, type FormEvent } from 'react'
import { Alert, CircularProgress } from '@mui/material'
import { Search as SearchIcon } from 'lucide-react'
import { api, errorText } from '../lib/api'
import { Empty, Heading } from '../components/Layout'
import EvidencePreview from '../components/EvidencePreview'
import type { Citation } from '../lib/types'

export default function Search() {
  const [q, setQ] = useState(''), [kind, setKind] = useState(''), [date, setDate] = useState(''), [tag, setTag] = useState('')
  const [includeVersions, setIncludeVersions] = useState(false)
  const [hits, setHits] = useState<Citation[] | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [selectedEvidence, setSelectedEvidence] = useState<Citation | null>(null)
  const search = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const { data } = await api.get('/search', { params: { q, file_type: kind || undefined, date_from: date || undefined,
        tag: tag || undefined, include_versions: includeVersions, top_k: 20 } })
      setHits(data)
    } catch (exception) { setError(errorText(exception)) }
    finally { setBusy(false) }
  }
  return <>
    <Heading eyebrow="Enterprise search" title="Find what matters" description="Search your own and shared sources, then inspect located evidence."/>
    <form className="surface p-5" onSubmit={search}>
      <div className="flex gap-3"><div className="relative flex-1"><SearchIcon className="absolute top-3.5 left-3 muted" size={18}/>
        <input className="field !pl-10" value={q} onChange={event => setQ(event.target.value)} placeholder="Search documents, media and logs" minLength={2} required/>
      </div><button className="action flex items-center gap-2" disabled={busy}>{busy && <CircularProgress size={17}/>} Search</button></div>
      <div className="grid sm:grid-cols-4 gap-3 mt-4">
        <label className="text-xs muted">File type<select className="field mt-1" value={kind} onChange={event => setKind(event.target.value)}><option value="">All types</option>{['pdf','docx','pptx','xlsx','csv','png','jpg','mp3','wav','mp4','json','log','txt'].map(value => <option key={value}>{value}</option>)}</select></label>
        <label className="text-xs muted">Uploaded since<input type="date" className="field mt-1" value={date} onChange={event => setDate(event.target.value)}/></label>
        <label className="text-xs muted">Tag<input className="field mt-1" placeholder="Optional tag" value={tag} onChange={event => setTag(event.target.value)}/></label>
        <label className="text-xs muted flex gap-2 items-center mt-4"><input type="checkbox" checked={includeVersions} onChange={event => setIncludeVersions(event.target.checked)}/> Include older versions</label>
      </div>
    </form>
    {error && <Alert severity="error" className="mt-5">{error}</Alert>}
    {hits !== null ? <div className="mt-8"><h2 className="font-bold text-lg mb-5">{hits.length} matching passages</h2>
      {hits.length ? <div className="space-y-4">{hits.map(hit => <div className="surface p-5" key={hit.chunk_id}>
        <div className="flex flex-wrap gap-3 justify-between"><div><span className="tag">{hit.modality || 'text'}</span>
          <h3 className="font-semibold mt-3">{hit.file_name} <span className="muted text-sm font-normal">· {hit.location}{hit.source_state === 'superseded' ? ' · older version' : ''}</span></h3>
        </div><button className="outline text-sm" onClick={() => setSelectedEvidence(hit)}>Inspect evidence</button></div>
        <p className="muted text-sm leading-7 mt-4 whitespace-pre-wrap line-clamp-5">{hit.excerpt}</p>
        <p className="muted text-xs mt-4">Retrieval signal (not calibrated): {hit.score.toFixed(3)} · passage {hit.number}{hit.quality?.flags?.length ? ' · review ' + hit.quality.flags.join(', ') : ''}</p>
      </div>)}</div> : <Empty title="No matches" detail="Try broader terms or remove a filter."/>}
    </div> : <div className="mt-8"><Empty title="Search your knowledge base" detail="Type at least two characters to find matching source passages."/></div>}
    <EvidencePreview citation={selectedEvidence} onClose={() => setSelectedEvidence(null)}/>
  </>
}
