import React, { useState } from 'react';
import { Paperclip, X, UploadCloud, FileText, Database, Loader2, CheckSquare, Square } from 'lucide-react';
import api from '../api/client';
import './FileUpload.css';

const FileUpload = ({ chatboxId, sessionFiles, selectedFileIds, onToggleFile, onUploadComplete }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [file, setFile] = useState(null);
  const [uploadingFiles, setUploadingFiles] = useState([]);
  const [error, setError] = useState('');

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    const fileToUpload = file;
    const tempId = Date.now().toString(); // Use a temp ID for the UI

    // Add to uploading list
    setUploadingFiles(prev => [...prev, { id: tempId, name: fileToUpload.name }]);

    setFile(null); // Reset selection immediately
    setIsOpen(false); // Close popup
    setError('');

    const formData = new FormData();
    formData.append('file', fileToUpload);
    formData.append('chatbox_id', chatboxId);

    try {
      const response = await api.post('/doc/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const taskId = response.data.task_id;

      if (taskId) {
        let isComplete = false;
        while (!isComplete) {
          await new Promise(resolve => setTimeout(resolve, 2000));
          try {
            const statusRes = await api.get(`/doc/task/${taskId}`);
            const state = statusRes.data.state;

            if (state === 'SUCCESS') {
              isComplete = true;
            } else if (state === 'FAILURE') {
              throw new Error(statusRes.data.error || 'Lỗi khi xử lý file');
            }
          } catch (pollErr) {
            console.error("Error polling task status:", pollErr);
            if (pollErr.response?.status === 404 || pollErr.message !== 'Network Error') {
              // Only throw if it's not a temporary network glitch or if explicitly failed
              if (pollErr.message && !pollErr.message.includes('Network Error')) {
                throw pollErr;
              }
            }
          }
        }
      }

      // Fetch history again to get the new file
      if (onUploadComplete) await onUploadComplete();
    } catch (err) {
      console.error(err);
      // Could show a toast error here instead, or keep it in the modal if we didn't close it
      alert('Lỗi tải lên file: ' + (err.message || err.response?.data?.detail || 'Không xác định'));
    } finally {
      // Remove from uploading list
      setUploadingFiles(prev => prev.filter(f => f.id !== tempId));
    }
  };

  return (
    <div className="file-upload-container">
      {/* Upload button */}
      <button
        className="btn btn-secondary upload-btn"
        onClick={() => setIsOpen(true)}
        disabled={uploadingFiles.length > 0}
        title={uploadingFiles.length > 0 ? "Vui lòng chờ tiến trình tải lên hoàn tất" : ""}
      >
        <Paperclip size={18} /> Đính kèm file
      </button>

      {/* List of currently attached files (Vertical) */}
      <div className="attached-files-list mt-3">
        {sessionFiles && sessionFiles.map(sf => {
          const isData = sf.display_filename.toLowerCase().match(/\.(csv|xlsx|xls)$/);
          const isSelected = selectedFileIds.includes(sf.id);

          return (
            <div
              key={sf.id}
              className={`file-row ${isSelected ? 'selected' : ''}`}
              onClick={() => onToggleFile(sf.id)}
            >
              <div className="file-checkbox">
                {isSelected ? <CheckSquare size={18} className="text-accent" /> : <Square size={18} className="text-muted" />}
              </div>
              <div className="file-icon">
                {isData ? <Database size={16} className="text-accent" /> : <FileText size={16} className="text-secondary" />}
              </div>
              <span className="file-name truncate" title={sf.display_filename}>
                {sf.display_filename}
              </span>
            </div>
          );
        })}

        {/* Show currently uploading files */}
        {uploadingFiles.map(uf => (
          <div key={uf.id} className="file-row uploading">
            <div className="file-checkbox">
              <Loader2 size={16} className="animate-spin text-accent" />
            </div>
            <div className="file-icon">
              <FileText size={16} className="text-muted" />
            </div>
            <span className="file-name truncate text-muted" title={uf.name}>
              {uf.name} (Đang tải...)
            </span>
          </div>
        ))}
      </div>

      {/* Upload Modal */}
      {isOpen && (
        <div className="modal-overlay flex-center">
          <div className="glass-card upload-modal animate-fade-in">
            <div className="flex-between mb-4">
              <h3 className="m-0">Tải lên tài liệu</h3>
              <button className="btn-icon" onClick={() => setIsOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <div className="upload-dropzone flex-center">
              <input
                type="file"
                onChange={handleFileChange}
                className="hidden-input"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="dropzone-label">
                <UploadCloud size={48} className="text-gradient mb-2" />
                {file ? (
                  <span className="text-primary font-medium">{file.name}</span>
                ) : (
                  <>
                    <span className="text-primary font-medium">Nhấn để chọn file</span>
                    <span className="text-muted text-sm">Hỗ trợ PDF, DOCX, CSV, Excel</span>
                  </>
                )}
              </label>
            </div>

            {error && <div className="error-message text-sm mt-3">{error}</div>}

            <div className="flex-end mt-4 gap-2">
              <button
                className="btn btn-secondary"
                onClick={() => setIsOpen(false)}
              >
                Hủy
              </button>
              <button
                className="btn btn-primary"
                onClick={handleUpload}
                disabled={!file || uploadingFiles.length > 0}
              >
                Tải lên
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
