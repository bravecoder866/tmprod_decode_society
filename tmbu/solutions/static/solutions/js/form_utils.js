/*
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.      
*/

//1. keep content form content using local storage

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('form').forEach(form => {
        const inputs = form.querySelectorAll('input, textarea');

        // Restore saved data
        inputs.forEach(input => {
            const savedValue = localStorage.getItem(`${form.name}-${input.name}`);
            if (savedValue) {
                input.value = savedValue;
            }

            // Save data on input change
            input.addEventListener('input', () => {
                if (input.value === '') {
                    localStorage.removeItem(`${form.name}-${input.name}`);
                } else {
                    localStorage.setItem(`${form.name}-${input.name}`, input.value);
                }
            });
        });

        // Clear data on form submission
        form.addEventListener('submit', () => {
            inputs.forEach(input => {
                localStorage.removeItem(`${form.name}-${input.name}`);
            });
        });
    });
});


// 2. form expands as typing

document.addEventListener("DOMContentLoaded", function () {
    function autoResizeTextarea(textarea) {
        const previousHeight = textarea.offsetHeight;
        textarea.style.height = "auto";
        textarea.style.height = textarea.scrollHeight + "px";
        
        const currentHeight = textarea.offsetHeight;
        const caretBottom = textarea.getBoundingClientRect().bottom;
        const viewportHeight = window.innerHeight;

        // If the bottom of textarea is beyond the viewport, scroll slightly
        if (caretBottom > viewportHeight) {
            window.scrollBy(0, currentHeight - previousHeight);
        }
    }

    // Apply auto-resize on all textareas
    document.querySelectorAll("textarea").forEach(textarea => {
        autoResizeTextarea(textarea); // Initial adjustment

        textarea.addEventListener("input", function () {
            autoResizeTextarea(this);
        });

        // Ensure textareas with pre-filled content expand properly on page load
        setTimeout(() => autoResizeTextarea(textarea), 100);
    });
});




// 3. Overlay on form submit

// Hide the overlay on initial page load or when returning via browser navigation
function hideOverlay() {
    document.getElementById('overlay').style.display = 'none';
}

document.addEventListener('DOMContentLoaded', hideOverlay);
window.addEventListener('pageshow', hideOverlay);

// Show overlay when form is submitted
document.addEventListener('DOMContentLoaded', function () {
    const allForms = document.querySelectorAll('form');
    allForms.forEach(form => {
        form.addEventListener('submit', function () {
            if (form.dataset.showOverlay === "true") {
                document.getElementById('overlay').style.display = 'block';
            }
        });
    });
});

