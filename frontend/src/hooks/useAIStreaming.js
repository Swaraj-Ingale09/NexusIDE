import { useCallback, useRef, useState } from 'react';

/**
 * Hook for WebSocket-based AI streaming.
 * Connects to ws://host/ws/ai-stream/ and streams AI responses chunk by chunk.
 * */
export function useAIStreaming() {
  const wsRef = useRef(null);
  const [streaming, setStreaming] = useState(false);
  const [streamedText, setStreamedText] = useState('');
  const chunksRef = useRef([]);
  const onDoneRef = useRef(null);

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return wsRef.current;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const token = localStorage.getItem('access_token') || '';

    const wsUrl = `${protocol}//${host}/ws/ai-stream/?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'chunk') {
          chunksRef.current.push(data.content);
          setStreamedText(chunksRef.current.join(''));
        } else if (data.type === 'completed') {
          setStreaming(false);
          const finalText = data.response || chunksRef.current.join('');
          if (onDoneRef.current) {
            onDoneRef.current(finalText, data.provider);
          }
        } else if (data.type === 'error') {
          setStreaming(false);
          if (onDoneRef.current) {
            onDoneRef.current(`Error: ${data.error}`, null);
          }
        }
      } catch {
        // Non-JSON message, ignore
      }
    };

    ws.onerror = () => {
      setStreaming(false);
    };

    ws.onclose = () => {
      wsRef.current = null;
    };

    return ws;
  }, []);

  const send = useCallback((action, code, context, onDone) => {
    const ws = connect();
    onDoneRef.current = onDone;
    chunksRef.current = [];
    setStreamedText('');
    setStreaming(true);

    const sendWhenOpen = () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action, code, context }));
      } else {
        setTimeout(sendWhenOpen, 50);
      }
    };

    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action, code, context }));
    } else {
      ws.onopen = () => {
        ws.send(JSON.stringify({ action, code, context }));
      };
    }
  }, [connect]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStreaming(false);
  }, []);

  return { send, streaming, streamedText, disconnect };
}
