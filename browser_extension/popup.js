// Popup script for PassGuard extension

document.addEventListener('DOMContentLoaded', async () => {
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const statusDetails = document.getElementById('statusDetails');
  const tokenInput = document.getElementById('tokenInput');
  const saveButton = document.getElementById('saveButton');
  const message = document.getElementById('message');
  
  // Check if token exists (but don't display it for security)
  chrome.storage.local.get(['passguard_token'], (result) => {
    if (result.passguard_token) {
      tokenInput.placeholder = "Token saved (hidden for security)";
    }
  });
  
  // Check server status
  async function checkStatus() {
    try {
      const response = await chrome.runtime.sendMessage({ action: 'checkStatus' });
      
      if (response.unlocked) {
        statusDot.className = 'status-dot online';
        statusText.textContent = 'PassGuard is running';
        statusDetails.textContent = 'Vault is unlocked and ready for autofill';
      } else {
        statusDot.className = 'status-dot offline';
        statusText.textContent = 'PassGuard is locked';
        statusDetails.textContent = 'Please unlock your vault to use autofill';
      }
    } catch (error) {
      statusDot.className = 'status-dot offline';
      statusText.textContent = 'PassGuard is not running';
      statusDetails.textContent = 'Please start PassGuard and unlock your vault';
    }
  }
  
  // Save token
  saveButton.addEventListener('click', async () => {
    const token = tokenInput.value.trim();
    
    if (!token) {
      showMessage('Please enter a token', 'error');
      return;
    }
    
    saveButton.disabled = true;
    saveButton.textContent = 'Saving...';
    
    try {
      await chrome.runtime.sendMessage({
        action: 'setToken',
        token: token
      });
      
      showMessage('Token saved successfully!', 'success');
      saveButton.textContent = 'Save Token';
      saveButton.disabled = false;
      
      // Recheck status
      setTimeout(checkStatus, 500);
    } catch (error) {
      showMessage('Failed to save token', 'error');
      saveButton.textContent = 'Save Token';
      saveButton.disabled = false;
    }
  });
  
  function showMessage(text, type) {
    message.textContent = text;
    message.className = `message ${type}`;
    message.style.display = 'block';
    
    setTimeout(() => {
      message.style.display = 'none';
    }, 3000);
  }
  
  // Initial status check
  checkStatus();
  
  // Refresh status every 5 seconds
  setInterval(checkStatus, 5000);
});
