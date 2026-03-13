import { create } from 'zustand'
import api from '../lib/api'

interface User {
  id: string
  email: string
  display_name: string
}

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, displayName: string) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: localStorage.getItem('access_token'),
  refreshToken: localStorage.getItem('refresh_token'),
  user: null,

  login: async (email, password) => {
    const res = await api.post('/auth/login', { email, password })
    const { access_token, refresh_token } = res.data
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    set({ accessToken: access_token, refreshToken: refresh_token })
  },

  register: async (email, password, displayName) => {
    const res = await api.post('/auth/register', {
      email,
      password,
      display_name: displayName,
    })
    const { access_token, refresh_token } = res.data
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    set({ accessToken: access_token, refreshToken: refresh_token })
  },

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ accessToken: null, refreshToken: null, user: null })
  },

  fetchUser: async () => {
    const res = await api.get('/auth/me')
    set({ user: res.data })
  },
}))
