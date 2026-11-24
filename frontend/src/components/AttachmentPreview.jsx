import React from 'react';
import { X, Image, FileText, Music } from 'lucide-react';

export default function AttachmentPreview({ file, mediaType, onRemove }) {
  if (!file) return null;

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getIcon = () => {
    if (mediaType === 'image') return <Image className="w-4 h-4 text-crimson-800" />;
    if (mediaType === 'document') return <FileText className="w-4 h-4 text-amber-700" />;
    if (mediaType === 'audio') return <Music className="w-4 h-4 text-blue-700" />;
    return <FileText className="w-4 h-4 text-charcoal-700" />;
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-2">
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-warm-100/90 border border-warm-300 text-xs text-charcoal-800 shadow-sm animate-in fade-in slide-in-from-bottom-1 duration-150">
        <div className="p-1 rounded-md bg-white shadow-subtle">
          {getIcon()}
        </div>
        <div className="flex flex-col">
          <span className="font-semibold max-w-[220px] truncate">{file.name}</span>
          <span className="text-[10px] text-charcoal-400">{formatSize(file.size)}</span>
        </div>
        <button
          type="button"
          onClick={onRemove}
          title="Remove attachment"
          className="ml-2 p-1 rounded-lg text-charcoal-400 hover:text-rose-600 hover:bg-white transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
