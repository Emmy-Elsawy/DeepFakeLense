import React, { useState } from 'react';
import { SAMPLE_CLAIMS } from '../utils/constants';

export default function LandingPage({
  inputType,
  setInputType,
  textClaim,
  setTextClaim,
  imageUrl,
  setImageUrl,
  language,
  setLanguage,
  onSubmit,
  isLoading
}) {
  const isRtl = language === 'ar';
  const [imagePreviewError, setImagePreviewError] = useState(false);

  const handleSelectSample = (sample) => {
    setInputType(sample.type);
    setTextClaim(sample.claim);
    if (sample.imageUrl) {
      setImageUrl(sample.imageUrl);
    } else {
      setImageUrl('');
    }
    if (sample.lang) {
      setLanguage(sample.lang);
    }
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    if (inputType === 'text' && !textClaim.trim()) return;
    if (inputType === 'image' && !imageUrl.trim()) return;
    onSubmit();
  };

  return (
    <main className="flex-grow flex flex-col items-center justify-center px-gutter py-12 md:py-20 relative w-full">
      <div className="max-w-container-max w-full mx-auto flex flex-col items-center">
        
        {/* Header Hero Title */}
        <div className="text-center mb-8 md:mb-10 max-w-2xl">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-container-high border border-outline-variant text-label-sm font-label text-primary font-semibold uppercase tracking-wider mb-4">
            <span className="w-2 h-2 rounded-full bg-secondary"></span>
            {isRtl ? 'نظام التحقق الذكي متعدد الوكلاء' : '5-Agent AI Fact-Checking Pipeline'}
          </span>
          <h1 className="text-headline-lg md:text-display font-display font-semibold text-primary mb-3 tracking-tight">
            {isRtl ? 'تحقق من صحة أي خبر أو صورة' : 'Verify any claim or image in seconds.'}
          </h1>
          <p className="text-body-md md:text-body-lg font-body text-on-surface-variant leading-relaxed">
            {isRtl
              ? 'محرك فحص ذكي مدعوم بالذكاء الاصطناعي، وقواعد بيانات التحقق، وفحص التزييف العميق للصور.'
              : 'Autonomous forensic pipeline leveraging Gemini 2.5, search consensus, Playwright scraping, and neural deepfake detection.'}
          </p>
        </div>

        {/* Central Glass Input Card */}
        <div className="w-full max-w-3xl glass-panel subtle-shadow rounded-xl p-6 md:p-8 mb-6 relative overflow-hidden bg-surface-container-lowest border border-outline-variant">
          {/* Tabs */}
          <div className="flex border-b border-outline-variant mb-6" role="tablist">
            <button
              type="button"
              onClick={() => setInputType('text')}
              className={`text-label-md font-label pb-3 px-4 transition-all duration-200 focus:outline-none flex items-center gap-2 ${
                inputType === 'text'
                  ? 'border-b-2 border-primary text-primary font-semibold'
                  : 'text-on-surface-variant hover:text-primary border-b-2 border-transparent'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">article</span>
              <span>{isRtl ? 'نص الادعاء' : 'Text claim'}</span>
            </button>

            <button
              type="button"
              onClick={() => setInputType('image')}
              className={`text-label-md font-label pb-3 px-4 transition-all duration-200 focus:outline-none flex items-center gap-2 ${
                inputType === 'image'
                  ? 'border-b-2 border-primary text-primary font-semibold'
                  : 'text-on-surface-variant hover:text-primary border-b-2 border-transparent'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">image</span>
              <span>{isRtl ? 'فحص صورة' : 'Upload image / URL'}</span>
            </button>
          </div>

          <form onSubmit={handleFormSubmit}>
            {/* Tab 1: Text Input Panel */}
            {inputType === 'text' && (
              <div className="w-full mb-6">
                <textarea
                  value={textClaim}
                  onChange={(e) => setTextClaim(e.target.value)}
                  dir={isRtl ? 'rtl' : 'ltr'}
                  rows={4}
                  className="w-full p-4 bg-surface-bright border border-outline-variant rounded-lg text-body-md font-body text-on-surface focus:border-primary focus:ring-1 focus:ring-primary resize-none placeholder-on-surface-variant/60 transition-shadow outline-none"
                  placeholder={
                    isRtl
                      ? 'الصق خبراً، أو تصريحاً، أو معلومة تريد التحقق منها هنا...'
                      : 'Paste a claim, headline, or statement to check...'
                  }
                />
              </div>
            )}

            {/* Tab 2: Image Input Panel */}
            {inputType === 'image' && (
              <div className="w-full mb-6 space-y-4">
                <div>
                  <label className="block text-label-sm font-label text-on-surface-variant mb-1.5 font-medium">
                    {isRtl ? 'رابط الصورة (Image URL)' : 'Image URL for Analysis'}
                  </label>
                  <div className="relative">
                    <input
                      type="url"
                      value={imageUrl}
                      onChange={(e) => {
                        setImageUrl(e.target.value);
                        setImagePreviewError(false);
                      }}
                      className="w-full p-3.5 pl-11 rtl:pl-4 rtl:pr-11 bg-surface-bright border border-outline-variant rounded-lg text-body-md font-body text-on-surface focus:border-primary focus:ring-1 focus:ring-primary placeholder-on-surface-variant/60 transition-shadow outline-none"
                      placeholder="https://example.com/photo-to-verify.jpg"
                    />
                    <span className="material-symbols-outlined absolute left-3.5 rtl:left-auto rtl:right-3.5 top-3.5 text-on-surface-variant text-[20px]">
                      link
                    </span>
                  </div>
                </div>

                {/* Optional Caption/Claim */}
                <div>
                  <label className="block text-label-sm font-label text-on-surface-variant mb-1.5 font-medium">
                    {isRtl ? 'وصف أو ادعاء مصاحب (اختياري)' : 'Associated Claim / Caption (Optional)'}
                  </label>
                  <input
                    type="text"
                    value={textClaim}
                    onChange={(e) => setTextClaim(e.target.value)}
                    dir={isRtl ? 'rtl' : 'ltr'}
                    className="w-full p-3 bg-surface-bright border border-outline-variant rounded-lg text-body-md font-body text-on-surface focus:border-primary focus:ring-1 focus:ring-primary placeholder-on-surface-variant/60 outline-none"
                    placeholder={isRtl ? 'مثال: صورة فوتوغرافية تزعم توثيق حدث معين...' : 'e.g., Image alleging discovery of extraterrestrial life'}
                  />
                </div>

                {/* Live Image Preview if URL entered */}
                {imageUrl.trim() && (
                  <div className="p-3 bg-surface-container-low border border-outline-variant rounded-lg flex items-center gap-4">
                    <div className="w-16 h-16 rounded bg-surface-dim overflow-hidden shrink-0 border border-outline-variant">
                      {!imagePreviewError ? (
                        <img
                          src={imageUrl}
                          alt="Target Preview"
                          className="w-full h-full object-cover"
                          onError={() => setImagePreviewError(true)}
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-outline">
                          <span className="material-symbols-outlined text-[24px]">broken_image</span>
                        </div>
                      )}
                    </div>
                    <div className="overflow-hidden">
                      <p className="text-label-sm font-label text-primary font-medium truncate">
                        {imageUrl}
                      </p>
                      <p className="text-label-sm font-label text-on-surface-variant">
                        {imagePreviewError ? 'Preview unavailable (will be fetched directly by backend)' : 'Image loaded & ready for deepfake detection'}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Action Submit Button */}
            <div className="flex justify-center mt-2">
              <button
                type="submit"
                disabled={isLoading || (inputType === 'text' && !textClaim.trim()) || (inputType === 'image' && !imageUrl.trim())}
                className="w-full md:w-auto min-w-[220px] bg-primary hover:bg-primary-container disabled:opacity-50 text-on-primary text-label-md font-label font-medium py-3.5 px-8 rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center gap-2 group cursor-pointer active:scale-98"
              >
                <span className="material-symbols-outlined group-hover:scale-110 transition-transform text-[20px]">
                  search
                </span>
                <span>{isRtl ? 'فحص الادعاء الآن' : 'Check Claim'}</span>
              </button>
            </div>
          </form>
        </div>

        {/* Quick Sample Claims Pills */}
        <div className="w-full max-w-3xl mt-4">
          <p className="text-label-sm font-label text-on-surface-variant text-center mb-3">
            {isRtl ? 'أو اختر أحد النماذج الجاهزة للاختبار الفوري:' : 'Or test immediately with a pre-configured sample:'}
          </p>
          <div className="flex flex-wrap items-center justify-center gap-2.5">
            {SAMPLE_CLAIMS.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSelectSample(sample)}
                className="bg-surface-container-low hover:bg-surface-container border border-outline-variant/70 rounded-full px-4 py-2 text-label-sm font-label text-on-surface hover:text-primary transition-all duration-200 flex items-center gap-2 shadow-xs hover:shadow-sm"
              >
                <span className="text-[11px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded bg-surface-container-high text-primary">
                  {sample.tag}
                </span>
                <span className="max-w-[240px] truncate">{sample.title}</span>
              </button>
            ))}
          </div>
        </div>

      </div>
    </main>
  );
}
