import axiosInstance from '@/api/axiosInstance';
import { LoginRequest, RegisterRequest, AuthResponse } from '@/types/auth';

function saveToken(token: string) {
  localStorage.setItem('token', token);
}

function handleAuthError(error: any): string {
  if (error.response) {
    // Server responded with a status other than 2xx
    if (error.response.data?.message) {
      return error.response.data.message;
    }
    return `Error: ${error.response.status} ${error.response.statusText}`;
  } else if (error.request) {
    // Request was made but no response received
    return 'Network error: No response from server.';
  } else {
    // Something else happened
    return error.message || 'Unknown error occurred.';
  }
}

export const AuthService = {
  async login(data: LoginRequest): Promise<AuthResponse> {
    try {
      const response = await axiosInstance.post<AuthResponse>('/auth/login', data);
      saveToken(response.data.token);
      return response.data;
    } catch (error: any) {
      throw new Error(handleAuthError(error));
    }
  },

  async register(data: RegisterRequest): Promise<AuthResponse> {
    try {
      const response = await axiosInstance.post<AuthResponse>('/auth/register', data);
      saveToken(response.data.token);
      return response.data;
    } catch (error: any) {
      throw new Error(handleAuthError(error));
    }
  },
};
