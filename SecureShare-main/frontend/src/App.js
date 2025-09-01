import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [user, setUser] = useState(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [files, setFiles] = useState([]);
  const [search, setSearch] = useState('');
  const [file, setFile] = useState(null);
  const [shareLinks, setShareLinks] = useState({});

  // Настройка API
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

  // Регистрация
  const register = async () => {
    try {
      const response = await api.post('/register', { email, password });
      localStorage.setItem('token', response.data.access_token);
      setUser({ email });
    } catch (error) {
      alert('Registration failed');
    }
  };

  // Вход
  const login = async () => {
    try {
      const response = await api.post('/token', `username=${email}&password=${password}`, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      localStorage.setItem('token', response.data.access_token);
      setUser({ email });
    } catch (error) {
      alert('Login failed');
    }
  };

  // Выход
  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  // Загрузка файла
  const uploadFile = async () => {
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await api.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setFiles([...files, response.data]);
    } catch (error) {
      alert('Upload failed');
    }
  };

  // Создание ссылки
  const createShareLink = async (fileId) => {
    try {
      const response = await api.post(`/files/${fileId}/share`, {
        expire_hours: 24,
        max_downloads: 5
      });
      
      setShareLinks({
        ...shareLinks,
        [fileId]: response.data.download_url
      });
      
      return response.data;
    } catch (error) {
      alert('Failed to create share link');
      return null;
    }
  };

  // Получение файлов
  const fetchFiles = async () => {
    try {
      const response = await api.get('/files', { params: { search } });
      setFiles(response.data);
    } catch (error) {
      console.error('Failed to fetch files', error);
    }
  };

  useEffect(() => {
    if (user) {
      fetchFiles();
    }
  }, [user, search]);

  if (!user) {
    return (
      <div className="container">
        <h1>SecureShare</h1>
        <div>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button onClick={register}>Register</button>
          <button onClick={login}>Login</button>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <h1>SecureShare</h1>
      <button onClick={logout}>Logout</button>
      
      <div>
        <input
          type="text"
          placeholder="Search files"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      
      <div>
        <input type="file" onChange={(e) => setFile(e.target.files[0])} />
        <button onClick={uploadFile}>Upload</button>
      </div>
      
      <h2>Your Files</h2>
      <ul>
        {files.map(f => (
          <li key={f.id}>
            {f.filename} - {(f.size / 1024 / 1024).toFixed(2)} MB
            {shareLinks[f.id] ? (
              <div>
                Share link: <a href={shareLinks[f.id]} target="_blank">{shareLinks[f.id]}</a>
              </div>
            ) : (
              <button onClick={() => createShareLink(f.id)}>Get Share Link</button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;