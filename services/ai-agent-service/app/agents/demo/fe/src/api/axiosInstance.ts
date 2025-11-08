import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// Placeholder for token retrieval logic
function getToken(): string | null {
  // TODO: Replace with actual implementation (e.g., Zustand store, localStorage)
  return localStorage.getItem('token');
}

const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

// Request interceptor
axiosInstance.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle global errors (e.g., unauthorized, network errors)
    // Example: if (error.response?.status === 401) { /* handle logout */ }
    return Promise.reject(error);
  }
);

export default axiosInstance;
