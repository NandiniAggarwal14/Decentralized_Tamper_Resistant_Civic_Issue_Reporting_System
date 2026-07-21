// Citizen Console Business Logic
let token = null;
let currentUser = null;
const feedContainer = document.getElementById('feed-container');

// Auth Guard Check
async function initializeDashboard() {
  token = auth.getToken();
  currentUser = await auth.checkAuthGuard(['citizen']);
  
  if (currentUser) {
    // Populate profile card
    document.getElementById('profile-name').textContent = currentUser.full_name;
    const initials = currentUser.full_name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase();
    document.getElementById('profile-initials').textContent = initials.substring(0, 2);
    
    // Load Feed
    await loadIssues();
  }
}

// Show Alerts
function showAlert(text, isError = false) {
  const banner = document.getElementById('alert-banner');
  const textEl = document.getElementById('alert-text');
  if (banner && textEl) {
    textEl.textContent = text;
    banner.className = `alert-banner ${isError ? 'alert-error' : 'alert-success'}`;
    banner.style.display = 'flex';
    setTimeout(() => { banner.style.display = 'none'; }, 5000);
  }
}

// Fetch and render issues list
async function loadIssues() {
  try {
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
    const url = '/api/issues';
    const res = await fetch(url, { headers });
    const data = await res.json();
    
    if (res.ok && data.success) {
      renderIssues(data.data);
    } else {
      feedContainer.innerHTML = `<p style="text-align: center; color: var(--text-muted); padding: 40px;">Failed to load complaints feed.</p>`;
    }
  } catch (err) {
    console.error('Error fetching issues:', err);
    feedContainer.innerHTML = `<p style="text-align: center; color: var(--text-muted); padding: 40px;">Connection failure. Is the server running?</p>`;
  }
}

// Render Issues Grid
function renderIssues(issues) {
  if (!issues || issues.length === 0) {
    feedContainer.innerHTML = `
      <div style="text-align: center; color: var(--text-muted); padding: 60px;">
        <span style="font-size: 3rem; display: block; margin-bottom: 16px;"></span>
        <p data-i18n="no_reports">No civic issues reported yet.</p>
      </div>
    `;
    if (window.i18n) window.i18n.translatePage();
    return;
  }

  feedContainer.innerHTML = issues.map(issue => {
    const statusText = window.i18n ? window.i18n.t(`badge-${issue.status}`, issue.status) : issue.status;
    const priorityText = window.i18n ? window.i18n.t(`badge-priority-${issue.priority}`, issue.priority) : issue.priority;
    
    // Parse uploaded media
    const mediaHTML = (issue.media_urls || []).map(media => {
      if (media.type === 'image') {
        return `<img src="${media.url}" class="gallery-image" onclick="window.open('${media.url}')" title="IPFS CID: ${media.cid}">`;
      } else if (media.type === 'audio') {
        return `
          <div class="media-audio-wrapper" style="width: 100%; margin-top: 8px;">
            <audio controls style="width: 100%; height: 36px;"><source src="${media.url}"></audio>
            <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 4px;">IPFS: ${media.cid}</div>
          </div>
        `;
      } else if (media.type === 'video') {
        return `
          <div class="media-video-wrapper" style="margin-top: 8px;">
            <video controls style="max-width: 100%; max-height: 200px; border-radius: 6px;"><source src="${media.url}"></video>
            <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 4px;">IPFS: ${media.cid}</div>
          </div>
        `;
      }
      return '';
    }).join('');

    const formattedDate = new Date(issue.created_at).toLocaleString();

    // Verify translations
    const verifBtnText = window.i18n ? window.i18n.t('verify_integrity', 'Verify Integrity') : 'Verify Integrity';

    // Resolution Proof & Contextual Voting Prompt
    let proofHTML = '';
    if (issue.status === 'resolved' && issue.completion_proof_url) {
      const proofLabelText = window.i18n ? window.i18n.t('resolution_proof_label', 'Resolution Proof') : 'Resolution Proof';
      const proofAiBadge = issue.completion_ai_prediction
        ? (issue.completion_ai_prediction === 'Fake'
            ? `<div style="margin-top:5px;"><span style="background:rgba(239,68,68,0.15);color:#fca5a5;border:1px solid rgba(239,68,68,0.4);border-radius:6px;padding:2px 8px;font-size:0.75rem;">🔴 PROOF: FAKE (AI-Generated)${issue.completion_ai_confidence ? ' ' + issue.completion_ai_confidence.toFixed(1) + '%' : ''}</span></div>`
            : `<div style="margin-top:5px;"><span style="background:rgba(16,185,129,0.15);color:#6ee7b7;border:1px solid rgba(16,185,129,0.4);border-radius:6px;padding:2px 8px;font-size:0.75rem;">🟢 PROOF: REAL${issue.completion_ai_confidence ? ' ' + issue.completion_ai_confidence.toFixed(1) + '%' : ''}</span></div>`)
        : '';
      proofHTML = `
        <div class="resolution-proof-container">
          <div style="font-size: 0.8rem; font-weight: 600; color: var(--success); margin-bottom: 4px;">${proofLabelText}</div>
          <img src="${issue.completion_proof_url}" class="resolution-proof-inline" onclick="window.open('${issue.completion_proof_url}', '_blank')" alt="Resolution Proof">
          ${proofAiBadge}
        </div>
      `;
    }

    // Rejection details
    let rejectionHTML = '';
    if (issue.status === 'rejected' && issue.rejection_reason) {
      const rejAiBadge = issue.rejection_ai_prediction
        ? (issue.rejection_ai_prediction === 'Fake'
            ? `<div style="margin-top:5px;"><span style="background:rgba(239,68,68,0.15);color:#fca5a5;border:1px solid rgba(239,68,68,0.4);border-radius:6px;padding:2px 8px;font-size:0.75rem;">🔴 REJECTION EVIDENCE: FAKE (AI-Generated)${issue.rejection_ai_confidence ? ' ' + issue.rejection_ai_confidence.toFixed(1) + '%' : ''}</span></div>`
            : `<div style="margin-top:5px;"><span style="background:rgba(16,185,129,0.15);color:#6ee7b7;border:1px solid rgba(16,185,129,0.4);border-radius:6px;padding:2px 8px;font-size:0.75rem;">🟢 REJECTION EVIDENCE: REAL${issue.rejection_ai_confidence ? ' ' + issue.rejection_ai_confidence.toFixed(1) + '%' : ''}</span></div>`)
        : '';
      rejectionHTML = `
        <div class="rejection-stamp-container" style="margin-top: 12px; width: 100%;">
          <div class="rejection-stamp">REJECTED</div>
          <div class="rejection-details">
            <div class="rejection-reason">
              <strong>Reason:</strong> ${escapeHtml(issue.rejection_reason)}
            </div>
            ${issue.rejection_proof_url ? `
              <div class="rejection-evidence">
                <strong>Evidence:</strong>
                <img src="${issue.rejection_proof_url}" class="rejection-proof-inline" onclick="window.open('${issue.rejection_proof_url}', '_blank')" alt="Rejection Evidence" style="max-height: 120px;">
                ${rejAiBadge}
              </div>
            ` : ''}
            <div class="rejection-official">
              <strong>Rejected By:</strong> ${escapeHtml(issue.rejected_by_name || 'Ward Official')}
              ${issue.rejected_by_contact ? ` | Contact: ${escapeHtml(issue.rejected_by_contact)}` : ''}
            </div>
          </div>
        </div>
      `;
    }

    const votePromptKey = issue.status === 'resolved' ? 'vote_satisfaction_prompt' : 'vote_support_prompt';
    const defaultPromptText = issue.status === 'resolved' ? 'Are you satisfied with the resolution?' : 'Do you also face this issue? Show your support.';
    const votePromptText = window.i18n ? window.i18n.t(votePromptKey, defaultPromptText) : defaultPromptText;

    let voteSectionHTML = '';
    if (issue.status !== 'rejected') {
      voteSectionHTML = `
        <div class="vote-section">
          ${proofHTML}
          <div class="vote-row">
            <div class="vote-widget">
              <button onclick="castVote('${issue.id}', 'up')" class="vote-btn up ${issue.votes.user_vote === 'up' ? 'active' : ''}">▲</button>
              <span class="vote-number" style="color: ${issue.votes.score >= 0 ? 'var(--success)' : 'var(--danger)'}">${issue.votes.score}</span>
              <button onclick="castVote('${issue.id}', 'down')" class="vote-btn down ${issue.votes.user_vote === 'down' ? 'active' : ''}">▼</button>
            </div>
            <span class="vote-context">${votePromptText}</span>
          </div>
        </div>
      `;
    }

    let aiBadgeHTML = '';
    if (issue.ai_prediction) {
      const isFake = issue.ai_prediction === 'Fake';
      const badgeStyle = isFake 
        ? 'background: rgba(239, 68, 68, 0.15); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4);'
        : 'background: rgba(16, 185, 129, 0.15); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.4);';
      const badgeIcon = isFake ? '🔴' : '🟢';
      const confText = issue.ai_confidence ? ` ${issue.ai_confidence.toFixed(1)}%` : '';
      aiBadgeHTML = `<span class="badge" style="${badgeStyle}" title="AI ResNet50 Inspection">${badgeIcon} ${issue.ai_prediction.toUpperCase()}${confText}</span>`;
    }

    return `
      <div class="issue-card ${issue.status}">
        <div class="issue-header">
          <div>
            <span class="badge badge-${issue.status}">${statusText}</span>
            <span class="badge badge-priority-${issue.priority}">${priorityText}</span>
            ${aiBadgeHTML}
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 6px;">
              Category: <strong>${window.i18n ? window.i18n.t(issue.category, issue.category) : issue.category}</strong>
            </div>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${formattedDate}</div>
        </div>

        <h3 class="issue-title">${escapeHtml(issue.title)}</h3>
        <p class="issue-body">${escapeHtml(issue.description)}</p>

        <!-- Gallery -->
        <div class="media-gallery">
          ${mediaHTML}
        </div>

        <!-- Rejection Details (if rejected) -->
        ${rejectionHTML}

        <!-- Meta list -->
        <div class="issue-meta-info">
          <span>Area: <strong>${escapeHtml(issue.area)}</strong></span>
          <span>Reporter: <strong>${escapeHtml(issue.reporter.name)}</strong></span>
          <span>Ward: <strong>${issue.ward_name || 'Unassigned'}</strong></span>
          <span>Upvotes: <strong>${issue.votes.upvotes}</strong></span>
        </div>

        <!-- Actions footer -->
        <div class="issue-footer" style="flex-direction: column; align-items: flex-start; gap: 12px;">
          <div style="display: flex; justify-content: space-between; width: 100%; align-items: center;">
            <button
              onclick="trackStatus('${issue.id}', '${issue.created_at}', this)"
              class="btn btn-secondary"
              style="padding: 6px 12px; font-size: 0.8rem;"
              data-rej-ai-pred="${issue.rejection_ai_prediction || ''}"
              data-rej-ai-conf="${issue.rejection_ai_confidence || ''}"
              data-comp-ai-pred="${issue.completion_ai_prediction || ''}"
              data-comp-ai-conf="${issue.completion_ai_confidence || ''}"
            >Track Status</button>
          </div>
          
          ${voteSectionHTML}
        </div>
      </div>
    `;
  }).join('');

  if (window.i18n) window.i18n.translatePage();
}

// Vote handling
async function castVote(issueId, voteType) {
  try {
    const headers = { 'Content-Type': 'application/json' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(`/api/issues/${issueId}/vote`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({ vote_type: voteType })
    });
    if (res.ok) {
      await loadIssues();
    } else {
      const errData = await res.json();
      showAlert(errData.detail || 'Failed to submit vote response.', true);
    }
  } catch (err) {
    showAlert('Error connecting to voting service.', true);
  }
}

// Track Status Trail timeline
async function trackStatus(issueId, createdAt, triggerBtn) {
  const modal = document.getElementById('trail-modal');
  const stepper = document.getElementById('trail-stepper');
  
  if (!modal || !stepper) return;
  
  // Read AI data passed from card button
  const aiData = triggerBtn ? {
    rejection_ai_prediction: triggerBtn.dataset.rejAiPred || null,
    rejection_ai_confidence: triggerBtn.dataset.rejAiConf ? parseFloat(triggerBtn.dataset.rejAiConf) : null,
    completion_ai_prediction: triggerBtn.dataset.compAiPred || null,
    completion_ai_confidence: triggerBtn.dataset.compAiConf ? parseFloat(triggerBtn.dataset.compAiConf) : null,
  } : {};
  
  modal.style.display = 'flex';
  stepper.innerHTML = `
    <div style="text-align: center; padding: 20px; color: var(--text-secondary);">
      <span style="animation: pulse-text 1s infinite; display: block; margin-bottom: 12px;">⌛ Fetching audit log ledger...</span>
    </div>
  `;
  
  try {
    const res = await fetch(`/api/issues/${issueId}/status-history`);
    const data = await res.json();
    
    if (res.ok && data.history) {
      const history = data.history;
      
      // Parse history steps
      let reportedTime = new Date(createdAt).toLocaleString();
      let routedTime = null;
      let routedDept = null;
      let inProgressTime = null;
      let inProgressComments = "";
      let resolvedTime = null;
      let resolvedComments = "";
      let proofUrl = null;
      let rejectedTime = null;
      let rejectedComments = "";
      let rejectedProofUrl = null;
      let rejectedByName = "";
      let rejectedByContact = "";
      
      history.forEach(item => {
        const itemTime = new Date(item.created_at).toLocaleString();
        if (item.new_status === 'pending' && item.comments && item.comments.includes('Routed to')) {
          routedTime = itemTime;
          routedDept = item.comments;
        } else if (item.new_status === 'in_progress') {
          inProgressTime = itemTime;
          inProgressComments = item.comments || "Action initiated by department official.";
        } else if (item.new_status === 'resolved') {
          resolvedTime = itemTime;
          resolvedComments = item.comments || "Complaint successfully resolved.";
          proofUrl = item.proof_url;
        } else if (item.new_status === 'rejected') {
          rejectedTime = itemTime;
          rejectedComments = item.comments || "Complaint was rejected by ward official.";
          rejectedProofUrl = item.proof_url;
          rejectedByName = item.changed_by_name || "Ward Official";
          rejectedByContact = item.changed_by_contact || "";
        }
      });
      
      let stepperHTML = '';
      if (rejectedTime) {
        stepperHTML = `
          <div class="stepper">
            <!-- Step 1: Reported -->
            <div class="step completed">
              <div class="step-line" style="background: rgba(239, 68, 68, 0.5);"></div>
              <div class="step-icon">📝</div>
              <div class="step-content">
                <h4 class="step-title">Complaint Reported</h4>
                <p class="step-desc">Issue registered by citizen. Status marked pending.</p>
                <span class="step-time">${reportedTime}</span>
              </div>
            </div>
            
            <!-- Step 2: Rejected -->
            <div class="step completed active" style="color: #ef4444;">
              <div class="step-icon" style="background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.4); color: #ef4444;">❌</div>
              <div class="step-content">
                <h4 class="step-title" style="color: #ef4444; font-weight: 700;">Complaint Rejected</h4>
                <p class="step-desc" style="color: var(--text-secondary);">${escapeHtml(rejectedComments)}</p>
                <div style="font-size: 0.8rem; margin: 8px 0; color: var(--text-muted); border-top: 1px dashed var(--border); padding-top: 8px;">
                  <strong>Rejected By:</strong> ${escapeHtml(rejectedByName)}<br>
                  ${rejectedByContact ? `<strong>Contact:</strong> ${escapeHtml(rejectedByContact)}` : ''}
                </div>
                ${rejectedProofUrl ? `<p style="margin-top:8px;"><a href="${rejectedProofUrl}" target="_blank" class="btn btn-secondary" style="padding:4px 8px;font-size:0.75rem;display:inline-block;border-color:rgba(239,68,68,0.3);color:#ef4444;">View Rejection Evidence</a></p>` : ''}
                ${aiData.rejection_ai_prediction ? `<div style="margin-top:6px;">${aiData.rejection_ai_prediction === 'Fake' ? '<span style="background:rgba(239,68,68,0.15);color:#fca5a5;border:1px solid rgba(239,68,68,0.4);border-radius:6px;padding:2px 8px;font-size:0.75rem;">🔴 REJECTION EVIDENCE: FAKE (AI-Generated)' + (aiData.rejection_ai_confidence ? ' ' + aiData.rejection_ai_confidence.toFixed(1) + '%' : '') + '</span>' : '<span style="background:rgba(16,185,129,0.15);color:#6ee7b7;border:1px solid rgba(16,185,129,0.4);border-radius:6px;padding:2px 8px;font-size:0.75rem;">🟢 REJECTION EVIDENCE: REAL' + (aiData.rejection_ai_confidence ? ' ' + aiData.rejection_ai_confidence.toFixed(1) + '%' : '') + '</span>'}</div>` : ''}
                <span class="step-time" style="color: #ef4444;">${rejectedTime}</span>
              </div>
            </div>
          </div>
        `;
      } else {
        // Compute status flags for rendering
        const isReported = true;
        const isRouted = !!(routedTime || inProgressTime || resolvedTime);
        const isInProgress = !!(inProgressTime || resolvedTime);
        const isResolved = !!resolvedTime;
        
        stepperHTML = `
          <div class="stepper">
            <!-- Step 1: Reported -->
            <div class="step ${isReported ? 'completed' : ''}">
              <div class="step-line"></div>
              <div class="step-icon">📝</div>
              <div class="step-content">
                <h4 class="step-title">Complaint Reported</h4>
                <p class="step-desc">Issue registered by citizen. Status marked pending.</p>
                <span class="step-time">${reportedTime}</span>
              </div>
            </div>
            
            <!-- Step 2: Routed -->
            <div class="step ${isRouted ? 'completed' : ''} ${isRouted && !isInProgress ? 'active' : ''}">
              <div class="step-line"></div>
              <div class="step-icon">🔄</div>
              <div class="step-content">
                <h4 class="step-title">Assigned & Routed</h4>
                <p class="step-desc">${routedTime ? (routedDept || 'Redirected to concern department.') : 'Awaiting routing by Ward representative.'}</p>
                ${routedTime ? `<span class="step-time">${routedTime}</span>` : ''}
              </div>
            </div>
            
            <!-- Step 3: In Progress -->
            <div class="step ${isInProgress ? 'completed' : ''} ${isInProgress && !isResolved ? 'active' : ''}">
              <div class="step-line"></div>
              <div class="step-icon">⚙️</div>
              <div class="step-content">
                <h4 class="step-title">Action Initiated</h4>
                <p class="step-desc">${inProgressTime ? inProgressComments : 'Pending department response.'}</p>
                ${inProgressTime ? `<span class="step-time">${inProgressTime}</span>` : ''}
              </div>
            </div>
            
            <!-- Step 4: Resolved -->
            <div class="step ${isResolved ? 'completed' : ''} ${isResolved ? 'active' : ''}">
              <div class="step-icon">✅</div>
              <div class="step-content">
                <h4 class="step-title">Completed & Resolved</h4>
                <p class="step-desc">${resolvedTime ? resolvedComments : 'Awaiting final verification proof.'}</p>
                ${proofUrl ? `<p style="margin-top:8px;"><a href="${proofUrl}" target="_blank" class="btn btn-secondary" style="padding:4px 8px;font-size:0.75rem;display:inline-block;">View Resolution Proof</a></p>` : ''}
                ${aiData.completion_ai_prediction ? `<div style="margin-top:6px;">${aiData.completion_ai_prediction === 'Fake' ? '<span style="background:rgba(239,68,68,0.15);color:#fca5a5;border:1px solid rgba(239,68,68,0.4);border-radius:6px;padding:2px 8px;font-size:0.75rem;">🔴 RESOLUTION PROOF: FAKE (AI-Generated)' + (aiData.completion_ai_confidence ? ' ' + aiData.completion_ai_confidence.toFixed(1) + '%' : '') + '</span>' : '<span style="background:rgba(16,185,129,0.15);color:#6ee7b7;border:1px solid rgba(16,185,129,0.4);border-radius:6px;padding:2px 8px;font-size:0.75rem;">🟢 RESOLUTION PROOF: REAL' + (aiData.completion_ai_confidence ? ' ' + aiData.completion_ai_confidence.toFixed(1) + '%' : '') + '</span>'}</div>` : ''}
                ${resolvedTime ? `<span class="step-time">${resolvedTime}</span>` : ''}
              </div>
            </div>
          </div>
        `;
      }
      
      stepper.innerHTML = stepperHTML;
    } else {
      stepper.innerHTML = `<p style="color: var(--danger); text-align: center;">Failed to load status history trail.</p>`;
    }
  } catch (err) {
    console.error(err);
    stepper.innerHTML = `<p style="color: var(--danger); text-align: center;">Connection error when fetching timeline.</p>`;
  }
}

function closeTrailModal() {
  const modal = document.getElementById('trail-modal');
  if (modal) modal.style.display = 'none';
}

// Escape utilities
function escapeHtml(value) {
  if (!value) return '';
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

// Run Startup
window.addEventListener('load', initializeDashboard);
// Redraw translations on lang change
window.addEventListener('languageChanged', loadIssues);
