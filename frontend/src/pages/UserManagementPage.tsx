import React, { useEffect, useState } from 'react';
import {
  Users,
  Shield,
  UserCheck,
  Trash2,
  AlertTriangle,
  RotateCw,
  Search,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { api } from '../services/apiClient';
import { useAuthStore } from '../stores/authStore';
import { User } from '../types';

export const UserManagementPage: React.FC = () => {
  const { user: currentUser } = useAuthStore();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const isSuperAdmin =
    currentUser?.email?.toLowerCase() === 'mathanprakashselvam@gmail.com' ||
    currentUser?.role === 'manager';

  const fetchUsers = async () => {
    setLoading(true);
    setActionError(null);
    try {
      const data = await api.getUsers();
      setUsers(data);
    } catch (err: any) {
      setActionError(err?.response?.data?.detail || 'Failed to fetch registered users.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleDeleteUser = async (userId: string, email: string) => {
    if (!window.confirm(`Are you sure you want to permanently delete user "${email}"? This action cannot be undone.`)) {
      return;
    }
    setDeletingId(userId);
    setActionError(null);
    setActionSuccess(null);
    try {
      await api.deleteUser(userId);
      setActionSuccess(`User "${email}" successfully deleted.`);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (err: any) {
      setActionError(err?.response?.data?.detail || 'Failed to delete user.');
    } finally {
      setDeletingId(null);
    }
  };

  const filteredUsers = users.filter(
    (u) =>
      u.role !== 'admin' &&
      (u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.role.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'admin':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
            <Shield className="h-3 w-3 mr-1" /> Operations Lead
          </span>
        );
      case 'manager':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            <UserCheck className="h-3 w-3 mr-1" /> Manager-Users
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <UserCheck className="h-3 w-3 mr-1" /> Tier-1 Agent
          </span>
        );
    }
  };

  return (
    <div className="flex-1 h-full min-h-0 flex flex-col overflow-hidden bg-slate-50 dark:bg-black text-slate-900 dark:text-neutral-100">
      {/* Top Header */}
      <header className="flex-shrink-0 bg-white dark:bg-black border-b border-slate-200 dark:border-neutral-800 px-6 py-3.5 flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center space-x-2">
              <Users className="h-5 w-5 text-sky-500" />
              <span>User Monitoring & Profiles</span>
            </h2>
            <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider border bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20">
              Manager-Users Control
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-neutral-400 mt-1">
            Real-time oversight of workspace accounts, onboarding profiles, and account permissions.
          </p>
        </div>
        <button
          onClick={fetchUsers}
          disabled={loading}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-100 dark:bg-neutral-900 hover:bg-slate-200 dark:hover:bg-neutral-800 text-slate-700 dark:text-neutral-300 text-xs font-bold rounded-full border border-slate-200 dark:border-neutral-800 transition"
        >
          <RotateCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-sky-500' : ''}`} />
          <span>Refresh</span>
        </button>
      </header>

      {/* Action Notification Banners */}
      {actionSuccess && (
        <div className="flex-shrink-0 bg-emerald-600 text-white text-xs py-2 px-6 font-bold flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="h-4 w-4" />
            <span>{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-white hover:underline text-xs">
            Dismiss
          </button>
        </div>
      )}

      {actionError && (
        <div className="flex-shrink-0 bg-rose-600 text-white text-xs py-2 px-6 font-bold flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4" />
            <span>{actionError}</span>
          </div>
          <button onClick={() => setActionError(null)} className="text-white hover:underline text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* Toolbar & Search */}
      <div className="flex-shrink-0 bg-white dark:bg-black border-b border-slate-200 dark:border-neutral-800 px-6 py-2.5 flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400 dark:text-neutral-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search users by name, email, or role..."
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-slate-50 dark:bg-neutral-950 border border-slate-200 dark:border-neutral-800 rounded-full text-slate-900 dark:text-neutral-100 placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
        </div>
        <div className="flex items-center space-x-4 text-xs font-semibold text-slate-500 dark:text-neutral-400">
          <span>Total Users: <strong className="text-slate-900 dark:text-white">{users.length}</strong></span>
          <span>Filtered: <strong className="text-slate-900 dark:text-white">{filteredUsers.length}</strong></span>
        </div>
      </div>

      {/* User Table Container */}
      <div className="flex-1 overflow-y-auto p-6 min-h-0">
        {loading ? (
          <div className="flex items-center justify-center h-48 text-slate-400 dark:text-neutral-500 text-sm">
            <RotateCw className="h-5 w-5 animate-spin mr-2 text-sky-500" />
            Loading registered users...
          </div>
        ) : filteredUsers.length === 0 ? (
          <div className="text-center py-16 bg-white dark:bg-neutral-900 rounded-2xl border border-slate-200 dark:border-neutral-800">
            <Users className="mx-auto h-12 w-12 text-slate-300 dark:text-neutral-700" />
            <h3 className="mt-3 text-sm font-bold text-slate-900 dark:text-white">No users found</h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-neutral-400 max-w-sm mx-auto">
              There are no registered accounts matching your search query.
            </p>
          </div>
        ) : (
          <div className="bg-white dark:bg-neutral-900 rounded-2xl border border-slate-200 dark:border-neutral-800 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-neutral-950/80 border-b border-slate-200 dark:border-neutral-800 text-slate-400 dark:text-neutral-500 uppercase tracking-wider font-bold">
                  <tr>
                    <th className="px-6 py-3.5">User Profile</th>
                    <th className="px-6 py-3.5">Email Address</th>
                    <th className="px-6 py-3.5">Workspace Role</th>
                    <th className="px-6 py-3.5">Registered On</th>
                    <th className="px-6 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-neutral-800/60 font-medium">
                  {filteredUsers.map((u) => {
                    const isSelf = currentUser?.id === u.id;
                    const canDelete = isSuperAdmin && !isSelf;

                    return (
                      <tr key={u.id} className="hover:bg-slate-50/60 dark:hover:bg-neutral-800/40 transition">
                        <td className="px-6 py-4">
                          <div className="flex items-center space-x-3">
                            <div className="h-8 w-8 rounded-full bg-slate-200 dark:bg-neutral-800 flex items-center justify-center font-bold text-slate-700 dark:text-neutral-300 text-xs">
                              {u.full_name ? u.full_name.charAt(0).toUpperCase() : u.email.charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <p className="font-bold text-slate-900 dark:text-white">{u.full_name || 'Support Agent'}</p>
                              <span className="text-[10px] text-slate-400 dark:text-neutral-500 font-mono">ID: {u.id.slice(0, 8)}</span>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 font-mono text-slate-700 dark:text-neutral-300">{u.email}</td>
                        <td className="px-6 py-4">{getRoleBadge(u.role)}</td>
                        <td className="px-6 py-4 text-slate-500 dark:text-neutral-400">
                          <div className="flex items-center space-x-1.5">
                            <Clock className="h-3.5 w-3.5" />
                            <span>
                              {new Date().toLocaleDateString(undefined, {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                              })}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-right">
                          {canDelete ? (
                            <button
                              onClick={() => handleDeleteUser(u.id, u.email)}
                              disabled={deletingId === u.id}
                              className="inline-flex items-center space-x-1 px-3 py-1 bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 font-bold text-xs rounded-full border border-rose-500/20 transition"
                              title="Delete user profile"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                              <span>{deletingId === u.id ? 'Deleting...' : 'Delete'}</span>
                            </button>
                          ) : isSelf ? (
                            <span className="text-[11px] text-slate-400 dark:text-neutral-600 italic">Current Session</span>
                          ) : (
                            <span className="text-[11px] text-slate-400 dark:text-neutral-600">Restricted</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

