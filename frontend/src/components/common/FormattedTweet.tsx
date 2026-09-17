import React from 'react';

interface FormattedTweetProps {
  text: string;
  className?: string;
}

export const FormattedTweet: React.FC<FormattedTweetProps> = ({ text, className = '' }) => {
  if (!text) return null;

  // Split text matching @apple support, @mentions, #hashtags, and http(s) URLs
  const parts = text.split(/(@apple\s+support|@[\w_]+|#[\w_]+|https?:\/\/[^\s]+)/gi);

  return (
    <span className={className}>
      {parts.map((part, index) => {
        if (!part) return null;
        const lower = part.toLowerCase();
        if (lower.startsWith('@') || lower.startsWith('#')) {
          return (
            <span
              key={index}
              className="text-sky-500 dark:text-sky-400 font-semibold hover:underline cursor-pointer inline-block"
            >
              {part}
            </span>
          );
        }
        if (lower.startsWith('http://') || lower.startsWith('https://')) {
          return (
            <a
              key={index}
              href={part}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sky-500 dark:text-sky-400 font-semibold hover:underline"
            >
              {part}
            </a>
          );
        }
        return <span key={index}>{part}</span>;
      })}
    </span>
  );
};

