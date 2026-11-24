import React from 'react';
import { FileSearch, Sparkles, Mic2, ShieldCheck } from 'lucide-react';

const features = [
  {
    icon: FileSearch,
    title: 'Official Notice Ingestion',
    desc: 'Targeted crawlers for ipu.ac.in and examdept.ggsipu.ac.in with incremental updates.',
  },
  {
    icon: Sparkles,
    title: 'Grounded Gemini RAG',
    desc: 'Semantic retrieval powered by Zilliz vector search with explicit source citations.',
  },
  {
    icon: Mic2,
    title: 'Voice & Multimodal',
    desc: 'Bilingual speech recognition and document parsing for PDFs, DOCX, and images.',
  },
  {
    icon: ShieldCheck,
    title: 'Verified Academic Data',
    desc: 'Engineered specifically for student evaluation and factual fidelity.',
  },
];

export default function FeatureGrid() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full max-w-4xl mx-auto my-8">
      {features.map((feature, idx) => {
        const Icon = feature.icon;
        return (
          <div
            key={idx}
            className="p-4 rounded-xl bg-white border border-warm-200/80 shadow-subtle hover:border-crimson-200 hover:shadow-premium transition-all duration-200"
          >
            <div className="w-8 h-8 rounded-lg bg-crimson-50 text-crimson-900 flex items-center justify-center mb-3">
              <Icon className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-sm text-charcoal-900 mb-1">{feature.title}</h3>
            <p className="text-xs text-charcoal-500 leading-relaxed">{feature.desc}</p>
          </div>
        );
      })}
    </div>
  );
}
