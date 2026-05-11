import React, { useState } from 'react';
import Sidebar from './Sidebar';
import ChatArea from './ChatArea';
import './ChatLayout.css';

const ChatLayout = () => {
  const [activeChatId, setActiveChatId] = useState(null);

  return (
    <div className="chat-layout">
      <Sidebar 
        activeChatId={activeChatId} 
        setActiveChatId={setActiveChatId} 
      />
      <div className="main-content">
        {activeChatId ? (
          <ChatArea chatboxId={activeChatId} />
        ) : (
          <div className="empty-state flex-center">
            <div className="text-center">
              <h2 className="text-gradient">Chào mừng đến với MADS</h2>
              <p className="text-muted">Chọn một cuộc trò chuyện ở menu bên trái hoặc tạo mới để bắt đầu.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatLayout;
