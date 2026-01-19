'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/hooks/useAppState';
import LoginPage from '@/components/LoginPage';

export default function LoginRoute() {
  const router = useRouter();
  const { isAuthenticated, token } = useAuthStore();

  // Redirect to home if already authenticated
  useEffect(() => {
    if (isAuthenticated && token) {
      router.push('/');
    }
  }, [isAuthenticated, token, router]);

  // If already authenticated, show nothing while redirecting
  if (isAuthenticated && token) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500 mx-auto mb-4" />
          <p className="text-gray-600">Redirecting...</p>
        </div>
      </div>
    );
  }

  return <LoginPage />;
}
