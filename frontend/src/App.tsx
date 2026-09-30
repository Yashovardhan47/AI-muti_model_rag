import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { useAuth } from './lib/auth'
const Home = lazy(() => import('./pages/Home'))
const Auth = lazy(() => import('./pages/Auth'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Upload = lazy(() => import('./pages/Upload'))
const Chat = lazy(() => import('./pages/Chat'))
const Search = lazy(() => import('./pages/Search'))
const Reports = lazy(() => import('./pages/Reports'))
const Admin = lazy(() => import('./pages/Admin'))

export default function App() {
  const user = useAuth(s => s.user)
  return <Suspense fallback={<div className="min-h-screen grid place-items-center muted">Loading workspace…</div>}><Routes>
    <Route path="/" element={<Home/>}/>
    <Route path="/login" element={<Auth mode="login"/>}/>
    <Route path="/register" element={<Auth mode="register"/>}/>
    <Route path="/app" element={user ? <Layout/> : <Navigate to="/login" replace/>}>
      <Route index element={<Dashboard/>}/><Route path="upload" element={<Upload/>}/><Route path="chat" element={<Chat/>}/><Route path="search" element={<Search/>}/><Route path="reports" element={<Reports/>}/><Route path="admin" element={user?.role === 'admin' ? <Admin/> : <Navigate to="/app" replace/>}/>
    </Route><Route path="*" element={<Navigate to="/" replace/>}/>
  </Routes></Suspense>
}
