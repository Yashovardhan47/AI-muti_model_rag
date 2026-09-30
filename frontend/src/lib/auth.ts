import { create } from 'zustand'
import type { User } from './types'

type AuthState = { access: string | null; refresh: string | null; user: User | null; setTokens: (a: string, r: string, u: User) => void; clear: () => void }
const read = (key: string) => sessionStorage.getItem(key)
export const useAuth = create<AuthState>(set => ({
  access: read('atlas_access'), refresh: read('atlas_refresh'), user: (() => { try { return JSON.parse(read('atlas_user') || 'null') as User | null } catch { return null } })(),
  setTokens: (access, refresh, user) => { sessionStorage.setItem('atlas_access', access); sessionStorage.setItem('atlas_refresh', refresh); sessionStorage.setItem('atlas_user', JSON.stringify(user)); set({ access, refresh, user }) },
  clear: () => { ['atlas_access','atlas_refresh','atlas_user'].forEach(k => sessionStorage.removeItem(k)); set({ access: null, refresh: null, user: null }) }
}))
