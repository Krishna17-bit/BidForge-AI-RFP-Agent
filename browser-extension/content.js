// Listen for autocompletion messages from popup.js
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'fill_input') {
    const activeEl = document.activeElement;
    if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.isContentEditable)) {
      if (activeEl.isContentEditable) {
        activeEl.innerHTML = request.text;
      } else {
        activeEl.value = request.text;
      }
      
      // Dispatch input events to trigger React/Vue field listeners
      activeEl.dispatchEvent(new Event('input', { bubbles: true }));
      activeEl.dispatchEvent(new Event('change', { bubbles: true }));
      
      sendResponse({ status: 'filled' });
    } else {
      alert('Please select or focus a text input field first before clicking an answer.');
      sendResponse({ status: 'no_focus' });
    }
  }
});
