import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { BarChart3, BookOpen, ChevronRight, FileBarChart2, FolderSearch, LayoutDashboard, LogOut, Menu, MessageSquareText, Moon, Shield, Sun, UploadCloud, X } from 'lucide-react'
import { motion } from 'framer-motion'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'

const items = [
  { to: '/app', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/app/upload', label: 'Upload center', icon: UploadCloud },
  { to: '/app/chat', label: 'Ask Atlas', icon: MessageSquareText },
  { to: '/app/search', label: 'Search', icon: FolderSearch },
  { to: '/app/reports', label: 'Reports', icon: FileBarChart2 }
]
export function Layout() {
  const [open, setOpen] = useState(false)
  const [theme, setTheme] = useState(localStorage.getItem('atlas_theme') || 'dark')
  const { user, refresh, clear } = useAuth()
  const navigate = useNavigate()
  const toggle = () => { const next = theme === 'dark' ? 'light' : 'dark'; setTheme(next); localStorage.setItem('atlas_theme', next); document.documentElement.dataset.theme = next }
  const logout = async () => { if (refresh) await api.post('/auth/logout', { refresh_token: refresh }).catch(() => {}); clear(); navigate('/login') }
  return <div className="min-h-screen md:flex">
    {open && <button aria-label="Close menu" className="fixed inset-0 bg-black/60 z-30 md:hidden" onClick={() => setOpen(false)} />}
    <aside className={`${open ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0 fixed md:sticky top-0 left-0 z-40 h-screen w-65 shrink-0 border-r p-5 transition-transform flex flex-col`} style={{background:'var(--surface)',borderColor:'var(--line)'}}>
      <div className="flex items-center justify-between mb-10"><div className="flex items-center gap-3"><span className="w-10 h-10 grid place-items-center rounded-xl bg-teal-300 text-slate-950"><BookOpen size={23}/></span><div><div className="font-extrabold tracking-wide">ATLAS<span style={{color:'var(--accent)'}}>.</span></div><div className="text-[10px] tracking-[.23em] muted uppercase">Document intelligence</div></div></div><button className="md:hidden" onClick={() => setOpen(false)}><X/></button></div>
      <p className="muted text-xs uppercase tracking-widest px-3 mb-3">Workspace</p>
      <nav className="space-y-1">{items.map(({to,label,icon:Icon,end}) => <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)} className={({isActive}) => `flex items-center gap-3 rounded-xl px-3 py-3 text-sm transition ${isActive ? 'bg-teal-300/15 text-teal-300 font-semibold' : 'muted hover:bg-white/5'}`}><Icon size={18}/>{label}</NavLink>)}{user?.role === 'admin' && <NavLink to="/app/admin" className={({isActive}) => `flex items-center gap-3 rounded-xl px-3 py-3 text-sm ${isActive ? 'bg-teal-300/15 text-teal-300' : 'muted'}`}><Shield size={18}/>Administration</NavLink>}</nav>
      <div className="mt-auto pt-7"><div className="raised p-3 mb-4"><div className="text-xs muted">Signed in as</div><div className="font-medium text-sm truncate mt-1">{user?.email}</div></div><button onClick={logout} className="flex items-center gap-2 muted hover:text-red-400 px-3 py-2"><LogOut size={18}/>Sign out</button></div>
    </aside>
    <main className="flex-1 min-w-0"><header className="h-18 px-5 md:px-9 flex items-center justify-between border-b" style={{borderColor:'var(--line)'}}><button className="md:hidden" onClick={() => setOpen(true)} aria-label="Open menu"><Menu/></button><div className="hidden md:flex items-center gap-2 text-sm muted"><span>Workspace</span><ChevronRight size={14}/><span style={{color:'var(--text)'}}>Intelligence hub</span></div><div className="flex items-center gap-3"><span className="tag hidden sm:inline-flex"><span className="w-1.5 h-1.5 bg-teal-300 rounded-full"/>Private workspace</span><button className="outline !p-2" aria-label="Toggle theme" onClick={toggle}>{theme === 'dark' ? <Sun size={17}/> : <Moon size={17}/>}</button><span className="w-9 h-9 rounded-full bg-indigo-400/20 grid place-items-center text-indigo-300 font-semibold">{user?.email[0].toUpperCase()}</span></div></header>
      <motion.div key={location.pathname} initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{duration:.24}} className="p-5 md:p-9 max-w-7xl mx-auto"><Outlet/></motion.div>
    </main>
  </div>
}
export function Heading({eyebrow,title,description,children}:{eyebrow:string,title:string,description:string,children?:React.ReactNode}) { return <div className="flex flex-wrap gap-4 justify-between items-end mb-8"><div><p className="text-xs font-bold uppercase tracking-[.22em] mb-3" style={{color:'var(--accent)'}}>{eyebrow}</p><h1 className="text-3xl md:text-4xl font-bold tracking-tight">{title}</h1><p className="muted mt-3 max-w-2xl">{description}</p></div>{children}</div> }
export function Empty({title,detail}:{title:string,detail:string}) { return <div className="surface text-center p-12"><BarChart3 className="mx-auto mb-4 muted" size={28}/><h3 className="font-semibold">{title}</h3><p className="muted text-sm mt-2">{detail}</p></div> }
