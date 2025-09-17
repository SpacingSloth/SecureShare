import React, { useState, useEffect } from 'react';
import './SecuritySettings.css';

const SecuritySettings = ({ api }) => {
  const [is2FAEnabled, setIs2FAEnabled] = useState(false);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(true);
  const [message, setMessage] = useState('');

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);

  const fetch2FAStatus = async () => {
    try {
      setStatusLoading(true);
      const response = await api.get('/2fa-status');
      setIs2FAEnabled(response.data.two_factor_enabled);
    } catch (error) {
      console.error('Failed to fetch 2FA status', error);
      setMessage('Error retrieving 2FA status');
    } finally {
      setStatusLoading(false);
    }
  };

  useEffect(() => {
    fetch2FAStatus();
  }, []);

  const toggle2FA = async () => {
    setLoading(true);
    try {
      const endpoint = is2FAEnabled ? '/disable-2fa' : '/enable-2fa';
      const response = await api.post(endpoint);
      setIs2FAEnabled(response.data.enabled);
      setMessage(response.data.message);
    } catch (error) {
      console.error('Failed to toggle 2FA', error);
      setMessage('Error updating 2FA settings: ' + (error.response?.data?.detail || error.message));
      fetch2FAStatus(); 
    } finally {
      setLoading(false);
    }
  };

  const changePassword = async () => {
    if (newPassword !== confirmPassword) {
      setMessage('New password and confirmation do not match');
      return;
    }
    if (newPassword.length < 8) {
      setMessage('Password must be at least 8 characters');
      return;
    }

    setPasswordLoading(true);
    try {
      await api.post('/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setMessage('Password updated successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error) {
      console.error('Failed to change password', error);
      setMessage('Error updating password: ' + (error.response?.data?.detail || error.message));
    } finally {
      setPasswordLoading(false);
    }
  };

  if (statusLoading) {
    return (
      <div className="security-settings">
        <h2>Security</h2>
        <p className="loading-text">
          <span className="loading-indicator"></span>
          Loading 2FA status...
        </p>
      </div>
    );
  }

  return (
    <div className="security-settings">
      <h2>Security</h2>

      {message && (
        <div className={`message ${message.includes('Error') ? 'message-error' : 'message-success'}`}>
          {message}
        </div>
      )}

      <div className="setting-item">
        <h3>Two-factor authentication</h3>
        <p>
          Two-factor authentication adds an extra layer of security to your account,
          requiring more than just a password to sign in.
        </p>

        {/* небольшой гарантированный отступ над кнопкой */}
        <div className="status-text" style={{ marginBottom: '0.9rem' }}>
          Current status:{' '}
          <span className={`status-indicator ${is2FAEnabled ? 'status-enabled' : 'status-disabled'}`}>
            {is2FAEnabled ? 'Enabled' : 'Disabled'}
          </span>
        </div>

        <button
          onClick={toggle2FA}
          disabled={loading}
          className={is2FAEnabled ? 'btn-danger' : 'btn-primary'}
        >
          {loading ? 'Working...' : (is2FAEnabled ? 'Disable 2FA' : 'Enable 2FA')}
        </button>
      </div>

      <div className="setting-item">
        <h3>Change password</h3>
        <p>Changing your password regularly improves your account security.</p>

        {/* форма без автоподстановки */}
        <form
          className="password-form"
          autoComplete="off"
          onSubmit={(e) => { e.preventDefault(); changePassword(); }}
        >
          {/* Декой-поля: уводят менеджеры паролей от реального current password */}
          <input type="text" name="username" autoComplete="username" style={{ display: 'none' }} readOnly />
          <input type="password" name="password" autoComplete="new-password" style={{ display: 'none' }} readOnly />

          {/* Current password — отключаем автоподстановку */}
          <input
            id="currentPassword"
            type="password"
            className="form-input"
            placeholder="Current password"
            name="current_password_unmanaged"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            autoComplete="off"
            aria-autocomplete="none"
            autoCapitalize="off"
            autoCorrect="off"
            inputMode="text"
            data-lpignore="true"
            data-1p-ignore
            data-bwignore="true"
            onFocus={(e) => e.currentTarget.setAttribute('autocomplete', 'off')}
          />

          <input
            type="password"
            placeholder="New password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="form-input"
            name="new_password"
            autoComplete="new-password"
          />

          <input
            type="password"
            placeholder="Confirm new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="form-input"
            name="confirm_new_password"
            autoComplete="new-password"
          />

          <button
            type="submit"
            onClick={changePassword}
            disabled={passwordLoading}
            className="btn-primary"
          >
            {passwordLoading ? 'Updating...' : 'Update password'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default SecuritySettings;
