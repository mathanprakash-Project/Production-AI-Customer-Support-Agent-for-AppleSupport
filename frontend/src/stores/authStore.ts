import { create } from 'zustand';
import { User } from '../types';

interface AuthState {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

function isTokenValid(token: string | null): boolean {
  if (!token) return false;
  try {
    const payloadBase64 = token.split('.')[1];
    if (!payloadBase64) return false;
    const payloadJson = JSON.parse(atob(payloadBase64));
    if (payloadJson.exp && payloadJson.exp * 1000 < Date.now()) {
      return false; // Expired
    }
    return true;
  } catch {
    return false;
  }
}

export const useAuthStore = create<AuthState>((set, get) => {
  const savedToken = localStorage.getItem('token');
  const savedUser = localStorage.getItem('user');
  const validToken = isTokenValid(savedToken) ? savedToken : null;

  if (!validToken && savedToken) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }

  return {
    token: validToken,
    user: validToken && savedUser ? JSON.parse(savedUser) : null,

    setAuth: (token: string, user: User) => {
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
      set({ token, user });
    },

    logout: () => {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      set({ token: null, user: null });
    },

    isAuthenticated: () => {
      const currentToken = get().token;
      if (!isTokenValid(currentToken)) {
        if (currentToken) get().logout();
        return false;
      }
      return true;
    },
  };
});
