/**
 * Poetry Camera - Software Updates JavaScript
 */

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', () => {
    // Set up event listeners
    document.getElementById('btn-check-updates').addEventListener('click', checkForUpdates);
    document.getElementById('btn-apply-updates').addEventListener('click', () => openModal('update-modal'));
    document.getElementById('btn-confirm-update').addEventListener('click', applyUpdates);
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
                    <a class="button is-success mt-3" href="/system">Go to System tab to restart</a>
                </div>
            `;
            document.getElementById('btn-apply-updates').style.display = 'none';
            document.getElementById('update-commits').style.display = 'none';
            
            showNotification('Updates applied! Restart from the System tab to complete.', 'success');
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
