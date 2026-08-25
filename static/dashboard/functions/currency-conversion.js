// Currency conversion for pricing fields
// Note: currencyRate and currencyCode are defined in pricing-zones.js

function addCurrencyConversion(input) {
  if (!input || input.dataset.conversionAdded) return;
  
  // Check if conversion display already exists
  if (input.parentNode.querySelector('.currency-conversion')) {
    input.dataset.conversionAdded = 'true';
    return;
  }
  
  // Create conversion display element
  const conversionDisplay = document.createElement('small');
  conversionDisplay.className = 'text-muted currency-conversion';
  conversionDisplay.style.display = 'block';
  conversionDisplay.style.marginTop = '4px';
  conversionDisplay.style.fontSize = '0.8rem';
  input.parentNode.appendChild(conversionDisplay);
  
  input.dataset.conversionAdded = 'true';
  
  // Update conversion on input
  const updateConversion = function() {
    const usdValue = parseFloat(input.value);
    const currencyRateDisplay = document.getElementById('currencyRateDisplay');
    const currencyRate = currencyRateDisplay ? parseFloat(currencyRateDisplay.textContent) || 0 : 0;
    const currencyCodeDisplay = document.querySelector('[data-currency-code]');
    const currencyCode = currencyCodeDisplay ? currencyCodeDisplay.textContent : '';
    
    if (!isNaN(usdValue) && currencyRate > 0) {
      const localValue = (usdValue * currencyRate).toFixed(2);
      conversionDisplay.textContent = `≈ ${localValue} ${currencyCode}`;
    } else {
      conversionDisplay.textContent = '';
    }
  };
  
  input.addEventListener('input', updateConversion);
  input.addEventListener('change', updateConversion);
  
  // Initial update if value exists
  updateConversion();
}

// Force update conversion for all inputs
function updateAllConversions() {
  const conversionDisplays = document.querySelectorAll('.currency-conversion');
  conversionDisplays.forEach(display => {
    const input = display.previousElementSibling;
    if (input && input.value) {
      const usdValue = parseFloat(input.value);
      const currencyRateDisplay = document.getElementById('currencyRateDisplay');
      const currencyRate = currencyRateDisplay ? parseFloat(currencyRateDisplay.textContent) || 0 : 0;
      const currencyCodeDisplay = document.querySelector('[data-currency-code]');
      const currencyCode = currencyCodeDisplay ? currencyCodeDisplay.textContent : '';
      
      if (!isNaN(usdValue) && currencyRate > 0) {
        const localValue = (usdValue * currencyRate).toFixed(2);
        display.textContent = `≈ ${localValue} ${currencyCode}`;
      }
    }
  });
}

// Add conversion to all pricing input fields
function addConversionToAllInputs() {
  const pricingInputs = document.querySelectorAll('[name^="zone"][type="number"]');
  pricingInputs.forEach(input => {
    addCurrencyConversion(input);
  });
}

// Add conversion when division type changes
// Note: divisionTypeSelect is defined in pricing-zones.js
if (typeof divisionTypeSelect !== 'undefined' && divisionTypeSelect) {
  divisionTypeSelect.addEventListener('change', function() {
    setTimeout(function() {
      addConversionToAllInputs();
      updateAllConversions();
    }, 200);
  });
}

// Add conversion on page load
document.addEventListener('DOMContentLoaded', function() {
  addConversionToAllInputs();
});

// Also add conversion when form is shown
const setupBtn = document.getElementById('setupPricingZoneBtn');
if (setupBtn) {
  setupBtn.addEventListener('click', function() {
    setTimeout(addConversionToAllInputs, 100);
  });
}

// Also add conversion when edit button is clicked
const editBtn = document.getElementById('editPricingZoneBtn');
if (editBtn) {
  editBtn.addEventListener('click', function() {
    setTimeout(function() {
      addConversionToAllInputs();
      updateAllConversions();
    }, 300);
  });
}
