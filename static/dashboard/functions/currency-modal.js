// Currency modal functionality
document.addEventListener('DOMContentLoaded', function() {
  const editCurrencyBtn = document.getElementById('editCurrencyBtn');
  const addCurrencyBtn = document.getElementById('addCurrencyBtn');
  const saveCurrencyBtn = document.getElementById('saveCurrencyBtn');
  const currencyForm = document.getElementById('currencyForm');
  const modalFetchRateBtn = document.getElementById('modalFetchRateBtn');
  const currencyModalElement = document.getElementById('currencyModal');
  
  let rateTimerInterval = null;
  
  console.log('Currency modal JS loaded');
  console.log('editCurrencyBtn:', editCurrencyBtn);
  console.log('addCurrencyBtn:', addCurrencyBtn);
  console.log('currencyModalElement:', currencyModalElement);
  console.log('Bootstrap available:', typeof bootstrap !== 'undefined');
  console.log('Bootstrap.Modal available:', typeof bootstrap !== 'undefined' && bootstrap.Modal);
  
  // Function to check and show timer
  function checkRateCooldown(lastUpdateTimestamp) {
    const now = Math.floor(Date.now() / 1000);
    const cooldownTime = 60; // 60 seconds
    const timeSinceUpdate = now - lastUpdateTimestamp;
    const remainingTime = cooldownTime - timeSinceUpdate;
    
    const modalRateTimer = document.getElementById('modalRateTimer');
    
    if (remainingTime > 0) {
      // Show countdown and disable button
      if (modalRateTimer) {
        modalRateTimer.style.display = 'inline';
        modalRateTimer.textContent = `Wait ${remainingTime}s`;
      }
      if (modalFetchRateBtn) {
        modalFetchRateBtn.disabled = true;
      }
      
      // Start countdown
      if (rateTimerInterval) clearInterval(rateTimerInterval);
      rateTimerInterval = setInterval(() => {
        const now = Math.floor(Date.now() / 1000);
        const timeSinceUpdate = now - lastUpdateTimestamp;
        const remaining = cooldownTime - timeSinceUpdate;
        
        if (remaining <= 0) {
          clearInterval(rateTimerInterval);
          if (modalRateTimer) modalRateTimer.style.display = 'none';
          if (modalFetchRateBtn) modalFetchRateBtn.disabled = false;
        } else {
          if (modalRateTimer) modalRateTimer.textContent = `Wait ${remaining}s`;
        }
      }, 1000);
    } else {
      // Enable button
      if (modalRateTimer) modalRateTimer.style.display = 'none';
      if (modalFetchRateBtn) modalFetchRateBtn.disabled = false;
    }
  }
  
  // Open modal for edit
  if (editCurrencyBtn) {
    editCurrencyBtn.addEventListener('click', function() {
      console.log('Edit Currency button clicked');
      const currencyModalTitle = document.getElementById('currencyModalTitle');
      const modalCurrencyCode = document.getElementById('modalCurrencyCode');
      const modalRateToUsd = document.getElementById('modalRateToUsd');
      const modalRateToUsdHidden = document.getElementById('modalRateToUsdHidden');
      const modalNameEn = document.getElementById('modalNameEn');
      const modalNameAr = document.getElementById('modalNameAr');
      const modalSymbolEn = document.getElementById('modalSymbolEn');
      const modalSymbolAr = document.getElementById('modalSymbolAr');
      
      const currencyNameEn = document.getElementById('currencyNameEn');
      const currencyNameAr = document.getElementById('currencyNameAr');
      const currencySymbolEn = document.getElementById('currencySymbolEn');
      const currencySymbolAr = document.getElementById('currencySymbolAr');
      const exchangeRate = document.getElementById('exchangeRate');
      const rateUpdateTimestamp = document.getElementById('rateUpdateTimestamp');
      
      if (currencyModalTitle) currencyModalTitle.textContent = 'Edit Currency';
      
      // Set currency code
      const currencyCodeEl = document.querySelector("[data-currency-code]");
      if (modalCurrencyCode) modalCurrencyCode.value = currencyCodeEl ? currencyCodeEl.textContent : "";
      
      // Set current rate from database
      const rateValue = exchangeRate ? exchangeRate.textContent : '';
      if (modalRateToUsd && modalRateToUsdHidden) {
        modalRateToUsd.textContent = rateValue || '-';
        modalRateToUsdHidden.value = rateValue || '';
      }
      
      // Check cooldown
      if (rateUpdateTimestamp) {
        const lastUpdate = parseInt(rateUpdateTimestamp.getAttribute('data-timestamp'));
        if (lastUpdate) {
          checkRateCooldown(lastUpdate);
        }
      }
      
      // Set other fields
      if (modalNameEn) modalNameEn.value = currencyNameEn ? currencyNameEn.textContent : '';
      if (modalNameAr) modalNameAr.value = currencyNameAr ? currencyNameAr.textContent : '';
      if (modalSymbolEn) modalSymbolEn.value = currencySymbolEn ? currencySymbolEn.textContent : '';
      if (modalSymbolAr) modalSymbolAr.value = currencySymbolAr ? currencySymbolAr.textContent : '';
      
      // Initialize and show modal on click
      if (currencyModalElement && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        const modal = new bootstrap.Modal(currencyModalElement);
        modal.show();
      } else {
        console.error('Cannot initialize modal:', {
          element: !!currencyModalElement,
          bootstrap: typeof bootstrap !== 'undefined',
          modalClass: typeof bootstrap !== 'undefined' && bootstrap.Modal
        });
      }
    });
  }
  
  // Open modal for add
  if (addCurrencyBtn) {
    addCurrencyBtn.addEventListener('click', function() {
      console.log('Add Currency button clicked');
      const currencyModalTitle = document.getElementById('currencyModalTitle');
      if (currencyModalTitle) currencyModalTitle.textContent = 'Add Currency';
      if (currencyForm) currencyForm.reset();
      
      // Reset rate display
      const modalRateToUsd = document.getElementById('modalRateToUsd');
      const modalRateToUsdHidden = document.getElementById('modalRateToUsdHidden');
      const modalRateTimer = document.getElementById('modalRateTimer');
      if (modalRateToUsd) modalRateToUsd.textContent = '-';
      if (modalRateToUsdHidden) modalRateToUsdHidden.value = '';
      if (modalRateTimer) modalRateTimer.style.display = 'none';
      if (modalFetchRateBtn) modalFetchRateBtn.disabled = false;
      if (rateTimerInterval) clearInterval(rateTimerInterval);
      
      // Initialize and show modal on click
      if (currencyModalElement && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        const modal = new bootstrap.Modal(currencyModalElement);
        modal.show();
      } else {
        console.error('Cannot initialize modal:', {
          element: !!currencyModalElement,
          bootstrap: typeof bootstrap !== 'undefined',
          modalClass: typeof bootstrap !== 'undefined' && bootstrap.Modal
        });
      }
    });
  }
  
  // Save currency
  if (saveCurrencyBtn) {
    saveCurrencyBtn.addEventListener('click', function() {
      const formData = new FormData(currencyForm);
      const data = {};
      
      for (let [key, value] of formData.entries()) {
        if (value) {
          data[key] = value;
        }
      }
      
      const countryId = document.querySelector('[name="country_id"]')?.value;
      
      fetch('/api/dashboard/countries/' + countryId + '/update-currency/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(data)
      })
      .then(response => response.json())
      .then(result => {
        if (result.success) {
          showToast('Currency updated successfully!', 'success');
          // Hide modal
          if (currencyModalElement && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            const modal = bootstrap.Modal.getInstance(currencyModalElement);
            if (modal) modal.hide();
          }
          location.reload();
        } else {
          showToast(result.error || 'Error updating currency', 'error');
        }
      })
      .catch(error => {
        showToast('Error: ' + error, 'error');
      });
    });
  }
  
  // Get rate functionality for modal - now calls backend API
  if (modalFetchRateBtn) {
    modalFetchRateBtn.addEventListener('click', function() {
      const modalCurrencyCode = document.getElementById('modalCurrencyCode');
      if (modalCurrencyCode) {
        const currencyCode = modalCurrencyCode.value;
        if (currencyCode && currencyCode.length === 3) {
          modalFetchRateBtn.disabled = true;
          modalFetchRateBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
          
          fetch('/api/dashboard/countries/currencies/update-rate-by-code/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ currency_code: currencyCode })
          })
          .then(response => response.json())
          .then(result => {
            const modalRateToUsd = document.getElementById('modalRateToUsd');
            const modalRateToUsdHidden = document.getElementById('modalRateToUsdHidden');
            if (result.success && modalRateToUsd && modalRateToUsdHidden) {
              modalRateToUsd.textContent = result.data.rate;
              modalRateToUsdHidden.value = result.data.rate;
              showToast('Rate fetched successfully!', 'success');
              
              // Start cooldown timer
              if (result.data.updated_timestamp) {
                checkRateCooldown(result.data.updated_timestamp);
              }
            } else {
              showToast(result.error || 'Error fetching rate', 'error');
              modalFetchRateBtn.disabled = false;
            }
          })
          .catch(error => {
            showToast('Error fetching rate', 'error');
            modalFetchRateBtn.disabled = false;
          })
          .finally(() => {
            modalFetchRateBtn.innerHTML = `
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4 v-4h-4" />
              </svg>
              Get Rate
            `;
          });
        }
      }
    });
  }
});
