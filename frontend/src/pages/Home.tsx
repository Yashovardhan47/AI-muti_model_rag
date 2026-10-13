import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ArrowUpRight, FileCheck2, FolderSearch, MessageSquareText, UploadCloud, FileBarChart2 } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { Heading } from '../components/Layout'

type Overview = {
  files: number
  ready: number
  queries: number
  recent: { name: string; status: string; created_at: string }[]
}

const actions = [
  { to: '/app/upload', icon: UploadCloud, title: 'Add sources', detail: 'Upload a document, image, recording, or log.' },
  { to: '/app/chat', icon: MessageSquareText, title: 'Ask Atlas', detail: 'Get an answer linked to supporting evidence.' },
  { to: '/app/search', icon: FolderSearch, title: 'Search content', detail: 'Find passages across your indexed files.' },
  { to: '/app/reports', icon: FileBarChart2, title: 'Export a report', detail: 'Review your activity and download results.' }
]

export default function Home() {
  const email = useAuth(state => state.user?.email || '')
  const name = email.split('@')[0].replace(/[._-]+/g, ' ').trim()
  const greeting = name ? name.charAt(0).toUpperCase() + name.slice(1) : 'there'
  const { data, isLoading, error } = useQuery<Overview>({ queryKey: ['dashboard'], queryFn: async () => (await api.get('/dashboard')).data })
  const next = data?.files === 0
    ? { title: 'Start with a source', detail: 'Upload a supported file to build your private knowledge base.', to: '/app/upload', label: 'Go to upload center' }
    : data?.ready === 0
      ? { title: 'Your sources are being prepared', detail: 'Check processing status in the upload center. Search and answers become available after indexing.', to: '/app/upload', label: 'View processing' }
      : { title: 'Put your sources to work', detail: String(data?.ready ?? 0) + ' indexed files are ready to search and question.', to: '/app/chat', label: 'Ask a question' }

  return <>
    <Heading eyebrow="Your home" title={'Welcome, ' + greeting + '.'} description="Pick up your work, add sources, and get back to the evidence that matters."/>
    {error && <p role="alert" className="text-red-400 mb-5">Your latest workspace activity is unavailable right now. The tools below are still accessible.</p>}
    <section className="surface p-6 md:p-8 bg-gradient-to-br from-teal-300/10 via-transparent to-indigo-400/5" aria-labelledby="next-title">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div className="max-w-xl"><p className="text-xs font-bold uppercase tracking-[.2em] text-teal-300">Your next step</p><h2 id="next-title" className="text-2xl font-bold mt-3">{isLoading ? 'Loading your workspace…' : error ? 'Choose where to begin' : next.title}</h2><p className="muted mt-3 leading-7">{isLoading ? 'Checking your sources and recent work.' : error ? 'Upload, search, chat, and reports are available from the workspace menu.' : next.detail}</p></div>
        <Link to={error ? '/app/upload' : next.to} className="action inline-flex items-center gap-2">{error ? 'Open upload center' : next.label}<ArrowUpRight size={17}/></Link>
      </div>
      <div className="grid sm:grid-cols-3 gap-3 mt-8">
        <div className="raised p-4"><p className="muted text-sm">Your files</p><p className="text-2xl font-bold mt-2">{isLoading ? '…' : data?.files ?? '—'}</p></div>
        <div className="raised p-4"><p className="muted text-sm">Ready to search</p><p className="text-2xl font-bold mt-2">{isLoading ? '…' : data?.ready ?? '—'}</p></div>
        <div className="raised p-4"><p className="muted text-sm">Questions asked</p><p className="text-2xl font-bold mt-2">{isLoading ? '…' : data?.queries ?? '—'}</p></div>
      </div>
    </section>
    <section className="mt-9" aria-labelledby="actions-title"><div className="flex flex-wrap items-end justify-between gap-3 mb-5"><div><p className="text-xs font-bold uppercase tracking-[.2em] text-teal-300">Workspace tools</p><h2 id="actions-title" className="text-xl font-bold mt-2">What would you like to do?</h2></div><Link to="/app/overview" className="text-sm text-teal-300 hover:underline">View detailed analytics</Link></div><div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">{actions.map(({to,icon:Icon,title,detail})=><Link to={to} key={to} className="surface p-6 hover:border-teal-300/50 transition flex flex-col min-h-48"><div className="w-11 h-11 rounded-xl bg-teal-300/12 grid place-items-center text-teal-300"><Icon size={21}/></div><h3 className="font-bold mt-5">{title}</h3><p className="muted text-sm leading-6 mt-2">{detail}</p><ArrowUpRight className="text-teal-300 mt-auto self-end" size={18}/></Link>)}</div></section>
    <div className="grid lg:grid-cols-[1.2fr_.8fr] gap-5 mt-9"><section className="surface p-6" aria-labelledby="recent-title"><div className="flex justify-between items-center gap-3"><h2 id="recent-title" className="font-bold text-lg">Recent sources</h2><Link to="/app/upload" className="text-sm text-teal-300 hover:underline">Open library</Link></div>{data?.recent?.length ? <div className="space-y-3 mt-5">{data.recent.slice(0,4).map((file,index)=><div className="raised p-4 flex items-center gap-3" key={file.name + '-' + index}><span className="w-9 h-9 rounded-lg bg-teal-300/12 text-teal-300 grid place-items-center"><FileCheck2 size={17}/></span><div className="flex-1 min-w-0"><p className="truncate text-sm font-medium">{file.name}</p><p className="muted text-xs mt-1">{new Date(file.created_at).toLocaleDateString()}</p></div><span className="tag">{file.status}</span></div>)}</div> : <p className="muted text-sm mt-8">{isLoading ? 'Loading recent sources…' : 'No recent sources. Your first upload will appear here.'}</p>}</section><section className="surface p-6" aria-labelledby="path-title"><h2 id="path-title" className="font-bold text-lg">From source to answer</h2><p className="muted text-sm mt-2 mb-6">A simple path through your private workspace.</p><ol className="space-y-5">{[['01','Upload a file','Choose source and OCR settings.'],['02','Wait for indexing','Text and locations become searchable.'],['03','Ask and inspect','Open citations before relying on an answer.']].map(([number,title,detail])=><li key={number} className="flex gap-4"><span className="text-teal-300 font-mono text-sm">{number}</span><div><p className="font-semibold text-sm">{title}</p><p className="muted text-sm mt-1">{detail}</p></div></li>)}</ol></section></div>
  </>
}
