import React, { useState } from 'react';
import { AlertTriangle, Check, X, Edit2 } from 'lucide-react';
import api from '../api/client';
import './HITLApproval.css';

const HITLApproval = ({ chatboxId, toolCalls, onComplete }) => {
  const [editing, setEditing] = useState(false);
  const [editedArgs, setEditedArgs] = useState(() => {
    try {
      return JSON.stringify(toolCalls[0].args, null, 2);
    } catch {
      return '{}';
    }
  });
  const [loading, setLoading] = useState(false);

  const handleAction = async (actionType) => {
    setLoading(true);
    try {
      let payload = { action: actionType };
      if (actionType === 'edit') {
        try {
          payload.edited_args = JSON.parse(editedArgs);
        } catch (e) {
          alert('JSON không hợp lệ');
          setLoading(false);
          return;
        }
      }

      // Instead of standard fetch, we use custom fetch if we want to stream the resume response
      // But the endpoint /chat/{id}/approve returns SSE. We should pass the action up
      // to ChatArea to handle the SSE stream.
      if (onComplete) {
        onComplete(payload);
      }
    } finally {
      setLoading(false);
    }
  };

  const tool = toolCalls[0] || {};

  return (
    <div className="hitl-card glass-card">
      <div className="hitl-header">
        <AlertTriangle size={20} className="text-warning" />
        <h4>Cần xác nhận từ con người</h4>
      </div>
      
      <div className="hitl-body">
        <p className="text-sm text-muted mb-2">
          Agent muốn thực thi công cụ: <strong>{tool.name}</strong>
        </p>
        
        {editing ? (
          <textarea 
            className="hitl-textarea" 
            value={editedArgs}
            onChange={(e) => setEditedArgs(e.target.value)}
            rows={5}
          />
        ) : (
          <pre className="hitl-pre">
            <code>{JSON.stringify(tool.args, null, 2)}</code>
          </pre>
        )}
      </div>

      <div className="hitl-footer">
        {editing ? (
          <>
            <button className="btn btn-secondary text-sm" onClick={() => setEditing(false)}>Hủy sửa</button>
            <button className="btn btn-primary text-sm" disabled={loading} onClick={() => handleAction('edit')}>
              {loading ? 'Đang gửi...' : 'Gửi sửa đổi'}
            </button>
          </>
        ) : (
          <>
            <button className="btn btn-danger text-sm" disabled={loading} onClick={() => handleAction('reject')}>
              <X size={16} /> Từ chối
            </button>
            <button className="btn btn-secondary text-sm" disabled={loading} onClick={() => setEditing(true)}>
              <Edit2 size={16} /> Sửa
            </button>
            <button className="btn btn-primary text-sm bg-success" disabled={loading} onClick={() => handleAction('approve')}>
              <Check size={16} /> Chấp nhận
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default HITLApproval;
