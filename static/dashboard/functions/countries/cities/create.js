console.log('City creation script loaded');

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded');
    const cityForm = document.getElementById('cityForm');
    console.log('Form found:', cityForm);
    
    if (cityForm) {
        cityForm.addEventListener('submit', function(e) {
            console.log('Form submitted');
            e.preventDefault();
            e.stopPropagation();
            console.log('Default prevented');
            
            const formData = new FormData(cityForm);
            const data = {};
            formData.forEach((value, key) => {
                data[key] = value;
            });
            console.log('Form data:', data);

            // Convert numeric fields
            if (data.default_zoom) data.default_zoom = parseInt(data.default_zoom);
            if (data.population) data.population = parseInt(data.population);
            if (data.latitude) data.latitude = parseFloat(data.latitude);
            if (data.longitude) data.longitude = parseFloat(data.longitude);
            if (data.south) data.south = parseFloat(data.south);
            if (data.north) data.north = parseFloat(data.north);
            if (data.west) data.west = parseFloat(data.west);
            if (data.east) data.east = parseFloat(data.east);

            // Show loading state
            const submitBtn = cityForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = 'Creating...';
            
            console.log('Sending request to API');
            fetch('/api/dashboard/countries/cities/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(data)
            })
            .then(response => {
                console.log('Response received:', response);
                return response.json();
            })
            .then(result => {
                console.log('Result:', result);
                if (result.success) {
                    showToast('City created successfully!', 'success');
                    setTimeout(() => {
                        // Redirect to cities list
                        const countrySlug = document.querySelector('input[name="country_id"]').dataset.countrySlug;
                        console.log('Country slug:', countrySlug);
                        if (countrySlug) {
                            window.location.href = '/dashboard/countries/' + countrySlug + '/cities/';
                        } else {
                            window.location.href = '/dashboard/countries/cities/';
                        }
                    }, 1000);
                } else {
                    showToast(result.error || 'Error creating city', 'error');
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error creating city', 'error');
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            });
        });
    }
});
