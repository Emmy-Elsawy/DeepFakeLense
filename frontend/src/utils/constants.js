/**
 * DeepFakeLens Constants and Helpers
 */

export const SAMPLE_CLAIMS = [
  {
    title: "RAG Cache Hit (Instant)",
    claim: "The Great Wall of China is visible from space with the naked eye.",
    type: "text",
    lang: "en",
    tag: "Instant Cache"
  },
  {
    title: "Real-time Live Fact Check",
    claim: "NASA launched the Artemis II mission with four astronauts around the Moon in 2026.",
    type: "text",
    lang: "en",
    tag: "5-Agent Pipeline"
  },
  {
    title: "Arabic Claim (RTL)",
    claim: "مايكروسوفت ستوقف دعم ويندوز 10 في أكتوبر 2025",
    type: "text",
    lang: "ar",
    tag: "Arabic / RTL"
  },
  {
    title: "Image Deepfake Analysis",
    claim: "Portrait photograph of historical subject",
    imageUrl: "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/402px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
    type: "image",
    lang: "en",
    tag: "Vision Forensics"
  }
];

export const VERDICT_CONFIG = {
  true: {
    label: "True",
    labelAr: "صحيح",
    subtitle: "The claim is supported by authoritative evidence.",
    subtitleAr: "الادعاء مدعوم بأدلة ومصادر موثوقة.",
    icon: "check_circle",
    badgeBg: "bg-secondary-container text-on-secondary-container border border-secondary/30",
    color: "text-secondary",
    borderColor: "bg-secondary",
    pillBg: "bg-secondary/10 text-secondary border border-secondary/20",
  },
  false: {
    label: "False",
    labelAr: "غير صحيح / كاذب",
    subtitle: "The core assertion is demonstrably incorrect.",
    subtitleAr: "الادعاء غير صحيح وتم دحضه بالأدلة.",
    icon: "cancel",
    badgeBg: "bg-error-container text-on-error-container border border-error/30",
    color: "text-error",
    borderColor: "bg-error",
    pillBg: "bg-error/10 text-error border border-error/20",
  },
  misleading: {
    label: "Misleading",
    labelAr: "مضلل / غير دقيق",
    subtitle: "Contains elements of truth but lacks crucial context.",
    subtitleAr: "يحتوي على بعض الحقائق ولكنه مجتزأ أو مضلل.",
    icon: "warning",
    badgeBg: "bg-amber-100 text-amber-900 border border-amber-300",
    color: "text-amber-700",
    borderColor: "bg-amber-500",
    pillBg: "bg-amber-500/10 text-amber-700 border border-amber-500/20",
  },
  unverified: {
    label: "Unverified",
    labelAr: "غير مؤكد / غير مثبت",
    subtitle: "Insufficient authoritative data found to verify or refute this claim.",
    subtitleAr: "لا توجد أدلة كافية لتأكيد أو نفي هذا الادعاء حالياً.",
    icon: "help",
    badgeBg: "bg-surface-variant text-on-surface-variant border border-outline-variant",
    color: "text-on-surface-variant",
    borderColor: "bg-outline-variant",
    pillBg: "bg-surface-variant text-on-surface-variant border border-outline-variant",
  }
};

export const STANCE_CONFIG = {
  supports: {
    label: "Supports",
    labelAr: "يؤيد",
    icon: "check",
    bg: "bg-secondary-container text-on-secondary-container",
  },
  contradicts: {
    label: "Contradicts",
    labelAr: "يناقض",
    icon: "block",
    bg: "bg-error-container text-on-error-container",
  },
  context: {
    label: "Context",
    labelAr: "سياق",
    icon: "info",
    bg: "bg-surface-container-high text-on-surface-variant",
  },
};
