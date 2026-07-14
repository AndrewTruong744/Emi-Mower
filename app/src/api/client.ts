import { create } from 'axios';
import { useBoundStore } from '../store/useBoundStore';

const client = create({
  baseURL: process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.request.use(
  (config) => {
    const idToken = useBoundStore.getState().idToken;
    if (idToken) {
      config.headers.Authorization = `Bearer ${idToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

client.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    const errorMsg = error.response?.data?.detail || error.message || 'API error';
    return Promise.reject(new Error(errorMsg));
  }
);

export default client;
