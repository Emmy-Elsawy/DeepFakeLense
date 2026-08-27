import React from 'react';
import { VERDICT_CONFIG, STANCE_CONFIG } from '../utils/constants';
import ImageAuthenticity from './ImageAuthenticity';
import FollowUpSection from './FollowUpSection';

export default function VerdictView({
  resultData,
  claimText,
  imageUrl,
  inputType,
  language,
  onReset
}) {
  const isRtl = language === 'ar';
  
  // Normalize verdict key (true, false, misleading, unverified)
  const rawVerdict = String(resultData?.verdict || 'unverified').toLowerCase();
  const verdictConfig = VERDICT_CONFIG[rawVerdict] || VERDICT_CONFIG.unverified;

  // Confidence percentage
  const rawConfidence = resultData?.confidence ?? 0.95;
  const confidencePercent = Math.round(rawConfidence * 100);

  // Sources array
  const sources = Array.isArray(resultData?.sources) ? resultData.sources : [];

  // Helper to extract clean domain
  const getDomain = (url) => {
    try {
      const u = new URL(url);
      return u.hostname.replace(/^www\./, '');
    } catch {
      return url || 'source';
    }
  };

  return (
    <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-10 md:py-16">
      <div className="max-w-3xl mx-auto space-y-10">
        
        {/* Main Verdict Card */}
        <section className="bg-surface-container-lowest card-shadow border border-outline-variant rounded-2xl p-6 md:p-10 relative overflow-hidden space-y-8">
          
          {/* Top colored status indicator stripe */}
          <div className={`absolute top-0 left-0 w-full h-1.5 ${verdictConfig.borderColor}`}></div>

          {/* Investigated Claim Header */}
          <div className="space-y-3">
            <p className="text-label-sm font-label text-on-surface-variant uppercase tracking-wider font-semibold">
              {isRtl ? 'نص الادعاء المفحوص' : 'Claim Investigated'}
            </p>
            <blockquote
              className="text-headline-md md:text-headline-lg font-display text-primary border-l-4 border-outline-variant pl-5 rtl:pl-0 rtl:pr-5 rtl:border-l-0 rtl:border-r-4 py-1 italic leading-relaxed"
              dir={isRtl ? 'rtl' : 'ltr'}
            >
              "{claimText || resultData?.text_claim || 'Claim statement'}"
            </blockquote>
          </div>

          {/* Verdict Status & Confidence Bar */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-t border-b border-outline-variant/60 py-6">
            
            {/* Verdict Badge */}
            <div className="flex items-center gap-4">
              <div className={`rounded-full p-3 flex items-center justify-center shrink-0 ${verdictConfig.badgeBg}`}>
                <span className="material-symbols-outlined icon-fill text-[32px]">
                  {verdictConfig.icon}
                </span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className={`text-headline-lg font-headline font-bold uppercase tracking-tight ${verdictConfig.color}`}>
                    {isRtl ? verdictConfig.labelAr : verdictConfig.label}
                  </h2>
                </div>
                <p className="text-body-md font-body text-on-surface-variant mt-0.5">
                  {isRtl ? verdictConfig.subtitleAr : verdictConfig.subtitle}
                </p>
              </div>
            </div>

            {/* Confidence Score Bar */}
            <div className="flex flex-col gap-2 min-w-[200px] bg-surface-container-low p-3.5 rounded-xl border border-outline-variant/40">
              <div className="flex justify-between items-end">
                <span className="text-label-sm font-label text-on-surface-variant font-medium">
                  {isRtl ? 'درجة ثقة النظام' : 'System Confidence'}
                </span>
                <span className="text-label-md font-label font-bold text-primary">
                  {confidencePercent}%
                </span>
              </div>
              <div className="w-full h-2 bg-surface-variant rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${verdictConfig.borderColor}`}
                  style={{ width: `${confidencePercent}%` }}
                ></div>
              </div>
            </div>

          </div>

          {/* Forensic Explanation Paragraphs */}
          <div className="space-y-3">
            <h3 className="text-headline-md font-headline font-semibold text-primary">
              {isRtl ? 'التقرير الجنائي والتحليلي' : 'Forensic Analysis'}
            </h3>
            <div className="prose max-w-none text-body-md md:text-body-lg font-body text-on-surface leading-relaxed" dir={isRtl ? 'rtl' : 'ltr'}>
              <p className="whitespace-pre-line">
                {resultData?.explanation || (isRtl ? 'تم فحص الأدلة وتأكيد النتائج.' : 'Consensus synthesis generated.')}
              </p>
            </div>
          </div>

        </section>

        {/* Conditional Image Authenticity Panel */}
        {resultData?.image_authenticity && (
          <ImageAuthenticity
            authenticity={resultData.image_authenticity}
            imageUrl={imageUrl}
            language={language}
          />
        )}

        {/* Verified Sources Grid */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 border-b border-outline-variant pb-3">
            <span className="material-symbols-outlined text-primary text-[20px]">
              library_books
            </span>
            <h3 className="text-headline-md font-headline font-semibold text-primary">
              {isRtl ? 'المصادر المعتمدة والتوثيق' : 'Verified Evidence & Sources'}
            </h3>
            <span className="text-label-sm font-label font-medium px-2 py-0.5 rounded-full bg-surface-container-high text-primary">
              {sources.length}
            </span>
          </div>

          {sources.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {sources.map((source, idx) => {
                const stanceKey = String(source.stance || 'context').toLowerCase();
                const stanceConfig = STANCE_CONFIG[stanceKey] || STANCE_CONFIG.context;
                const domain = getDomain(source.url);

                return (
                  <a
                    key={idx}
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block bg-surface-container-lowest border border-outline-variant rounded-xl p-5 hover:border-primary transition-all duration-200 group card-shadow hover:shadow-md"
                  >
                    <div className="flex justify-between items-start mb-3 gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="w-6 h-6 bg-surface-container-high rounded flex items-center justify-center text-label-sm font-bold text-primary uppercase shrink-0">
                          {domain.slice(0, 2)}
                        </div>
                        <span className="text-label-sm font-label text-on-surface-variant truncate font-medium">
                          {domain}
                        </span>
                      </div>
                      
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-label-sm font-label font-medium shrink-0 ${stanceConfig.bg}`}>
                        <span className="material-symbols-outlined text-[13px] mr-1 rtl:mr-0 rtl:ml-1">
                          {stanceConfig.icon}
                        </span>
                        {isRtl ? stanceConfig.labelAr : stanceConfig.label}
                      </span>
                    </div>

                    <h4 className="text-body-md font-body font-medium text-primary group-hover:text-primary-container transition-colors line-clamp-2" dir={isRtl ? 'rtl' : 'ltr'}>
                      {source.title || domain}
                    </h4>
                  </a>
                );
              })}
            </div>
          ) : (
            <div className="bg-surface-container-low rounded-xl p-8 text-center border border-dashed border-outline-variant space-y-2">
              <span className="material-symbols-outlined text-outline text-[32px]">
                manage_search
              </span>
              <h4 className="text-label-md font-label font-semibold text-primary">
                {isRtl ? 'تم التحقق من قاعدة المعرفة' : 'Knowledge Base & Baseline Consensus'}
              </h4>
              <p className="text-body-md font-body text-on-surface-variant max-w-md mx-auto">
                {isRtl
                  ? 'تم استرجاع الحكم والتحقق من خلال قاعدة بيانات الحقائق المعتمدة والتحليل العصبي المباشر.'
                  : 'Verdict was corroborated through pre-verified knowledge cache and direct multimodal analysis.'}
              </p>
            </div>
          )}
        </section>

        {/* Follow-up Question Section */}
        <FollowUpSection
          contextData={resultData}
          language={language}
        />

        {/* Reset Action */}
        <div className="flex justify-center border-t border-outline-variant pt-8">
          <button
            onClick={onReset}
            className="flex items-center gap-2 bg-surface-container-lowest hover:bg-surface-container border border-outline-variant text-primary text-label-md font-label font-medium px-8 py-3.5 rounded-xl transition-all duration-200 card-shadow hover:shadow-md cursor-pointer active:scale-98"
          >
            <span className="material-symbols-outlined text-[20px]">
              refresh
            </span>
            <span>{isRtl ? 'فحص ادعاء آخر' : 'Check another claim'}</span>
          </button>
        </div>

      </div>
    </main>
  );
}
