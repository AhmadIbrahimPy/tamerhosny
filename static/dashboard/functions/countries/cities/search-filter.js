document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const clearSearch = document.getElementById('clearSearch');
    const filterButton = document.getElementById('filterButton');
    const filterPopup = document.getElementById('filterPopup');
    const applyFilters = document.getElementById('applyFilters');
    const clearFilters = document.getElementById('clearFilters');
    const closeFilterPopup = document.getElementById('closeFilterPopup');
    const activeFilters = document.getElementById('activeFilters');
    const tableBody = document.querySelector('tbody');
    
    // Get country_slug from URL: /dashboard/countries/{country_slug}/cities/ (scoped)
    // vs /dashboard/countries/cities/ (global list, no country segment)
    const urlParams = new URLSearchParams(window.location.search);
    const pathParts = window.location.pathname.split('/');
    const countrySlug = pathParts[3] && pathParts[3] !== 'cities' ? pathParts[3] : '';
    
    let currentFilters = {
        search: '',
        population_min: '',
        population_max: '',
        has_regions: '',
        created_after: '',
        created_before: ''
    };
    
    // Initialize from URL parameters
    function initializeFromURL() {
        currentFilters.search = urlParams.get('search') || '';
        currentFilters.population_min = urlParams.get('population_min') || '';
        currentFilters.population_max = urlParams.get('population_max') || '';
        currentFilters.has_regions = urlParams.get('has_regions') || '';
        currentFilters.created_after = urlParams.get('created_after') || '';
        currentFilters.created_before = urlParams.get('created_before') || '';
        
        // Update input values
        if (searchInput) searchInput.value = currentFilters.search;
        if (document.getElementById('filterPopulationMin')) document.getElementById('filterPopulationMin').value = currentFilters.population_min;
        if (document.getElementById('filterPopulationMax')) document.getElementById('filterPopulationMax').value = currentFilters.population_max;
        if (document.getElementById('filterHasRegions')) document.getElementById('filterHasRegions').value = currentFilters.has_regions;
        if (document.getElementById('filterCreatedAfter')) document.getElementById('filterCreatedAfter').value = currentFilters.created_after;
        if (document.getElementById('filterCreatedBefore')) document.getElementById('filterCreatedBefore').value = currentFilters.created_before;
        
        // Show active filters (only for filters, not search)
        updateActiveFilters();
        
        // Update clear search button visibility
        updateClearSearchButton();
        
        // Load initial data
        loadFilteredCities();
    }
    
    // Update URL with current filters (without reload)
    function updateURL() {
        const url = new URL(window.location);
        const params = new URLSearchParams();
        
        if (currentFilters.search) params.set('search', currentFilters.search);
        if (currentFilters.population_min) params.set('population_min', currentFilters.population_min);
        if (currentFilters.population_max) params.set('population_max', currentFilters.population_max);
        if (currentFilters.has_regions) params.set('has_regions', currentFilters.has_regions);
        if (currentFilters.created_after) params.set('created_after', currentFilters.created_after);
        if (currentFilters.created_before) params.set('created_before', currentFilters.created_before);
        
        url.search = params.toString();
        window.history.pushState({}, '', url);
    }
    
    // Update active filters display (only for filters, not search)
    function updateActiveFilters() {
        if (!activeFilters) return;
        
        activeFilters.innerHTML = '';
        let hasFilters = false;
        
        // Skip search - only show filter tags
        if (currentFilters.population_min) {
            hasFilters = true;
            const tag = createFilterTag('Population Min', currentFilters.population_min, 'population_min');
            activeFilters.appendChild(tag);
        }
        
        if (currentFilters.population_max) {
            hasFilters = true;
            const tag = createFilterTag('Population Max', currentFilters.population_max, 'population_max');
            activeFilters.appendChild(tag);
        }
        
        if (currentFilters.has_regions) {
            hasFilters = true;
            const tag = createFilterTag('Has Regions', currentFilters.has_regions === 'yes' ? 'Yes' : 'No', 'has_regions');
            activeFilters.appendChild(tag);
        }
        
        if (currentFilters.created_after) {
            hasFilters = true;
            const tag = createFilterTag('Created After', currentFilters.created_after, 'created_after');
            activeFilters.appendChild(tag);
        }
        
        if (currentFilters.created_before) {
            hasFilters = true;
            const tag = createFilterTag('Created Before', currentFilters.created_before, 'created_before');
            activeFilters.appendChild(tag);
        }
        
        if (hasFilters) {
            activeFilters.style.display = 'flex';
        } else {
            activeFilters.style.display = 'none';
        }
    }
    
    // Create filter tag
    function createFilterTag(label, value, filterKey) {
        const tag = document.createElement('span');
        tag.className = 'badge rounded-pill bg-primary text-white d-flex align-items-center gap-2 px-3 py-2';
        tag.style.fontSize = '0.875rem';
        tag.innerHTML = `
            <span>${label}: <strong>${value}</strong></span>
            <button type="button" class="btn-close btn-close-white" style="font-size: 0.6rem; padding: 0.25rem;" data-filter="${filterKey}"></button>
        `;
        
        const closeBtn = tag.querySelector('.btn-close');
        closeBtn.addEventListener('click', function() {
            currentFilters[filterKey] = '';
            updateURL();
            updateActiveFilters();
            loadFilteredCities();
        });
        
        return tag;
    }
    
    // Update clear search button visibility
    function updateClearSearchButton() {
        if (!clearSearch) return;
        
        if (currentFilters.search) {
            clearSearch.style.display = 'block';
        } else {
            clearSearch.style.display = 'none';
        }
    }
    
    // Load filtered cities via API (without page refresh)
    function loadFilteredCities() {
        if (!tableBody) return;
        
        // Show loading state
        tableBody.innerHTML = '<tr><td colspan="5" class="text-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></td></tr>';
        
        // Build API URL
        const apiUrl = new URL('/api/dashboard/countries/cities/filtered/', window.location.origin);
        if (countrySlug) apiUrl.searchParams.set('country_slug', countrySlug);
        if (currentFilters.search) apiUrl.searchParams.set('search', currentFilters.search);
        if (currentFilters.population_min) apiUrl.searchParams.set('population_min', currentFilters.population_min);
        if (currentFilters.population_max) apiUrl.searchParams.set('population_max', currentFilters.population_max);
        if (currentFilters.has_regions) apiUrl.searchParams.set('has_regions', currentFilters.has_regions);
        if (currentFilters.created_after) apiUrl.searchParams.set('created_after', currentFilters.created_after);
        if (currentFilters.created_before) apiUrl.searchParams.set('created_before', currentFilters.created_before);
        
        fetch(apiUrl)
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    renderCitiesTable(result.data);
                } else {
                    tableBody.innerHTML = '<tr><td colspan="5" class="text-center py-5 text-danger">' + (result.error || 'Error loading cities') + '</td></tr>';
                }
            })
            .catch(error => {
                console.error('Error loading filtered cities:', error);
                tableBody.innerHTML = '<tr><td colspan="5" class="text-center py-5 text-danger">Error loading cities</td></tr>';
            });
    }
    
    // Render cities table from API data
    function renderCitiesTable(citiesData) {
        if (!tableBody) return;
        
        if (citiesData.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center py-5 text-muted">No cities found</td></tr>';
            return;
        }
        
        tableBody.innerHTML = '';
        
        citiesData.forEach(city => {
            const row = document.createElement('tr');
            const cityUrl = `/dashboard/countries/${city.country_slug || ''}/cities/${city.slug}/`;
            row.innerHTML = `
                <td>
                    <a href="${cityUrl}" class="text-inherit">${city.name || '-'}</a>
                </td>
                <td>${city.country || '-'}</td>
                <td>${city.regions_count || 0}</td>
                <td>
                    <span class="badge ${city.auto_created ? 'bg-info' : 'bg-success'}">${city.auto_created ? 'Auto' : 'Manual'}</span>
                </td>
                <td>${city.created_at ? city.created_at.split(' ')[0] : '-'}</td>
            `;
            tableBody.appendChild(row);
        });
    }
    
    // Position filter popup next to filter button
    function positionFilterPopup() {
        if (!filterButton || !filterPopup) return;
        
        const buttonRect = filterButton.getBoundingClientRect();
        filterPopup.style.position = 'fixed';
        filterPopup.style.right = (window.innerWidth - buttonRect.left) + 'px';
        filterPopup.style.top = (buttonRect.bottom + 5) + 'px';
    }
    
    // Search input - load via API with debounce
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            currentFilters.search = this.value;
            updateActiveFilters();
            updateClearSearchButton();
            updateURL();
            // Debounce to avoid too many API calls
            clearTimeout(searchInput.searchTimeout);
            searchInput.searchTimeout = setTimeout(() => {
                loadFilteredCities();
            }, 500);
        });
    }
    
    // Clear search
    if (clearSearch) {
        clearSearch.addEventListener('click', function() {
            if (searchInput) searchInput.value = '';
            currentFilters.search = '';
            updateURL();
            updateActiveFilters();
            updateClearSearchButton();
            loadFilteredCities();
        });
    }
    
    // Toggle filter popup
    if (filterButton) {
        filterButton.addEventListener('click', function() {
            if (filterPopup) {
                if (filterPopup.style.display === 'none' || filterPopup.style.display === '') {
                    positionFilterPopup();
                    filterPopup.style.display = 'block';
                } else {
                    filterPopup.style.display = 'none';
                }
            }
        });
    }
    
    // Close filter popup
    if (closeFilterPopup) {
        closeFilterPopup.addEventListener('click', function() {
            if (filterPopup) filterPopup.style.display = 'none';
        });
    }
    
    // Apply filters
    if (applyFilters) {
        applyFilters.addEventListener('click', function() {
            currentFilters.population_min = document.getElementById('filterPopulationMin').value;
            currentFilters.population_max = document.getElementById('filterPopulationMax').value;
            currentFilters.has_regions = document.getElementById('filterHasRegions').value;
            currentFilters.created_after = document.getElementById('filterCreatedAfter').value;
            currentFilters.created_before = document.getElementById('filterCreatedBefore').value;
            
            updateActiveFilters();
            updateURL();
            loadFilteredCities();
            
            if (filterPopup) filterPopup.style.display = 'none';
        });
    }
    
    // Clear all filters
    if (clearFilters) {
        clearFilters.addEventListener('click', function() {
            currentFilters = {
                search: '',
                population_min: '',
                population_max: '',
                has_regions: '',
                created_after: '',
                created_before: ''
            };
            
            if (searchInput) searchInput.value = '';
            if (document.getElementById('filterPopulationMin')) document.getElementById('filterPopulationMin').value = '';
            if (document.getElementById('filterPopulationMax')) document.getElementById('filterPopulationMax').value = '';
            if (document.getElementById('filterHasRegions')) document.getElementById('filterHasRegions').value = '';
            if (document.getElementById('filterCreatedAfter')) document.getElementById('filterCreatedAfter').value = '';
            if (document.getElementById('filterCreatedBefore')) document.getElementById('filterCreatedBefore').value = '';
            
            updateActiveFilters();
            updateClearSearchButton();
            updateURL();
            loadFilteredCities();
            
            if (filterPopup) filterPopup.style.display = 'none';
        });
    }
    
    // Reposition on window resize
    window.addEventListener('resize', function() {
        if (filterPopup && filterPopup.style.display === 'block') {
            positionFilterPopup();
        }
    });
    
    // Initialize
    initializeFromURL();
});
