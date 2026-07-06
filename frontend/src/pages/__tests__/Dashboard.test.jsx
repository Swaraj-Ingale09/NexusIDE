import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { ThemeProvider } from '../context/ThemeContext';

vi.mock('../utils/api', () => ({
  default: { get: vi.fn(), post: vi.fn() },
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

import Dashboard from '../pages/Dashboard';

const renderWithProviders = (component) => {
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <ThemeProvider>
        <AuthProvider>
          {component}
        </AuthProvider>
      </ThemeProvider>
    </MemoryRouter>
  );
};

describe('Dashboard Page', () => {
  it('renders without crashing', () => {
    renderWithProviders(<Dashboard />);
  });

  it('shows user greeting', () => {
    renderWithProviders(<Dashboard />);
    expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
  });
});
