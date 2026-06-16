document.addEventListener('DOMContentLoaded', async () => {
  const connStatus = document.getElementById('conn-status');
  const oppSelect = document.getElementById('opp-select');
  const fetchBtn = document.getElementById('fetch-btn');
  const container = document.getElementById('answers-container');
  
  const BASE_URL = 'http://127.0.0.1:8000';

  // 1. Check API Connection
  try {
    const res = await fetch(`${BASE_URL}/health`);
    if (res.ok) {
      connStatus.textContent = 'Active';
      connStatus.style.color = 'green';
    }
  } catch (e) {
    connStatus.textContent = 'Inactive';
    connStatus.style.color = 'red';
  }

  // 2. Fetch Opportunities
  try {
    const res = await fetch(`${BASE_URL}/api/opportunities`);
    if (res.ok) {
      const opps = await res.json();
      opps.forEach(opp => {
        const opt = document.createElement('option');
        opt.value = opp.id;
        opt.textContent = `${opp.title} (${opp.buyer})`;
        oppSelect.appendChild(opt);
      });
    }
  } catch (e) {
    console.error('Could not fetch opportunities:', e);
  }

  // 3. Load Answers
  fetchBtn.addEventListener('click', async () => {
    const oppId = oppSelect.value;
    if (!oppId) {
      alert('Please select an opportunity first.');
      return;
    }
    
    container.innerHTML = 'Loading answers...';
    
    try {
      const res = await fetch(`${BASE_URL}/api/compliance-matrix/${oppId}`);
      if (res.ok) {
        const items = await res.json();
        container.innerHTML = '';
        if (items.length === 0) {
          container.innerHTML = 'No compliance evidence records found.';
          return;
        }
        
        items.forEach(item => {
          const div = document.createElement('div');
          div.className = 'answer-item';
          div.innerHTML = `<strong>Req:</strong> ${item.requirement.substring(0, 50)}...<br/><small style="color:#4f46e5">Evidence: ${item.evidence.substring(0, 100)}...</small>`;
          
          div.addEventListener('click', () => {
            // Send message to content script to fill the focused input
            chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
              chrome.tabs.sendMessage(tabs[0].id, {
                action: 'fill_input',
                text: item.evidence
              });
            });
          });
          container.appendChild(div);
        });
      }
    } catch (e) {
      container.innerHTML = 'Error loading answers from backend.';
    }
  });
});
