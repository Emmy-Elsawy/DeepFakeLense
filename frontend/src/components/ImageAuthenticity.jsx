import React from 'react';

export default function ImageAuthenticity({ authenticity, imageUrl, language }) {
  if (!authenticity) return null;

  const isRtl = language === 'ar';
  const confidence = authenticity.confidence || 0.85;
  const percentage = Math.round(confidence * 100);
  const isAi = authenticity.is_ai_generated;

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden card-shadow space-y-0">
      
      {/* Optional Image Header Preview */}
      {imageUrl && (
        <div className="relative w-full h-56 md:h-64 bg-surface-container-low border-b border-outline-variant overflow-hidden">
          <img
            src={imageUrl}
            alt="Source Material"
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent"></div>
          <div className="absolute bottom-4 left-4 rtl:left-auto rtl:right-4 flex items-center space-x-2 rtl:space-x-reverse">
            <span className="material-symbols-outlined text-white icon-fill text-[20px]">
              image
            </span>
            <span className="text-white text-label-sm font-label font-medium uppercase tracking-wider">
              {isRtl ? 'المحتوى المرئي المفحوص' : 'Source Visual Material'}
            </span>
          </div>
        </div>
      )}

      <div className="p-6 md:p-8 space-y-6">
        
        {/* Section Header */}
        <div className="flex items-center justify-between border-b border-outline-variant pb-4">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[22px]">
              psychology
            </span>
            <h3 className="text-headline-md font-headline font-semibold text-primary">
              {isRtl ? 'تحليل التزييف العميق والذكاء الاصطناعي' : 'Image Forensics & Deepfake Detection'}
            </h3>
          </div>
          <span
            className={`text-label-sm font-label font-semibold px-3 py-1 rounded-full uppercase tracking-wider ${
              isAi
                ? 'bg-error-container text-on-error-container'
                : 'bg-secondary-container text-on-secondary-container'
            }`}
          >
            {isAi
              ? isRtl ? 'مرجح توليده بالذكاء الاصطناعي' : 'AI Generated'
              : isRtl ? 'أصلي / غير مولد' : 'Natural / Authentic'}
          </span>
        </div>

        {/* Forensic Authenticity Meter Gauge */}
        <div className="bg-surface-bright border border-outline-variant rounded-lg p-5">
          <div className="flex justify-between items-center mb-3">
            <span className="text-label-md font-label text-on-surface font-medium">
              {isRtl ? 'احتمالية التوليد الاصطناعي (Synthetic Likelihood)' : 'AI-Generation Likelihood'}
            </span>
            <span className={`text-headline-md font-headline font-bold ${isAi ? 'text-error' : 'text-secondary'}`}>
              {percentage}%
            </span>
          </div>

          {/* Horizontal Gauge Bar */}
          <div className="w-full h-2.5 bg-surface-container-highest rounded-full overflow-hidden flex">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${
                isAi ? 'bg-error' : 'bg-secondary'
              }`}
              style={{ width: `${percentage}%` }}
            ></div>
          </div>

          <div className="flex justify-between mt-2 text-label-sm font-label text-on-surface-variant font-medium">
            <span>{isRtl ? 'طبيعي / بشري (Human)' : 'Human / Authentic (0%)'}</span>
            <span>{isRtl ? 'مصطنع / ذكاء اصطناعي (Synthetic)' : 'Synthetic / AI (100%)'}</span>
          </div>
        </div>

        {/* Forensic Notes */}
        {authenticity.note && (
          <div className="bg-surface-container-low border border-outline-variant/60 rounded-lg p-4">
            <h4 className="text-label-sm font-label uppercase tracking-wider text-primary font-semibold mb-1.5">
              {isRtl ? 'ملاحظة التحليل البصري:' : 'Forensic Visual Notes:'}
            </h4>
            <p className="text-body-md font-body text-on-surface-variant leading-relaxed" dir={isRtl ? 'rtl' : 'ltr'}>
              {authenticity.note}
            </p>
          </div>
        )}

        {/* Disclaimer Caveat Banner */}
        <div className="bg-surface-container-low text-on-surface-variant rounded-lg flex items-start p-3.5 border border-outline-variant/40 text-label-sm font-label">
          <span className="material-symbols-outlined text-outline mr-2.5 rtl:mr-0 rtl:ml-2.5 shrink-0 text-[18px]">
            info
          </span>
          <p className="leading-snug">
            {isRtl
              ? 'تنويه: هذا الفحص يعتمد على مؤشرات ونماذج تحليل الترددات والأنماط، ويجب تقييمه كجزء من سياق تحقيقي متكامل.'
              : 'Forensic Disclaimer: Deepfake detection provides heuristic and frequency domain signals. Results should be interpreted within broader journalistic and investigative context.'}
          </p>
        </div>

      </div>
    </div>
  );
}
