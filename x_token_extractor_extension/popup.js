document.addEventListener('DOMContentLoaded', async () => {
  const currentTokenEl = document.getElementById('currentToken');
  const tokenCountEl = document.getElementById('tokenCount');
  const tokensListEl = document.getElementById('tokensList');
  const addBtn = document.getElementById('addBtn');
  const copyCurrentBtn = document.getElementById('copyCurrentBtn');
  const copyAllTokensBtn = document.getElementById('copyAllTokensBtn');
  const downloadBtn = document.getElementById('downloadBtn');
  const clearBtn = document.getElementById('clearBtn');
  const statusMsg = document.getElementById('statusMsg');

  let currentAuthToken = null;
  let savedTokens = [];

  function showStatus(text, isError = false) {
    statusMsg.textContent = text;
    statusMsg.className = isError ? 'status error' : 'status success';
    setTimeout(() => {
      statusMsg.textContent = '';
      statusMsg.className = 'status';
    }, 2500);
  }

  // Load saved tokens from Chrome storage
  const storageData = await chrome.storage.local.get(['tokensList']);
  if (storageData.tokensList && Array.isArray(storageData.tokensList)) {
    savedTokens = storageData.tokensList;
  }
  updateUI();

  // Fetch current active auth_token
  async function fetchCurrentToken() {
    const urls = ['https://x.com', 'https://twitter.com'];
    for (const url of urls) {
      try {
        const cookie = await chrome.cookies.get({ url: url, name: 'auth_token' });
        if (cookie && cookie.value) {
          return cookie.value;
        }
      } catch (e) {}
    }
    return null;
  }

  currentAuthToken = await fetchCurrentToken();
  if (currentAuthToken) {
    currentTokenEl.textContent = currentAuthToken;
  } else {
    currentTokenEl.textContent = 'Not logged in on x.com';
    currentTokenEl.style.color = '#71767b';
  }

  function updateUI() {
    tokenCountEl.textContent = `${savedTokens.length} Saved`;
    tokensListEl.value = savedTokens.join('\n');
  }

  async function saveTokensToStorage() {
    await chrome.storage.local.set({ tokensList: savedTokens });
    updateUI();
  }

  // Add current token to list
  addBtn.addEventListener('click', async () => {
    if (!currentAuthToken) {
      showStatus('No active account token detected!', true);
      return;
    }
    if (savedTokens.includes(currentAuthToken)) {
      showStatus('This token is already in the list!', true);
      return;
    }
    savedTokens.push(currentAuthToken);
    await saveTokensToStorage();
    showStatus('Token added to list!');
  });

  // Copy current token
  copyCurrentBtn.addEventListener('click', async () => {
    if (currentAuthToken) {
      await navigator.clipboard.writeText(currentAuthToken);
      showStatus('Copied current token!');
    } else {
      showStatus('No token to copy', true);
    }
  });

  // Copy all tokens
  copyAllTokensBtn.addEventListener('click', async () => {
    if (savedTokens.length === 0) {
      showStatus('List is empty!', true);
      return;
    }
    await navigator.clipboard.writeText(savedTokens.join('\n'));
    showStatus(`Copied all ${savedTokens.length} tokens!`);
  });

  // Download tokens.txt
  downloadBtn.addEventListener('click', () => {
    if (savedTokens.length === 0) {
      showStatus('No tokens to download!', true);
      return;
    }
    const blob = new Blob([savedTokens.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'tokens.txt';
    a.click();
    URL.revokeObjectURL(url);
    showStatus('Downloaded tokens.txt!');
  });

  // Clear list
  clearBtn.addEventListener('click', async () => {
    if (savedTokens.length === 0) return;
    if (confirm('Are you sure you want to clear all saved tokens?')) {
      savedTokens = [];
      await saveTokensToStorage();
      showStatus('Tokens list cleared.');
    }
  });
});
