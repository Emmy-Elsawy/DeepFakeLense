import React from 'react';

export default function ErrorCard({ error, onRetry, onReset, language }) {
  const isRtl = language === 'ar';

  return (
    <main className="flex-grow flex flex-col items-center justify-center py-16 px-gutter w-full">
      <div className="w-full max-w-lg bg-surface-container-lowest border border-error/30 rounded-2xl p-8 md:p-10 card-shadow text-center space-y-6 relative overflow-hidden">
        
        {/* Top Accent Bar */}
        <div className="absolute top-0 left-0 w-full h-1.5 bg-error"></div>

        {/* Error Icon */}
        <div className="w-16 h-16 bg-error-container text-on-error-container rounded-full flex items-center justify-center mx-auto">
          <span className="material-symbols-outlined text-[36px] icon-fill">
            error
          </span>
        </div>

        {/* Title and Message */}
        <div>
          <h2 className="text-headline-md font-headline font-semibold text-primary mb-2">
            {isRtl ? 'تعذر إتمام عملية الفحص' : 'Analysis Incomplete'}
          </h2>
          <p className="text-body-md font-body text-on-surface-variant leading-relaxed">
            {error || (isRtl ? 'حدث خطأ أثناء الاتصال بالخادم أو الوكلاء.' : 'An error occurred during verification pipeline execution.')}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          {onRetry && (
            <button
              onClick={onRetry}
              className="w-full sm:w-auto bg-primary hover:bg-primary-container text-on-primary text-label-md font-label font-medium px-6 py-3 rounded-lg transition-all shadow-sm flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined text-[18px]">refresh</span>
              <span>{isRtl ? 'إعادة المحاولة' : 'Try Again'}</span>
            </button>
          )}

          <button
            onClick={onReset}
            className="w-full sm:w-auto bg-surface-container-low hover:bg-surface-container text-primary border border-outline-variant text-label-md font-label font-medium px-6 py-3 rounded-lg transition-all flex items-center justify-center gap-2"
          >
            <span className="material-symbols-outlined text-[18px]">arrow_back</span>
            <span>{isRtl ? 'العودة للرئيسية' : 'Return to Home'}</span>
          </button>
        </div>

      </div>
    </main>
  );
}
