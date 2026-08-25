document.addEventListener('DOMContentLoaded', function() {
    const cityForm = document.getElementById('cityForm');

    if (cityForm) {
        cityForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const formData = new FormData(cityForm);
            const data = {};
            formData.forEach((value, key) => {
                if (value !== '' && key !== 'city_id') {
                    data[key] = value;
                }
            });

            // Convert numeric fields
            if (data.default_zoom) data.default_zoom = parseInt(data.default_zoom);
            if (data.population) data.population = parseInt(data.population);
            if (data.latitude) data.latitude = parseFloat(data.latitude);
            if (data.longitude) data.longitude = parseFloat(data.longitude);
            if (data.south) data.south = parseFloat(data.south);
            if (data.north) data.north = parseFloat(data.north);
            if (data.west) data.west = parseFloat(data.west);
            if (data.east) data.east = parseFloat(data.east);

            const cityId = cityForm.getAttribute('data-city-id');
            const countrySlug = cityForm.getAttribute('data-country-slug');

            const submitBtn = cityForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = 'Updating...';

            fetch(`/api/dashboard/countries/cities/${cityId}/update/`, {
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
                    showToast('City updated successfully!', 'success');
                    setTimeout(() => {
                        window.location.href = '/dashboard/countries/' + countrySlug + '/cities/' + result.data.slug + '/';
                    }, 1000);
                } else {
                    showToast(result.error || 'Error updating city', 'error');
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error updating city', 'error');
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            });
        });
    }
});
