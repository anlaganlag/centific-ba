import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useAuthStore } from '../stores/authStore'

// Mock axios
vi.mock('../lib/api', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

describe('useAuthStore', () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore.setState({
      accessToken: null,
      refreshToken: null,
      user: null,
    })
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('should initialize with null tokens', () => {
    const { result } = renderHook(() => useAuthStore())
    expect(result.current.accessToken).toBeNull()
    expect(result.current.refreshToken).toBeNull()
    expect(result.current.user).toBeNull()
  })

  it('should clear tokens on logout', () => {
    const { result } = renderHook(() => useAuthStore())

    // Set some state
    act(() => {
      useAuthStore.setState({
        accessToken: 'test_token',
        refreshToken: 'test_refresh',
        user: { id: '1', email: 'test@test.com', display_name: 'Test' },
      })
    })

    // Logout
    act(() => {
      result.current.logout()
    })

    expect(result.current.accessToken).toBeNull()
    expect(result.current.refreshToken).toBeNull()
    expect(result.current.user).toBeNull()
  })

  it('should persist token to localStorage on login', async () => {
    const api = await import('../lib/api')
    const mockPost = vi.mocked(api.default.post)

    mockPost.mockResolvedValueOnce({
      data: {
        access_token: 'new_access_token',
        refresh_token: 'new_refresh_token',
      },
    })

    const { result } = renderHook(() => useAuthStore())

    await act(async () => {
      await result.current.login('test@test.com', 'password')
    })

    expect(localStorage.setItem).toHaveBeenCalledWith('access_token', 'new_access_token')
    expect(localStorage.setItem).toHaveBeenCalledWith('refresh_token', 'new_refresh_token')
  })
})
