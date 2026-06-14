import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Bot, User, Loader2, BrainCircuit, Wrench, CheckCheck, AlertCircle } from 'lucide-react';
import api from '../api/client';
import FileUpload from './FileUpload';
import ChartViewer from './ChartViewer';
import ToolExecutionLog from './ToolExecutionLog';
import './ChatArea.css';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const extractValidJSON = (str) => {
  let firstBrace = str.indexOf('{');
  let firstBracket = str.indexOf('[');
  let startIdx = -1;
  let isObject = false;

  if (firstBrace !== -1 && (firstBracket === -1 || firstBrace < firstBracket)) {
    startIdx = firstBrace; isObject = true;
  } else if (firstBracket !== -1) {
    startIdx = firstBracket;
  } else {
    return str;
  }

  let openTokens = 0, inString = false, escapeNext = false;
  for (let i = startIdx; i < str.length; i++) {
    const char = str[i];
    if (escapeNext) { escapeNext = false; continue; }
    if (char === '\\') { escapeNext = true; continue; }
    if (char === '"') { inString = !inString; continue; }
    if (!inString) {
      if (isObject) {
        if (char === '{') openTokens++;
        if (char === '}') { openTokens--; if (openTokens === 0) return str.substring(startIdx, i + 1); }
      } else {
        if (char === '[') openTokens++;
        if (char === ']') { openTokens--; if (openTokens === 0) return str.substring(startIdx, i + 1); }
      }
    }
  }
  
  if (openTokens > 0) {
    if (isObject) {
      return str.substring(startIdx) + '}'.repeat(openTokens);
    } else {
      return str.substring(startIdx) + ']'.repeat(openTokens);
    }
  }
  
  return str;
};

const tryParsePlotlyJSON = (jsonStr) => {
  try {
    const parsed = JSON.parse(jsonStr);
    if (parsed && typeof parsed === 'object' && Array.isArray(parsed.data) && parsed.layout && typeof parsed.layout === 'object') {
      let filteredData = [], extractedLayout = parsed.layout || {};
      parsed.data.forEach(item => {
        if (item && typeof item === 'object' && item.type === 'layout') {
          if (Object.keys(extractedLayout).length === 0) { const { type, ...rest } = item; extractedLayout = rest; }
        } else { filteredData.push(item); }
      });
      return { type: 'plotly', data: filteredData, layout: extractedLayout };
    }
  } catch (_) { }
  return null;
};

const processStreamText = (text) => {
  if (!text) return { cleanText: '', chartData: null };
  const tagPattern = /<CHART_JSON>([\s\S]*?)(<\/CHART_JSON>|$)/;
  const tagMatch = text.match(tagPattern);
  if (tagMatch) {
    const cleanText = text.replace(tagPattern, '').trim();
    if (tagMatch[2] === '</CHART_JSON>') {
      try {
        let jsonStr = tagMatch[1].trim();
        if (jsonStr.startsWith('```json')) jsonStr = jsonStr.replace(/^```json\n?/, '').replace(/\n?```$/, '').trim();
        else if (jsonStr.startsWith('```')) jsonStr = jsonStr.replace(/^```\n?/, '').replace(/\n?```$/, '').trim();
        jsonStr = extractValidJSON(jsonStr);
        return { cleanText, chartData: tryParsePlotlyJSON(jsonStr) };
      } catch (_) { return { cleanText, chartData: null }; }
    }
    return { cleanText, chartData: null };
  }
  const jsonStart = text.indexOf('{');
  if (jsonStart !== -1) {
    try {
      const rawJsonStr = extractValidJSON(text.substring(jsonStart));
      const chartData = tryParsePlotlyJSON(rawJsonStr);
      if (chartData) {
        const cleanText = (text.substring(0, jsonStart) + text.substring(jsonStart + rawJsonStr.length)).trim();
        return { cleanText, chartData };
      }
    } catch (_) { }
  }
  return { cleanText: text, chartData: null };
};

// ---------------------------------------------------------------------------
// Step Progress Bar Component
// ---------------------------------------------------------------------------

const STEP_DEFS = [
  { key: 'thinking', label: 'Suy nghĩ', Icon: BrainCircuit },
  { key: 'tool',     label: 'Thực thi',  Icon: Wrench },
  { key: 'done',     label: 'Hoàn thành', Icon: CheckCheck },
];

const StepProgressBar = ({ currentStep, toolName, elapsedSec }) => {
  const steps = STEP_DEFS;
  const activeIdx = steps.findIndex(s => s.key === currentStep);

  return (
    <div className="step-progress-bar">
      {steps.map((step, idx) => {
        const isActive = idx === activeIdx;
        const isDone = idx < activeIdx;
        const cls = isDone ? 'step done' : isActive ? 'step active' : 'step';
        return (
          <React.Fragment key={step.key}>
            <div className={cls}>
              <div className="step-icon">
                {isActive && step.key !== 'done'
                  ? <Loader2 size={14} className="animate-spin" />
                  : <step.Icon size={14} />
                }
              </div>
              <span className="step-label">
                {isActive && step.key === 'tool' && toolName
                  ? <><span className="tool-name-chip">{toolName}</span></>
                  : step.label}
              </span>
              {isActive && elapsedSec > 0 && (
                <span className="step-elapsed">{elapsedSec}s</span>
              )}
            </div>
            {idx < steps.length - 1 && <div className={`step-connector ${isDone ? 'done' : ''}`} />}
          </React.Fragment>
        );
      })}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main ChatArea
// ---------------------------------------------------------------------------

const ChatArea = ({ chatboxId }) => {
  const [messages, setMessages]             = useState([]);
  const [sessionFiles, setSessionFiles]     = useState([]);
  const [selectedFileIds, setSelectedFileIds] = useState([]);
  const [input, setInput]                   = useState('');
  const [loadingHistory, setLoadingHistory] = useState(true);

  // Streaming states
  const [isStreaming, setIsStreaming]           = useState(false);
  const [currentStreamText, setCurrentStreamText] = useState('');
  const [streamStatus, setStreamStatus]         = useState('');

  // Step progress
  const [currentStep, setCurrentStep]   = useState('thinking');
  const [activeToolName, setActiveToolName] = useState('');
  const [elapsedSec, setElapsedSec]     = useState(0);
  const elapsedTimerRef                 = useRef(null);

  // Tool execution log
  const [toolLog, setToolLog] = useState([]);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  useEffect(() => { scrollToBottom(); }, [messages, currentStreamText, streamStatus, toolLog]);

  // ---------------------------------------------------------------------------
  // Elapsed timer helpers
  // ---------------------------------------------------------------------------
  const startElapsedTimer = useCallback(() => {
    setElapsedSec(0);
    if (elapsedTimerRef.current) clearInterval(elapsedTimerRef.current);
    elapsedTimerRef.current = setInterval(() => setElapsedSec(s => s + 1), 1000);
  }, []);

  const stopElapsedTimer = useCallback(() => {
    if (elapsedTimerRef.current) { clearInterval(elapsedTimerRef.current); elapsedTimerRef.current = null; }
    setElapsedSec(0);
  }, []);

  useEffect(() => () => stopElapsedTimer(), [stopElapsedTimer]);

  // ---------------------------------------------------------------------------
  // Tool log helpers
  // ---------------------------------------------------------------------------
  const addToolEntry = useCallback((run_id, tool_name, args, timestamp) => {
    setToolLog(prev => [...prev, { run_id, tool_name, args, status: 'running', output_preview: null, duration_ms: null, timestamp }]);
  }, []);

  const finishToolEntry = useCallback((run_id, output_preview, duration_ms, is_error) => {
    setToolLog(prev => prev.map(e =>
      e.run_id === run_id
        ? { ...e, status: is_error ? 'error' : 'done', output_preview, duration_ms }
        : e
    ));
  }, []);

  // ---------------------------------------------------------------------------
  // Fetch history
  // ---------------------------------------------------------------------------
  const fetchHistory = async (silent = false) => {
    if (!silent) setLoadingHistory(true);
    try {
      const response = await api.get(`/chat/${chatboxId}/history`);
      setMessages(response.data.messages);
      const files = response.data.session_files;
      setSessionFiles(files);
      setSelectedFileIds(files.map(f => f.id));

    } catch (error) {
      console.error('[ChatArea] Error fetching history:', error);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (chatboxId) {
      setIsStreaming(false);
      setCurrentStreamText('');
      setStreamStatus('');
      setToolLog([]);
      setCurrentStep('thinking');
      setActiveToolName('');
      stopElapsedTimer();
      fetchHistory(false);
    }
  }, [chatboxId]);

  const toggleFileSelection = (fileId) => {
    setSelectedFileIds(prev => prev.includes(fileId) ? prev.filter(id => id !== fileId) : [...prev, fileId]);
  };

  // ---------------------------------------------------------------------------
  // Core stream processor
  // ---------------------------------------------------------------------------
  const processStream = async (url, body) => {
    setIsStreaming(true);
    setCurrentStreamText('');
    setStreamStatus('');
    setCurrentStep('thinking');
    setActiveToolName('');
    startElapsedTimer();

    const token = localStorage.getItem('access_token');

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}${url}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify(body)
        }
      );

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let streamContent = '';
      let buffer = ''; // accumulate partial SSE frames

      outer: while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Split on double-newline (SSE event boundary)
        const parts = buffer.split('\n\n');
        // Last part may be incomplete – keep it in buffer
        buffer = parts.pop() ?? '';

        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith('data: ')) continue;
          const dataStr = line.slice(6).trim();

          if (dataStr === '[DONE]') break outer;
          if (!dataStr) continue;

          try {
            const event = JSON.parse(dataStr);

            switch (event.type) {
              case 'token':
                streamContent += event.content;
                setCurrentStreamText(streamContent);
                setStreamStatus('');
                setCurrentStep('thinking');
                break;

              case 'status':
                setStreamStatus(event.content);
                break;

              case 'tool_start':
                setCurrentStep('tool');
                setActiveToolName(event.tool_name);
                startElapsedTimer();
                addToolEntry(event.run_id, event.tool_name, event.args, event.timestamp);
                break;

              case 'tool_end':
                setCurrentStep('thinking');
                setActiveToolName('');
                startElapsedTimer();
                finishToolEntry(event.run_id, event.output_preview, event.duration_ms, event.is_error);
                break;

              case 'error':
                setStreamStatus(`⚠️ Lỗi: ${event.content}`);
                console.error('[SSE error event]', event.content);
                break;
            }
          } catch (e) {
            console.error('[ChatArea] JSON parse error in SSE:', e, dataStr);
          }
        }
      }


      setCurrentStep('done');
      stopElapsedTimer();
      await fetchHistory(true);

    } catch (error) {
      console.error('[ChatArea] Stream error:', error);
      setStreamStatus('⚠️ Đã xảy ra lỗi khi kết nối.');
      stopElapsedTimer();
    } finally {
      setIsStreaming(false);
      setCurrentStreamText('');
      setStreamStatus('');
      setCurrentStep('thinking');
      setActiveToolName('');
    }
  };

  // ---------------------------------------------------------------------------
  // Send / approve handlers
  // ---------------------------------------------------------------------------
  const handleSendMessage = async () => {
    if (!input.trim() || isStreaming) return;
    const messageText = input;
    setInput('');
    setToolLog([]);
    setMessages(prev => [...prev, { role: 'user', content: messageText, id: Date.now() }]);
    await processStream(`/chat/${chatboxId}/stream?prompt=${encodeURIComponent(messageText)}`, selectedFileIds);
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  if (loadingHistory) {
    return <div className="chat-area flex-center"><Loader2 className="animate-spin text-accent" size={32} /></div>;
  }

  return (
    <div className="chat-area">
      <div className="chat-header flex-between">
        <h3 className="m-0 text-gradient">MADS Assistant</h3>
      </div>

      <div className="messages-container">
        {messages.length === 0 && !isStreaming && (
          <div className="empty-chat-placeholder text-center text-muted">
            <Bot size={48} className="mb-4 opacity-50" />
            <p>Bắt đầu cuộc trò chuyện. Bạn có thể hỏi bất cứ điều gì!</p>
          </div>
        )}

        {messages.map((msg, index) => (
          <div key={msg.id || index} className={`message-wrapper ${msg.role}`}>
            <div className="message-avatar">
              {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
            </div>
            <div className="message-content">
              {msg.role === 'assistant' ? (() => {
                const processed = processStreamText(msg.content);
                const chartToRender = msg.metadata_data?.chart || processed.chartData;
                return (
                  <>
                    <div className="markdown-body">
                      <ReactMarkdown>{processed.cleanText}</ReactMarkdown>
                    </div>
                    {chartToRender && <ChartViewer chartData={chartToRender} />}
                  </>
                );
              })() : (
                <p>{msg.content}</p>
              )}
            </div>
          </div>
        ))}

        {/* Tool Execution Log – hiển thị xuyên suốt session */}
        {toolLog.length > 0 && (
          <div className="message-wrapper assistant tool-log-wrapper">
            <div className="message-avatar"><Bot size={20} /></div>
            <div className="message-content tool-log-content">
              <ToolExecutionLog entries={toolLog} isStreaming={isStreaming} />
            </div>
          </div>
        )}

        {/* Streaming bubble */}
        {isStreaming && (
          <div className="message-wrapper assistant">
            <div className="message-avatar"><Bot size={20} /></div>
            <div className="message-content">
              {/* Step Progress Bar */}
              <StepProgressBar
                currentStep={currentStep}
                toolName={activeToolName}
                elapsedSec={elapsedSec}
              />

              {/* Streaming text */}
              {(() => {
                const { cleanText, chartData } = processStreamText(currentStreamText);
                return (
                  <>
                    {cleanText && (
                      <div className="markdown-body">
                        <ReactMarkdown>{cleanText}</ReactMarkdown>
                      </div>
                    )}
                    {chartData && <ChartViewer chartData={chartData} />}
                  </>
                );
              })()}

              {/* Status text */}
              {streamStatus && (
                <div className="status-indicator animate-pulse text-sm text-accent mt-2">
                  <Loader2 size={14} className="animate-spin inline-block mr-1" />
                  {streamStatus}
                </div>
              )}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <div className="file-upload-wrapper mb-3">
          <FileUpload
            chatboxId={chatboxId}
            sessionFiles={sessionFiles}
            selectedFileIds={selectedFileIds}
            onToggleFile={toggleFileSelection}
            onUploadComplete={() => fetchHistory(true)}
          />
        </div>

        <div className="input-wrapper glass">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); }
            }}
            placeholder="Nhập tin nhắn... (Nhấn Enter để gửi)"
            disabled={isStreaming}
            rows={1}
            className="chat-input"
          />
          <button
            className="send-btn btn-icon"
            onClick={handleSendMessage}
            disabled={!input.trim() || isStreaming}
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatArea;
