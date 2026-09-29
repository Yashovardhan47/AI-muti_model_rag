import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Alert, CircularProgress } from '@mui/material'
import { Download, ExternalLink, Plus, RotateCcw, Send, Sparkles } from 'lucide-react'
import { api, errorText, previewFile } from '../lib/api'
import { useAuth } from '../lib/auth'
import { Heading } from '../components/Layout'
import type { Message, StoredFile } from '../lib/types'

export default function Chat() {
  const [question,setQuestion]=useState(''), [session,setSession]=useState(''), [messages,setMessages]=useState<Message[]>([]), [busy,setBusy]=useState(false), [error,setError]=useState(''), [queryType,setQueryType]=useState('qa'),[fileIds,setFileIds]=useState<string[]>([]),[topK,setTopK]=useState(6)
  const bottom=useRef<HTMLDivElement>(null)
  const {data:files=[]}=useQuery<StoredFile[]>({queryKey:['files'],queryFn:async()=> (await api.get('/files/list')).data})
  const {data:sessions=[],refetch}=useQuery<{id:string;title:string}[]>({queryKey:['sessions'],queryFn:async()=> (await api.get('/chat/history')).data})
  useEffect(()=>{bottom.current?.scrollIntoView({behavior:'smooth'})},[messages])
  const load = async (id:string)=>{setSession(id);setError('');try{setMessages((await api.get(`/chat/history/${id}`)).data)}catch(e){setError(errorText(e))}}
  const ask = async (value:string)=>{
    if(!value.trim()||busy)return
    setBusy(true);setError('');setMessages(old=>[...old,{role:'user',content:value},{role:'assistant',content:''}]);setQuestion('')
    try {
      const body=JSON.stringify({question:value,session_id:session||null,file_ids:fileIds,query_type:queryType,top_k:topK})
      const request=()=>fetch('/api/chat/query/stream',{method:'POST',headers:{'Content-Type':'application/json','Authorization':`Bearer ${useAuth.getState().access}`},body})
      let response=await request()
      if(response.status===401 && useAuth.getState().refresh){
        const tokens=(await api.post('/auth/refresh',{refresh_token:useAuth.getState().refresh})).data
        useAuth.getState().setTokens(tokens.access_token,tokens.refresh_token,tokens.user)
        response=await request()
      }
      if(!response.ok||!response.body)throw new Error(`Chat request failed (${response.status})`)
      const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',finished=false
      while(true){const {done,value:bytes}=await reader.read();if(done)break;buffer+=decoder.decode(bytes,{stream:true});let boundary:number
        while((boundary=buffer.indexOf('\n\n'))>=0){const raw=buffer.slice(0,boundary);buffer=buffer.slice(boundary+2);const event=raw.match(/^event: (.+)$/m)?.[1];const line=raw.match(/^data: (.+)$/m)?.[1];if(!line)continue;const payload=JSON.parse(line)
          if(event==='delta')setMessages(old=>old.map((m,i)=>i===old.length-1?{...m,content:m.content+payload.text}:m))
          if(event==='final'){finished=true;setSession(payload.session_id);setMessages(old=>old.map((m,i)=>i===old.length-1?{...m,content:payload.answer,citations:payload.citations}:m));refetch()}
          if(event==='error')throw new Error(payload.detail)
        }
      }
      if(!finished)throw new Error('The answer stream ended unexpectedly')
    } catch(e){setError(errorText(e));setMessages(old=>old.slice(0,-2));setQuestion(value)} finally{setBusy(false)}
  }
  const exportAnswer=(text:string)=>{const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([text],{type:'text/markdown'}));link.download='atlas-answer.md';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000)}
  return <><Heading eyebrow="Evidence-based assistant" title="Ask Atlas" description="Ask questions across your indexed sources and inspect the passages behind every answer."/><div className="grid lg:grid-cols-[250px_1fr] gap-5 h-[calc(100vh-220px)] min-h-135"><aside className="surface p-4 overflow-y-auto"><button className="outline w-full flex gap-2 justify-center items-center" onClick={()=>{setSession('');setMessages([]);setQuestion('')}}><Plus size={17}/> New conversation</button><p className="muted uppercase text-xs tracking-wider mt-7 mb-3 px-2">Recent conversations</p><div className="space-y-1">{sessions.map(s=><button key={s.id} onClick={()=>load(s.id)} className={`w-full text-left truncate p-3 rounded-xl text-sm ${session===s.id?'bg-teal-300/15 text-teal-300':'muted hover:bg-white/5'}`}>{s.title}</button>)}{!sessions.length&&<p className="muted text-sm px-2">No conversations yet.</p>}</div></aside><section className="surface flex flex-col min-h-0"><div className="border-b p-4 flex flex-wrap gap-3 items-center" style={{borderColor:'var(--line)'}}><select aria-label="Query type" className="field !w-auto" value={queryType} onChange={e=>setQueryType(e.target.value)}>{[['qa','Question & answer'],['summary','Summarize'],['compare','Compare'],['risks','Find risks'],['keywords','Keywords'],['charts','Explain charts'],['actions','Action items'],['contract','Contract clauses'],['invoice','Invoice extraction'],['meeting','Meeting summary']].map(([v,l])=><option value={v} key={v}>{l}</option>)}</select><select aria-label="Filter by source" className="field !w-auto max-w-45" value={fileIds[0]||''} onChange={e=>setFileIds(e.target.value?[e.target.value]:[])}><option value="">All my sources</option>{files.filter(f=>f.status==='ready').map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select><label className="muted text-xs">Top K <input className="w-12 field !p-1 ml-1" type="number" min={1} max={20} value={topK} onChange={e=>setTopK(Number(e.target.value))}/></label></div><div className="flex-1 overflow-y-auto p-5 space-y-6">{!messages.length&&<div className="h-full grid place-items-center text-center"><div><div className="w-15 h-15 bg-teal-300/15 text-teal-300 rounded-2xl grid place-items-center mx-auto mb-5"><Sparkles size={28}/></div><h2 className="text-xl font-bold">What would you like to know?</h2><p className="muted text-sm mt-3 max-w-md">Try “Summarize the main risks” or “Compare the two quarterly reports.”</p><div className="flex flex-wrap gap-2 justify-center mt-6">{['Summarize the key findings','List open action items','What anomalies appear in the logs?'].map(x=><button key={x} className="outline text-xs" onClick={()=>setQuestion(x)}>{x}</button>)}</div></div></div>}{messages.map((m,i)=><div key={i} className={`flex ${m.role==='user'?'justify-end':'justify-start'}`}><div className={`${m.role==='user'?'bg-teal-300 text-slate-950':'raised'} rounded-2xl p-4 max-w-[90%] lg:max-w-[80%]`}><p className="whitespace-pre-wrap text-sm leading-7">{m.content}</p>{m.role==='assistant'&&<><div className="flex gap-2 mt-4"><button className="outline !p-2" title="Export answer" onClick={()=>exportAnswer(m.content)}><Download size={15}/></button><button className="outline !p-2" title="Regenerate" onClick={()=>{const previous=messages.slice(0,i).reverse().find(x=>x.role==='user');if(previous)ask(previous.content)}}><RotateCcw size={15}/></button></div>{!!m.citations?.length&&<div className="border-t mt-4 pt-4" style={{borderColor:'var(--line)'}}><div className="muted text-xs uppercase tracking-wider mb-3">Sources</div><div className="space-y-2">{m.citations.map(c=><button key={c.chunk_id} className="raised p-3 w-full text-left hover:border-teal-300/40" onClick={()=>previewFile(c.file_id).catch(e=>setError(errorText(e)))}><span className="text-teal-300 text-xs font-semibold">[{c.number}] {c.file_name} · {c.location} <ExternalLink size={12} className="inline"/></span><p className="muted text-xs mt-1 line-clamp-2">{c.excerpt}</p></button>)}</div></div>}</>}</div></div>)}{busy&&<div className="flex gap-3 muted items-center"><CircularProgress size={16}/> Searching sources and composing an answer…</div>}<div ref={bottom}/></div>{error&&<Alert severity="error" onClose={()=>setError('')}>{error}</Alert>}<form className="p-4 border-t flex gap-3" style={{borderColor:'var(--line)'}} onSubmit={(e:FormEvent)=>{e.preventDefault();ask(question)}}><input className="field flex-1" placeholder="Ask a question about your sources..." value={question} onChange={e=>setQuestion(e.target.value)}/><button className="action" disabled={busy||!question.trim()} aria-label="Send"><Send size={18}/></button></form><p className="muted text-[11px] px-5 pb-3">Answers are grounded in retrieved passages. Review source files for important decisions.</p></section></div></>
}
