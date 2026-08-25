// Image preview functionality
const imageInput = document.getElementById('imageInput');
const imagePreview = document.getElementById('imagePreview');
const imagePlaceholder = document.getElementById('imagePlaceholder');
const imageDisplay = document.getElementById('imageDisplay');
const imageOverlay = document.getElementById('imageOverlay');
const changeImageBtn = document.getElementById('changeImageBtn');
const removeImageBtn = document.getElementById('removeImageBtn');

// Show overlay if image exists
if (imageDisplay && imageDisplay.src && !imageDisplay.classList.contains('d-none')) {
    imageOverlay.classList.remove('d-none');
}

// Click on preview to open file dialog
if (imagePreview) {
    imagePreview.addEventListener('click', function() {
        imageInput.click();
    });

    // Handle file selection
    imageInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                imageDisplay.src = e.target.result;
                imageDisplay.classList.remove('d-none');
                imagePlaceholder.classList.add('d-none');
                imageOverlay.classList.remove('d-none');
            }
            reader.readAsDataURL(file);
        }
    });

    // Change image button
    changeImageBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        imageInput.click();
    });

    // Remove image button
    removeImageBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        imageInput.value = '';
        imageDisplay.src = '';
        imageDisplay.classList.add('d-none');
        imagePlaceholder.classList.remove('d-none');
        imageOverlay.classList.add('d-none');
    });
}
