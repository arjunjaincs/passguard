// Background service worker for PassGuard extension

const API_URL = 'http://127.0.0.1:5777';
let authToken = null;

// Load token from storage on startup
chrome.storage.local.get(['passguard_token'], (result) => {
  if (result.passguard_token) {
    authToken = result.passguard_token;
    console.log('[PassGuard] Token loaded from storage');
  }
});

// Listen for messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getCredentials') {
    getCredentials(request.domain)
      .then(sendResponse)
      .catch(error => sendResponse({ error: error.message }));
    return true; // Keep channel open for async response
  }
  
  if (request.action === 'setToken') {
    authToken = request.token;
    chrome.storage.local.set({ passguard_token: authToken });
    sendResponse({ success: true });
    return true;
  }
  
  if (request.action === 'checkStatus') {
    checkServerStatus()
      .then(sendResponse)
      .catch(error => sendResponse({ error: error.message, unlocked: false }));
    return true;
  }
});

// Get credentials from PassGuard API
async function getCredentials(domain) {
  if (!authToken) {
    throw new Error('No authentication token. Please configure PassGuard extension.');
  }
  
  try {
    const response = await fetch(`${API_URL}/get_credentials?domain=${encodeURIComponent(domain)}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });
    
    if (response.status === 403) {
      throw new Error('Vault not unlocked. Please unlock PassGuard first.');
    }
    
    if (response.status === 401) {
      throw new Error('Invalid token. Please reconfigure PassGuard extension.');
    }
    
    if (response.status === 404) {
      return { found: false, message: 'No credentials found for this site' };
    }
    
    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }
    
    const data = await response.json();
    
    if (data.multiple) {
      return { found: true, multiple: true, credentials: data.credentials };
    } else {
      return { found: true, credential: data.credential };
    }
  } catch (error) {
    if (error.message.includes('Failed to fetch')) {
      throw new Error('PassGuard is not running or vault is locked');
    }
    throw error;
  }
}

// Check if PassGuard server is running
async function checkServerStatus() {
  try {
    const response = await fetch(`${API_URL}/health`, {
      method: 'GET'
    });
    
    if (response.ok) {
      const data = await response.json();
      // Vault is ready if it was unlocked once this session
      return { unlocked: data.vault === 'ready', status: data.status };
    }
    return { unlocked: false };
  } catch (error) {
    return { unlocked: false };
  }
}
