/**
 * DeepFakeLens API Client
 * Connects to FastAPI backend at http://localhost:8000
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Submit a claim or image for full 5-agent fact-checking and deepfake analysis
 * @param {Object} payload
 * @param {'text' | 'image'} payload.input_type
 * @param {string | null} [payload.text_claim]
 * @param {string | null} [payload.image_url]
 * @param {'en' | 'ar' | 'auto'} [payload.language]
 * @returns {Promise<Object>} PipelineResponse JSON
 */
export async function analyzeClaim({ input_type, text_claim = null, image_url = null, language = 'en' }) {
  // Normalize language
  let lang = language;
  if (lang === 'auto') {
    // Basic Arabic detection
    const isArabic = text_claim && /[\u0600-\u06FF]/.test(text_claim);
    lang = isArabic ? 'ar' : 'en';
  }

  const body = {
    input_type,
    text_claim: text_claim ? text_claim.trim() : null,
    image_url: image_url ? image_url.trim() : null,
    language: lang,
  };

  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let errorDetail = `Server returned status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

/**
 * Ask a follow-up question reusing existing analysis context
 * @param {Object} payload
 * @param {string} payload.question
 * @param {Object} payload.context
 * @param {'en' | 'ar'} [payload.language]
 * @returns {Promise<{ answer: string }>}
 */
export async function askFollowUp({ question, context, language = 'en' }) {
  const body = {
    question: question.trim(),
    context,
    language,
  };

  const response = await fetch(`${API_BASE_URL}/follow-up`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let errorDetail = `Failed to get follow-up answer (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return response.json();
}
