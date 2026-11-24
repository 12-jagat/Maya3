import React, { useState } from 'react';
import { Maximize2, X, Download } from 'lucide-react';

export default function ImagePreview({ src, alt, caption }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!src) return null;

  return (
    <>
      <div className="mt-2.5 relative group max-w-sm rounded-xl overflow-hidden border border-warm-200/90 shadow-sm bg-warm-50">
        <img
          src={src}
          alt={alt || 'Uploaded notice'}
          className="w-full max-h-64 object-cover cursor-pointer transition-transform duration-200 group-hover:scale-105"
          onClick={() => setIsOpen(true)}
        />
        <div
          onClick={() => setIsOpen(true)}
          className="absolute inset-0 bg-charcoal-950/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center cursor-pointer text-white"
        >
          <div className="p-2 rounded-full bg-charcoal-900/80 backdrop-blur-sm flex items-center gap-1.5 text-xs font-medium">
            <Maximize2 className="w-3.5 h-3.5" />
            <span>Expand</span>
          </div>
        </div>
        {caption && (
          <div className="px-3 py-1.5 text-[11px] text-charcoal-600 bg-white/95 border-t border-warm-200 truncate">
            {caption}
          </div>
        )}
      </div>

      {/* Lightbox Modal */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-charcoal-950/85 backdrop-blur-sm p-4 animate-in fade-in duration-150"
          onClick={() => setIsOpen(false)}
        >
          <div
            className="relative max-w-4xl max-h-[90vh] bg-white rounded-2xl overflow-hidden shadow-2xl flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-warm-200 bg-warm-50">
              <span className="text-xs font-semibold text-charcoal-800 truncate">{caption || alt || 'Image Preview'}</span>
              <div className="flex items-center gap-2">
                <a
                  href={src}
                  download
                  title="Download image"
                  className="p-1 rounded-lg text-charcoal-500 hover:text-charcoal-900 hover:bg-warm-200 transition-colors"
                >
                  <Download className="w-4 h-4" />
                </a>
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="p-1 rounded-lg text-charcoal-500 hover:text-charcoal-900 hover:bg-warm-200 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="p-2 overflow-auto max-h-[80vh] flex items-center justify-center bg-charcoal-900">
              <img src={src} alt={alt || 'Image'} className="max-w-full max-h-full object-contain rounded-lg" />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
