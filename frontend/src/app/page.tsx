'use client';

import { useSyncExternalStore } from 'react';
import { useAuthStore } from '@/hooks/useAppState';
import Dashboard from '@/components/Dashboard';
import LoginPage from '@/components/LoginPage';

// Custom hook to handle hydration
function useHydrated() {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );
}

export default function Home() {
  const { isAuthenticated, token } = useAuthStore();
  const isHydrated = useHydrated();

  // Show loading state while hydrating
  if (!isHydrated) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Show login page if not authenticated
  if (!isAuthenticated && !token) {
    return <LoginPage />;
  }

  // Show dashboard if authenticated
  return <Dashboard />;
}
