import React, { useEffect, useState } from 'react';

const STAGES = [
  {
    id: 1,
    title: "Reading your claim...",
    titleAr: "قراءة وتحليل نص الادعاء...",
    desc: "Claim parsed and key search terms extracted.",
    descAr: "تم استخراج محاور الادعاء والكلمات المفتاحية."
  },
  {
    id: 2,
    title: "Checking knowledge base...",
    titleAr: "فحص قاعدة المعرفة والذاكرة الذكية...",
    desc: "Querying ChromaDB RAG cache for known fact-checks.",
    descAr: "البحث في قاعدة بيانات الادعاءات السابقة والحقائق المؤكدة."
  },
  {
    id: 3,
    title: "Searching trusted sources...",
    titleAr: "البحث في المصادر الإخبارية المعتمدة...",
    desc: "Querying Reuters, AP, Snopes, FactCheck.org, and BBC.",
    descAr: "استرجاع التقارير من رويترز، أسوشيتد برس، فتبينوا، وبي بي سي."
  },
  {
    id: 4,
    title: "Reading & extracting articles...",
    titleAr: "استخراج محتوى المقالات والتحليلات...",
    desc: "Scraping and filtering full article text with Playwright.",
    descAr: "قراءة نصوص الصفحات واستخلاص الفقرات ذات الصلة."
  },
  {
    id: 5,
    title: "Cross-referencing & writing verdict...",
    titleAr: "مقارنة الأدلة وصياغة الحكم النهائي...",
    desc: "Neural consensus, stance classification, and confidence scoring.",
    descAr: "تحليل التناقض والتأييد وتحديد درجة الثقة والحكم النهائي."
  }
];

export default function LoadingStatus({ language, claimText, isImage }) {
  const isRtl = language === 'ar';
  const [currentStep, setCurrentStep] = useState(1);
  const [elapsed, setElapsed] = useState(0);

  // Staged progress timer
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);

    // Progression: Step 1 (0.8s), Step 2 (1.8s), Step 3 (3.5s), Step 4 (6.0s), Step 5 (8.5s)
    const t1 = setTimeout(() => setCurrentStep(2), 800);
    const t2 = setTimeout(() => setCurrentStep(3), 2000);
    const t3 = setTimeout(() => setCurrentStep(4), 4500);
    const t4 = setTimeout(() => setCurrentStep(5), 7500);

    return () => {
      clearInterval(timer);
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
    };
  }, []);

  const progressPercent = Math.min(100, Math.round((currentStep / STAGES.length) * 100));

  return (
    <main className="flex-grow flex flex-col items-center justify-center py-12 md:py-20 px-gutter w-full">
      <div className="w-full max-w-xl mx-auto flex flex-col items-center">
        
        {/* Main Status Container Card */}
        <div className="w-full glass-panel subtle-shadow rounded-2xl p-8 md:p-10 border border-outline-variant bg-surface-container-lowest relative overflow-hidden">
          
          {/* Top Status Title */}
          <div className="text-center mb-8">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary-container text-on-secondary-container text-label-sm font-label font-semibold uppercase tracking-wider mb-3">
              <span className="w-2 h-2 rounded-full bg-secondary animate-ping"></span>
              {isRtl ? 'جاري التحقق الفوري' : 'Live Verification Pipeline'}
            </span>
            <h2 className="text-headline-md font-headline font-semibold text-primary">
              {isRtl ? 'فحص مصداقية الادعاء...' : 'Analyzing Claim Forensics'}
            </h2>
            {claimText && (
              <p className="text-body-md font-body text-on-surface-variant mt-2 italic max-w-md mx-auto truncate" dir={isRtl ? 'rtl' : 'ltr'}>
                "{claimText}"
              </p>
            )}
          </div>

          {/* Staged Trail Step List */}
          <div className="space-y-6 relative pl-2 rtl:pl-0 rtl:pr-2">
            {/* Connecting Vertical Line */}
            <div className="absolute left-[19px] rtl:left-auto rtl:right-[19px] top-4 bottom-4 w-0.5 bg-outline-variant/40 -z-0"></div>

            {STAGES.map((stage) => {
              const isCompleted = currentStep > stage.id;
              const isActive = currentStep === stage.id;

              return (
                <div key={stage.id} className="flex items-start relative z-10">
                  {/* Step Icon Indicator */}
                  <div className="shrink-0 mr-4 rtl:mr-0 rtl:ml-4 mt-0.5">
                    {isCompleted ? (
                      <div className="w-6 h-6 rounded-full bg-secondary text-on-secondary flex items-center justify-center shadow-xs">
                        <span className="material-symbols-outlined text-[16px]">check</span>
                      </div>
                    ) : isActive ? (
                      <div className="w-6 h-6 rounded-full bg-surface-container border-2 border-secondary flex items-center justify-center relative">
                        <div className="w-2.5 h-2.5 rounded-full bg-secondary pulse-ring"></div>
                      </div>
                    ) : (
                      <div className="w-6 h-6 rounded-full bg-surface-container border border-outline-variant/60 flex items-center justify-center">
                        <span className="w-1.5 h-1.5 rounded-full bg-outline-variant/60"></span>
                      </div>
                    )}
                  </div>

                  {/* Step Content */}
                  <div className="flex-1">
                    <h4
                      className={`text-label-md font-label font-medium transition-colors ${
                        isActive
                          ? 'text-primary font-semibold'
                          : isCompleted
                          ? 'text-primary/80'
                          : 'text-on-surface-variant/50'
                      }`}
                    >
                      {isRtl ? stage.titleAr : stage.title}
                    </h4>
                    {(isActive || isCompleted) && (
                      <p className="text-label-sm font-label text-on-surface-variant mt-0.5 leading-snug">
                        {isRtl ? stage.descAr : stage.desc}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Progress Bar & Elapsed Time */}
          <div className="mt-10 pt-6 border-t border-outline-variant/40">
            <div className="flex justify-between items-center text-label-sm font-label text-on-surface-variant mb-2">
              <span>{isRtl ? 'التقدم' : 'Progress'}</span>
              <span>{elapsed}s elapsed</span>
            </div>
            <div className="h-1.5 w-full bg-surface-container rounded-full overflow-hidden">
              <div
                className="h-full bg-secondary rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progressPercent}%` }}
              ></div>
            </div>
            <p className="text-center text-label-sm font-label text-outline mt-3 flex justify-center items-center gap-1.5">
              <span className="material-symbols-outlined text-[16px] animate-spin text-secondary">
                sync
              </span>
              <span>
                {isRtl
                  ? 'جاري تشغيل وكلاء التدقيق المتزامنين...'
                  : 'Synthesizing evidence across consensus models...'}
              </span>
            </p>
          </div>

        </div>

      </div>
    </main>
  );
}
