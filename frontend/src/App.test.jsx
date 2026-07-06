import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

// Mock the lazy-loaded components
vi.mock('./pages/Home', () => ({
  default: () => <div data-testid="home-page">Home Page</div>,
}));

vi.mock('./pages/Login', () => ({
  default: () => <div data-testid="login-page">Login Page</div>,
}));

vi.mock('./pages/Register', () => ({
  default: () => <div data-testid="register-page">Register Page</div>,
}));

vi.mock('./pages/NotFound', () => ({
  default: () => <div data-testid="not-found-page">Not Found</div>,
}));

describe('App Component', () => {
  it('renders without crashing', () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );
  });

  it('renders home page on default route', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByTestId('home-page')).toBeInTheDocument();
  });

  it('renders login page on /login route', () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
  });

  it('renders 404 page for unknown routes', () => {
    render(
      <MemoryRouter initialEntries={['/unknown-route']}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByTestId('not-found-page')).toBeInTheDocument();
  });

  it('opens command palette with Ctrl+K', () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );

    // Simulate Ctrl+K
    fireEvent.keyDown(window, { key: 'k', ctrlKey: true });

    // Command palette should be visible (we can check for its presence)
    // Note: This test assumes CommandPalette component has some testable output
  });

  it('opens keyboard shortcuts modal with Ctrl+/', () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );

    // Simulate Ctrl+/
    fireEvent.keyDown(window, { key: '/', ctrlKey: true });

    // Shortcuts modal should be visible
  });
});

describe('Page Transitions', () => {
  it('applies animation classes to pages', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    const homePage = screen.getByTestId('home-page');
    expect(homePage.closest('[class*="motion"]')).toBeInTheDocument();
  });
});

describe('Error Handling', () => {
  it('has error boundary wrapper', () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );

    // Error boundary should be present
    // This is a basic check - in real tests you'd throw an error to test boundary
  });
});
