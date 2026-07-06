import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { ThemeProvider } from '../context/ThemeContext';

// Mock API
vi.mock('../utils/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

// Mock useAuth
vi.mock('../context/AuthContext', async () => {
  const actual = await vi.importActual('../context/AuthContext');
  return {
    ...actual,
    useAuth: () => ({
      user: { id: 1, username: 'testuser', is_superuser: false },
      loading: false,
    }),
  };
});

import Community from '../pages/Community';
import api from '../utils/api';

const renderWithProviders = (component, initialEntries = ['/']) => {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <ThemeProvider>
        <AuthProvider>
          {component}
        </AuthProvider>
      </ThemeProvider>
    </MemoryRouter>
  );
};

describe('Community Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', async () => {
    api.get.mockResolvedValue({ data: { results: [], count: 0 } });
    renderWithProviders(<Community />);
    expect(screen.getByText(/community/i)).toBeInTheDocument();
  });

  it('displays posts when loaded', async () => {
    api.get.mockResolvedValue({
      data: {
        results: [
          {
            id: 1,
            title: 'Test Post',
            content: 'Test content',
            user: { username: 'testuser' },
            likes: 5,
            views: 10,
            created_at: '2024-01-01T00:00:00Z',
            category: 'general',
            comments: [],
          },
        ],
        count: 1,
      },
    });

    renderWithProviders(<Community />);
    await waitFor(() => {
      expect(screen.getByText('Test Post')).toBeInTheDocument();
    });
  });

  it('shows empty state when no posts', async () => {
    api.get.mockResolvedValue({ data: { results: [], count: 0 } });
    renderWithProviders(<Community />);
    await waitFor(() => {
      expect(screen.getByText(/no posts/i)).toBeInTheDocument();
    });
  });
});
