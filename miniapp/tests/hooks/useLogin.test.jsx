import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/preact';
import { useLogin } from '../../src/hooks/useLogin';

// Wrapper component to test the hook
function TestComponent({ onLogin }) {
  const login = useLogin(onLogin);
  return (
    <div>
      <div data-testid="mode">{login.mode}</div>
      <div data-testid="error">{login.error}</div>
      <div data-testid="loading">{login.loading ? 'true' : 'false'}</div>
      <input data-testid="username" onChange={(e) => login.setUsername(e.target.value)} />
      <input data-testid="token" onChange={(e) => login.setToken(e.target.value)} />
      
      <button data-testid="submit-username" onClick={login.handleUsernameSubmit}>Submit Username</button>
      <button data-testid="submit-token" onClick={login.handleTokenSubmit}>Submit Token</button>
    </div>
  );
}

describe('useLogin hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
    localStorage.clear();
  });

  it('initially in username mode', () => {
    render(<TestComponent onLogin={() => {}} />);
    expect(screen.getByTestId('mode').textContent).toBe('username');
    expect(screen.getByTestId('loading').textContent).toBe('false');
  });

  it('validates username input', async () => {
    render(<TestComponent onLogin={() => {}} />);
    
    // empty sumbit
    fireEvent.click(screen.getByTestId('submit-username'));
    expect(screen.getByTestId('error').textContent).toBe('Введите корректный @username');
    
    // single char submit
    const input = screen.getByTestId('username');
    fireEvent.change(input, { target: { value: 'a' } });
    fireEvent.click(screen.getByTestId('submit-username'));
    expect(screen.getByTestId('error').textContent).toBe('Введите корректный @username');
  });

  it('handles immediate approval username login', async () => {
    const onLoginMock = vi.fn();
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'approved', token: 'test-token-123' })
    });

    render(<TestComponent onLogin={onLoginMock} />);
    
    const input = screen.getByTestId('username');
    fireEvent.change(input, { target: { value: 'john' } });
    fireEvent.click(screen.getByTestId('submit-username'));
    
    expect(screen.getByTestId('loading').textContent).toBe('true');
    
    await waitFor(() => {
      expect(onLoginMock).toHaveBeenCalled();
      expect(localStorage.getItem('auth_token')).toBe('test-token-123');
    });
  });

  it('transitions to pending mode when logic returns pending', async () => {
    const onLoginMock = vi.fn();
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'pending', poll_token: 'poll-123', message: 'Wait' })
    });

    render(<TestComponent onLogin={onLoginMock} />);
    
    const input = screen.getByTestId('username');
    fireEvent.change(input, { target: { value: 'jane' } });
    fireEvent.click(screen.getByTestId('submit-username'));
    
    await waitFor(() => {
      expect(screen.getByTestId('mode').textContent).toBe('pending');
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });
  });

  it('validates token input', async () => {
    render(<TestComponent onLogin={() => {}} />);
    
    fireEvent.click(screen.getByTestId('submit-token'));
    expect(screen.getByTestId('error').textContent).toBe('Вставьте токен');
  });

  it('stores token and calls onLogin', async () => {
    const onLoginMock = vi.fn().mockResolvedValueOnce(true);
    render(<TestComponent onLogin={onLoginMock} />);
    
    const input = screen.getByTestId('token');
    fireEvent.change(input, { target: { value: 'my-manual-token' } });
    fireEvent.click(screen.getByTestId('submit-token'));
    
    await waitFor(() => {
      expect(onLoginMock).toHaveBeenCalled();
      expect(localStorage.getItem('auth_token')).toBe('my-manual-token');
    });
  });

  it('clears storage and shows error on failed token login', async () => {
    const onLoginMock = vi.fn().mockRejectedValueOnce(new Error('Fetch failed'));
    render(<TestComponent onLogin={onLoginMock} />);
    
    const input = screen.getByTestId('token');
    fireEvent.change(input, { target: { value: 'bad-token' } });
    fireEvent.click(screen.getByTestId('submit-token'));
    
    await waitFor(() => {
      expect(onLoginMock).toHaveBeenCalled();
      expect(localStorage.getItem('auth_token')).toBeNull();
      expect(screen.getByTestId('error').textContent).toBe('Fetch failed');
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });
  });
});
