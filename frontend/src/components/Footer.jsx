import React from 'react';

export default function Footer({ language }) {
  const isRtl = language === 'ar';

  return (
    <footer className="bg-surface-bright border-t border-outline-variant w-full mt-auto">
      <div className="flex flex-col md:flex-row justify-between items-center w-full px-margin-mobile md:px-margin-desktop py-8 max-w-container-max mx-auto space-y-6 md:space-y-0 text-on-surface-variant">
        {/* Trust Signals */}
        <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-8 order-2 md:order-1">
          <div className="flex items-center gap-2 text-label-sm font-label">
            <span className="material-symbols-outlined text-[16px] text-secondary">
              verified_user
            </span>
            <span>{isRtl ? 'مدعوم بمصادر معتمدة' : 'Powered by trusted sources'}</span>
          </div>
          <div className="flex items-center gap-2 text-label-sm font-label">
            <span className="material-symbols-outlined text-[16px] text-primary">
              lock_open
            </span>
            <span>{isRtl ? 'بدون تسجيل دخول' : 'No login required'}</span>
          </div>
          <div className="flex items-center gap-2 text-label-sm font-label">
            <span className="material-symbols-outlined text-[16px] text-secondary">
              money_off
            </span>
            <span>{isRtl ? 'مجاني 100%' : 'Free to use'}</span>
          </div>
        </div>

        {/* Branding & Copyright */}
        <div className="text-label-sm font-label order-3 md:order-2 text-center md:text-right rtl:md:text-left">
          <span>© 2026 DeepFakeLens. {isRtl ? 'منظومة التدقيق والتحقق الجنائي الرقمي' : 'Forensic Verification Suite.'}</span>
        </div>
      </div>
    </footer>
  );
}
