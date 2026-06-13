import React, { useState } from 'react';
import { Terminal, CheckCircle2, XCircle, Loader2, ChevronDown, ChevronUp, Clock } from 'lucide-react';
import './ToolExecutionLog.css';

/**
 * Renders the icon + color for a tool entry based on its status.
 */
const StatusIcon = ({ status, size = 16 }) => {
  if (status === 'running') return <Loader2 size={size} className="tool-log-icon running animate-spin" />;
  if (status === 'done') return <CheckCircle2 size={size} className="tool-log-icon done" />;
  if (status === 'error') return <XCircle size={size} className="tool-log-icon error" />;
  return <Terminal size={size} className="tool-log-icon" />;
};

/**
 * A single collapsible tool execution entry.
 */
const ToolEntry = ({ entry }) => {
  const [expanded, setExpanded] = useState(false);

  const durationLabel = entry.duration_ms != null
    ? entry.duration_ms >= 1000
      ? `${(entry.duration_ms / 1000).toFixed(1)}s`
      : `${entry.duration_ms}ms`
    : null;

  return (
    <div className={`tool-entry tool-entry--${entry.status}`}>
      <div className="tool-entry-header" onClick={() => setExpanded(v => !v)}>
        <StatusIcon status={entry.status} />
        <span className="tool-entry-name">{entry.tool_name}</span>

        <div className="tool-entry-meta">
          {entry.status === 'running' && (
            <span className="tool-entry-badge running">Đang chạy…</span>
          )}
          {durationLabel && entry.status !== 'running' && (
            <span className="tool-entry-badge duration">
              <Clock size={11} />
              {durationLabel}
            </span>
          )}
          {entry.status === 'error' && (
            <span className="tool-entry-badge error">Lỗi</span>
          )}
        </div>

        <button className="tool-entry-expand-btn" aria-label="Toggle details">
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {expanded && (
        <div className="tool-entry-body">
          {entry.args && Object.keys(entry.args).length > 0 && (
            <div className="tool-entry-section">
              <span className="tool-entry-section-label">Input</span>
              <pre className="tool-entry-pre">{JSON.stringify(entry.args, null, 2)}</pre>
            </div>
          )}
          {entry.output_preview && (
            <div className="tool-entry-section">
              <span className="tool-entry-section-label">Output preview</span>
              <pre className="tool-entry-pre tool-entry-pre--output">{entry.output_preview}</pre>
            </div>
          )}
          <div className="tool-entry-timestamp">{entry.timestamp}</div>
        </div>
      )}
    </div>
  );
};

/**
 * ToolExecutionLog – collapsible panel showing all tools run in this session.
 * Props:
 *   entries: Array<{ id, run_id, tool_name, status, args, output_preview, duration_ms, timestamp }>
 */
const ToolExecutionLog = ({ entries = [] }) => {
  const [panelOpen, setPanelOpen] = useState(true);

  if (entries.length === 0) return null;

  const runningCount = entries.filter(e => e.status === 'running').length;
  const errorCount = entries.filter(e => e.status === 'error').length;

  return (
    <div className="tool-log-panel glass">
      {/* Panel header */}
      <button className="tool-log-panel-header" onClick={() => setPanelOpen(v => !v)}>
        <div className="tool-log-panel-title">
          <Terminal size={15} />
          <span>Lịch sử thực thi công cụ</span>
          <span className="tool-log-count">{entries.length}</span>
          {runningCount > 0 && (
            <span className="tool-log-badge running">
              <Loader2 size={11} className="animate-spin" /> {runningCount} đang chạy
            </span>
          )}
          {errorCount > 0 && (
            <span className="tool-log-badge error">{errorCount} lỗi</span>
          )}
        </div>
        {panelOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {/* Panel body */}
      {panelOpen && (
        <div className="tool-log-body">
          {entries.map(entry => (
            <ToolEntry key={entry.run_id || entry.id} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
};

export default ToolExecutionLog;
