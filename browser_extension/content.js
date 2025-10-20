// Content script for detecting and filling login forms

console.log('[PassGuard] Content script loaded');
console.log('[PassGuard] Current URL:', window.location.href);

// Detect login forms on page
function detectLoginForms() {
  const loginForms = [];
  
  // Find all password fields first (including those in shadow DOM)
  const passwordFields = document.querySelectorAll('input[type="password"]');
  
  passwordFields.forEach(passwordField => {
    // Skip if already processed AND still visible
    if (passwordField.dataset.passguardProcessed && isVisible(passwordField)) return;
    
    // Skip if not visible
    if (!isVisible(passwordField)) return;
    
    // Find the closest form or container
    const form = passwordField.closest('form') || passwordField.closest('div[role="form"]') || passwordField.parentElement;
    
    // Look for username/email field near the password field
    let usernameField = null;
    
    // Search within the form/container and nearby elements
    const container = form || passwordField.closest('body');
    const inputs = container.querySelectorAll('input');
    
    inputs.forEach(input => {
      if (input === passwordField) return;
      if (!isVisible(input)) return;
      
      const type = input.type.toLowerCase();
      const name = (input.name || '').toLowerCase();
      const id = (input.id || '').toLowerCase();
      const placeholder = (input.placeholder || '').toLowerCase();
      const autocomplete = (input.autocomplete || '').toLowerCase();
      const ariaLabel = (input.getAttribute('aria-label') || '').toLowerCase();
      
      // Detect username/email field with broader matching
      if (type === 'email' || type === 'text' || type === 'tel') {
        if (name.includes('user') || name.includes('email') || name.includes('login') || name.includes('identifier') ||
            id.includes('user') || id.includes('email') || id.includes('login') || id.includes('identifier') ||
            placeholder.includes('user') || placeholder.includes('email') || placeholder.includes('login') || placeholder.includes('identifier') ||
            autocomplete.includes('username') || autocomplete.includes('email') ||
            ariaLabel.includes('user') || ariaLabel.includes('email') || ariaLabel.includes('login')) {
          if (!usernameField) {
            usernameField = input;
          }
        }
      }
    });
    
    // Even if no username field, still add (some sites only have password)
    loginForms.push({ form, usernameField, passwordField });
    passwordField.dataset.passguardProcessed = 'true';
  });
  
  return loginForms;
}

// Check if element is visible
function isVisible(element) {
  if (!element) return false;
  const style = window.getComputedStyle(element);
  return style.display !== 'none' && 
         style.visibility !== 'hidden' && 
         style.opacity !== '0' &&
         element.offsetWidth > 0 && 
         element.offsetHeight > 0;
}

// Store found forms globally
let cachedLoginForms = [];

// Add floating autofill button
function addFloatingButton() {
  const loginForms = detectLoginForms();
  console.log(`[PassGuard] Found ${loginForms.length} login form(s)`);
  
  // Update cache if forms found
  if (loginForms.length > 0) {
    cachedLoginForms = loginForms;
  }
  
  // Use cached forms if current detection fails but we had forms before
  const formsToUse = loginForms.length > 0 ? loginForms : cachedLoginForms;
  
  // If no forms at all, don't show button
  if (formsToUse.length === 0) {
    console.log('[PassGuard] No forms found yet, will keep checking...');
    // Remove button if it exists
    const existing = document.getElementById('passguard-floating-btn');
    if (existing) existing.remove();
    return;
  }
  
  // Check if button already exists and is valid
  const existing = document.getElementById('passguard-floating-btn');
  if (existing && document.body.contains(existing)) {
    // Button exists and is still in DOM, don't recreate
    return;
  }
  
  // Create floating button
  const floatingBtn = document.createElement('div');
  floatingBtn.id = 'passguard-floating-btn';
  floatingBtn.innerHTML = `
    <div class="passguard-float-content">
      <div class="passguard-icon">🔐</div>
      <div class="passguard-text">Fill with PassGuard</div>
    </div>
  `;
  
  floatingBtn.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 15px 25px;
    border-radius: 50px;
    cursor: pointer;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 16px;
    font-weight: 600;
    box-shadow: 0 4px 20px rgba(102, 126, 234, 0.5);
    z-index: 999999;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    gap: 10px;
    animation: slideInRight 0.5s ease;
  `;
  
  floatingBtn.onmouseover = () => {
    floatingBtn.style.transform = 'scale(1.05) translateY(-2px)';
    floatingBtn.style.boxShadow = '0 6px 25px rgba(102, 126, 234, 0.7)';
  };
  
  floatingBtn.onmouseout = () => {
    floatingBtn.style.transform = 'scale(1) translateY(0)';
    floatingBtn.style.boxShadow = '0 4px 20px rgba(102, 126, 234, 0.5)';
  };
  
  floatingBtn.onclick = async () => {
    floatingBtn.style.pointerEvents = 'none';
    floatingBtn.innerHTML = '<div class="passguard-float-content"><div class="passguard-icon">⏳</div><div class="passguard-text">Loading...</div></div>';
    
    try {
      const domain = window.location.hostname;
      const response = await chrome.runtime.sendMessage({
        action: 'getCredentials',
        domain: domain
      });
      
      if (response.error) {
        showNotification(response.error, 'error');
        resetFloatingButton(floatingBtn);
        return;
      }
      
      if (!response.found) {
        showNotification('No credentials found for this site', 'warning');
        resetFloatingButton(floatingBtn);
        return;
      }
      
      // Get the first form from cache
      const { usernameField, passwordField } = formsToUse[0];
      const cred = response.multiple ? response.credentials[0] : response.credential;
      
      fillCredentials(usernameField, passwordField, cred);
      showNotification('Credentials filled successfully!', 'success');
      
      floatingBtn.innerHTML = '<div class="passguard-float-content"><div class="passguard-icon">✓</div><div class="passguard-text">Filled!</div></div>';
      floatingBtn.style.background = 'linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)';
      
      setTimeout(() => {
        resetFloatingButton(floatingBtn);
      }, 2000);
      
    } catch (error) {
      console.error('[PassGuard] Error:', error);
      showNotification('Failed to autofill. Is PassGuard running?', 'error');
      resetFloatingButton(floatingBtn);
    }
  };
  
  document.body.appendChild(floatingBtn);
}

function resetFloatingButton(btn) {
  btn.style.pointerEvents = 'auto';
  btn.innerHTML = '<div class="passguard-float-content"><div class="passguard-icon">🔐</div><div class="passguard-text">Fill with PassGuard</div></div>';
  btn.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
}

// Add autofill button to login forms (legacy - keep for compatibility)
function addAutofillButtons() {
  addFloatingButton();
  
  const loginForms = detectLoginForms();
  
  if (loginForms.length === 0) return;
  
  loginForms.forEach(({ form, usernameField, passwordField }) => {
    // Check if button already exists
    if (form && form.querySelector('.passguard-autofill-btn')) return;
    
    // Create autofill button
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'passguard-autofill-btn';
    button.innerHTML = '🔐 Fill with PassGuard';
    button.style.cssText = `
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 600;
      margin: 10px 0;
      box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
      transition: all 0.3s ease;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    `;
    
    button.onmouseover = () => {
      button.style.transform = 'translateY(-2px)';
      button.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.6)';
    };
    
    button.onmouseout = () => {
      button.style.transform = 'translateY(0)';
      button.style.boxShadow = '0 2px 8px rgba(102, 126, 234, 0.4)';
    };
    
    button.onclick = async () => {
      button.disabled = true;
      button.innerHTML = '⏳ Loading...';
      
      try {
        const domain = window.location.hostname;
        const response = await chrome.runtime.sendMessage({
          action: 'getCredentials',
          domain: domain
        });
        
        if (response.error) {
          showNotification(response.error, 'error');
          button.innerHTML = '🔐 Fill with PassGuard';
          button.disabled = false;
          return;
        }
        
        if (!response.found) {
          showNotification('No credentials found for this site', 'warning');
          button.innerHTML = '🔐 Fill with PassGuard';
          button.disabled = false;
          return;
        }
        
        if (response.multiple) {
          // Multiple credentials found - use first one or show selector
          const cred = response.credentials[0];
          fillCredentials(usernameField, passwordField, cred);
          showNotification(`Filled credentials for ${cred.username}`, 'success');
        } else {
          fillCredentials(usernameField, passwordField, response.credential);
          showNotification('Credentials filled successfully!', 'success');
        }
        
        button.innerHTML = '✓ Filled!';
        setTimeout(() => {
          button.innerHTML = '🔐 Fill with PassGuard';
          button.disabled = false;
        }, 2000);
        
      } catch (error) {
        console.error('[PassGuard] Error:', error);
        showNotification('Failed to autofill. Is PassGuard running?', 'error');
        button.innerHTML = '🔐 Fill with PassGuard';
        button.disabled = false;
      }
    };
    
    // Insert button after password field
    try {
      // Try to insert after password field
      if (passwordField.parentNode) {
        // Create a container div for better positioning
        const buttonContainer = document.createElement('div');
        buttonContainer.style.cssText = 'margin: 10px 0; text-align: left;';
        buttonContainer.appendChild(button);
        
        // Insert after password field
        if (passwordField.nextSibling) {
          passwordField.parentNode.insertBefore(buttonContainer, passwordField.nextSibling);
        } else {
          passwordField.parentNode.appendChild(buttonContainer);
        }
      }
    } catch (error) {
      console.error('[PassGuard] Failed to insert button:', error);
    }
  });
}

// Fill credentials into form fields
function fillCredentials(usernameField, passwordField, credential) {
  if (usernameField) {
    usernameField.value = credential.username;
    usernameField.dispatchEvent(new Event('input', { bubbles: true }));
    usernameField.dispatchEvent(new Event('change', { bubbles: true }));
  }
  
  if (passwordField) {
    passwordField.value = credential.password;
    passwordField.dispatchEvent(new Event('input', { bubbles: true }));
    passwordField.dispatchEvent(new Event('change', { bubbles: true }));
  }
}

// Show notification
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = 'passguard-notification';
  
  const colors = {
    success: '#2ecc71',
    error: '#e74c3c',
    warning: '#f39c12',
    info: '#3498db'
  };
  
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: ${colors[type]};
    color: white;
    padding: 15px 20px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    z-index: 999999;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px;
    font-weight: 500;
    animation: slideIn 0.3s ease;
  `;
  
  notification.textContent = message;
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn {
    from {
      transform: translateX(400px);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  
  @keyframes slideOut {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(400px);
      opacity: 0;
    }
  }
  
  @keyframes slideInRight {
    from {
      transform: translateX(400px);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
`;
document.head.appendChild(style);

// Initialize on page load
function initPassGuard() {
  try {
    console.log('[PassGuard] Initializing...');
    addAutofillButtons();
  } catch (error) {
    console.error('[PassGuard] Initialization error:', error);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    console.log('[PassGuard] DOM loaded, searching for forms...');
    initPassGuard();
  });
} else {
  console.log('[PassGuard] Page already loaded, searching for forms...');
  initPassGuard();
}

// Re-check for forms after dynamic content loads (debounced)
let debounceTimer;
const observer = new MutationObserver(() => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    addAutofillButtons();
  }, 500); // Wait 500ms after last change
});

// Start observing after a short delay to let page settle
setTimeout(() => {
  if (document.body) {
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
    console.log('[PassGuard] Mutation observer started');
  }
}, 1000);

// Also check periodically for the first 10 seconds (for slow-loading sites)
let checkCount = 0;
const periodicCheck = setInterval(() => {
  addAutofillButtons();
  checkCount++;
  if (checkCount >= 10) {
    clearInterval(periodicCheck);
    console.log('[PassGuard] Periodic checks completed');
  }
}, 1000);
