import React, { useState, useEffect } from 'react';
import TopNavBar from './components/TopNavBar';
import Footer from './components/Footer';
import LandingPage from './components/LandingPage';
import LoadingStatus from './components/LoadingStatus';
import VerdictView from './components/VerdictView';
import ErrorCard from './components/ErrorCard';
import { analyzeClaim } from './api/client';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState('landing'); // 'landing' | 'loading' | 'verdict' | 'error'
  const [inputType, setInputType] = useState('text'); // 'text' | 'image'
  const [textClaim, setTextClaim] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [language, setLanguage] = useState('en'); // 'en' | 'ar' | 'auto'
  
  const [resultData, setResultData] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Sync RTL attribute on document root
  useEffect(() => {
    const isRtl = language === 'ar' || (language === 'auto' && /[\u0600-\u06FF]/.test(textClaim));
    document.documentElement.dir = isRtl ? 'rtl' : 'ltr';
    document.documentElement.lang = language === 'ar' ? 'ar' : 'en';
  }, [language, textClaim]);

  // Execute Analysis Pipeline
  const handleAnalyze = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    setCurrentScreen('loading');

    try {
      const data = await analyzeClaim({
        input_type: inputType,
        text_claim: textClaim,
        image_url: imageUrl,
        language,
      });

      setResultData(data);
      // Small tick for smooth transition
      setTimeout(() => {
        setCurrentScreen('verdict');
      }, 300);
    } catch (err) {
      console.error('Analyze error:', err);
      setErrorMessage(err.message || 'Failed to complete analysis.');
      setCurrentScreen('error');
    } finally {
      setIsLoading(false);
    }
  };

  // Reset to Landing Screen
  const handleReset = () => {
    setCurrentScreen('landing');
    setResultData(null);
    setErrorMessage(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const isRtl = language === 'ar' || (language === 'auto' && /[\u0600-\u06FF]/.test(textClaim));

  return (
    <div className={`min-h-screen flex flex-col bg-background text-on-background antialiased ${isRtl ? 'rtl' : 'ltr'}`} dir={isRtl ? 'rtl' : 'ltr'}>
      {/* Shared Navigation Header */}
      <TopNavBar
        language={language}
        setLanguage={setLanguage}
        onReset={handleReset}
      />

      {/* Screen Routing */}
      {currentScreen === 'landing' && (
        <LandingPage
          inputType={inputType}
          setInputType={setInputType}
          textClaim={textClaim}
          setTextClaim={setTextClaim}
          imageUrl={imageUrl}
          setImageUrl={setImageUrl}
          language={language}
          setLanguage={setLanguage}
          onSubmit={handleAnalyze}
          isLoading={isLoading}
        />
      )}

      {currentScreen === 'loading' && (
        <LoadingStatus
          language={language}
          claimText={inputType === 'text' ? textClaim : imageUrl}
          isImage={inputType === 'image'}
        />
      )}

      {currentScreen === 'verdict' && resultData && (
        <VerdictView
          resultData={resultData}
          claimText={textClaim}
          imageUrl={imageUrl}
          inputType={inputType}
          language={language}
          onReset={handleReset}
        />
      )}

      {currentScreen === 'error' && (
        <ErrorCard
          error={errorMessage}
          onRetry={handleAnalyze}
          onReset={handleReset}
          language={language}
        />
      )}

      {/* Shared Footer */}
      <Footer language={language} />
    </div>
  );
}
