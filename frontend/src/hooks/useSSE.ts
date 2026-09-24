import { useState, useCallback, useRef } from 'react';

interface SSEEvent {
  event: string;
  data: any;
}

interface UseSSEReturn {
  events: SSEEvent[];
  isStreaming: boolean;
  error: string | null;
  startStream: (url: string) => void;
  stopStream: () => void;
  currentStage: { name: string; index: number; total: number } | null;
  streamedTokens: string;
  draftComplete: boolean;
  safetyResult: { passed: boolean; flags: string[] } | null;
  pipelineComplete: boolean;
  totalMs: number | null;
}

export function useSSE(): UseSSEReturn {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<{ name: string; index: number; total: number } | null>(null);
  const [streamedTokens, setStreamedTokens] = useState('');
  const [draftComplete, setDraftComplete] = useState(false);
  const [safetyResult, setSafetyResult] = useState<{ passed: boolean; flags: string[] } | null>(null);
  const [pipelineComplete, setPipelineComplete] = useState(false);
  const [totalMs, setTotalMs] = useState<number | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const stopStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const startStream = useCallback((url: string) => {
    stopStream();
    setEvents([]);
    setError(null);
    setStreamedTokens('');
    setDraftComplete(false);
    setSafetyResult(null);
    setPipelineComplete(false);
    setTotalMs(null);
    setCurrentStage(null);
    setIsStreaming(true);

    const token = localStorage.getItem('token');
    // EventSource doesn't support headers, so append token as query param
    const separator = url.includes('?') ? '&' : '?';
    const fullUrl = token ? `${url}${separator}token=${token}` : url;
    
    const es = new EventSource(fullUrl);
    eventSourceRef.current = es;

    const handleEvent = (eventName: string) => (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        setEvents(prev => [...prev, { event: eventName, data }]);

        switch (eventName) {
          case 'stage_start':
            setCurrentStage({ name: data.stage, index: data.index, total: data.total });
            break;
          case 'token':
            setStreamedTokens(prev => prev + data.content);
            break;
          case 'draft_complete':
            setDraftComplete(true);
            break;
          case 'safety_result':
            setSafetyResult(data);
            break;
          case 'done':
            setPipelineComplete(true);
            setTotalMs(data.total_ms);
            setIsStreaming(false);
            es.close();
            break;
          case 'error':
            setError(data.message);
            setIsStreaming(false);
            es.close();
            break;
        }
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    };

    es.addEventListener('stage_start', handleEvent('stage_start'));
    es.addEventListener('stage_complete', handleEvent('stage_complete'));
    es.addEventListener('token', handleEvent('token'));
    es.addEventListener('draft_complete', handleEvent('draft_complete'));
    es.addEventListener('safety_result', handleEvent('safety_result'));
    es.addEventListener('done', handleEvent('done'));
    es.addEventListener('error', handleEvent('error'));
    
    es.onerror = () => {
      setError('Connection lost. Please retry.');
      setIsStreaming(false);
      es.close();
    };
  }, [stopStream]);

  return { events, isStreaming, error, startStream, stopStream, currentStage, streamedTokens, draftComplete, safetyResult, pipelineComplete, totalMs };
}
