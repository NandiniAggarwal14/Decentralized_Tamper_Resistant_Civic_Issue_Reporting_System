document.addEventListener('DOMContentLoaded', () => {
  // Check auth session
  const user = auth.getUser();
  if (user) {
    const initialsEl = document.getElementById('profile-initials');
    const nameEl = document.getElementById('profile-name');
    const roleEl = document.getElementById('profile-role');
    
    if (initialsEl) initialsEl.textContent = (user.full_name || user.username || 'U').charAt(0).toUpperCase();
    if (nameEl) nameEl.textContent = user.full_name || user.username;
    if (roleEl) roleEl.textContent = user.role ? user.role.toUpperCase() : 'USER';
  }

  setupDropzone();
});

function setupDropzone() {
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('ai-file-input');

  if (!dropZone || !fileInput) return;

  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.add('highlight'), false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.remove('highlight'), false);
  });

  dropZone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files && files.length > 0) {
      handleFileSelection(files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelection(e.target.files[0]);
    }
  });
}

function handleFileSelection(file) {
  if (!file.type.startsWith('image/')) {
    showAlert('Please select a valid image file (JPG, PNG, WebP).', 'danger');
    return;
  }

  // Display image preview
  const reader = new FileReader();
  reader.onload = (e) => {
    const previewImg = document.getElementById('ai-preview-img');
    if (previewImg) previewImg.src = e.target.result;
    runInference(file);
  };
  reader.readAsDataURL(file);
}

async function runInference(file) {
  const resultCard = document.getElementById('ai-result-card');
  const verdictLabel = document.getElementById('verdict-label');
  const verdictSubtitle = document.getElementById('verdict-subtitle');
  const verdictIcon = document.getElementById('verdict-icon');
  const verdictBanner = document.getElementById('verdict-banner');
  const confidenceText = document.getElementById('confidence-text');
  const confidenceBar = document.getElementById('confidence-bar');
  const statProb = document.getElementById('stat-probability');

  if (resultCard) resultCard.style.display = 'block';

  // Set loading state
  if (verdictLabel) verdictLabel.textContent = 'Analyzing Image...';
  if (verdictSubtitle) verdictSubtitle.textContent = 'Running ResNet50 deep learning model...';
  if (verdictIcon) verdictIcon.textContent = '⚡';
  if (verdictBanner) {
    verdictBanner.style.background = 'rgba(255, 255, 255, 0.05)';
    verdictBanner.style.border = '1px solid var(--border)';
    verdictBanner.style.color = 'var(--text-primary)';
  }
  if (confidenceBar) confidenceBar.style.width = '0%';
  if (confidenceText) confidenceText.textContent = '0.00%';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const token = auth.getToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch('/api/ai/predict', {
      method: 'POST',
      headers: headers,
      body: formData
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Server error (${response.status})`);
    }

    const data = await response.json();
    displayResult(data);

  } catch (err) {
    console.error('Inference error:', err);
    showAlert(`Inference Failed: ${err.message}`, 'danger');
    if (verdictLabel) verdictLabel.textContent = 'Inspection Failed';
    if (verdictSubtitle) verdictSubtitle.textContent = err.message;
    if (verdictIcon) verdictIcon.textContent = '⚠️';
  }
}

function displayResult(data) {
  const verdictLabel = document.getElementById('verdict-label');
  const verdictSubtitle = document.getElementById('verdict-subtitle');
  const verdictIcon = document.getElementById('verdict-icon');
  const verdictBanner = document.getElementById('verdict-banner');
  const confidenceText = document.getElementById('confidence-text');
  const confidenceBar = document.getElementById('confidence-bar');
  const statProb = document.getElementById('stat-probability');

  const isFake = data.prediction === 'Fake';
  const confidence = data.confidence || 0;
  const probability = data.probability || 0;

  if (confidenceText) confidenceText.textContent = `${confidence.toFixed(2)}%`;
  if (confidenceBar) {
    confidenceBar.style.width = `${confidence}%`;
    confidenceBar.style.background = isFake ? 'var(--danger)' : 'var(--success)';
  }
  if (statProb) statProb.textContent = probability.toFixed(4);

  if (isFake) {
    if (verdictLabel) verdictLabel.textContent = 'FAKE (AI-Generated)';
    if (verdictSubtitle) verdictSubtitle.textContent = `High probability of synthetic/AI image generation (${confidence.toFixed(2)}% confidence)`;
    if (verdictIcon) verdictIcon.textContent = '🔴';
    if (verdictBanner) {
      verdictBanner.style.background = 'var(--danger-glow)';
      verdictBanner.style.border = '1px solid var(--danger)';
      verdictBanner.style.color = '#fca5a5';
    }
  } else {
    if (verdictLabel) verdictLabel.textContent = 'REAL (Authentic Photo)';
    if (verdictSubtitle) verdictSubtitle.textContent = `Image verified as authentic camera capture (${confidence.toFixed(2)}% confidence)`;
    if (verdictIcon) verdictIcon.textContent = '🟢';
    if (verdictBanner) {
      verdictBanner.style.background = 'var(--success-glow)';
      verdictBanner.style.border = '1px solid var(--success)';
      verdictBanner.style.color = '#6ee7b7';
    }
  }
}

function resetAiInspector() {
  const fileInput = document.getElementById('ai-file-input');
  const resultCard = document.getElementById('ai-result-card');
  const alertBanner = document.getElementById('ai-alert-banner');

  if (fileInput) fileInput.value = '';
  if (resultCard) resultCard.style.display = 'none';
  if (alertBanner) alertBanner.style.display = 'none';
}

function showAlert(message, type = 'info') {
  const alertBanner = document.getElementById('ai-alert-banner');
  const alertText = document.getElementById('ai-alert-text');

  if (alertBanner && alertText) {
    alertText.textContent = message;
    alertBanner.className = `alert-banner alert-${type}`;
    alertBanner.style.display = 'block';
  }
}
