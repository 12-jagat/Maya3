import React, { useState, useRef } from 'react';
import { Paperclip, Image, FileText, Music, AlertCircle } from 'lucide-react';

export default function FileUploadButton({ onFileSelect, disabled }) {
  const [isOpen, setIsOpen] = useState(false);
  const fileInputRef = useRef(null);
  const [activeAccept, setActiveAccept] = useState('*');
  const [activeType, setActiveType] = useState('image');

  const triggerPicker = (type, accept) => {
    setActiveType(type);
    setActiveAccept(accept);
    setIsOpen(false);
    setTimeout(() => {
      if (fileInputRef.current) {
        fileInputRef.current.accept = accept;
        fileInputRef.current.click();
      }
    }, 50);
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileSelect(file, activeType);
    }
    // Reset file input value so selecting the same file triggers change
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="relative">
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={handleFileChange}
      />

      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        disabled={disabled}
        title="Attach file (Image, PDF, DOCX, Audio)"
        className={`p-2.5 rounded-xl transition-all ${
          isOpen
            ? 'bg-crimson-100 text-crimson-900'
            : 'text-charcoal-500 hover:text-crimson-800 hover:bg-warm-100 disabled:opacity-40'
        }`}
      >
        <Paperclip className="w-4 h-4" />
      </button>

      {/* Menu dropdown */}
      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-20"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute bottom-12 left-0 z-30 w-52 bg-white rounded-2xl shadow-premium border border-warm-200/90 p-1.5 animate-in fade-in slide-in-from-bottom-2 duration-150">
            <button
              type="button"
              onClick={() => triggerPicker('image', 'image/jpeg,image/png,image/webp')}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-charcoal-700 hover:text-crimson-900 hover:bg-warm-100 rounded-xl transition-colors text-left"
            >
              <div className="p-1.5 rounded-lg bg-crimson-50 text-crimson-900">
                <Image className="w-3.5 h-3.5" />
              </div>
              <div>
                <div className="font-semibold">Notice Image</div>
                <div className="text-[10px] text-charcoal-400">JPG, PNG, WEBP (≤10MB)</div>
              </div>
            </button>

            <button
              type="button"
              onClick={() => triggerPicker('document', '.pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-charcoal-700 hover:text-crimson-900 hover:bg-warm-100 rounded-xl transition-colors text-left"
            >
              <div className="p-1.5 rounded-lg bg-amber-50 text-amber-900">
                <FileText className="w-3.5 h-3.5" />
              </div>
              <div>
                <div className="font-semibold">Document</div>
                <div className="text-[10px] text-charcoal-400">PDF, DOCX (≤30MB)</div>
              </div>
            </button>

            <button
              type="button"
              onClick={() => triggerPicker('audio', 'audio/wav,audio/mpeg,audio/mp3,audio/x-m4a,audio/aac,.wav,.mp3,.m4a,.aac')}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-charcoal-700 hover:text-crimson-900 hover:bg-warm-100 rounded-xl transition-colors text-left"
            >
              <div className="p-1.5 rounded-lg bg-blue-50 text-blue-900">
                <Music className="w-3.5 h-3.5" />
              </div>
              <div>
                <div className="font-semibold">Audio Note</div>
                <div className="text-[10px] text-charcoal-400">WAV, MP3, M4A (≤20MB)</div>
              </div>
            </button>
          </div>
        </>
      )}
    </div>
  );
}
