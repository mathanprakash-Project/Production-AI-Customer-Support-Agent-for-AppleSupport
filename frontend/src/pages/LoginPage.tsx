import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Twitter, Lock, Mail, User as UserIcon, ArrowRight, Sun, Moon, UserCheck } from 'lucide-react';
import { api } from '../services/apiClient';
import { useAuthStore } from '../stores/authStore';
import { useTheme } from '../context/ThemeContext';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const { theme, toggleTheme } = useTheme();

  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      if (mode === 'login') {
        const data = await api.login(email, password);
        setAuth(data.access_token, data.user);
        navigate('/inbox');
      } else {
        await api.register(email, password, fullName || 'Support Agent', 'agent');
        setSuccess('Support Agent account created successfully! Please sign in with your credentials.');
        setMode('login');
        setPassword('');
      }
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          (mode === 'login'
            ? 'Invalid email or password. Please verify your credentials.'
            : 'Failed to create account. Ensure email is valid and not already registered.')
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-between bg-slate-50 dark:bg-black text-slate-900 dark:text-neutral-100 transition-colors duration-200 font-sans p-4 sm:p-8 animate-fade-in">
      {/* Top Header Navigation */}
      <header className="w-full max-w-6xl mx-auto flex items-center justify-between py-4">
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-xl bg-black dark:bg-white text-white dark:text-black flex items-center justify-center font-bold shadow-sm">
            <Twitter className="h-5 w-5 fill-current" />
          </div>
          <div>
            <h1 className="font-bold text-slate-900 dark:text-white text-base tracking-tight leading-tight">
              Apple Support Workspace
            </h1>
            <p className="text-xs text-slate-400 dark:text-neutral-500 font-medium">@AppleSupport Customer AI Agent</p>
          </div>
        </div>

        <button
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          className="p-2.5 rounded-full text-slate-500 dark:text-neutral-400 hover:bg-slate-200/60 dark:hover:bg-neutral-800 transition border border-slate-200 dark:border-neutral-800"
        >
          {theme === 'dark' ? (
            <Sun className="h-4 w-4 text-amber-400" />
          ) : (
            <Moon className="h-4 w-4 text-slate-700" />
          )}
        </button>
      </header>

      {/* Center Auth Box */}
      <div className="w-full max-w-md mx-auto my-auto py-8">
        <div className="card p-8 card-hover">
          {/* Mode Selector Tabs */}
          <div className="flex items-center p-1 bg-slate-100 dark:bg-black rounded-full border border-slate-200 dark:border-neutral-800 mb-6">
            <button
              type="button"
              onClick={() => {
                setMode('login');
                setError(null);
                setSuccess(null);
              }}
              className={`flex-1 py-2 text-xs font-bold rounded-full transition-all text-center ${
                mode === 'login'
                  ? 'bg-white dark:bg-neutral-800 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-500 dark:text-neutral-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('register');
                setError(null);
                setSuccess(null);
              }}
              className={`flex-1 py-2 text-xs font-bold rounded-full transition-all text-center ${
                mode === 'register'
                  ? 'bg-white dark:bg-neutral-800 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-500 dark:text-neutral-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              Create Account
            </button>
          </div>

          <div className="mb-6">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
              {mode === 'login' ? 'Sign in to your account' : 'Register new agent account'}
            </h2>
            <p className="text-xs text-slate-500 dark:text-neutral-400 mt-1">
              {mode === 'login'
                ? 'Sign in with your Support Agent or Manager credentials.'
                : 'Register a new Tier-1 Support Agent account for @AppleSupport frontline operations.'}
            </p>
          </div>

          {success && (
            <div className="mb-5 p-3.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs rounded-xl font-medium">
              {success}
            </div>
          )}

          {error && (
            <div className="mb-5 p-3.5 bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs rounded-xl font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <>
                <div>
                  <label className="block section-title mb-1.5">
                    Full Name
                  </label>
                  <div className="relative">
                    <UserIcon className="absolute left-3.5 top-2.5 h-4 w-4 text-slate-400 dark:text-neutral-500" />
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      required
                      className="input-field pl-10"
                      placeholder="e.g. Jane Doe"
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-2.5 px-3.5 py-2.5 bg-sky-500/10 border border-sky-500/20 rounded-xl text-sky-600 dark:text-sky-400 text-xs font-medium">
                  <UserCheck className="h-4 w-4 flex-shrink-0" />
                  <span>Role: <strong>Tier-1 Support Agent</strong></span>
                </div>
              </>
            )}

            <div>
              <label className="block section-title mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-2.5 h-4 w-4 text-slate-400 dark:text-neutral-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="input-field pl-10"
                  placeholder="agent@tweetsupport.local"
                />
              </div>
            </div>

            <div>
              <label className="block section-title mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-2.5 h-4 w-4 text-slate-400 dark:text-neutral-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="input-field pl-10"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full mt-2 flex items-center justify-center space-x-2"
            >
              <span>
                {loading
                  ? mode === 'login'
                    ? 'Authenticating...'
                    : 'Creating Account...'
                  : mode === 'login'
                  ? 'Sign In to Workspace'
                  : 'Create Agent Account'}
              </span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>

      {/* Footer */}
      <footer className="w-full max-w-6xl mx-auto py-4 text-center text-xs text-slate-400 dark:text-neutral-600 font-medium border-t border-slate-200/50 dark:border-neutral-900">
        Apple Support Customer Service AI Agent • GKE Production Release
      </footer>
    </div>
  );
};
