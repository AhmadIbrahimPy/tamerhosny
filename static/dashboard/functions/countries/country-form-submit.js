// Country form submission handler
document.getElementById('countryForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const form = this;
    const formData = new FormData(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    const currencyCode = formData.get('curr');
    const currentRate = formData.get('rate_to_usd');
    const isEdit = form.getAttribute('data-form-type') === 'edit';
    const countryId = form.getAttribute('data-country-id');
    
    // Disable form and show loading
    const formInputs = form.querySelectorAll('input, button, select');
    formInputs.forEach(input => {
        input.disabled = true;
    });
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ' + (isEdit ? 'Updating...' : 'Creating...');
    
    // Function to submit the form
    const submitForm = () => {
        const data = {};
        
        // Convert FormData to JSON object
        for (let [key, value] of formData.entries()) {
            if (value && key !== 'image') {
                data[key] = value;
            }
        }
        
        // Convert numeric fields
        if (data.number_length) data.number_length = parseInt(data.number_length);
        if (data.latitude) data.latitude = parseFloat(data.latitude);
        if (data.longitude) data.longitude = parseFloat(data.longitude);
        if (data.south) data.south = parseFloat(data.south);
        if (data.north) data.north = parseFloat(data.north);
        if (data.west) data.west = parseFloat(data.west);
        if (data.east) data.east = parseFloat(data.east);
        if (data.rate_to_usd) data.rate_to_usd = parseFloat(data.rate_to_usd);
        if (data.default_zoom) data.default_zoom = parseInt(data.default_zoom);
        if (data.population) data.population = parseInt(data.population);
        
        // Handle file upload separately if needed
        if (formData.get('image') && formData.get('image').size > 0) {
            const fileFormData = new FormData();
            for (let [key, value] of formData.entries()) {
                fileFormData.append(key, value);
            }
            
            const url = isEdit ? `/api/dashboard/countries/${countryId}/update/` : '/api/dashboard/countries/create/';
            
            fetch(url, {
                method: 'POST',
                body: fileFormData
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    showToast(isEdit ? 'Country updated successfully!' : 'Country created successfully!', 'success');
                    setTimeout(() => {
                        if (isEdit) {
                            window.location.href = '/dashboard/countries/' + form.getAttribute('data-country-slug') + '/';
                        } else {
                            window.location.href = '/dashboard/countries/' + result.data.slug + '/';
                        }
                    }, 1500);
                } else {
                    showToast(result.error || 'Error saving country', 'error');
                    formInputs.forEach(input => {
                        input.disabled = false;
                    });
                    submitBtn.innerHTML = isEdit ? 'Update Country' : 'Create Country';
                }
            })
            .catch(error => {
                showToast('Error: ' + error, 'error');
                formInputs.forEach(input => {
                    input.disabled = false;
                });
                submitBtn.innerHTML = isEdit ? 'Update Country' : 'Create Country';
            });
        } else {
            // Submit as JSON
            const url = isEdit ? `/api/dashboard/countries/${countryId}/update/` : '/api/dashboard/countries/create/';
            
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
                    showToast(isEdit ? 'Country updated successfully!' : 'Country created successfully!', 'success');
                    setTimeout(() => {
                        if (isEdit) {
                            window.location.href = '/dashboard/countries/' + form.getAttribute('data-country-slug') + '/';
                        } else {
                            window.location.href = '/dashboard/countries/' + result.data.slug + '/';
                        }
                    }, 1500);
                } else {
                    showToast(result.error || 'Error saving country', 'error');
                    formInputs.forEach(input => {
                        input.disabled = false;
                    });
                    submitBtn.innerHTML = isEdit ? 'Update Country' : 'Create Country';
                }
            })
            .catch(error => {
                showToast('Error: ' + error, 'error');
                formInputs.forEach(input => {
                    input.disabled = false;
                });
                submitBtn.innerHTML = isEdit ? 'Update Country' : 'Create Country';
            });
        }
    };
    
    submitForm();
});
