/**
 * Poetry Camera - Settings JavaScript
 */

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', () => {
    // Set up event listeners
    document.getElementById('btn-save-printer').addEventListener('click', savePrinterSettings);
    document.getElementById('btn-save-openai').addEventListener('click', saveOpenAISettings);
    document.getElementById('btn-save-prompts').addEventListener('click', savePrompts);
    document.getElementById('btn-reset-prompts').addEventListener('click', () => openModal('reset-modal'));
    document.getElementById('btn-confirm-reset').addEventListener('click', resetPrompts);
    
    // Printer type change handler
    document.getElementById('printer-type').addEventListener('change', updatePrinterVisibility);
    
    // Initialize printer visibility
    updatePrinterVisibility();
});

// ==================== Printer Visibility ====================

function updatePrinterVisibility() {
    const printerType = document.getElementById('printer-type').value;
    const catSettings = document.getElementById('cat-printer-settings');
    const networkSettings = document.getElementById('network-printer-settings');
    
    if (printerType === 'cat_printer') {
        catSettings.style.display = 'block';
        networkSettings.style.display = 'none';
    } else if (printerType === 'network_printer') {
        catSettings.style.display = 'none';
        networkSettings.style.display = 'block';
    } else {
        // Both
        catSettings.style.display = 'block';
        networkSettings.style.display = 'block';
    }
}

// ==================== Save Printer Settings ====================

async function savePrinterSettings() {
    const btn = document.getElementById('btn-save-printer');
    
    const config = {
        type: document.getElementById('printer-type').value,
        cat_printer: {
            name: document.getElementById('cat-printer-name').value,
            mac_address: document.getElementById('cat-printer-mac').value
        },
        network_printer: {
            address: document.getElementById('network-printer-address').value,
            port: parseInt(document.getElementById('network-printer-port').value) || 9100
        }
    };
    
    setButtonLoading(btn, true);
    
    try {
        const result = await apiCall('/api/settings/printer', 'POST', config);
        
        if (result.success) {
            showNotification('Printer settings saved!', 'success');
        } else {
            showNotification(result.error || 'Failed to save settings', 'danger');
        }
    } catch (error) {
        showNotification('Error saving settings: ' + error.message, 'danger');
    } finally {
        setButtonLoading(btn, false);
    }
}

// ==================== Save OpenAI Settings ====================

async function saveOpenAISettings() {
    const btn = document.getElementById('btn-save-openai');
    
    const config = {
        model: document.getElementById('openai-model').value,
        poem_format: document.getElementById('poem-format').value
    };
    
    setButtonLoading(btn, true);
    
    try {
        const result = await apiCall('/api/settings/openai', 'POST', config);
        
        if (result.success) {
            showNotification('AI settings saved!', 'success');
        } else {
            showNotification(result.error || 'Failed to save settings', 'danger');
        }
    } catch (error) {
        showNotification('Error saving settings: ' + error.message, 'danger');
    } finally {
        setButtonLoading(btn, false);
    }
}

// ==================== Save Prompts ====================

async function savePrompts() {
    const btn = document.getElementById('btn-save-prompts');

    const config = {
        poem_prompt: document.getElementById('poem-prompt').value
    };

    setButtonLoading(btn, true);

    try {
        const result = await apiCall('/api/settings/openai', 'POST', config);

        if (result.success) {
            showNotification('Prompt saved!', 'success');
        } else {
            showNotification(result.error || 'Failed to save prompt', 'danger');
        }
    } catch (error) {
        showNotification('Error saving prompt: ' + error.message, 'danger');
    } finally {
        setButtonLoading(btn, false);
    }
}

// ==================== Reset Prompts ====================

async function resetPrompts() {
    const btn = document.getElementById('btn-confirm-reset');
    
    setButtonLoading(btn, true);
    
    try {
        const result = await apiCall('/api/settings/reset', 'POST', { section: 'openai' });
        
        if (result.success) {
            closeModal('reset-modal');
            showNotification('Prompts reset to defaults. Refreshing...', 'success');
            
            // Reload the page to get fresh defaults
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showNotification(result.error || 'Failed to reset prompts', 'danger');
        }
    } catch (error) {
        showNotification('Error resetting prompts: ' + error.message, 'danger');
    } finally {
        setButtonLoading(btn, false);
    }
}
