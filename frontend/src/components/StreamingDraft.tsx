import React from 'react';
import { CheckCircle2, Circle, Loader2, ShieldCheck, ShieldAlert, Clock } from 'lucide-react';

interface StreamingDraftProps {
  currentStage: { name: string; index: number; total: number } | null;
  streamedTokens: string;
  draftComplete: boolean;
  safetyResult: { passed: boolean; flags: string[] } | null;
  pipelineComplete: boolean;
  totalMs: number | null;
  isStreaming: boolean;
}

export const StreamingDraft: React.FC<StreamingDraftProps> = ({
  currentStage, streamedTokens, draftComplete, safetyResult, pipelineComplete, totalMs, isStreaming
}) => {
  const stages = ['Intent Classification', 'Knowledge Retrieval', 'Escalation Analysis', 'Response Drafting', 'Safety Validation'];
  const currentIndex = currentStage?.index || 0;
  
  return (
    <div className="space-y-4 animate-fade-in">
      {/* Pipeline Progress */}
      <div className="flex items-center justify-between px-2">
        {stages.map((stage, idx) => {
          const stageNum = idx + 1;
          const isComplete = stageNum < currentIndex || pipelineComplete;
          const isCurrent = stageNum === currentIndex && isStreaming;
          
          return (
            <React.Fragment key={stage}>
              <div className="flex flex-col items-center gap-1.5">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300 ${
                  isComplete ? 'bg-emerald-500 text-white' :
                  isCurrent ? 'bg-sky-500 text-white animate-pulse-subtle' :
                  'bg-slate-100 dark:bg-neutral-800 text-slate-400 dark:text-neutral-600'
                }`}>
                  {isComplete ? <CheckCircle2 className="w-4 h-4" /> :
                   isCurrent ? <Loader2 className="w-4 h-4 animate-spin" /> :
                   <Circle className="w-4 h-4" />}
                </div>
                <span className={`text-[10px] font-semibold text-center max-w-[80px] leading-tight ${
                  isComplete ? 'text-emerald-600 dark:text-emerald-400' :
                  isCurrent ? 'text-sky-600 dark:text-sky-400' :
                  'text-slate-400 dark:text-neutral-600'
                }`}>{stage}</span>
              </div>
              {idx < stages.length - 1 && (
                <div className={`flex-1 h-0.5 mx-1 rounded-full transition-all duration-500 ${
                  stageNum < currentIndex || pipelineComplete ? 'bg-emerald-500' : 'bg-slate-200 dark:bg-neutral-800'
                }`} />
              )}
            </React.Fragment>
          );
        })}
      </div>
      
      {/* Streaming Text */}
      {streamedTokens && (
        <div className="bg-slate-50 dark:bg-black border border-slate-200 dark:border-neutral-800 rounded-xl p-4 min-h-[80px]">
          <p className="text-sm text-slate-800 dark:text-neutral-200 leading-relaxed">
            {streamedTokens}
            {isStreaming && !draftComplete && (
              <span className="inline-block w-0.5 h-4 bg-sky-500 ml-0.5 animate-pulse" />
            )}
          </p>
        </div>
      )}
      
      {/* Safety & Completion */}
      <div className="flex items-center justify-between">
        {safetyResult && (
          <div className={`badge ${
            safetyResult.passed 
              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
              : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20'
          }`}>
            {safetyResult.passed ? <ShieldCheck className="w-3 h-3 mr-1" /> : <ShieldAlert className="w-3 h-3 mr-1" />}
            {safetyResult.passed ? 'Safety Passed' : `${safetyResult.flags.length} Safety Flag(s)`}
          </div>
        )}
        {totalMs !== null && (
          <div className="badge bg-slate-100 dark:bg-neutral-800 text-slate-600 dark:text-neutral-400 border-slate-200 dark:border-neutral-700">
            <Clock className="w-3 h-3 mr-1" />
            {totalMs}ms total
          </div>
        )}
      </div>
    </div>
  );
};
