import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { UserPlus } from 'lucide-react';
import './Login.css';

const Register = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const { register, loading } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');
    
    if (!username || !password || !confirmPassword) {
      setError('Vui lòng nhập đầy đủ thông tin');
      return;
    }

    if (password !== confirmPassword) {
      setError('Mật khẩu xác nhận không khớp');
      return;
    }

    const result = await register(username, password);
    if (result.success) {
      setSuccessMsg('Đăng ký thành công! Đang chuyển hướng...');
      setTimeout(() => {
        navigate('/login');
      }, 1500);
    } else {
      setError(result.message);
    }
  };

  return (
    <div className="login-container flex-center">
      <div className="glass-card login-card animate-fade-in">
        <div className="login-header">
          <div className="logo-container flex-center">
            <UserPlus size={28} className="text-gradient" />
          </div>
          <h2>Tạo tài khoản mới</h2>
          <p className="text-muted text-sm">Đăng ký để tham gia MADS</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="error-message text-sm">{error}</div>}
          {successMsg && <div className="error-message text-sm" style={{background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', borderColor: 'rgba(16, 185, 129, 0.2)'}}>{successMsg}</div>}
          
          <div className="form-group">
            <label htmlFor="username">Tên đăng nhập</label>
            <input
              id="username"
              type="text"
              className="input-field"
              placeholder="Chọn tên đăng nhập..."
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Mật khẩu</label>
            <input
              id="password"
              type="password"
              className="input-field"
              placeholder="Nhập mật khẩu..."
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Xác nhận mật khẩu</label>
            <input
              id="confirmPassword"
              type="password"
              className="input-field"
              placeholder="Nhập lại mật khẩu..."
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
            />
          </div>

          <button 
            type="submit" 
            className="btn btn-primary login-btn" 
            disabled={loading}
          >
            {loading ? 'Đang xử lý...' : 'Đăng ký ngay'}
          </button>
          
          <div className="login-footer text-center mt-4">
            <span className="text-muted text-sm">Đã có tài khoản? </span>
            <span 
              className="text-primary cursor-pointer hover-underline" 
              onClick={() => navigate('/login')}
            >
              Đăng nhập
            </span>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Register;
