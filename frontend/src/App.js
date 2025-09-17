import './App.css';
import './styles/theme.css';
import api, { setOnUnauthorized } from './lib/api';
import { ensureShareLink } from './lib/sharing';
import CopyButton from './components/CopyButton.jsx';
import SecuritySettings from './SecuritySettings';
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';

const Toggle = ({ id, checked, onChange, label }) => (
  <label className="toggle" htmlFor={id}>
    <input
      id={id}
      type="checkbox"
      className="toggle-input sr-only"
      checked={checked}
      onChange={(e) => onChange(e.target.checked)}
    />
    <span className="toggle-track" aria-hidden="true">
      <span className="toggle-thumb" />
    </span>
    <span className="toggle-text">{label}</span>
  </label>
);

const LoginForm = ({
  email, setEmail,
  password, setPassword,
  onLogin,
  onSwitchToRegister,
  onShowForgotPassword
}) => (
  <div className="auth-form">
    <h2>Sign in</h2>

    <input
      type="email"
      placeholder="Email"
      value={email}
      onChange={(e) => setEmail(e.target.value)}
      className="form-input"
      autoComplete="username"
    />

    <input
      type="password"
      placeholder="Password"
      value={password}
      onChange={(e) => setPassword(e.target.value)}
      className="form-input"
      autoComplete="current-password"
    />

    <div className="auth-buttons">
      <button type="button" onClick={onLogin} className="btn-primary">Login</button>
      <button type="button" onClick={onSwitchToRegister} className="btn-secondary">
        No account? Sign up
      </button>
    </div>

    <button
      type="button"
      onClick={onShowForgotPassword}
      className="btn-link forgot-link"
    >
      Forgot password?
    </button>
  </div>
);

const RegisterForm = ({ email, setEmail, password, setPassword, onRegister, onSwitchToLogin }) => (
  <div className="auth-form">
    <h2>Sign up</h2>
    <input
      type="email"
      placeholder="Email"
      value={email}
      onChange={(e) => setEmail(e.target.value)}
      className="form-input"
    />
    <input
      type="password"
      placeholder="Password"
      value={password}
      onChange={(e) => setPassword(e.target.value)}
      className="form-input"
    />
    <div className="auth-buttons">
      <button onClick={onRegister} className="btn-primary">Register</button>
      <button onClick={onSwitchToLogin} className="btn-secondary"> Back to sign in</button>
    </div>
  </div>
);

const VerificationForm = ({
  title,
  message,
  verificationCode,
  setVerificationCode,
  onVerify,
  onCancel
}) => (
  <div className="auth-form">
    <h2>{title}</h2>
    <p>{message}</p>
    <input
      type="text"
      placeholder="Verification code"
      value={verificationCode}
      onChange={(e) => setVerificationCode(e.target.value)}
      className="form-input"
    />
    <div className="auth-buttons">
      <button onClick={onVerify} className="btn-primary" disabled={!verificationCode.trim()}>Verify</button>
      <button onClick={onCancel} className="btn-secondary">Back to sign in</button>
    </div>
  </div>
);

const ForgotPasswordForm = ({
  resetEmail, setResetEmail,
  onResetRequest,
  onBackToLogin,
  resetLoading,
  forgotCooldown
}) => (
  <div className="auth-form">
    <h2>Password recovery</h2>
    <p>Enter your email and we will send you a reset code</p>

    <input
      type="email"
      placeholder="Email"
      value={resetEmail}
      onChange={(e) => setResetEmail(e.target.value)}
      className="form-input"
      autoComplete="email"
    />

    <div className="auth-buttons">
      <button
        onClick={onResetRequest}
        disabled={resetLoading || forgotCooldown > 0 || !resetEmail.trim()}
        className="btn-primary"
        type="button"
      >
        {resetLoading ? 'Sending...' : (forgotCooldown > 0 ? `Resend in ${forgotCooldown}s` : 'Send code')}
      </button>

      <button onClick={onBackToLogin} className="btn-secondary" type="button">
        Back to sign in
      </button>
    </div>
  </div>
);

const ResetPasswordForm = ({
  resetEmail, setResetEmail,
  resetCode, setResetCode,
  newPassword, setNewPassword,
  onResetPassword,
  onBack,
  resetLoading,
  resetTTL
}) => (
  <div className="auth-form">
    <h2>Reset password</h2>
    <p>Enter the code you received by email and your new password</p>

    <input
      type="email"
      placeholder="Email"
      value={resetEmail}
      onChange={(e) => setResetEmail(e.target.value)}
      className="form-input"
      autoComplete="email"
    />

    <input
      type="text"
      placeholder="Verification code"
      value={resetCode}
      onChange={(e) => setResetCode(e.target.value)}
      className="form-input"
      inputMode="numeric"
    />

    <div className="code-hint">
      {resetTTL > 0 ? `Code expires in ${resetTTL}s` : 'Code expired — request a new one from previous screen.'}
    </div>

    <input
      type="password"
      placeholder="New password"
      value={newPassword}
      onChange={(e) => setNewPassword(e.target.value)}
      className="form-input"
      autoComplete="new-password"
    />

    <div className="auth-buttons">
      <button
        onClick={onResetPassword}
        disabled={resetLoading || resetTTL <= 0 || !resetEmail.trim() || !resetCode.trim() || !newPassword}
        className="btn-primary"
        type="button"
      >
        {resetLoading ? 'Resetting...' : 'Reset password'}
      </button>
      <button onClick={onBack} className="btn-secondary" type="button">Back</button>
    </div>
  </div>
);


const FileList = ({ files, shareLinks, onCreateShareLink, shareSettings, onDeleteFile, deletingId }) => (
  <div className="file-list">
    <h2>Your Files</h2>
    {files.length === 0 ? (
      <p className="no-files">No files yet — upload your first one.</p>
    ) : (
      <table className="files-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Size</th>
            <th>Link</th>
          </tr>
        </thead>
        <tbody>
          {files.map(f => (
            <tr key={f.id}>
              <td>{f.filename}</td>
              <td>{(f.size / 1024).toFixed(1)} KB</td>
              <td>
                {shareLinks[f.id] ? (
                  <div className="share-link">
                    <a href={shareLinks[f.id]} target="_blank" rel="noopener noreferrer">Open</a>
                    <CopyButton text={shareLinks[f.id]} />
                    <button onClick={() => onDeleteFile(f.id)} disabled={deletingId === f.id} className="btn-secondary">
                      {deletingId === f.id ? 'Deleting...' : 'Delete'}
                    </button>
                  </div>
                ) : (
                  <div className="share-link">
                    <button
                      onClick={() => onCreateShareLink(f.id, shareSettings)}
                      className="btn-primary"
                    >
                      Share
                    </button>
                    <button onClick={() => onDeleteFile(f.id)} disabled={deletingId === f.id} className="btn-secondary">
                      {deletingId === f.id ? 'Deleting...' : 'Delete'}
                    </button>
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    )}
  </div>
);

function App() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    setOnUnauthorized(() => () => {
      localStorage.removeItem('token');
      setUser(null);
      setAuthMode('login');
    });
  }, []);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authMode, setAuthMode] = useState('login');
  const [verificationCode, setVerificationCode] = useState('');
  const [userId, setUserId] = useState(null);
  const [authMessage, setAuthMessage] = useState('');

  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [resetLoading, setResetLoading] = useState(false);

  const [forgotCooldown, setForgotCooldown] = useState(0); 
  const [resetTTL, setResetTTL] = useState(0);             

  const [twoFaTTL, setTwoFaTTL] = useState(0);             
  const [twoFaCooldown, setTwoFaCooldown] = useState(0);   

  const [files, setFiles] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [shareLinks, setShareLinks] = useState({});
  const [expireDays, setExpireDays] = useState(7);
  const [maxViews, setMaxViews] = useState('');
  const [reuseExisting, setReuseExisting] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const [fileType, setFileType] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [totalFiles, setTotalFiles] = useState(0);
  const [sortBy, setSortBy] = useState('created_at');
  const [order, setOrder] = useState('desc');
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        setUser({ email: payload.sub });
      } catch {
        localStorage.removeItem('token');
      }
    }
  }, []);


  const register = async () => {
    try {
      const response = await api.post('/register', { email, password });
      if (response.data.requires_verification) {
        setUserId(response.data.user_id);
        setAuthMode('verifyEmail');
        setAuthMessage('Check your email for the verification code');
      } else {
        localStorage.setItem('token', response.data.access_token);
        setUser({ email });
      }
    } catch (error) {
      alert('Registration failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  const verifyEmail = async () => {
    try {
      const response = await api.post('/verify-email', { user_id: userId, code: verificationCode });
      localStorage.setItem('token', response.data.access_token);
      setUser({ email });
      setAuthMode('login');
    } catch (error) {
      alert('Verification failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  const login = async () => {
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      const response = await api.post('/token', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });

      if (response.status === 200) {
        localStorage.setItem('token', response.data.access_token);
        setUser({ email });
      } else if (response.status === 202) {
        setUserId(response.data.user_id);
        setAuthMode('verify2FA');
        setAuthMessage('Check your email for the 2FA code');
        setTwoFaTTL(60);
        setTwoFaCooldown(60);
      }
    } catch (error) {
      alert('Login failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  const resend2FACode = async () => {
    if (twoFaCooldown > 0) return;
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      const res = await api.post('/token', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      if (res.status === 202) {
        setTwoFaTTL(60);
        setTwoFaCooldown(60);
        setAuthMessage('A new 2FA code was sent to your email.');
      } else if (res.status === 200) {
        localStorage.setItem('token', res.data.access_token);
        setUser({ email });
        setAuthMode('login');
      }
    } catch (e) {
      alert('Failed to resend 2FA code: ' + (e.response?.data?.detail || e.message));
    }
  };

  const verify2FA = async () => {
    const code = (verificationCode || '').trim();
    if (!code) { setAuthMessage('Enter the 2FA code from the email.'); return; }
    try {
      const res = await api.post('/verify-2fa', { user_id: userId, code });
      localStorage.setItem('token', res.data.access_token);
      setUser({ email });
      setAuthMode('login');
      setAuthMessage('');
    } catch (err) {
      setAuthMessage(err?.response?.data?.detail || '2FA verification failed. Check the code and try again.');
    }
  };


  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    setAuthMode('login');
  };

  const handleForgotPasswordRequest = async () => {
    if (!resetEmail.trim() || forgotCooldown > 0) return;
    setResetLoading(true);
    try {
      await api.post('/forgot-password', { email: resetEmail });
      setAuthMessage('If the email is registered, a reset code has been sent.');
      setForgotCooldown(60);
      setResetTTL(60);
      setShowForgotPassword(false);
      setShowResetPassword(true);
    } catch (error) {
      setAuthMessage('Error requesting password reset: ' + (error.response?.data?.detail || error.message));
    }
    setResetLoading(false);
  };

  const handleResetPassword = async () => {
    if (!resetEmail.trim() || !resetCode.trim() || !newPassword) return;
    setResetLoading(true);
    try {
      await api.post('/reset-password', {
        email: resetEmail,
        code: resetCode,
        new_password: newPassword
      });
      setAuthMessage('Password changed successfully. You can now sign in with your new password.');
      setShowResetPassword(false);
      setAuthMode('login');
      setResetEmail('');
      setResetCode('');
      setNewPassword('');
      setResetTTL(0);
    } catch (error) {
      setAuthMessage('Error resetting password: ' + (error.response?.data?.detail || error.message));
    }
    setResetLoading(false);
  };

  const backToLoginFromReset = () => {
    setShowForgotPassword(false);
    setShowResetPassword(false);
    setResetEmail('');
    setResetCode('');
    setNewPassword('');
    setForgotCooldown(0);
    setResetTTL(0);
  };

  const deleteFile = async (fileId) => {
    try {
      setDeletingId(fileId);
      const attempts = [
        () => api.delete(`/files/${fileId}`),
        () => api.delete(`/file/${fileId}`),
        () => api.delete(`/files`, { params: { id: fileId } }),
        () => api.post(`/files/${fileId}/delete`),
      ];
      let lastError = null;
      for (const attempt of attempts) {
        try {
          await attempt();
          setFiles((prev) => prev.filter((f) => f.id !== fileId));
          setShareLinks((prev) => { const n = { ...prev }; delete n[fileId]; return n; });
          return;
        } catch (e) {
          lastError = e;
          const s = e?.response?.status;
          if (s === 404 || s === 405) continue;
          break;
        }
      }
      throw lastError || new Error('Failed to delete file');
    } catch (e) {
      alert('Delete failed: ' + (e.response?.data?.detail || e.message));
    } finally {
      setDeletingId(null);
    }
  };

  const uploadFile = async () => {
    if (!selectedFiles || selectedFiles.length === 0) return;
    setUploading(true);
    try {
      for (const f of selectedFiles) {
        const formData = new FormData();
        formData.append('file', f);
        const response = await api.post(`/upload?expire_days=${expireDays}`, formData);
        await createShareLink(response.data.id, { expireDays, maxViews, reuseExisting });
      }
      setSelectedFiles([]);
      await fetchFiles();
    } catch (error) {
      alert('Upload failed: ' + (error.response?.data?.detail || error.message));
    } finally {
      setUploading(false);
    }
  };

  const createShareLink = async (fileId, settings) => {
    try {
      const url = await ensureShareLink(fileId, settings);
      setShareLinks(prev => ({ ...prev, [fileId]: url }));
      return url;
    } catch (e) {
      alert('Failed to create share link: ' + (e.response?.data?.detail || e.message));
    }
  };

  const fetchFiles = async (signal = null) => {
    try {
      const config = signal ? { signal } : {};
      const params = {
        search: search.trim() || undefined,
        file_type: fileType || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        sort_by: sortBy,
        order,
        skip: (currentPage - 1) * itemsPerPage,
        limit: itemsPerPage,
      };
      Object.keys(params).forEach(key => params[key] === undefined && delete params[key]);
      const response = await api.get('/files', { params, ...config });
      setFiles(response.data.files);
      setTotalFiles(response.data.total);
    } catch (error) {
      if (error.name !== 'CanceledError') console.error('Failed to fetch files', error);
    }
  };

  const resetFilters = () => {
    setSearch('');
    setFileType('');
    setStartDate('');
    setEndDate('');
    setCurrentPage(1);
    setSortBy('created_at');
    setOrder('desc');
    setItemsPerPage(10);
  };

  useEffect(() => { setCurrentPage(1); },
    [search, fileType, startDate, endDate, itemsPerPage, sortBy, order]);

  useEffect(() => {
    if (!user) return;
    const controller = new AbortController();
    const timer = setTimeout(() => { fetchFiles(controller.signal); }, 300);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [user, search, fileType, startDate, endDate, currentPage, itemsPerPage, sortBy, order]);

  useEffect(() => {
    if (!forgotCooldown && !resetTTL && !twoFaTTL && !twoFaCooldown) return;
    const id = setInterval(() => {
      setForgotCooldown(s => (s > 0 ? s - 1 : 0));
      setResetTTL(s => (s > 0 ? s - 1 : 0));
      setTwoFaTTL(s => (s > 0 ? s - 1 : 0));
      setTwoFaCooldown(s => (s > 0 ? s - 1 : 0));
    }, 1000);
    return () => clearInterval(id);
  }, [forgotCooldown, resetTTL, twoFaTTL, twoFaCooldown]);


  const renderAuthForm = () => {
    if (showForgotPassword) {
      return (
        <ForgotPasswordForm
          resetEmail={resetEmail}
          setResetEmail={setResetEmail}
          onResetRequest={handleForgotPasswordRequest}
          onBackToLogin={backToLoginFromReset}
          resetLoading={resetLoading}
          forgotCooldown={forgotCooldown}
        />
      );
    }

    if (showResetPassword) {
      return (
        <ResetPasswordForm
          resetEmail={resetEmail}
          setResetEmail={setResetEmail}
          resetCode={resetCode}
          setResetCode={setResetCode}
          newPassword={newPassword}
          setNewPassword={setNewPassword}
          onResetPassword={handleResetPassword}
          onBack={() => { setShowResetPassword(false); setShowForgotPassword(true); }}
          resetLoading={resetLoading}
          resetTTL={resetTTL}
        />
      );
    }

    switch (authMode) {
      case 'register':
        return (
          <RegisterForm
            email={email}
            setEmail={setEmail}
            password={password}
            setPassword={setPassword}
            onRegister={register}
            onSwitchToLogin={() => setAuthMode('login')}
          />
        );

      case 'verifyEmail':
        return (
          <VerificationForm
            title="Email verification"
            message={authMessage}
            verificationCode={verificationCode}
            setVerificationCode={setVerificationCode}
            onVerify={verifyEmail}
            onCancel={() => setAuthMode('login')}
          />
        );

      case 'verify2FA':
        return (
          <div className="auth-form">
            <h2>Two-factor authentication</h2>
            <p>{authMessage || 'Check your email for the 2FA code'}</p>

            <input
              type="text"
              placeholder="Verification code"
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value)}
              className="form-input"
              inputMode="numeric"
              autoComplete="one-time-code"
            />

            {/* TTL и кулдаун */}
            <div className="code-hint">
              {twoFaTTL > 0 ? `` : 'Code expired — request a new one.'}
            </div>

            <div className="auth-buttons">
              <button
                onClick={verify2FA}
                className="btn-primary"
                disabled={!verificationCode.trim()}
              >
                Verify
              </button>

              <button
                onClick={async () => {
                  try {
                    const fd = new URLSearchParams();
                    fd.append('username', email);
                    fd.append('password', password);
                    const r = await api.post('/token', fd, {
                      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
                    });
                    if (r.status === 202) {
                      setTwoFaTTL(60);
                      setTwoFaCooldown(60);
                      setAuthMessage('New 2FA code sent to your email.');
                    }
                  } catch (e) {
                    setAuthMessage(e?.response?.data?.detail || e.message);
                  }
                }}
                className="btn-secondary"
                disabled={twoFaCooldown > 0}
                title={twoFaCooldown > 0 ? `Resend in ${twoFaCooldown}s` : 'Resend code'}
              >
                {twoFaCooldown > 0 ? `Resend in ${twoFaCooldown}s` : 'Resend code'}
              </button>

              <button
                onClick={() => setAuthMode('login')}
                className="btn-secondary"
              >
                Back
              </button>
            </div>
          </div>
        );


      default:
        return (
          <LoginForm
            email={email}
            setEmail={setEmail}
            password={password}
            setPassword={setPassword}
            onLogin={login}
            onSwitchToRegister={() => setAuthMode('register')}
            onShowForgotPassword={() => setShowForgotPassword(true)}
          />
        );
    }
  };

  if (!user) {
    return (
      <div className="container auth-container">
        <h1>SecureShare</h1>
        {renderAuthForm()}
      </div>
    );
  }

  return (
    <Router>
      <div className="container">
        <div className="header">
          <div className="brand"><span className="brand-badge"></span> SecureShare</div>
        </div>
        <header>
          <h1>SecureShare</h1>
          <nav>
            <Link to="/">Files</Link>
            <Link to="/settings/security">Security</Link>
          </nav>
          <button onClick={logout} className="btn-secondary">Logout</button>
        </header>

        <Routes>
          <Route path="/" element={
            <>
              <div className="sharing-settings">
                <h3>Sharing settings</h3>
                <div className="settings-grid">
                  <div className="setting-group">
                    <label>Expiration (days)</label>
                    <input
                      type="number"
                      min="1"
                      max="365"
                      value={expireDays}
                      onChange={(e) => setExpireDays(Number(e.target.value))}
                      className="form-input"
                    />
                  </div>

                  <div className="setting-group">
                    <label>Download limit</label>
                    <input
                      type="number"
                      min="1"
                      placeholder="By default one"
                      value={maxViews}
                      onChange={(e) => setMaxViews(e.target.value)}
                      className="form-input"
                    />
                  </div>
                </div>
              </div>

              <div className="search-and-filters">
                <div className="search-section">
                  <input
                    type="text"
                    placeholder="Search files by name"
                    value={search}
                    onChange={(e) => { setSearch(e.target.value); setCurrentPage(1); }}
                    className="form-input"
                  />
                  <button
                    onClick={() => setShowFilters(!showFilters)}
                    className="btn-secondary"
                  >
                    {showFilters ? 'Hide Filters' : 'Show Filters'}
                  </button>
                  <button onClick={resetFilters} className="btn-secondary">
                    Reset Filters
                  </button>
                </div>

                {showFilters && (
                  <div className="filters-panel">
                    <div className="filter-group">
                      <label>File Type</label>
                      <input
                        type="text"
                        placeholder="e.g., pdf, jpg, docx"
                        value={fileType}
                        onChange={(e) => setFileType(e.target.value)}
                        className="form-input"
                      />
                    </div>

                    <div className="filter-group">
                      <label>Start Date</label>
                      <input
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        className="form-input"
                      />
                    </div>

                    <div className="filter-group">
                      <label>End Date</label>
                      <input
                        type="date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        className="form-input"
                      />
                    </div>

                    <div className="filter-group">
                      <label>Items per page</label>
                      <select
                        value={itemsPerPage}
                        onChange={(e) => { setItemsPerPage(Number(e.target.value)); setCurrentPage(1); }}
                        className="form-input"
                      >
                        <option value={10}>10</option>
                        <option value={25}>25</option>
                        <option value={50}>50</option>
                        <option value={100}>100</option>
                      </select>
                    </div>
                  </div>
                )}
              </div>

              <div className="upload-section card">
                <label className="btn-primary">
                  {uploading ? 'Uploading...' : 'Select files'}
                  <input
                    type="file"
                    multiple
                    onChange={(e) => setSelectedFiles(Array.from(e.target.files || []))}
                    style={{ display: 'none' }}
                  />
                </label>
                {selectedFiles && selectedFiles.length > 0 && (
                  <div className="selected-files-hint">{`${selectedFiles.length} file(s) selected`}</div>
                )}
                <button onClick={uploadFile} disabled={uploading} className="btn-primary">
                  Upload selected
                </button>
              </div>

              <FileList
                files={files}
                shareLinks={shareLinks}
                onCreateShareLink={createShareLink}
                shareSettings={{ expireDays, maxViews, reuseExisting }}
                onDeleteFile={deleteFile}
                deletingId={deletingId}
              />

              {totalFiles > 0 && (
                <div className="pagination-footer">
                  <button
                    onClick={() => setCurrentPage(1)}
                    disabled={currentPage === 1}
                    className="btn-secondary"
                  >
                    First
                  </button>

                  <button
                    onClick={() => setCurrentPage(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="btn-secondary"
                  >
                    Previous
                  </button>

                  <span className="page-info">
                    Page {currentPage} of {Math.ceil(totalFiles / itemsPerPage)}
                  </span>

                  <button
                    onClick={() => setCurrentPage(currentPage + 1)}
                    disabled={currentPage >= Math.ceil(totalFiles / itemsPerPage)}
                    className="btn-secondary"
                  >
                    Next
                  </button>

                  <button
                    onClick={() => setCurrentPage(Math.ceil(totalFiles / itemsPerPage))}
                    disabled={currentPage >= Math.ceil(totalFiles / itemsPerPage)}
                    className="btn-secondary"
                  >
                    Last
                  </button>

                  <span className="total-info">Total files: {totalFiles}</span>
                </div>
              )}
            </>
          } />

          <Route path="/settings/security" element={
            <SecuritySettings api={api} />
          } />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
