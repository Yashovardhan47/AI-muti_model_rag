import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Alert, CircularProgress } from '@mui/material'
import { Download, ExternalLink, Plus, RotateCcw, Send, Sparkles, ShieldCheck } from 'lucide-react'
import { api, errorText, previewFile } from '../lib/api'
import { useAuth } from '../lib/auth'
import { Heading } from '../components/Layout'
import type { EvidenceAudit, Message, StoredFile } from '../lib/types'

const queryTypes = [
  ['qa', 'Question & answer'], ['summary', 'Summarize'], ['compare', 'Compare'],
  ['risks', 'Find risks'], ['keywords', 'Keywords'], ['charts', 'Explain charts'],
  ['actions', 'Action items'], ['contract', 'Contract clauses'],
  ['invoice', 'Invoice extraction'], ['meeting', 'Meeting summary']
]

function EvidencePanel({ audit }: { audit?: EvidenceAudit }) {
  if (!audit?.status) return null
  const labels = {
    source_excerpts: 'Direct source passages',
    citation_checked: 'Citation and number checks passed',
    withheld: 'Generated answer withheld',
    insufficient: 'No retrieved evidence'
  }
  return <details className="raised p-3 mt-4 text-xs">
    <summary className="cursor-pointer flex items-center gap-2 font-semibold"><ShieldCheck size={15}/>{labels[audit.status]}</summary>
    {audit.warnings.map((warning, index) => <p className="muted mt-2" key={index}>{warning}</p>)}
    {audit.checks.length > 0 && <div className="mt-3 space-y-2">
      {audit.checks.map((check, index) => <p key={index} className="border-t pt-2" style={{ borderColor: 'var(--line)' }}>
        {check.text} <span className="muted">· cited {check.citation_numbers.map(n => '[' + n + ']').join(' ')}</span>
      </p>)}
    </div>}
  </details>
}

export default function Chat() {
  const [question, setQuestion] = useState('')
  const [session, setSession] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [busy, setBusy] = useState(false)
  const [phase, setPhase] = useState('Searching sources and composing an answer…')
  const [error, setError] = useState('')
  const [queryType, setQueryType] = useState('qa')
  const [fileIds, setFileIds] = useState<string[]>([])
  const [topK, setTopK] = useState(6)
  const bottom = useRef<HTMLDivElement>(null)
  const { data: files = [] } = useQuery<StoredFile[]>({ queryKey: ['files'], queryFn: async () => (await api.get('/files/list')).data })
  const { data: sessions = [], refetch } = useQuery<{ id: string; title: string }[]>({ queryKey: ['sessions'], queryFn: async () => (await api.get('/chat/history')).data })

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const load = async (id: string) => {
    setSession(id)
    setError('')
    try { setMessages((await api.get('/chat/history/' + id)).data) }
    catch (exception) { setError(errorText(exception)) }
  }

  const ask = async (value: string) => {
    if (!value.trim() || busy) return
    setBusy(true)
    setPhase('Searching sources and composing an answer…')
    setError('')
    setMessages(old => [...old, { role: 'user', content: value }, { role: 'assistant', content: '' }])
    setQuestion('')
    try {
      const body = JSON.stringify({ question: value, session_id: session || null, file_ids: fileIds, query_type: queryType, top_k: topK })
      const request = () => fetch('/api/chat/query/stream', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + useAuth.getState().access }, body
      })
      let response = await request()
      if (response.status === 401 && useAuth.getState().refresh) {
        const tokens = (await api.post('/auth/refresh', { refresh_token: useAuth.getState().refresh })).data
        useAuth.getState().setTokens(tokens.access_token, tokens.refresh_token, tokens.user)
        response = await request()
      }
      if (!response.ok || !response.body) throw new Error('Chat request failed (' + response.status + ')')
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let finished = false
      while (true) {
        const { done, value: bytes } = await reader.read()
        if (done) break
        buffer += decoder.decode(bytes, { stream: true }).replace(/\r\n/g, '\n')
        let boundary: number
        while ((boundary = buffer.indexOf('\n\n')) >= 0) {
          const raw = buffer.slice(0, boundary)
          buffer = buffer.slice(boundary + 2)
          const event = raw.match(/^event: (.+)$/m)?.[1]
          const line = raw.match(/^data: (.+)$/m)?.[1]
          if (!line) continue
          const payload = JSON.parse(line)
          if (event === 'progress') setPhase(payload.stage)
          if (event === 'delta') setMessages(old => old.map((message, index) =>
            index === old.length - 1 ? { ...message, content: message.content + payload.text } : message))
          if (event === 'final') {
            finished = true
            setSession(payload.session_id)
            setMessages(old => old.map((message, index) =>
              index === old.length - 1 ? { ...message, content: payload.answer, citations: payload.citations, audit: payload.audit } : message))
            refetch()
          }
          if (event === 'error') throw new Error(payload.detail)
        }
      }
      if (!finished) throw new Error('The answer stream ended unexpectedly')
    } catch (exception) {
      setError(errorText(exception))
      setMessages(old => old.slice(0, -2))
      setQuestion(value)
    } finally { setBusy(false) }
  }

  const exportAnswer = (message: Message) => {
    const sources = (message.citations || []).map(c =>
      '[' + c.number + '] ' + c.file_name + ' — ' + c.location + ' (' + (c.available === false ? 'source no longer available' : 'source available') + ')'
    ).join('\n')
    const content = message.content + '\n\nEvidence status: ' + (message.audit?.status || 'legacy answer; audit unavailable') + '\n\nSources:\n' + sources
    const link = document.createElement('a')
    link.href = URL.createObjectURL(new Blob([content], { type: 'text/markdown' }))
    link.download = 'atlas-answer.md'
    link.click()
    setTimeout(() => URL.revokeObjectURL(link.href), 1000)
  }

  return <>
    <Heading eyebrow="Evidence-based assistant" title="Ask Atlas" description="Ask across indexed sources and inspect each answer's evidence audit."/>
    <div className="grid lg:grid-cols-[250px_1fr] gap-5 h-[calc(100vh-220px)] min-h-135">
      <aside className="surface p-4 overflow-y-auto">
        <button className="outline w-full flex gap-2 justify-center items-center" onClick={() => { setSession(''); setMessages([]); setQuestion('') }}><Plus size={17}/> New conversation</button>
        <p className="muted uppercase text-xs tracking-wider mt-7 mb-3 px-2">Recent conversations</p>
        <div className="space-y-1">
          {sessions.map(item => <button key={item.id} onClick={() => load(item.id)} className={'w-full text-left truncate p-3 rounded-xl text-sm ' + (session === item.id ? 'bg-teal-300/15 text-teal-300' : 'muted hover:bg-white/5')}>{item.title}</button>)}
          {!sessions.length && <p className="muted text-sm px-2">No conversations yet.</p>}
        </div>
      </aside>
      <section className="surface flex flex-col min-h-0">
        <div className="border-b p-4 flex flex-wrap gap-3 items-center" style={{ borderColor: 'var(--line)' }}>
          <select aria-label="Query type" className="field !w-auto" value={queryType} onChange={event => setQueryType(event.target.value)}>
            {queryTypes.map(([value, label]) => <option value={value} key={value}>{label}</option>)}
          </select>
          <select aria-label="Filter by source" className="field !w-auto max-w-45" value={fileIds[0] || ''} onChange={event => setFileIds(event.target.value ? [event.target.value] : [])}>
            <option value="">All my sources</option>
            {files.filter(file => file.status === 'ready').map(file => <option key={file.id} value={file.id}>{file.name}</option>)}
          </select>
          <label className="muted text-xs">Top K <input className="w-12 field !p-1 ml-1" type="number" min={1} max={20} value={topK} onChange={event => setTopK(Number(event.target.value))}/></label>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {!messages.length && <div className="h-full grid place-items-center text-center"><div>
            <div className="w-15 h-15 bg-teal-300/15 text-teal-300 rounded-2xl grid place-items-center mx-auto mb-5"><Sparkles size={28}/></div>
            <h2 className="text-xl font-bold">What would you like to know?</h2>
            <p className="muted text-sm mt-3 max-w-md">Try “Summarize the main risks” or “Compare the two quarterly reports.”</p>
            <div className="flex flex-wrap gap-2 justify-center mt-6">{['Summarize the key findings', 'List open action items', 'What anomalies appear in the logs?'].map(text => <button key={text} className="outline text-xs" onClick={() => setQuestion(text)}>{text}</button>)}</div>
          </div></div>}
          {messages.map((message, index) => <div key={message.id || index} className={'flex ' + (message.role === 'user' ? 'justify-end' : 'justify-start')}>
            <div className={(message.role === 'user' ? 'bg-teal-300 text-slate-950' : 'raised') + ' rounded-2xl p-4 max-w-[90%] lg:max-w-[80%]'}>
              <p className="whitespace-pre-wrap text-sm leading-7">{message.content}</p>
              {message.role === 'assistant' && <>
                {message.audit && <EvidencePanel audit={message.audit}/>}
                <div className="flex gap-2 mt-4">
                  <button className="outline !p-2" title="Export answer" onClick={() => exportAnswer(message)}><Download size={15}/></button>
                  <button className="outline !p-2" title="Regenerate" onClick={() => { const previous = messages.slice(0, index).reverse().find(item => item.role === 'user'); if (previous) ask(previous.content) }}><RotateCcw size={15}/></button>
                </div>
                {!!message.citations?.length && <div className="border-t mt-4 pt-4" style={{ borderColor: 'var(--line)' }}>
                  <div className="muted text-xs uppercase tracking-wider mb-3">Sources · original file and location</div>
                  <div className="space-y-2">{message.citations.map(citation => <button key={citation.chunk_id} disabled={citation.available === false} className="raised p-3 w-full text-left hover:border-teal-300/40 disabled:opacity-50 disabled:cursor-not-allowed" onClick={() => previewFile(citation.file_id).catch(exception => setError(errorText(exception)))}>
                    <span className="text-teal-300 text-xs font-semibold">[{citation.number}] {citation.file_name} · {citation.location} {citation.available === false ? '· source removed or changed' : <ExternalLink size={12} className="inline"/>}</span>
                    <p className="muted text-xs mt-1 line-clamp-2">{citation.excerpt}</p>
                  </button>)}</div>
                </div>}
              </>}
            </div>
          </div>)}
          {busy && <div className="flex gap-3 muted items-center"><CircularProgress size={16}/>{phase}</div>}
          <div ref={bottom}/>
        </div>
        {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}
        <form className="p-4 border-t flex gap-3" style={{ borderColor: 'var(--line)' }} onSubmit={(event: FormEvent) => { event.preventDefault(); ask(question) }}>
          <input className="field flex-1" placeholder="Ask a question about your sources..." value={question} onChange={event => setQuestion(event.target.value)}/>
          <button className="action" disabled={busy || !question.trim()} aria-label="Send"><Send size={18}/></button>
        </form>
        <p className="muted text-[11px] px-5 pb-3">Citation and number checks are structural. Review the original source for important decisions.</p>
      </section>
    </div>
  </>
}
