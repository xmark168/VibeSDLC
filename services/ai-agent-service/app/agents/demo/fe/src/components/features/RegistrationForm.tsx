import React, { useState } from 'react';
import { Spinner } from '@/components/common/Spinner';
import { AuthService } from '@/services/authService';
import { RegisterRequest } from '@/types/auth';

interface RegistrationFormProps {
  onSuccess?: () => void;
}

export const RegistrationForm: React.FC<RegistrationFormProps> = ({ onSuccess }) => {
  const [form, setForm] = useState<RegisterRequest>({ name: '', email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await AuthService.register(form);
      setLoading(false);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setLoading(false);
      setError(err.message || 'Registration failed.');
    }
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit} aria-label="Registration Form">
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-gray-700">Name</label>
        <input
          id="name"
          name="name"
          type="text"
          value={form.name}
          onChange={handleChange}
          required
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
        />
      </div>
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700">Email</label>
        <input
          id="email"
          name="email"
          type="email"
          value={form.email}
          onChange={handleChange}
          required
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
        />
      </div>
      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          value={form.password}
          onChange={handleChange}
          required
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
        />
      </div>
      {error && (
        <div className="text-red-600 text-sm" role="alert">{error}</div>
      )}
      <button
        type="submit"
        className="w-full py-2 px-4 bg-indigo-600 text-white font-semibold rounded-md shadow hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        disabled={loading}
        aria-busy={loading}
      >
        {loading ? (<><span className="flex items-center justify-center"><Spinner size={20} className="mr-2" aria-label="Registering" />Registering...</span></>) : 'Register'}
      </button>
    </form>
  );
};
