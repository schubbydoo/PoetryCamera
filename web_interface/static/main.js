/**
 * Poetry Camera - Main JavaScript
 * Core utilities used across all pages
 */

// ==================== API Helper ====================

/**
 * Make an API call with proper error handling
 * @param {string} endpoint - API endpoint
 * @param {string} method - HTTP method (GET, POST, etc.)
 * @param {object} data - Request body data (for POST)
 * @returns {Promise<object>} - Response data
 */
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(endpoint, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Request failed');
        }
        
        return result;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ==================== Notifications ====================

/**
 * Show a notification message
 * @param {string} message - Message to display
 * @param {string} type - Notification type (success, danger, warning, info)
 * @param {number} duration - Auto-dismiss duration in ms (0 = no auto-dismiss)
 */
function showNotification(message, type = 'info', duration = 5000) {
    const container = document.querySelector('#flash-messages .container');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `notification is-${type} is-light`;
    notification.innerHTML = `
        <button class="delete"></button>
        ${escapeHtml(message)}
    `;
    
    container.appendChild(notification);
    
    // Add close handler
    notification.querySelector('.delete').addEventListener('click', () => {
        notification.remove();
    });
    
    // Auto-dismiss
    if (duration > 0) {
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);
    }
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} - Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== Button Loading State ====================

/**
 * Set button loading state
 * @param {HTMLElement} button - Button element
 * @param {boolean} loading - Whether button is loading
 */
function setButtonLoading(button, loading) {
    if (loading) {
        button.classList.add('is-loading');
        button.disabled = true;
    } else {
        button.classList.remove('is-loading');
        button.disabled = false;
    }
}

// ==================== Modal Management ====================

/**
 * Open a modal
 * @param {string} modalId - Modal element ID
 */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('is-active');
    }
}

/**
 * Close a modal
 * @param {string} modalId - Modal element ID
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('is-active');
    }
}

/**
 * Close all modals
 */
function closeAllModals() {
    document.querySelectorAll('.modal.is-active').forEach(modal => {
        modal.classList.remove('is-active');
    });
}

// ==================== Signal Strength Display ====================

/**
 * Create signal strength bars HTML
 * @param {number} signal - Signal strength (0-100)
 * @returns {string} - HTML for signal bars
 */
function createSignalBars(signal) {
    const bars = 4;
    const activeCount = Math.ceil((signal / 100) * bars);
    
    let html = '<div class="signal-bars">';
    for (let i = 1; i <= bars; i++) {
        const active = i <= activeCount ? 'active' : '';
        html += `<div class="signal-bar ${active}"></div>`;
    }
    html += '</div>';
    
    return html;
}

// ==================== DOM Ready Initialization ====================

document.addEventListener('DOMContentLoaded', () => {
    // Navbar burger toggle
    const navbarBurgers = document.querySelectorAll('.navbar-burger');
    navbarBurgers.forEach(burger => {
        burger.addEventListener('click', () => {
            const target = document.getElementById(burger.dataset.target);
            burger.classList.toggle('is-active');
            target.classList.toggle('is-active');
        });
    });
    
    // Auto-dismiss notifications after click
    document.querySelectorAll('.notification .delete').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.parentNode.remove();
        });
    });
    
    // Modal close handlers
    document.querySelectorAll('.modal-background, .modal .delete, .btn-cancel').forEach(el => {
        el.addEventListener('click', () => {
            const modal = el.closest('.modal');
            if (modal) {
                modal.classList.remove('is-active');
            }
        });
    });
    
    // Close modals on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });
    
    // Tab switching
    document.querySelectorAll('.tabs li').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.dataset.tab;
            if (!tabId) return;
            
            // Update tab active state
            tab.parentNode.querySelectorAll('li').forEach(t => t.classList.remove('is-active'));
            tab.classList.add('is-active');
            
            // Show/hide tab content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.style.display = 'none';
            });
            
            const targetContent = document.getElementById(tabId);
            if (targetContent) {
                targetContent.style.display = 'block';
            }
        });
    });
});

// ==================== Utility Functions ====================

/**
 * Debounce function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in ms
 * @returns {Function} - Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Format bytes to human readable string
 * @param {number} bytes - Number of bytes
 * @returns {string} - Formatted string
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
