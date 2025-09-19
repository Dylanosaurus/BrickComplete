/**
 * Common JavaScript functions for BrickComplete
 * Shared functionality across multiple pages
 */

/**
 * Shows a custom delete confirmation dialog with "don't ask again" option
 * @param {string} itemName - The name of the item being deleted (optional)
 * @param {string} additionalMessage - Additional message to display (optional)
 * @returns {Promise<boolean>} - Promise that resolves to true if confirmed, false if cancelled
 */
function showDeleteConfirmation(itemName = '', additionalMessage = '') {
    return new Promise((resolve) => {
        // Create modal backdrop
        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop fade show';
        backdrop.style.zIndex = '1040';
        document.body.appendChild(backdrop);
        
        // Create modal
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.style.zIndex = '1050';
        
        // Build the confirmation message
        let message = 'Are you sure you want to delete this item?';
        if (itemName) {
            message = `Are you sure you want to delete "${itemName}"?`;
        }
        if (additionalMessage) {
            message += ` ${additionalMessage}`;
        }
        
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-exclamation-triangle text-warning"></i>
                            Confirm Deletion
                        </h5>
                    </div>
                    <div class="modal-body">
                        <p>${message}</p>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="dontAskAgain">
                            <label class="form-check-label" for="dontAskAgain">
                                Don't ask again
                            </label>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" id="cancelBtn">Cancel</button>
                        <button type="button" class="btn btn-danger" id="confirmBtn">Delete</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Add event listeners
        const cancelBtn = modal.querySelector('#cancelBtn');
        const confirmBtn = modal.querySelector('#confirmBtn');
        const dontAskCheckbox = modal.querySelector('#dontAskAgain');
        
        cancelBtn.addEventListener('click', () => {
            cleanup();
            resolve(false);
        });
        
        confirmBtn.addEventListener('click', () => {
            // Save preference if checkbox is checked
            if (dontAskCheckbox.checked) {
                localStorage.setItem('skipDeleteConfirmation', 'true');
            }
            cleanup();
            resolve(true);
        });
        
        // Close on backdrop click
        backdrop.addEventListener('click', () => {
            cleanup();
            resolve(false);
        });
        
        // Close on escape key
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                cleanup();
                resolve(false);
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
        
        function cleanup() {
            document.body.removeChild(modal);
            document.body.removeChild(backdrop);
            document.removeEventListener('keydown', handleEscape);
        }
        
        // Focus on confirm button
        confirmBtn.focus();
    });
}

/**
 * Checks if the user has chosen to skip delete confirmations
 * @returns {boolean} - True if user wants to skip confirmations
 */
function shouldSkipDeleteConfirmation() {
    return localStorage.getItem('skipDeleteConfirmation') === 'true';
}

/**
 * Shows a floating toast notification with auto-dismiss
 * @param {string} message - The message to display
 * @param {string} type - The alert type (success, danger, warning, info)
 * @param {number} duration - Auto-dismiss duration in milliseconds (default: 3000)
 */
function showAlert(message, type, duration = 3000) {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        console.error('Toast container not found');
        return;
    }

    const toastDiv = document.createElement('div');
    toastDiv.className = `toast-notification ${type}`;
    
    // Set icon based on type
    let iconClass;
    switch(type) {
        case 'success':
            iconClass = 'fas fa-check-circle';
            break;
        case 'danger':
            iconClass = 'fas fa-exclamation-circle';
            break;
        case 'warning':
            iconClass = 'fas fa-exclamation-triangle';
            break;
        case 'info':
            iconClass = 'fas fa-info-circle';
            break;
        default:
            iconClass = 'fas fa-check-circle';
    }
    
    toastDiv.innerHTML = `
        <div class="toast-content">
            <i class="toast-icon ${iconClass}"></i>
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="removeToast(this)">&times;</button>
        </div>
        <div class="toast-progress" style="animation-duration: ${duration}ms;"></div>
    `;
    
    // Add to container
    toastContainer.appendChild(toastDiv);
    
    // Auto-dismiss after specified duration
    setTimeout(() => {
        removeToast(toastDiv.querySelector('.toast-close'));
    }, duration);
}

/**
 * Shows a floating toast notification (same as showAlert for consistency)
 * @param {string} message - The message to display
 * @param {string} type - The alert type (success, danger, warning, info)
 * @param {string|Element} targetSelector - CSS selector or DOM element (ignored for floating toasts)
 * @param {number} duration - Auto-dismiss duration in milliseconds (default: 3000)
 */
function showAlertNear(message, type, targetSelector, duration = 3000) {
    // For consistency, showAlertNear now also uses floating toasts
    showAlert(message, type, duration);
}

/**
 * Removes a toast notification with animation
 * @param {Element} closeButton - The close button element
 */
function removeToast(closeButton) {
    const toast = closeButton.closest('.toast-notification');
    if (toast) {
        toast.style.animation = 'slideDownOut 0.3s ease-out';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 300);
    }
}
