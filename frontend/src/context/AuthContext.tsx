import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { User, AuthTokens } from '../types';
import { apiClient } from '../services/api';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string, fullName: string, department?: string) => Promise<User>;
  logout: () => void;
  refreshUserProfile: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshUserProfile = useCallback(async (): Promise<User | null> => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setUser(null);
        return null;
      }
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      const res = await apiClient.get<User>('/auth/me');
      setUser(res.data);
      return res.data;
    } catch {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      delete apiClient.defaults.headers.common['Authorization'];
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        await refreshUserProfile();
      }
      setIsLoading(false);
    };
    initAuth();
  }, [refreshUserProfile]);

  const login = async (email: string, password: string): Promise<User> => {
    const res = await apiClient.post<AuthTokens>('/auth/login', { email, password });
    localStorage.setItem('access_token', res.data.access_token);
    localStorage.setItem('refresh_token', res.data.refresh_token);
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${res.data.access_token}`;

    // Fetch and populate user profile
    const profileRes = await apiClient.get<User>('/auth/me');
    setUser(profileRes.data);
    return profileRes.data;
  };

  const register = async (
    email: string,
    password: string,
    fullName: string,
    department?: string
  ): Promise<User> => {
    await apiClient.post<User>('/auth/register', {
      email,
      password,
      full_name: fullName,
      department: department || 'General',
      role: 'user',
    });
    // Automatically log in after registration
    return await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    delete apiClient.defaults.headers.common['Authorization'];
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        refreshUserProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

