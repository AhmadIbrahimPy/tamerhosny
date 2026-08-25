// Currency code input handler and rate fetching
const currencyCodeInput = document.getElementById('currencyCode');
const fetchRateBtn = document.getElementById('fetchRateBtn');
const rateToUsdDisplay = document.getElementById('rateToUsd');
const rateToUsdHidden = document.getElementById('rateToUsdHidden');

let rateTimerInterval = null;

// Function to check and show timer
function checkRateCooldown(lastUpdateTimestamp) {
  const now = Math.floor(Date.now() / 1000);
  const cooldownTime = 60; // 60 seconds
  const timeSinceUpdate = now - lastUpdateTimestamp;
  const remainingTime = cooldownTime - timeSinceUpdate;
  
  if (remainingTime > 0) {
    // Disable button
    if (fetchRateBtn) {
      fetchRateBtn.disabled = true;
      fetchRateBtn.innerHTML = `Wait ${remainingTime}s`;
    }
    
    // Start countdown
    if (rateTimerInterval) clearInterval(rateTimerInterval);
    rateTimerInterval = setInterval(() => {
      const now = Math.floor(Date.now() / 1000);
      const timeSinceUpdate = now - lastUpdateTimestamp;
      const remaining = cooldownTime - timeSinceUpdate;
      
      if (remaining <= 0) {
        clearInterval(rateTimerInterval);
        if (fetchRateBtn) {
          fetchRateBtn.disabled = false;
          fetchRateBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none" />
              <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
              <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4 v-4h-4" />
            </svg>
            Get Rate
          `;
        }
      } else {
        if (fetchRateBtn) fetchRateBtn.innerHTML = `Wait ${remaining}s`;
      }
    }, 1000);
  } else {
    // Enable button
    if (fetchRateBtn) fetchRateBtn.disabled = false;
  }
}

if (currencyCodeInput && fetchRateBtn) {
    currencyCodeInput.addEventListener('input', function() {
        const code = this.value.toUpperCase();
        if (code.length === 3) {
            fetchRateBtn.disabled = false;
        } else {
            fetchRateBtn.disabled = true;
        }
    });

    // Fetch rate button - now calls backend API
    fetchRateBtn.addEventListener('click', function() {
        const code = currencyCodeInput.value.toUpperCase();
        if (code.length !== 3) return;

        fetchRateBtn.disabled = true;
        fetchRateBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';

        fetch('/api/dashboard/countries/currencies/update-rate-by-code/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ currency_code: code })
        })
        .then(response => response.json())
        .then(result => {
            if (result.success && rateToUsdDisplay && rateToUsdHidden) {
                rateToUsdDisplay.textContent = result.data.rate;
                rateToUsdHidden.value = result.data.rate;
                showToast(`Rate for ${code}: ${result.data.rate}`, 'success');
                
                // Start cooldown timer
                if (result.data.updated_timestamp) {
                    checkRateCooldown(result.data.updated_timestamp);
                }
            } else {
                showToast(result.error || 'Error fetching rate', 'error');
                fetchRateBtn.disabled = false;
                fetchRateBtn.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                        <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                        <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4 v-4h-4" />
                    </svg>
                    Get Rate
                `;
            }
        })
        .catch(error => {
            showToast('Error fetching rate: ' + error, 'error');
            fetchRateBtn.disabled = false;
            fetchRateBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                    <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                    <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4 v-4h-4" />
                </svg>
                Get Rate
            `;
        });
    });
}
