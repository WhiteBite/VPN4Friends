import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchMe } from '../src/api';
import * as telegram from '../src/telegram';

// Mock telegram.js
vi.mock('../src/telegram', () => ({
  getInitData: vi.fn(),
}));

describe('api.js request handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
    
    // Default valid init data to bypass the first check
    telegram.getInitData.mockReturnValue('query_id=123');
  });

  it('throws Error if telegram initData is empty in production', async () => {
    // Vite test runs in node; simulate prod behavior by empty initData
    telegram.getInitData.mockReturnValue('');
    
    // Simulate import.meta.env.DEV = false by mocking it? 
    // Vitest runs in dev normally, let's just make sure the error handling is fine if DEV was false.
    // Instead, let's mock DEV property for this test.
    const originalDev = import.meta.env.DEV;
    import.meta.env.DEV = false;
    
    await expect(fetchMe()).rejects.toThrow('Telegram не передал данные профиля (initData пуст)');
    
    import.meta.env.DEV = originalDev;
  });

  it('handles standard 200 JSON responses', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      text: () => Promise.resolve('{"data": 123}'),
    });

    const result = await fetchMe();
    expect(result).toEqual({ data: 123 });
    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-Telegram-Init-Data': 'query_id=123'
        })
      })
    );
  });

  it('throws Error when success is false in 200 OK body', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      text: () => Promise.resolve('{"success": false, "message": "Backend logically failed"}'),
    });

    await expect(fetchMe()).rejects.toThrow('Backend logically failed');
  });

  it('throws Error with detail from 4xx Error', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: () => Promise.resolve('{"detail": "Bad request"}'),
    });

    await expect(fetchMe()).rejects.toThrow('Bad request');
  });
});
