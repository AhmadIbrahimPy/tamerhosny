// Pricing Zones Management
// Scoped to either a country or a city via #pricingZonesRoot's data attributes -
// a country page has one pricing zone per country, a city page one per city.
const pricingZonesRoot = document.getElementById('pricingZonesRoot');
const pricingZonesScopeType = pricingZonesRoot?.dataset.scopeType || 'country';
const pricingZonesScopeId = pricingZonesRoot?.dataset.scopeId;
const pricingZonesListUrl = pricingZonesScopeId
    ? (pricingZonesScopeType === 'city'
        ? `/api/dashboard/countries/cities/${pricingZonesScopeId}/pricing-zones/`
        : `/api/dashboard/countries/${pricingZonesScopeId}/pricing-zones/`)
    : null;

// Get currency rate from DOM or default to 0
const currencyRateDisplay = document.getElementById('currencyRateDisplay');
const currencyRate = currencyRateDisplay ? parseFloat(currencyRateDisplay.textContent) || 0 : 0;
const currencyCodeDisplay = document.querySelector('[data-currency-code]');
const currencyCode = currencyCodeDisplay ? currencyCodeDisplay.textContent : '';

// DOM Elements
const setupPricingZoneBtn = document.getElementById('setupPricingZoneBtn');
const editPricingZoneBtn = document.getElementById('editPricingZoneBtn');
const pricingZoneSetupForm = document.getElementById('pricingZoneSetupForm');
const pricingZoneForm = document.getElementById('pricingZoneForm');
const cancelSetupBtn = document.getElementById('cancelSetupBtn');
const divisionTypeSelect = document.getElementById('divisionType');
const pricingDisplayCard = document.getElementById('pricingDisplayCard');
const pricingDisplayContent = document.getElementById('pricingDisplayContent');
const pricingZonesEmpty = document.getElementById('pricingZonesEmpty');
const currentDivisionType = document.getElementById('currentDivisionType');
const formTitle = document.getElementById('formTitle');
const zoneIdInput = document.getElementById('zoneId');
const savePricingZoneBtn = document.getElementById('savePricingZoneBtn');

// Pricing field groups
const singleZoneFields = document.getElementById('singleZoneFields');
const twoZoneFields = document.getElementById('twoZoneFields');
const fourZoneFields = document.getElementById('fourZoneFields');

// Store current values before division type change
let currentValues = {};
let previousDivisionType = null;

// Load pricing zones when tab is activated
document.getElementById('pricing-zones-tab').addEventListener('click', function() {
    loadPricingZones();
});

// Load on page load
document.addEventListener('DOMContentLoaded', function() {
    loadPricingZones();
});

// Setup button click
setupPricingZoneBtn.addEventListener('click', function() {
    pricingZoneSetupForm.classList.remove('d-none');
    setupPricingZoneBtn.classList.add('d-none');
    formTitle.textContent = 'Configure Pricing Zones';
    savePricingZoneBtn.textContent = 'Save Pricing Zone';
    divisionTypeSelect.disabled = false;
    pricingZoneForm.reset();
    zoneIdInput.value = '';
    hideAllPricingFields();
    savePricingZoneBtn.classList.add('disabled');
    savePricingZoneBtn.disabled = true;
    currentValues = {};
    previousDivisionType = null;
});

// Edit button click
editPricingZoneBtn.addEventListener('click', function() {
    loadPricingZones().then(zones => {
        if (zones && zones.length > 0) {
            editPricingZone(zones[0].id);
        }
    });
});

// Cancel button click
cancelSetupBtn.addEventListener('click', function() {
    pricingZoneSetupForm.classList.add('d-none');
    setupPricingZoneBtn.classList.remove('d-none');
    pricingZoneForm.reset();
    hideAllPricingFields();
    currentValues = {};
    previousDivisionType = null;
});

// Division type change
divisionTypeSelect.addEventListener('change', function() {
    const newDivisionType = this.value;
    
    // Store current values BEFORE hiding fields and changing
    storeCurrentValues();
    
    hideAllPricingFields();
    
    // Enable/disable save button based on division type selection
    if (newDivisionType) {
        savePricingZoneBtn.classList.remove('disabled');
        savePricingZoneBtn.disabled = false;
    } else {
        savePricingZoneBtn.classList.add('disabled');
        savePricingZoneBtn.disabled = true;
    }
    
    // Show appropriate fields and restore values
    switch(newDivisionType) {
        case '1':
            singleZoneFields.classList.remove('d-none');
            restoreValues('single');
            break;
        case '2':
            twoZoneFields.classList.remove('d-none');
            restoreValues('two');
            break;
        case '4':
            fourZoneFields.classList.remove('d-none');
            restoreValues('four');
            break;
    }
    
    previousDivisionType = newDivisionType;
});

// Store current field values
function storeCurrentValues() {
    // Get all pricing fields that are currently visible
    currentValues = {
        zone1_local_price: document.getElementById('zone1_local_price')?.value || '',
        zone1_international_price: document.getElementById('zone1_international_price')?.value || '',
        zone2_a_local_price: document.getElementById('zone2_a_local_price')?.value || '',
        zone2_a_international_price: document.getElementById('zone2_a_international_price')?.value || '',
        zone2_b_local_price: document.getElementById('zone2_b_local_price')?.value || '',
        zone2_b_international_price: document.getElementById('zone2_b_international_price')?.value || '',
        zone4_north_local_price: document.getElementById('zone4_north_local_price')?.value || '',
        zone4_north_international_price: document.getElementById('zone4_north_international_price')?.value || '',
        zone4_south_local_price: document.getElementById('zone4_south_local_price')?.value || '',
        zone4_south_international_price: document.getElementById('zone4_south_international_price')?.value || '',
        zone4_east_local_price: document.getElementById('zone4_east_local_price')?.value || '',
        zone4_east_international_price: document.getElementById('zone4_east_international_price')?.value || '',
        zone4_west_local_price: document.getElementById('zone4_west_local_price')?.value || '',
        zone4_west_international_price: document.getElementById('zone4_west_international_price')?.value || '',
    };
}

// Restore values based on division type
function restoreValues(type) {
    if (type === 'single') {
        document.getElementById('zone1_local_price').value = currentValues.zone1_local_price || '';
        document.getElementById('zone1_international_price').value = currentValues.zone1_international_price || '';
    } else if (type === 'two') {
        document.getElementById('zone2_a_local_price').value = currentValues.zone1_local_price || currentValues.zone2_a_local_price || '';
        document.getElementById('zone2_a_international_price').value = currentValues.zone1_international_price || currentValues.zone2_a_international_price || '';
        document.getElementById('zone2_b_local_price').value = currentValues.zone2_b_local_price || '';
        document.getElementById('zone2_b_international_price').value = currentValues.zone2_b_international_price || '';
    } else if (type === 'four') {
        document.getElementById('zone4_north_local_price').value = currentValues.zone1_local_price || currentValues.zone2_a_local_price || currentValues.zone4_north_local_price || '';
        document.getElementById('zone4_north_international_price').value = currentValues.zone1_international_price || currentValues.zone2_a_international_price || currentValues.zone4_north_international_price || '';
        document.getElementById('zone4_south_local_price').value = currentValues.zone2_b_local_price || currentValues.zone4_south_local_price || '';
        document.getElementById('zone4_south_international_price').value = currentValues.zone2_b_international_price || currentValues.zone4_south_international_price || '';
        document.getElementById('zone4_east_local_price').value = currentValues.zone4_east_local_price || '';
        document.getElementById('zone4_east_international_price').value = currentValues.zone4_east_international_price || '';
        document.getElementById('zone4_west_local_price').value = currentValues.zone4_west_local_price || '';
        document.getElementById('zone4_west_international_price').value = currentValues.zone4_west_international_price || '';
    }
}

// Form submission
pricingZoneForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        if (value) {
            data[key] = value;
        }
    }
    
    const zoneId = zoneIdInput.value;
    const url = zoneId ? `/api/dashboard/countries/pricing-zones/${zoneId}/update/` : '/api/dashboard/countries/pricing-zones/create/';
    
    fetch(url, {
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
            showToast(zoneId ? 'Pricing zone updated successfully!' : 'Pricing zone created successfully!', 'success');
            pricingZoneSetupForm.classList.add('d-none');
            pricingZoneForm.reset();
            hideAllPricingFields();
            currentValues = {};
            previousDivisionType = null;
            loadPricingZones();
        } else {
            showToast(result.error || 'Error saving pricing zone', 'error');
        }
    })
    .catch(error => {
        showToast('Error: ' + error, 'error');
    });
});

// Load pricing zones
function loadPricingZones() {
    if (!pricingZonesListUrl) return Promise.resolve([]);

    return fetch(pricingZonesListUrl)
        .then(response => response.json())
        .then(result => {
            if (result.success && result.data.length > 0) {
                displayPricingZone(result.data[0]);
                setupPricingZoneBtn.classList.add('d-none');
                editPricingZoneBtn.classList.remove('d-none');
                return result.data;
            } else {
                showEmptyState();
                setupPricingZoneBtn.classList.remove('d-none');
                editPricingZoneBtn.classList.add('d-none');
                return [];
            }
        })
        .catch(error => {
            console.error('Error loading pricing zones:', error);
            showEmptyState();
            return [];
        });
}

// Display pricing zone (single zone per country)
function displayPricingZone(zone) {
    pricingZonesEmpty.classList.add('d-none');
    pricingDisplayCard.classList.remove('d-none');
    
    // Show division type badge
    currentDivisionType.classList.remove('d-none');
    currentDivisionType.textContent = getDivisionTypeText(zone.division_type);
    
    // Build pricing display based on division type
    let html = '';
    
    if (zone.division_type === 1) {
        html = `
            <div class="row">
                <div class="col-md-6">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">Local Price</h6>
                            <p class="card-text fs-4 mb-0">${zone.zone1_local_price ? zone.zone1_local_price + ' USD / km' : '-'}</p>
                            ${zone.zone1_local_price && currencyRate > 0 ? `<small class="text-muted">≈ ${(zone.zone1_local_price * currencyRate).toFixed(2)} ${currencyCode}</small>` : ''}
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">International Price</h6>
                            <p class="card-text fs-4 mb-0">${zone.zone1_international_price ? zone.zone1_international_price + ' USD / km' : '-'}</p>
                            ${zone.zone1_international_price && currencyRate > 0 ? `<small class="text-muted">≈ ${(zone.zone1_international_price * currencyRate).toFixed(2)} ${currencyCode}</small>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    } else if (zone.division_type === 2) {
        html = `
            <div class="row">
                <div class="col-md-6 mb-3">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">Zone A - Local</h6>
                            <p class="card-text mb-0">${zone.zone2_a_local_price ? zone.zone2_a_local_price + ' USD / km' : '-'}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 mb-3">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">Zone A - International</h6>
                            <p class="card-text mb-0">${zone.zone2_a_international_price ? zone.zone2_a_international_price + ' USD / km' : '-'}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 mb-3">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">Zone B - Local</h6>
                            <p class="card-text mb-0">${zone.zone2_b_local_price ? zone.zone2_b_local_price + ' USD / km' : '-'}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 mb-3">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">Zone B - International</h6>
                            <p class="card-text mb-0">${zone.zone2_b_international_price ? zone.zone2_b_international_price + ' USD / km' : '-'}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    } else if (zone.division_type === 4) {
        html = `
            <div class="row">
                <div class="col-md-6 mb-3">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">North - Local</h6>
                            <p class="card-text mb-0">${zone.zone4_north_local_price ? zone.zone4_north_local_price + ' USD / km' : '-'}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 mb-3">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">North - International</h6>
                            <p class="card-text mb-0">${zone.zone4_north_international_price ? zone.zone4_north_international_price + ' USD / km' : '-'}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 mb-3">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">South - Local</h6>
                            <p class="card-text mb-0">${zone.zone4_south_local_price ? zone.zone4_south_local_price + ' USD / km' : '-'}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 mb-3">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">South - International</h6>
                            <p class="card-text mb-0">${zone.zone4_south_international_price ? zone.zone4_south_international_price + ' USD / km' : '-'}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 mb-3">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">East - Local</h6>
                            <p class="card-text mb-0">${zone.zone4_east_local_price ? zone.zone4_east_local_price + ' USD / km' : '-'}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 mb-3">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">East - International</h6>
                            <p class="card-text mb-0">${zone.zone4_east_international_price ? zone.zone4_east_international_price + ' USD / km' : '-'}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 mb-3">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">West - Local</h6>
                            <p class="card-text mb-0">${zone.zone4_west_local_price ? zone.zone4_west_local_price + ' USD / km' : '-'}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 mb-3">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">West - International</h6>
                            <p class="card-text mb-0">${zone.zone4_west_international_price ? zone.zone4_west_international_price + ' USD / km' : '-'}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    pricingDisplayContent.innerHTML = html;
}

// Show empty state
function showEmptyState() {
    pricingZonesEmpty.classList.remove('d-none');
    pricingDisplayCard.classList.add('d-none');
    currentDivisionType.classList.add('d-none');
}

// Get division type text
function getDivisionTypeText(type) {
    switch(type) {
        case 1: return 'Single Zone';
        case 2: return 'Two Zones';
        case 4: return 'Four Zones';
        default: return 'Unknown';
    }
}

// Hide all pricing field groups
function hideAllPricingFields() {
    singleZoneFields.classList.add('d-none');
    twoZoneFields.classList.add('d-none');
    fourZoneFields.classList.add('d-none');
}

// Edit pricing zone
function editPricingZone(zoneId) {
    // Load zone data and populate form
    if (!pricingZonesListUrl) return;
    fetch(pricingZonesListUrl)
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                const zone = result.data.find(z => z.id == zoneId);
                if (zone) {
                    populateEditForm(zone);
                }
            }
        });
}

// Populate edit form
function populateEditForm(zone) {
    pricingZoneSetupForm.classList.remove('d-none');
    setupPricingZoneBtn.classList.add('d-none');
    editPricingZoneBtn.classList.add('d-none');
    
    formTitle.textContent = 'Edit Pricing Zone';
    savePricingZoneBtn.textContent = 'Update Pricing Zone';
    
    divisionTypeSelect.value = zone.division_type;
    divisionTypeSelect.disabled = false; // Allow changing division type
    divisionTypeSelect.dispatchEvent(new Event('change'));
    
    zoneIdInput.value = zone.id;
    
    // Populate pricing fields based on division type
    if (zone.division_type === 1) {
        document.getElementById('zone1_local_price').value = zone.zone1_local_price || '';
        document.getElementById('zone1_international_price').value = zone.zone1_international_price || '';
    } else if (zone.division_type === 2) {
        document.getElementById('zone2_a_local_price').value = zone.zone2_a_local_price || '';
        document.getElementById('zone2_a_international_price').value = zone.zone2_a_international_price || '';
        document.getElementById('zone2_b_local_price').value = zone.zone2_b_local_price || '';
        document.getElementById('zone2_b_international_price').value = zone.zone2_b_international_price || '';
    } else if (zone.division_type === 4) {
        document.getElementById('zone4_north_local_price').value = zone.zone4_north_local_price || '';
        document.getElementById('zone4_north_international_price').value = zone.zone4_north_international_price || '';
        document.getElementById('zone4_south_local_price').value = zone.zone4_south_local_price || '';
        document.getElementById('zone4_south_international_price').value = zone.zone4_south_international_price || '';
        document.getElementById('zone4_east_local_price').value = zone.zone4_east_local_price || '';
        document.getElementById('zone4_east_international_price').value = zone.zone4_east_international_price || '';
        document.getElementById('zone4_west_local_price').value = zone.zone4_west_local_price || '';
        document.getElementById('zone4_west_international_price').value = zone.zone4_west_international_price || '';
    }
    
    // Store initial values after populating
    setTimeout(() => {
        storeCurrentValues();
        previousDivisionType = zone.division_type;
    }, 100);
}
