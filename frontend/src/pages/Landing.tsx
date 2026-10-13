import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, AudioLines, BookOpen, Database, FileSearch, FileText, FolderSearch, Image, LockKeyhole, MessageSquareText, ScanEye, ShieldCheck, Sparkles, Table2, Video } from 'lucide-react'

const sources = [
  { icon: FileText, title: 'Documents', detail: 'PDF, Word, PowerPoint, and scanned pages' },
  { icon: Table2, title: 'Structured data', detail: 'Excel, CSV, tables, JSON, and sensor logs' },
  { icon: Image, title: 'Visual content', detail: 'Images, screenshots, charts, and OCR text' },
  { icon: AudioLines, title: 'Recordings', detail: 'Audio transcripts and video keyframes' }
]
const steps = [
  { number: '01', title: 'Bring in sources', detail: 'Upload files to a private workspace. Keep revisions so older evidence stays traceable.' },
  { number: '02', title: 'Extract and index', detail: 'Parse text, tables, OCR, transcripts, and frame content with source locations.' },
  { number: '03', title: 'Retrieve evidence', detail: 'Search with keyword and vector signals, filters, and optional reranking.' },
  { number: '04', title: 'Answer and inspect', detail: 'Read an answer with citations, then open the supporting source.' }
]
const capabilities = [
  { icon: ScanEye, title: 'Citations you can inspect', detail: 'Follow a claim to its page, slide, row, image region, or recording time.' },
  { icon: FolderSearch, title: 'Search across formats', detail: 'Find passages and compare source versions from one search space.' },
  { icon: ShieldCheck, title: 'Grounded answers', detail: 'Citation and number checks can withhold a draft and return source passages instead.' },
  { icon: LockKeyhole, title: 'Private by account', detail: 'User-scoped files, read grants, and role-based administration keep work separated.' }
]

export default function Landing() {
  return <div className="min-h-screen overflow-hidden">
    {import.meta.env.VITE_DEMO_MODE === 'true' && <div className="relative z-10 text-center px-6 py-3 bg-amber-300/10 text-amber-200 text-sm">Preview instance · Accounts and uploaded files may reset. Use sample files only.</div>}
    <div className="absolute top-0 left-1/3 w-140 h-110 bg-teal-300/12 blur-[130px] pointer-events-none" aria-hidden="true"/>
    <header className="relative max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4 px-6 py-7">
      <Link to="/" className="text-2xl font-black tracking-wide" aria-label="Atlas project overview">ATLAS<span className="text-teal-300">.</span></Link>
      <nav aria-label="Project overview" className="hidden md:flex items-center gap-7 text-sm muted">
        <a className="hover:text-teal-300" href="#formats">Formats</a><a className="hover:text-teal-300" href="#workflow">How it works</a><a className="hover:text-teal-300" href="#capabilities">Capabilities</a>
      </nav>
      <div className="flex gap-3"><Link to="/login" className="outline">Sign in</Link><Link to="/register" className="action">Create account</Link></div>
    </header>
    <main className="relative max-w-7xl mx-auto px-6">
      <section className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center py-16 md:py-24" aria-labelledby="landing-title">
        <motion.div initial={{opacity:0,y:22}} animate={{opacity:1,y:0}} transition={{duration:.35}}>
          <div className="tag mb-7"><Sparkles size={14}/> MULTIMODAL DOCUMENT INTELLIGENCE</div>
          <h1 id="landing-title" className="text-5xl md:text-7xl leading-[1.07] tracking-tight font-black">From scattered files to <span className="text-teal-300">traceable answers.</span></h1>
          <p className="muted text-lg mt-7 max-w-xl leading-8">Atlas brings documents, images, tables, recordings, video, and logs into one private knowledge workspace. Ask a question, compare sources, and see the evidence behind the answer.</p>
          <div className="flex flex-wrap gap-3 mt-9"><Link to="/register" className="action flex items-center gap-2">Start your workspace <ArrowRight size={17}/></Link><a href="#workflow" className="outline">Explore the workflow</a></div>
          <p className="muted text-sm mt-9">Ingest · Search · Ask · Verify</p>
        </motion.div>
        <motion.div initial={{opacity:0,scale:.97}} animate={{opacity:1,scale:1}} transition={{duration:.4,delay:.1}} className="surface p-5 md:p-7 shadow-2xl shadow-teal-900/20" aria-label="Illustrative cited answer">
          <div className="flex items-center justify-between gap-3 muted text-sm mb-6"><span className="flex items-center gap-2"><BookOpen size={17} className="text-teal-300"/> Evidence workspace</span><span className="tag">Illustrative</span></div>
          <div className="raised p-5 mb-4"><p className="text-xs uppercase tracking-widest text-teal-300 font-semibold">Question</p><p className="font-semibold mt-2">What changed between the quarterly reports?</p></div>
          <div className="border-l-2 border-teal-300 pl-5 py-2"><p className="text-xs uppercase tracking-widest text-teal-300 font-semibold mb-3">Answer with sources</p><p className="leading-7">The example reports show revenue increasing in Q2 while operating costs also rose. Inspect both source tables before using the comparison.</p><div className="mt-4 flex flex-wrap gap-2"><span className="tag">[1] Q1 report · page 4</span><span className="tag">[2] Q2 report · page 5</span></div></div>
          <div className="grid grid-cols-3 gap-3 mt-7">{[FileSearch,AudioLines,Video].map((Icon,index)=><div key={index} className="raised h-18 grid place-items-center"><Icon className="text-teal-300"/></div>)}</div>
          <p className="muted text-xs mt-5">This visual is an example. Real answers require indexed sources.</p>
        </motion.div>
      </section>
      <section id="formats" className="py-14 md:py-20 border-t" style={{borderColor:'var(--line)'}} aria-labelledby="formats-title">
        <p className="text-xs font-bold uppercase tracking-[.22em] text-teal-300 mb-3">One workspace, many sources</p><h2 id="formats-title" className="text-3xl md:text-4xl font-bold tracking-tight">Bring the full picture together.</h2>
        <p className="muted max-w-2xl mt-4 leading-7">Different formats keep their own useful context, from a PDF page to a timestamp in a recording.</p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 mt-8">{sources.map(({icon:Icon,title,detail})=><div key={title} className="surface p-6"><div className="w-11 h-11 rounded-xl bg-teal-300/12 grid place-items-center mb-5"><Icon className="text-teal-300" size={22}/></div><h3 className="font-bold text-lg">{title}</h3><p className="muted mt-2 text-sm leading-6">{detail}</p></div>)}</div>
      </section>
      <section id="workflow" className="py-14 md:py-20 border-t" style={{borderColor:'var(--line)'}} aria-labelledby="workflow-title">
        <p className="text-xs font-bold uppercase tracking-[.22em] text-teal-300 mb-3">How Atlas works</p><h2 id="workflow-title" className="text-3xl md:text-4xl font-bold tracking-tight">A path from file to evidence.</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 mt-9">{steps.map(step=><div key={step.number} className="surface p-6"><span className="text-teal-300 font-mono text-sm">{step.number}</span><h3 className="font-bold text-lg mt-7">{step.title}</h3><p className="muted mt-3 text-sm leading-7">{step.detail}</p></div>)}</div>
      </section>
      <section id="capabilities" className="py-14 md:py-20 border-t" style={{borderColor:'var(--line)'}} aria-labelledby="capabilities-title">
        <div className="grid lg:grid-cols-[.8fr_1.2fr] gap-12"><div><p className="text-xs font-bold uppercase tracking-[.22em] text-teal-300 mb-3">Built for review</p><h2 id="capabilities-title" className="text-3xl md:text-4xl font-bold tracking-tight">Useful answers need visible evidence.</h2><p className="muted mt-5 leading-7">Atlas combines retrieval and source inspection. Its automated checks reduce some unsupported claims, but important decisions still need a human to review the original material.</p><div className="flex items-center gap-3 mt-7 muted text-sm"><Database size={18} className="text-teal-300"/> Local and cloud AI provider options</div></div>
          <div className="grid sm:grid-cols-2 gap-4">{capabilities.map(({icon:Icon,title,detail})=><div key={title} className="raised p-5"><Icon className="text-teal-300 mb-4" size={22}/><h3 className="font-semibold">{title}</h3><p className="muted mt-2 text-sm leading-6">{detail}</p></div>)}</div></div>
      </section>
      <section className="py-14 md:py-20 border-t" style={{borderColor:'var(--line)'}} aria-labelledby="uses-title"><p className="text-xs font-bold uppercase tracking-[.22em] text-teal-300 mb-3">In the workspace</p><h2 id="uses-title" className="text-3xl md:text-4xl font-bold tracking-tight">Explore, compare, and report.</h2><div className="grid md:grid-cols-3 gap-5 mt-8">
        <div className="surface p-6"><MessageSquareText className="text-teal-300 mb-5"/><h3 className="font-semibold text-lg">Ask across sources</h3><p className="muted text-sm mt-3 leading-7">Summarize documents, find risks, extract action items, and inspect citations.</p></div>
        <div className="surface p-6"><FolderSearch className="text-teal-300 mb-5"/><h3 className="font-semibold text-lg">Search and compare</h3><p className="muted text-sm mt-3 leading-7">Filter by file metadata and compare indexed revisions or table values.</p></div>
        <div className="surface p-6"><ShieldCheck className="text-teal-300 mb-5"/><h3 className="font-semibold text-lg">Keep a record</h3><p className="muted text-sm mt-3 leading-7">Return to conversations and export reports from your workspace.</p></div>
      </div></section>
      <section className="surface p-8 md:p-12 mb-16 flex flex-wrap justify-between items-center gap-7" aria-labelledby="cta-title"><div><h2 id="cta-title" className="text-2xl md:text-3xl font-bold">Ready to work with your own sources?</h2><p className="muted mt-3">Create an account and continue to your personal home page.</p></div><Link to="/register" className="action inline-flex items-center gap-2">Create account <ArrowRight size={17}/></Link></section>
    </main>
    <footer className="border-t px-6 py-7 muted text-sm" style={{borderColor:'var(--line)'}}><div className="max-w-7xl mx-auto flex flex-wrap gap-4 justify-between"><span>ATLAS · Document Intelligence</span><Link to="/login" className="hover:text-teal-300">Already have an account? Sign in</Link></div></footer>
  </div>
}
