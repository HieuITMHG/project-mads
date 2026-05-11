import React, { useState, useEffect } from 'react';
import { Plus, MessageSquare, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';
import './Sidebar.css';

const Sidebar = ({ activeChatId, setActiveChatId }) => {
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(true);
  const { logout } = useAuth();

  const fetchChats = async () => {
    try {
      const response = await api.get('/chat/');
      setChats(response.data);
    } catch (error) {
      console.error('Error fetching chats:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChats();
  }, []);

  const handleNewChat = async () => {
    try {
      const response = await api.post('/chat/');
      setChats([response.data, ...chats]);
      setActiveChatId(response.data.id);
    } catch (error) {
      console.error('Error creating new chat:', error);
    }
  };

  return (
    <div className="sidebar glass">
      <div className="sidebar-header">
        <h1 className="text-gradient">MADS</h1>
        <button className="btn btn-primary new-chat-btn" onClick={handleNewChat}>
          <Plus size={18} />
          <span>Chat Mới</span>
        </button>
      </div>

      <div className="sidebar-content">
        <div className="chat-list">
          {loading ? (
            <div className="text-center text-muted p-4">Đang tải...</div>
          ) : chats.length === 0 ? (
            <div className="text-center text-muted text-sm p-4">Chưa có cuộc trò chuyện nào</div>
          ) : (
            chats.map(chat => (
              <div 
                key={chat.id} 
                className={`chat-item ${activeChatId === chat.id ? 'active' : ''}`}
                onClick={() => setActiveChatId(chat.id)}
              >
                <MessageSquare size={18} />
                <span className="chat-title truncate">{chat.title}</span>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="sidebar-footer">
        <button className="btn btn-secondary logout-btn" onClick={logout}>
          <LogOut size={18} />
          <span>Đăng xuất</span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
