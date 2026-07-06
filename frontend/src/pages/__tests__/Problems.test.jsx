import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { ThemeProvider } from '../context/ThemeContext';

vi.mock('../utils/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

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

import Problems from '../pages/Problems';
import api from '../utils/api';

const renderWithProviders = (component, initialEntries = ['/problems']) => {
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

describe('Problems Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', async () => {
    api.get.mockResolvedValue({ data: { results: [], count: 0 } });
    renderWithProviders(<Problems />);
    expect(screen.getByText(/problems/i)).toBeInTheDocument();
  });

  it('displays problem list', async () => {
    api.get.mockResolvedValue({
      data: {
        results: [
          {
            id: 1,
            title: 'Two Sum',
            difficulty: 'easy',
            category: 'arrays',
            submissions_count: 100,
          },
        ],
        count: 1,
      },
    });

    renderWithProviders(<Problems />);
    await waitFor(() => {
      expect(screen.getByText('Two Sum')).toBeInTheDocument();
    });
  });

  it('filters by difficulty', async () => {
    api.get.mockResolvedValue({ data: { results: [], count: 0 } });
    renderWithProviders(<Problems />);
    // Filter buttons should be present
    await waitFor(() => {
      expect(screen.getByText(/easy/i)).toBeInTheDocument();
    });
  });
});
