import React from 'react';

export default function TopNavBar({ language, setLanguage, onReset, onScrollToInput }) {
  const isRtl = language === 'ar';

  return (
    <nav className="bg-background w-full border-b border-outline-variant z-50 sticky top-0">
      <div className="flex justify-between items-center w-full px-margin-mobile md:px-margin-desktop py-4 max-w-container-max mx-auto">
        {/* Logo & Tagline */}
        <div className="flex items-center gap-4 md:gap-6">
          <button
            onClick={onReset}
            className="text-headline-md font-headline font-bold text-primary tracking-tight flex items-center space-x-2 text-left rtl:text-right group focus:outline-none"
          >
            <span className="material-symbols-outlined icon-fill text-primary group-hover:scale-105 transition-transform" style={{ fontSize: '28px' }}>
              policy
            </span>
            <span className="group-hover:text-primary-container transition-colors">
              DeepFakeLens
            </span>
          </button>
          <span className="text-body-md font-body text-on-surface-variant hidden lg:block border-l border-outline-variant pl-6 rtl:border-l-0 rtl:border-r rtl:pl-0 rtl:pr-6">
            {isRtl ? 'تحقق من صحة الادعاءات والصور في ثوانٍ' : 'Check any claim or image in seconds.'}
          </span>
        </div>

        {/* Actions & Language */}
        <div className="flex items-center space-x-4 rtl:space-x-reverse">
          {/* Language Switcher */}
          <div className="relative inline-flex items-center bg-surface-container-low border border-outline-variant rounded-lg px-3 py-1.5">
            <span className="material-symbols-outlined text-[18px] text-on-surface-variant mr-1.5 rtl:mr-0 rtl:ml-1.5">
              language
            </span>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="bg-transparent border-none text-label-sm font-label font-medium text-on-surface hover:text-primary focus:ring-0 cursor-pointer outline-none"
            >
              <option value="en">English (EN)</option>
              <option value="ar">العربية (AR)</option>
              <option value="auto">Auto-detect</option>
            </select>
          </div>

          <button
            onClick={onScrollToInput || onReset}
            className="bg-accent hover:bg-accent-hover text-white px-5 py-2 rounded text-label-md font-label font-medium transition-all duration-200 shadow-sm hover:shadow active:scale-95"
          >
            {isRtl ? 'ابدأ الفحص' : 'Analyze Now'}
          </button>
        </div>
      </div>
    </nav>
  );
}
