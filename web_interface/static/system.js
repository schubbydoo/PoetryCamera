/**
 * Poetry Camera - System Management JavaScript
 */

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', () => {
    // Set up event listeners
    document.getElementById('btn-check-updates').addEventListener('click', checkForUpdates);
    document.getElementById('btn-apply-updates').addEventListener('click', () => openModal('update-modal'));
    document.getElementById('btn-confirm-update').addEventListener('click', applyUpdates);
    document.getElementById('btn-reboot').addEventListener('click', () => openModal('reboot-modal'));
    document.getElementById('btn-confirm-reboot').addEventListener('click', rebootDevice);
});

// ==================== Check for Updates ====================

async function checkForUpdates() {
    const btn = document.getElementById('btn-check-updates');
    const statusDiv = document.getElementById('update-status');
    const commitsDiv = document.getElementById('update-commits');
    const applyBtn = document.getElementById('btn-apply-updates');
    
    setButtonLoading(btn, true);
    statusDiv.innerHTML = `
        <p class="has-text-info">
            <span class="icon"><i class="fas fa-spinner fa-spin"></i></span>
            Checking for updates...
        </p>
    `;
    commitsDiv.style.display = 'none';
    applyBtn.style.display = 'none';
    
    try {
        const result = await apiCall('/api/check_updates');
        
        if (result.success) {
            if (result.updates_available) {
                statusDiv.innerHTML = `
                    <p class="has-text-success">
                        <span class="icon"><i class="fas fa-gift"></i></span>
                        <strong>${result.commits_behind} update(s) available!</strong>
                    </p>
                `;
                
                // Show commit list
                if (result.commits && result.commits.length > 0) {
                    commitsDiv.querySelector('.commit-list').innerHTML = 
                        result.commits.map(commit => `<p>${escapeHtml(commit)}</p>`).join('');
                    commitsDiv.style.display = 'block';
                }
                
                applyBtn.style.display = 'inline-flex';
            } else {
                statusDiv.innerHTML = `
                    <p class="has-text-success">
                        <span class="icon"><i class="fas fa-check-circle"></i></span>
                        <strong>You're up to date!</strong> No updates available.
                    </p>
                `;
            }
        } else {
            statusDiv.innerHTML = `
                <p class="has-text-danger">
                    <span class="icon"><i class="fas fa-exclamation-circle"></i></span>
                    ${escapeHtml(result.error || 'Failed to check for updates')}
                </p>
            `;
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <p class="has-text-danger">
                <span class="icon"><i class="fas fa-exclamation-circle"></i></span>
                Error checking for updates: ${escapeHtml(error.message)}
            </p>
        `;
    } finally {
        setButtonLoading(btn, false);
    }
}

// ==================== Apply Updates ====================

async function applyUpdates() {
    const btn = document.getElementById('btn-confirm-update');
    const statusDiv = document.getElementById('update-status');
    
    setButtonLoading(btn, true);
    
    try {
        const result = await apiCall('/api/apply_updates', 'POST');
        
        closeModal('update-modal');
        
        if (result.success) {
            statusDiv.innerHTML = `
                <div class="notification is-success is-light">
                    <p><strong>Updates applied successfully!</strong></p>
                    <p class="mt-2">${escapeHtml(result.message)}</p>
                    <button class="button is-success mt-3" onclick="openModal('reboot-modal')">
                        <span class="icon"><i class="fas fa-power-off"></i></span>
                        <span>Reboot Now</span>
                    </button>
                </div>
            `;
            document.getElementById('btn-apply-updates').style.display = 'none';
            document.getElementById('update-commits').style.display = 'none';
            
            showNotification('Updates applied! Please reboot to complete.', 'success');
        } else {
            showNotification(result.error || 'Failed to apply updates', 'danger');
        }
    } catch (error) {
        closeModal('update-modal');
        showNotification('Error applying updates: ' + error.message, 'danger');
    } finally {
        setButtonLoading(btn, false);
    }
}

// ==================== Reboot Device ====================

async function rebootDevice() {
    const btn = document.getElementById('btn-confirm-reboot');
    
    setButtonLoading(btn, true);
    
    try {
        const result = await apiCall('/api/reboot', 'POST');
        
        if (result.success) {
            closeModal('reboot-modal');
            
            // Show rebooting message
            document.querySelector('.main-content .container').innerHTML = `
                <div class="has-text-centered py-6">
                    <span class="icon is-large has-text-warning">
                        <i class="fas fa-3x fa-spinner fa-spin"></i>
                    </span>
                    <h2 class="title is-4 mt-5">Rebooting...</h2>
                    <p class="has-text-grey">
                        The device is restarting. This page will attempt to reconnect automatically.
                    </p>
                    <p class="has-text-grey mt-2">
                        If it doesn't reconnect, please refresh the page in about 30 seconds.
                    </p>
                </div>
            `;
            
            // Try to reconnect after delay
            setTimeout(attemptReconnect, 15000);
        } else {
            showNotification(result.error || 'Failed to reboot', 'danger');
        }
    } catch (error) {
        showNotification('Error: ' + error.message, 'danger');
    } finally {
        setButtonLoading(btn, false);
    }
}

// ==================== Reconnect After Reboot ====================

let reconnectAttempts = 0;
const maxReconnectAttempts = 20;

async function attemptReconnect() {
    reconnectAttempts++;
    
    try {
        const response = await fetch('/api/status', { 
            method: 'GET',
            cache: 'no-cache'
        });
        
        if (response.ok) {
            // Device is back online
            window.location.reload();
            return;
        }
    } catch (error) {
        // Still offline
    }
    
    if (reconnectAttempts < maxReconnectAttempts) {
        // Try again in 3 seconds
        setTimeout(attemptReconnect, 3000);
    } else {
        // Give up, show manual refresh message
        document.querySelector('.main-content .container').innerHTML = `
            <div class="has-text-centered py-6">
                <span class="icon is-large has-text-warning">
                    <i class="fas fa-3x fa-exclamation-triangle"></i>
                </span>
                <h2 class="title is-4 mt-5">Reconnection Timeout</h2>
                <p class="has-text-grey">
                    Could not automatically reconnect to the device.
                </p>
                <button class="button is-primary mt-4" onclick="window.location.reload()">
                    <span class="icon"><i class="fas fa-sync-alt"></i></span>
                    <span>Refresh Page</span>
                </button>
            </div>
        `;
    }
}

// Helper function (also defined in main.js)
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
