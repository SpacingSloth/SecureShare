import React, { useState, useEffect } from 'react';
import './SecuritySettings.css';

const SecuritySettings = ({ api }) => {
  const [is2FAEnabled, setIs2FAEnabled] = useState(false);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(true);
  const [message, setMessage] = useState('');
  
  // Состояния для смены пароля
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);

  // Функция для получения статуса 2FA
  const fetch2FAStatus = async () => {
    try {
      setStatusLoading(true);
      const response = await api.get('/2fa-status');
      setIs2FAEnabled(response.data.two_factor_enabled);
    } catch (error) {
      console.error('Failed to fetch 2FA status', error);
      setMessage('Ошибка при получении статуса 2FA');
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
      
      // Обновляем состояние на основе ответа сервера
      setIs2FAEnabled(response.data.enabled);
      setMessage(response.data.message);
    } catch (error) {
      console.error('Failed to toggle 2FA', error);
      setMessage('Ошибка при изменении настроек 2FA: ' + (error.response?.data?.detail || error.message));
      // В случае ошибки перезапрашиваем статус
      fetch2FAStatus();
    }
    setLoading(false);
  };

  const changePassword = async () => {
    // Проверяем, что пароли совпадают
    if (newPassword !== confirmPassword) {
      setMessage('Новый пароль и подтверждение не совпадают');
      return;
    }
    
    // Проверяем минимальную длину пароля
    if (newPassword.length < 8) {
      setMessage('Пароль должен содержать не менее 8 символов');
      return;
    }
    
    setPasswordLoading(true);
    try {
      await api.post('/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      });
      
      setMessage('Пароль успешно изменен');
      // Очищаем поля формы
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error) {
      console.error('Failed to change password', error);
      setMessage('Ошибка при изменении пароля: ' + (error.response?.data?.detail || error.message));
    }
    setPasswordLoading(false);
  };

  if (statusLoading) {
    return (
      <div className="security-settings">
        <h2>Настройки безопасности</h2>
        <p className="loading-text">
          <span className="loading-indicator"></span>
          Загрузка статуса 2FA...
        </p>
      </div>
    );
  }

  return (
    <div className="security-settings">
      <h2>Настройки безопасности</h2>
      {message && (
        <div className={`message ${message.includes('Ошибка') ? 'message-error' : 'message-success'}`}>
          {message}
        </div>
      )}
      
      <div className="setting-item">
        <h3>Двухфакторная аутентификация</h3>
        <p>
          Двухфакторная аутентификация добавляет дополнительный уровень безопасности к вашей учетной записи, 
          требуя не только пароль для входа.
        </p>
        
        <div className="status-text">
          Текущий статус: 
          <span className={`status-indicator ${is2FAEnabled ? 'status-enabled' : 'status-disabled'}`}>
            {is2FAEnabled ? 'Включена' : 'Выключена'}
          </span>
        </div>
        
        <button 
          onClick={toggle2FA} 
          disabled={loading}
          className={is2FAEnabled ? 'btn-danger' : 'btn-primary'}
        >
          {loading ? 'Обработка...' : (is2FAEnabled ? 'Отключить 2FA' : 'Включить 2FA')}
        </button>
      </div>
      
      <div className="setting-item">
        <h3>Смена пароля</h3>
        <p>
          Регулярная смена пароля повышает безопасность вашей учетной записи.
        </p>
        
        <div className="password-form">
          <input
            type="password"
            placeholder="Текущий пароль"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="form-input"
          />
          <input
            type="password"
            placeholder="Новый пароль"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="form-input"
          />
          <input
            type="password"
            placeholder="Подтвердите новый пароль"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="form-input"
          />
          <button 
            onClick={changePassword} 
            disabled={passwordLoading}
            className="btn-primary"
          >
            {passwordLoading ? 'Изменение...' : 'Изменить пароль'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SecuritySettings;