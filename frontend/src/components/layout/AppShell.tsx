import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Inbox,
  BarChart3,
  BookOpen,
  Settings,
  LogOut,
  Sparkles,
  ShieldCheck,
  Sun,
  Moon,
  Shield,
  UserCheck,
  Twitter,
  Users,
} from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { useTheme } from '../../context/ThemeContext';

interface AppShellProps {
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { theme, toggleTheme } = useTheme();

  const isAdmin = user?.role === 'admin';
  const isManager = user?.role === 'manager' || user?.email?.toLowerCase() === 'mathanprakashselvam@gmail.com';
  const canMonitorUsers = isAdmin || isManager;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const frontlineNav = [
    { label: 'Agent Inbox', path: '/inbox', icon: Inbox },
  ];

  const governanceNav = [
    { label: 'Analytics & ROI', path: '/analytics', icon: BarChart3 },
    { label: 'Knowledge Base', path: '/knowledge', icon: BookOpen },
    { label: 'Evaluation Benchmark', path: '/eval', icon: ShieldCheck, adminOnly: true },
    { label: 'Intent Taxonomy', path: '/intents', icon: Sparkles },
    { label: 'User Monitoring', path: '/users', icon: Users, privilegedOnly: true },
    { label: 'System & Rules', path: '/settings', icon: Settings, adminOnly: true },
  ];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 dark:bg-black text-slate-900 dark:text-neutral-100 font-sans transition-colors duration-200">
      {/* Sidebar - X (Twitter) Inspired */}
      <aside className="w-64 flex-shrink-0 bg-white dark:bg-black text-slate-700 dark:text-neutral-300 flex flex-col justify-between border-r border-slate-200 dark:border-neutral-800 select-none">
        <div className="flex-1 overflow-y-auto">
          {/* Brand Header */}
          <div className="p-5 border-b border-slate-100 dark:border-neutral-800 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="h-9 w-9 rounded-xl bg-black dark:bg-white text-white dark:text-black flex items-center justify-center font-bold shadow-sm">
                <Twitter className="h-5 w-5 fill-current" />
              </div>
              <div>
                <h1 className="font-bold text-slate-900 dark:text-white text-base tracking-tight leading-tight flex items-center space-x-1.5">
                  <span>Apple Support</span>
                </h1>
                <p className="text-xs text-slate-400 dark:text-neutral-500 font-medium">@AppleSupport Workspace</p>
              </div>
            </div>

            {/* Light / Dark Mode Toggle */}
            <button
              onClick={toggleTheme}
              title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
              className="p-2 rounded-full text-slate-500 dark:text-neutral-400 hover:bg-slate-100 dark:hover:bg-neutral-800 transition"
            >
              {theme === 'dark' ? (
                <Sun className="h-4 w-4 text-amber-400" />
              ) : (
                <Moon className="h-4 w-4 text-slate-700" />
              )}
            </button>
          </div>

          {/* Frontline Operations Section */}
          <div className="p-3">
            <div className="px-3 py-2 text-[11px] font-bold text-slate-400 dark:text-neutral-500 uppercase tracking-wider">
              Operations
            </div>
            <nav className="space-y-1">
              {frontlineNav.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname.startsWith(item.path);
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center justify-between px-3 py-2.5 rounded-full text-sm font-semibold transition-all ${
                      isActive
                        ? 'bg-sky-500/10 text-sky-600 dark:text-sky-400 font-bold'
                        : 'hover:bg-slate-100 dark:hover:bg-neutral-900 text-slate-700 dark:text-neutral-300'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <Icon className={`h-5 w-5 ${isActive ? 'text-sky-500' : 'text-slate-500 dark:text-neutral-400'}`} />
                      <span>{item.label}</span>
                    </div>
                    {!isAdmin && (
                      <span className="text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 px-2 py-0.5 rounded-full font-bold border border-emerald-500/20">
                        Live
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* System Governance Section */}
          <div className="p-3 pt-0">
            <div className="px-3 py-2 text-[11px] font-bold text-slate-400 dark:text-neutral-500 uppercase tracking-wider flex items-center justify-between">
              <span>Governance & AI</span>
              {isAdmin && (
                <span className="text-[10px] bg-purple-500/10 text-purple-600 dark:text-purple-400 px-2 py-0.5 rounded-full font-bold border border-purple-500/20">
                  Admin Lead
                </span>
              )}
              {isManager && (
                <span className="text-[10px] bg-amber-500/10 text-amber-600 dark:text-amber-400 px-2 py-0.5 rounded-full font-bold border border-amber-500/20">
                  Manager
                </span>
              )}
            </div>
            <nav className="space-y-1">
              {governanceNav.map((item: any) => {
                if (item.adminOnly && !isAdmin) return null;
                if (item.privilegedOnly && !canMonitorUsers) return null;

                const Icon = item.icon;
                const isActive = location.pathname.startsWith(item.path);
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center justify-between px-3 py-2.5 rounded-full text-sm font-semibold transition-all ${
                      isActive
                        ? 'bg-sky-500/10 text-sky-600 dark:text-sky-400 font-bold'
                        : 'hover:bg-slate-100 dark:hover:bg-neutral-900 text-slate-700 dark:text-neutral-300'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <Icon className={`h-5 w-5 ${isActive ? 'text-sky-500' : 'text-slate-500 dark:text-neutral-400'}`} />
                      <span>{item.label}</span>
                    </div>
                    {item.adminOnly && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full font-bold border bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20">
                        Admin
                      </span>
                    )}
                    {item.privilegedOnly && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full font-bold border bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20">
                        Lead
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>

        {/* User Profile & Role Footer */}
        <div className="p-4 border-t border-slate-100 dark:border-neutral-800 bg-slate-50/50 dark:bg-neutral-950/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3 overflow-hidden">
              <div className={`h-9 w-9 rounded-full flex items-center justify-center text-xs font-bold text-white shadow-sm flex-shrink-0 ${
                isManager ? 'bg-amber-600' : isAdmin ? 'bg-purple-600' : 'bg-sky-600'
              }`}>
                {isAdmin ? <Shield className="h-4 w-4" /> : <UserCheck className="h-4 w-4" />}
              </div>
              <div className="truncate">
                <p className="text-xs font-bold text-slate-900 dark:text-white truncate">
                  {user?.full_name || (isManager ? 'Manager-Users' : isAdmin ? 'Operations Admin' : 'Support Agent')}
                </p>
                <div className="flex items-center space-x-1.5 mt-0.5">
                  <span className={`inline-block w-1.5 h-1.5 rounded-full ${
                    isManager ? 'bg-amber-500' : isAdmin ? 'bg-purple-500' : 'bg-emerald-500'
                  }`} />
                  <span className={`text-[10px] font-bold tracking-tight uppercase ${
                    isManager
                      ? 'text-amber-600 dark:text-amber-400'
                      : isAdmin
                      ? 'text-purple-600 dark:text-purple-400'
                      : 'text-emerald-600 dark:text-emerald-400'
                  }`}>
                    {isManager ? 'Manager-Users' : isAdmin ? 'Operations Lead' : 'Tier-1 Agent'}
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Sign Out"
              className="p-2 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-500/10 rounded-full transition"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 h-full min-h-0 overflow-hidden flex flex-col bg-slate-50 dark:bg-black transition-colors duration-200 animate-fade-in">
        {children}
      </main>
    </div>
  );
};
