import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Bot, User, Loader2 } from 'lucide-react';
import api from '../api/client';
import FileUpload from './FileUpload';
import HITLApproval from './HITLApproval';
import ChartViewer from './ChartViewer';
import './ChatArea.css';

const extractValidJSON = (str) => {
  let firstBrace = str.indexOf('{');
  let firstBracket = str.indexOf('[');
  let startIdx = -1;
  let isObject = false;

  if (firstBrace !== -1 && (firstBracket === -1 || firstBrace < firstBracket)) {
    startIdx = firstBrace;
    isObject = true;
  } else if (firstBracket !== -1) {
    startIdx = firstBracket;
    isObject = false;
  } else {
    return str;
  }

  let openTokens = 0;
  let inString = false;
  let escapeNext = false;

  for (let i = startIdx; i < str.length; i++) {
    const char = str[i];
    if (escapeNext) {
      escapeNext = false;
      continue;
    }
    if (char === '\\') {
      escapeNext = true;
      continue;
    }
    if (char === '"') {
      inString = !inString;
      continue;
    }
    if (!inString) {
      if (isObject) {
        if (char === '{') openTokens++;
        if (char === '}') {
          openTokens--;
          if (openTokens === 0) return str.substring(startIdx, i + 1);
        }
      } else {
        if (char === '[') openTokens++;
        if (char === ']') {
          openTokens--;
          if (openTokens === 0) return str.substring(startIdx, i + 1);
        }
      }
    }
  }
  return str;
};

const ChatArea = ({ chatboxId }) => {
  const [messages, setMessages] = useState([]);
  const [sessionFiles, setSessionFiles] = useState([]);
  const [selectedFileIds, setSelectedFileIds] = useState([]);
  const [input, setInput] = useState('');
  const [loadingHistory, setLoadingHistory] = useState(true);

  // Streaming states
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamText, setCurrentStreamText] = useState('');
  const [streamStatus, setStreamStatus] = useState('');
  const [pendingHITL, setPendingHITL] = useState(null);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentStreamText, streamStatus, pendingHITL]);

  const fetchHistory = async (silent = false) => {
    if (!silent) setLoadingHistory(true);
    try {
      const response = await api.get(`/chat/${chatboxId}/history`);
      setMessages(response.data.messages);
      const files = response.data.session_files;
      setSessionFiles(files);

      // Mặc định chọn tất cả các file
      setSelectedFileIds(files.map(f => f.id));

      if (response.data.pending_tools && response.data.pending_tools.length > 0) {
        setPendingHITL(response.data.pending_tools);
        setIsStreaming(true);
      } else {
        setPendingHITL(null);
      }
    } catch (error) {
      console.error('Error fetching history:', error);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (chatboxId) {
      setIsStreaming(false);
      setCurrentStreamText('');
      setStreamStatus('');
      setPendingHITL(null);
      fetchHistory(false);
    }
  }, [chatboxId]);

  const toggleFileSelection = (fileId) => {
    setSelectedFileIds(prev =>
      prev.includes(fileId)
        ? prev.filter(id => id !== fileId)
        : [...prev, fileId]
    );
  };

  const processStream = async (url, body) => {
    setIsStreaming(true);
    setCurrentStreamText('');
    setStreamStatus('');
    setPendingHITL(null);
    let hitlTriggered = false;

    const token = localStorage.getItem('access_token');

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}${url}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let streamContent = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (dataStr === '[DONE]') {
              break;
            }
            if (!dataStr) continue;

            try {
              const event = JSON.parse(dataStr);

              if (event.type === 'token') {
                streamContent += event.content;
                setCurrentStreamText(streamContent);
                setStreamStatus('');
                // [DEBUG] uncomment below to trace each token
                // console.log('[DEBUG token]', event.content);
              } else if (event.type === 'status') {
                setStreamStatus(event.content);
              } else if (event.type === 'hitl_approval_required') {
                setPendingHITL(event.tool_calls);
                hitlTriggered = true;
                break;
              } else if (event.type === 'error') {
                setStreamStatus(`Lỗi: ${event.content}`);
              }
            } catch (e) {
              console.error('JSON parse error:', e, dataStr);
            }
          }
        }
        if (hitlTriggered) break;
      }

      if (!hitlTriggered) {
        // [DEBUG] In toàn bộ nội dung raw từ server
        console.group('%c[DEBUG] Full stream content from server', 'color: #4ade80; font-weight: bold');
        console.log(streamContent);
        console.groupEnd();

        // [DEBUG] Thử parse chart data ngay tại đây
        const debugParsed = processStreamText(streamContent);
        console.group('%c[DEBUG] processStreamText result', 'color: #60a5fa; font-weight: bold');
        console.log('cleanText (first 500 chars):', debugParsed.cleanText?.slice(0, 500));
        console.log('chartData:', debugParsed.chartData);
        console.groupEnd();

        await fetchHistory(true);
      }

    } catch (error) {
      console.error('Stream error:', error);
      setStreamStatus('Đã xảy ra lỗi khi kết nối.');
    } finally {
      if (!hitlTriggered) {
        setIsStreaming(false);
        setCurrentStreamText('');
        setStreamStatus('');
      }
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim() || isStreaming) return;

    const messageText = input;
    setInput('');

    setMessages(prev => [...prev, { role: 'user', content: messageText, id: Date.now() }]);

    // Chỉ gửi các file đã được tick chọn
    await processStream(`/chat/${chatboxId}/stream?prompt=${encodeURIComponent(messageText)}`, selectedFileIds);
  };

  const handleHITLComplete = async (payload) => {
    setPendingHITL(null);
    setStreamStatus('Đang gửi phản hồi của bạn...');
    await processStream(`/chat/${chatboxId}/approve`, payload);
  };

  const tryParsePlotlyJSON = (jsonStr) => {
    try {
      const parsed = JSON.parse(jsonStr);
      // Must have 'data' array and 'layout' object to be a Plotly figure
      if (
        parsed &&
        typeof parsed === 'object' &&
        Array.isArray(parsed.data) &&
        parsed.layout &&
        typeof parsed.layout === 'object'
      ) {
        let filteredData = [];
        let extractedLayout = parsed.layout || {};
        parsed.data.forEach(item => {
          if (item && typeof item === 'object' && item.type === 'layout') {
            if (Object.keys(extractedLayout).length === 0) {
              const { type, ...rest } = item;
              extractedLayout = rest;
            }
          } else {
            filteredData.push(item);
          }
        });
        return { type: 'plotly', data: filteredData, layout: extractedLayout };
      }
    } catch (_) { }
    return null;
  };

  const processStreamText = (text) => {
    if (!text) return { cleanText: '', chartData: null };

    // --- Attempt 1: explicit <CHART_JSON> tag ---
    const tagPattern = /<CHART_JSON>([\s\S]*?)(<\/CHART_JSON>|$)/;
    const tagMatch = text.match(tagPattern);
    if (tagMatch) {
      const cleanText = text.replace(tagPattern, '').trim();
      // Only parse when we have the closing tag (not mid-stream)
      if (tagMatch[2] === '</CHART_JSON>') {
        try {
          let jsonStr = tagMatch[1].trim();
          console.log("[DEBUG] Raw CHART_JSON string from stream:", jsonStr);
          if (jsonStr.startsWith('```json')) {
            jsonStr = jsonStr.replace(/^```json\n?/, '').replace(/\n?```$/, '').trim();
          } else if (jsonStr.startsWith('```')) {
            jsonStr = jsonStr.replace(/^```\n?/, '').replace(/\n?```$/, '').trim();
          }
          jsonStr = extractValidJSON(jsonStr);
          console.log("[DEBUG] Cleaned JSON string:", jsonStr);
          const chartData = tryParsePlotlyJSON(jsonStr);
          console.log("[DEBUG] Final chartData object:", chartData);
          return { cleanText, chartData };
        } catch (e) {
          console.error("[DEBUG] JSON parse error in processStreamText:", e);
          return { cleanText, chartData: null };
        }
      }
      return { cleanText, chartData: null };
    }

    // --- Attempt 2: fallback — raw Plotly JSON anywhere in the text ---
    // Look for the outermost {...} that contains both 'data' and 'layout'
    const jsonStart = text.indexOf('{');
    if (jsonStart !== -1) {
      try {
        const rawJsonStr = extractValidJSON(text.substring(jsonStart));
        const chartData = tryParsePlotlyJSON(rawJsonStr);
        if (chartData) {
          console.log("[DEBUG] Detected raw Plotly JSON without tag");
          // Remove the raw JSON blob from the displayed text
          const cleanText = (text.substring(0, jsonStart) + text.substring(jsonStart + rawJsonStr.length)).trim();
          return { cleanText, chartData };
        }
      } catch (_) { }
    }

    return { cleanText: text, chartData: null };
  };

  if (loadingHistory) {
    return <div className="chat-area flex-center"><Loader2 className="animate-spin text-accent" size={32} /></div>;
  }

  return (
    <div className="chat-area">
      {/* Header chỉ để trang trí hoặc để trống, file upload chuyển xuống dưới */}
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
              {msg.role === 'assistant' ? (
                (() => {
                  const processed = processStreamText(msg.content);
                  const chartToRender = msg.metadata_data?.chart || processed.chartData;

                  // [DEBUG] Log tất cả assistant messages để so sánh
                  console.log(
                    `[DEBUG msg#${msg.id ?? index}]`,
                    'has metadata_data.chart:', !!msg.metadata_data?.chart,
                    '| has processedChartData:', !!processed.chartData,
                    '| chartToRender:', chartToRender ? `type=${chartToRender.type}, data.length=${chartToRender.data?.length}` : 'null',
                    '| content preview:', msg.content?.slice(0, 80)
                  );

                  return (
                    <>
                      <div className="markdown-body">
                        <ReactMarkdown>{processed.cleanText}</ReactMarkdown>
                      </div>
                      {chartToRender && (
                        <ChartViewer chartData={chartToRender} />
                      )}
                    </>
                  );
                })()
              ) : (
                <p>{msg.content}</p>
              )}
            </div>
          </div>
        ))}


        {isStreaming && (
          <div className="message-wrapper assistant">
            <div className="message-avatar">
              <Bot size={20} />
            </div>
            <div className="message-content">
              {(() => {
                const { cleanText, chartData } = processStreamText(currentStreamText);
                return (
                  <>
                    {cleanText && (
                      <div className="markdown-body">
                        <ReactMarkdown>{cleanText}</ReactMarkdown>
                      </div>
                    )}
                    {chartData && (
                      <ChartViewer chartData={chartData} />
                    )}
                  </>
                );
              })()}
              {streamStatus && (
                <div className="status-indicator animate-pulse text-sm text-accent mt-2">
                  <Loader2 size={14} className="animate-spin inline-block mr-1" />
                  {streamStatus}
                </div>
              )}
              {pendingHITL && (
                <HITLApproval
                  chatboxId={chatboxId}
                  toolCalls={pendingHITL}
                  onComplete={handleHITLComplete}
                />
              )}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        {/* Upload File area placed above the input box */}
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
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
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
