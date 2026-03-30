import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ConnectionCard from '../src/components/ConnectionCard';

describe('ConnectionCard Component', () => {

  it('renders request button when user has no profile', () => {
    const profile = { has_profile: false, request_status: null };
    render(<ConnectionCard profile={profile} onRequest={() => {}} />);
    
    expect(screen.getByText('Запросить доступ')).toBeInTheDocument();
    expect(screen.getByText('Нет VPN')).toBeInTheDocument();
  });

  it('renders pending state properly', () => {
    const profile = { has_profile: false, request_status: 'pending' };
    render(<ConnectionCard profile={profile} />);
    
    expect(screen.getByText('Заявка на рассмотрении')).toBeInTheDocument();
    expect(screen.queryByText('Запросить доступ')).not.toBeInTheDocument();
  });

  it('renders reject state and allows requesting again', () => {
    const profile = { has_profile: false, request_status: 'rejected' };
    render(<ConnectionCard profile={profile} />);
    
    expect(screen.getByText('Заявка отклонена')).toBeInTheDocument();
    expect(screen.getByText('Запросить повторно')).toBeInTheDocument();
  });

  it('calls onRequest when submitting the form', () => {
    const profile = { has_profile: false, request_status: null };
    const onRequestMock = vi.fn();
    
    render(<ConnectionCard profile={profile} onRequest={onRequestMock} />);
    
    // Open form
    fireEvent.click(screen.getByText('Запросить доступ'));
    
    // Type in textarea
    const textarea = screen.getByPlaceholderText(/зачем вам VPN/i);
    fireEvent.change(textarea, { target: { value: 'test reason' } });
    
    // Submit form
    fireEvent.click(screen.getByText('Отправить'));
    
    expect(onRequestMock).toHaveBeenCalledWith('test reason');
  });

  it('renders copy button when profile exists', () => {
    const profile = { has_profile: true };
    const onCopyMock = vi.fn();
    
    render(<ConnectionCard profile={profile} onCopySubscription={onCopyMock} />);
    
    expect(screen.getByText('Скопировать ссылку')).toBeInTheDocument();
    
    const copyButton = screen.getByText('Скопировать ссылку');
    fireEvent.click(copyButton);
    
    expect(onCopyMock).toHaveBeenCalled();
  });

});
