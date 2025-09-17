import axios from 'axios';
import './App.css';
import SecuritySettings from './SecuritySettings';
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';

// Конфигурация API
const api = axios.create({
  baseURL: 'http://localhost:8000',
});

// Перехватчик для авторизации
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Перехватчик для обработки ошибок 401
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      setUser(null);
      setAuthMode('login');
    }
    return Promise.reject(error);
  }
);

// Компоненты аутентификации
const LoginForm = ({
  email,
  setEmail,
  password,
  setPassword,
  onLogin,
  onSwitchToRegister,
  onShowForgotPassword
}) => (
  <div className="auth-form">
    <h2>Вход</h2>
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
      <button onClick={onLogin} className="btn-primary">Login</button>
      <button onClick={onSwitchToRegister} className="btn-secondary">Нет аккаунта? Зарегистрироваться</button>
      <button onClick={onShowForgotPassword} className="btn-link">Забыли пароль?</button>
    </div>
  </div>
);

const RegisterForm = ({ email, setEmail, password, setPassword, onRegister, onSwitchToLogin }) => (
  <div className="auth-form">
    <h2>Регистрация</h2>
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
      <button onClick={onSwitchToLogin} className="btn-secondary">Уже есть аккаунт? Войти</button>
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
      placeholder="Код подтверждения"
      value={verificationCode}
      onChange={(e) => setVerificationCode(e.target.value)}
      className="form-input"
    />
    <div className="auth-buttons">
      <button onClick={onVerify} className="btn-primary">Подтвердить</button>
      <button onClick={onCancel} className="btn-secondary">Назад к входу</button>
    </div>
  </div>
);

const ForgotPasswordForm = (props) => {
  const {
    resetEmail,
    setResetEmail,
    onResetRequest,
    onBackToLogin,
    resetLoading
  } = props;

  return (
    <div className="auth-form">
      <h2>Восстановление пароля</h2>
      <p>Введите ваш email, и мы вышлем вам код для сброса пароля</p>
      <input
        type="email"
        placeholder="Email"
        value={resetEmail}
        onChange={(e) => setResetEmail(e.target.value)}
        className="form-input"
      />
      <div className="auth-buttons">
        <button onClick={onResetRequest} disabled={resetLoading} className="btn-primary">
          {resetLoading ? 'Отправка...' : 'Отправить код'}
        </button>
        <button onClick={onBackToLogin} className="btn-secondary">Назад к входу</button>
      </div>
    </div>
  );
};

const ResetPasswordForm = (props) => {
  const {
    resetEmail,
    setResetEmail,
    resetCode,
    setResetCode,
    newPassword,
    setNewPassword,
    onResetPassword,
    onBack,
    resetLoading
  } = props;

  return (
    <div className="auth-form">
      <h2>Сброс пароля</h2>
      <p>Введите код, который вы получили по email, и новый пароль</p>
      <input
        type="email"
        placeholder="Email"
        value={resetEmail}
        onChange={(e) => setResetEmail(e.target.value)}
        className="form-input"
      />
      <input
        type="text"
        placeholder="Код подтверждения"
        value={resetCode}
        onChange={(e) => setResetCode(e.target.value)}
        className="form-input"
      />
      <input
        type="password"
        placeholder="Новый пароль"
        value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
        className="form-input"
      />
      <div className="auth-buttons">
        <button onClick={onResetPassword} disabled={resetLoading} className="btn-primary">
          {resetLoading ? 'Сброс...' : 'Сбросить пароль'}
        </button>
        <button onClick={onBack} className="btn-secondary">Назад</button>
      </div>
    </div>
  );
};

// Компонент файлов
const FileList = ({ files, shareLinks, onCreateShareLink, shareSettings }) => (
  <div className="file-list">
    <h2>Your Files</h2>
    {files.length === 0 ? (
      <p className="no-files">Пока нет файлов — загрузите первый.</p>
    ) : (
      <table className="files-table">
        <thead>
          <tr>
            <th>Имя</th>
            <th>Размер</th>
            <th>Ссылка</th>
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
                    <a href={shareLinks[f.id]} target="_blank" rel="noopener noreferrer">Открыть</a>
                    <button onClick={() => onCreateShareLink(f.id, shareSettings)}>
                      Копировать
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => onCreateShareLink(f.id, shareSettings)}
                    className="btn-primary"
                  >
                    Поделиться
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    )}
  </div>
);

// Главный компонент
function App() {
  const [user, setUser] = useState(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [files, setFiles] = useState([]);
  const [search, setSearch] = useState('');
  const [file, setFile] = useState(null);
  const [shareLinks, setShareLinks] = useState({});
  const [authMode, setAuthMode] = useState('login');
  const [verificationCode, setVerificationCode] = useState('');
  const [userId, setUserId] = useState(null);
  const [authMessage, setAuthMessage] = useState('');

  // Состояния для восстановления пароля
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [resetLoading, setResetLoading] = useState(false);

  // Состояния для общего доступа к файлам
  const [expireDays, setExpireDays] = useState(7);
  const [maxViews, setMaxViews] = useState('');
  const [reuseExisting, setReuseExisting] = useState(true);
  const [uploading, setUploading] = useState(false);

  // Состояния для поиска и фильтрации файлов в списке
  const [fileType, setFileType] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [totalFiles, setTotalFiles] = useState(0);
  const [showFilters, setShowFilters] = useState(false);

  // Проверка аутентификации при загрузке
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        setUser({ email: payload.sub });
      } catch (error) {
        console.error('Invalid token', error);
        localStorage.removeItem('token');
      }
    }
  }, []);

  // Функции аутентификации
  const register = async () => {
    try {
      const response = await api.post('/register', { email, password });

      if (response.data.requires_verification) {
        setUserId(response.data.user_id);
        setAuthMode('verifyEmail');
        setAuthMessage('Проверьте вашу почту для получения кода подтверждения');
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
      const response = await api.post('/verify-email', {
        user_id: userId,
        code: verificationCode
      });

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
        setAuthMessage('Проверьте вашу почту для получения кода двухфакторной аутентификации');
      }
    } catch (error) {
      alert('Login failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  const verify2FA = async () => {
    try {
      const response = await api.post('/verify-2fa', {
        user_id: userId,
        code: verificationCode
      });

      localStorage.setItem('token', response.data.access_token);
      setUser({ email });
      setAuthMode('login');
    } catch (error) {
      alert('2FA verification failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    setAuthMode('login');
  };

  // Функции для работы с файлами
  const uploadFile = async () => {
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await api.post(`/upload?expire_days=${expireDays}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setFiles([...files, response.data]);

      // Сразу создать ссылку с текущими настройками
      await createShareLink(response.data.id, { expireDays, maxViews, reuseExisting });
    } catch (error) {
      alert('Upload failed: ' + (error.response?.data?.detail || error.message));
    } finally {
      setUploading(false);
    }
  };

  const createShareLink = async (fileId, settings) => {
    try {
      // Строим query string с параметрами
      const params = new URLSearchParams();
      params.set('file_id', fileId);
      params.set('expire_days', settings.expireDays);

      if (settings.maxViews) {
        params.set('max_views', settings.maxViews);
      }

      params.set('reuse', settings.reuseExisting.toString());

      const response = await api.post(`/share-links/ensure?${params.toString()}`);
      const shareUrl = response.data.share_url;

      setShareLinks({
        ...shareLinks,
        [fileId]: shareUrl
      });

      return shareUrl;
    } catch (error) {
      alert('Failed to create share link: ' + (error.response?.data?.detail || error.message));
      return null;
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
        skip: (currentPage - 1) * itemsPerPage,
        limit: itemsPerPage,
      };

      // Убираем undefined параметры
      Object.keys(params).forEach(key => params[key] === undefined && delete params[key]);

      console.log('Fetching files with params:', params);
      const response = await api.get('/files', {
        params,
        ...config
      });

      setFiles(response.data.files);
      setTotalFiles(response.data.total);
    } catch (error) {
      if (error.name === 'CanceledError') {
        console.log('Request canceled');
      } else {
        console.error('Failed to fetch files', error);
      }
    }
  };


  // Функции для восстановления пароля
  const handleForgotPassword = async () => {
    setResetLoading(true);
    try {
      await api.post('/forgot-password', { email: resetEmail });
      setAuthMessage('Если email зарегистрирован, вы получите код сброса');
      setShowForgotPassword(false);
      setShowResetPassword(true);
    } catch (error) {
      setAuthMessage('Ошибка при запросе сброса пароля: ' + (error.response?.data?.detail || error.message));
    }
    setResetLoading(false);
  };

  const handleResetPassword = async () => {
    setResetLoading(true);
    try {
      await api.post('/reset-password', {
        email: resetEmail,
        code: resetCode,
        new_password: newPassword
      });
      setAuthMessage('Пароль успешно изменен. Теперь вы можете войти с новым паролем.');
      setShowResetPassword(false);
      setAuthMode('login');
      setResetEmail('');
      setResetCode('');
      setNewPassword('');
    } catch (error) {
      setAuthMessage('Ошибка при сбросе пароля: ' + (error.response?.data?.detail || error.message));
    }
    setResetLoading(false);
  };

  const handleBackToLogin = () => {
    setShowForgotPassword(false);
    setShowResetPassword(false);
    setResetEmail('');
    setResetCode('');
    setNewPassword('');
  };

  // Функция для сброса фильтров
  const resetFilters = () => {
    setSearch('');
    setFileType('');
    setStartDate('');
    setEndDate('');
    setCurrentPage(1);
  };

  // AbortController для отмены предыдущих запросов
  useEffect(() => {
    if (user) {
      const controller = new AbortController();

      // Добавляем задержку для поиска, чтобы избежать слишком частых запросов
      const timer = setTimeout(() => {
        fetchFiles(controller.signal);
      }, 300); // Задержка 300 мс

      return () => {
        controller.abort();
        clearTimeout(timer);
      };
    }
  }, [user, search, fileType, startDate, endDate, currentPage, itemsPerPage]);

  // Рендеринг форм аутентификации
  const renderAuthForm = () => {
    if (showForgotPassword) {
      return (
        <ForgotPasswordForm
          resetEmail={resetEmail}
          setResetEmail={setResetEmail}
          onResetRequest={handleForgotPassword}
          onBackToLogin={handleBackToLogin}
          resetLoading={resetLoading}
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
          onBack={() => {
            setShowResetPassword(false);
            setShowForgotPassword(true);
          }}
          resetLoading={resetLoading}
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
            title="Подтверждение Email"
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
            <h2>Двухфакторная аутентификация</h2>
            <p>{authMessage}</p>
            <input
              type="text"
              placeholder="Код подтверждения"
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value)}
              className="form-input"
            />
            <div className="auth-buttons">
              <button onClick={verify2FA} className="btn-primary">Подтвердить</button>
              <button onClick={() => setAuthMode('login')} className="btn-secondary">Назад к входу</button>
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
        <header>
          <h1>SecureShare</h1>
          <nav>
            <Link to="/">Files</Link>
            <Link to="/settings/security">Security Settings</Link>
          </nav>
          <button onClick={logout} className="btn-secondary">Logout</button>
        </header>

        <Routes>
          <Route path="/" element={
            <>
              <div className="sharing-settings">
                <h3>Настройки общего доступа</h3>
                <div className="settings-grid">
                  <div className="setting-group">
                    <label>Срок действия (дней)</label>
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
                    <label>Лимит скачиваний</label>
                    <input
                      type="number"
                      min="1"
                      placeholder="Без лимита"
                      value={maxViews}
                      onChange={(e) => setMaxViews(e.target.value)}
                      className="form-input"
                    />
                  </div>

                  <div className="setting-group">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={reuseExisting}
                        onChange={(e) => setReuseExisting(e.target.checked)}
                      />
                      Переиспользовать существующие ссылки
                    </label>
                  </div>
                </div>
              </div>

              <div className="search-and-filters">
                <div className="search-section">
                  <input
                    type="text"
                    placeholder="Search files by name"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
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
                        onChange={(e) => setItemsPerPage(Number(e.target.value))}
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

                {/* Пагинация */}
                {totalFiles > 0 && (
                  <div className="pagination">
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

                    <span className="total-info">
                      Total files: {totalFiles}
                    </span>
                  </div>
                )}
              </div>

              <div className="upload-section">
                <label className="btn-primary">
                  {uploading ? 'Загрузка...' : 'Загрузить файл'}
                  <input
                    type="file"
                    onChange={(e) => setFile(e.target.files[0])}
                    style={{ display: 'none' }}
                  />
                </label>
                <button onClick={uploadFile} disabled={uploading} className="btn-primary">
                  Upload
                </button>
              </div>

              <FileList
                files={files}
                shareLinks={shareLinks}
                onCreateShareLink={createShareLink}
                shareSettings={{ expireDays, maxViews, reuseExisting }}
              />
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

я не буду вносить эти изменения, поскольку поиск файлов по имени и их фильтрация не происходят автоматически через useEffect и я прошу тебя выяснить почему.
