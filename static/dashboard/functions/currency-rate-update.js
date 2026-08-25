// Currency rate update functionality
const updateRateBtn = document.getElementById('updateRateBtn');
const exchangeRateEl = document.getElementById('exchangeRate');
const lastUpdatedEl = document.getElementById('lastUpdated');
const rateUpdateTimestamp = document.getElementById('rateUpdateTimestamp');
const rateCountdown = document.getElementById('rateCountdown');

let rateTimerInterval = null;

// Function to check and show timer
function checkRateCooldown(lastUpdateTimestamp) {
  const now = Math.floor(Date.now() / 1000); // Current time in seconds
  const cooldownTime = 60; // 60 seconds
  const timeSinceUpdate = now - lastUpdateTimestamp;
  const remainingTime = cooldownTime - timeSinceUpdate;
  
  console.log('Cooldown check:', { now, lastUpdateTimestamp, timeSinceUpdate, remainingTime });
  
  if (remainingTime > 0) {
    // Hide button and show countdown
    if (updateRateBtn) updateRateBtn.style.display = 'none';
    if (rateCountdown) {
      rateCountdown.style.display = 'inline';
      rateCountdown.textContent = `Wait: ${Math.ceil(remainingTime)}s`;
    }
    
    // Start countdown
    if (rateTimerInterval) clearInterval(rateTimerInterval);
    rateTimerInterval = setInterval(() => {
      const now = Math.floor(Date.now() / 1000);
      const timeSinceUpdate = now - lastUpdateTimestamp;
      const remaining = cooldownTime - timeSinceUpdate;
      
      if (remaining <= 0) {
        clearInterval(rateTimerInterval);
        // Show button and hide countdown
        if (updateRateBtn) updateRateBtn.style.display = 'inline-block';
        if (rateCountdown) rateCountdown.style.display = 'none';
      } else {
        if (rateCountdown) rateCountdown.textContent = `Wait: ${Math.ceil(remaining)}s`;
      }
    }, 1000);
  } else {
    // Show button and hide countdown
    if (updateRateBtn) updateRateBtn.style.display = 'inline-block';
    if (rateCountdown) rateCountdown.style.display = 'none';
  }
}

if (updateRateBtn && exchangeRateEl) {
  const currencyId = updateRateBtn.getAttribute('data-currency-id');
  
  // Check cooldown on page load
  if (rateUpdateTimestamp) {
    const lastUpdate = parseInt(rateUpdateTimestamp.getAttribute('data-timestamp'));
    console.log('Initial timestamp:', lastUpdate);
    if (lastUpdate) {
      checkRateCooldown(lastUpdate);
    }
  }
  
  // Manual update button handler
  updateRateBtn.addEventListener('click', function() {
    updateCurrencyRate(currencyId);
  });

  // Auto-update currency rate every 5 minutes (300000 ms)
  setInterval(() => {
    updateCurrencyRate(currencyId);
  }, 300000);

  // Initial update after 30 seconds to avoid immediate API call on page load
  setTimeout(() => {
    updateCurrencyRate(currencyId);
  }, 30000);
}

function updateCurrencyRate(currencyId) {
  if (!updateRateBtn) return;
  
  // Hide button and show loading
  if (updateRateBtn) updateRateBtn.style.display = 'none';
  if (rateCountdown) {
    rateCountdown.style.display = 'inline';
    rateCountdown.textContent = 'Updating in progress...';
  }

  fetch(`/api/dashboard/countries/currencies/${currencyId}/update-rate/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCookie('csrftoken')
    }
  })
  .then(response => response.json())
  .then(result => {
    if (result.success) {
      exchangeRateEl.textContent = result.data.rate;
      if (lastUpdatedEl) lastUpdatedEl.textContent = result.data.updated_at;
      
      // Update timestamp and start cooldown
      if (rateUpdateTimestamp && result.data.updated_timestamp) {
        rateUpdateTimestamp.setAttribute('data-timestamp', result.data.updated_timestamp);
        console.log('Updated timestamp:', result.data.updated_timestamp);
        checkRateCooldown(result.data.updated_timestamp);
      }
      
      console.log('Currency rate updated successfully');
    } else {
      console.error('Failed to update currency rate:', result.error);
      // Show button on error
      if (updateRateBtn) updateRateBtn.style.display = 'inline-block';
      if (rateCountdown) rateCountdown.style.display = 'none';
    }
  })
  .catch(error => {
    console.error('Error updating currency rate:', error);
    // Show button on error
    if (updateRateBtn) updateRateBtn.style.display = 'inline-block';
    if (rateCountdown) rateCountdown.style.display = 'none';
  });
}
