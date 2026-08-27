import React, { useState } from 'react';
import { askFollowUp } from '../api/client';

export default function FollowUpSection({ contextData, language }) {
  const isRtl = language === 'ar';
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [qaThread, setQaThread] = useState([]);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const userQuestion = question.trim();
    setQuestion('');
    setLoading(true);
    setError(null);

    // Append optimistic user query
    const newEntry = {
      question: userQuestion,
      answer: null,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setQaThread((prev) => [...prev, newEntry]);

    try {
      const resp = await askFollowUp({
        question: userQuestion,
        context: contextData,
        language
      });

      // Update last entry with real answer
      setQaThread((prev) =>
        prev.map((item, index) =>
          index === prev.length - 1 ? { ...item, answer: resp.answer } : item
        )
      );
    } catch (err) {
      setError(err.message || 'Failed to get follow-up answer.');
      setQaThread((prev) =>
        prev.map((item, index) =>
          index === prev.length - 1
            ? { ...item, answer: isRtl ? 'عذراً، تعذر الإجابة على السؤال حالياً.' : 'Could not generate answer.' }
            : item
        )
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="space-y-6 pt-4">
      
      {/* Follow-up Header */}
      <div className="flex items-center gap-2 border-b border-outline-variant pb-3">
        <span className="material-symbols-outlined text-primary text-[20px]">
          forum
        </span>
        <h3 className="text-headline-md font-headline font-semibold text-primary">
          {isRtl ? 'اسأل سؤالاً استيضاحياً' : 'Ask a Follow-Up Question'}
        </h3>
      </div>

      {/* Discussion Thread History */}
      {qaThread.length > 0 && (
        <div className="space-y-4">
          {qaThread.map((item, index) => (
            <div key={index} className="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 space-y-3">
              
              {/* Question */}
              <div className="flex items-start gap-2.5">
                <span className="material-symbols-outlined text-primary mt-0.5 text-[18px]">
                  help_outline
                </span>
                <p className="text-body-md font-body font-semibold text-primary" dir={isRtl ? 'rtl' : 'ltr'}>
                  {item.question}
                </p>
              </div>

              {/* Answer */}
              <div className="border-t border-outline-variant/40 pt-3 flex items-start gap-2.5 pl-6 rtl:pl-0 rtl:pr-6">
                <span className="material-symbols-outlined text-secondary mt-0.5 text-[18px]">
                  auto_awesome
                </span>
                <div className="flex-1">
                  {item.answer ? (
                    <p className="text-body-md font-body text-on-surface leading-relaxed" dir={isRtl ? 'rtl' : 'ltr'}>
                      {item.answer}
                    </p>
                  ) : (
                    <div className="flex items-center gap-2 text-label-sm font-label text-on-surface-variant">
                      <span className="material-symbols-outlined text-[16px] animate-spin text-secondary">
                        sync
                      </span>
                      <span>{isRtl ? 'جاري استنتاج الإجابة من الأدلة المجمعة...' : 'Extracting context from gathered evidence...'}</span>
                    </div>
                  )}
                </div>
              </div>

            </div>
          ))}
        </div>
      )}

      {/* Error notification if any */}
      {error && (
        <p className="text-label-sm font-label text-error bg-error-container/40 p-2.5 rounded-lg">
          {error}
        </p>
      )}

      {/* Input Bar */}
      <form onSubmit={handleSubmit}>
        <div className="bg-surface-container-low border border-outline-variant rounded-xl p-2 flex items-center focus-within:ring-2 focus-within:ring-primary focus-within:border-transparent transition-all">
          <span className="material-symbols-outlined text-on-surface-variant ml-3 rtl:ml-0 rtl:mr-3 text-[20px]">
            chat_bubble_outline
          </span>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
            dir={isRtl ? 'rtl' : 'ltr'}
            className="flex-1 bg-transparent border-none focus:ring-0 text-body-md font-body text-on-surface placeholder:text-on-surface-variant/60 py-3 px-4 outline-none"
            placeholder={
              isRtl
                ? 'اسأل عن تفاصيل إضافية أو مصدر معين...'
                : 'Ask a follow-up about this claim or evidence...'
            }
          />
          <button
            type="submit"
            disabled={!question.trim() || loading}
            className="bg-primary hover:bg-primary-container disabled:opacity-40 text-on-primary p-2.5 rounded-lg transition-opacity flex items-center justify-center h-10 w-10 shrink-0 cursor-pointer active:scale-95"
          >
            {loading ? (
              <span className="material-symbols-outlined text-[20px] animate-spin">sync</span>
            ) : (
              <span className="material-symbols-outlined text-[20px] rtl:rotate-180">send</span>
            )}
          </button>
        </div>
      </form>

    </section>
  );
}
