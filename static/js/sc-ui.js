/**
 * OmicVerse Single Cell Analysis — UI Components, Navigation & Status
 */

Object.assign(SingleCellAnalysis.prototype, {

    setupNavigation() {
        // Setup navigation menu toggle functionality
        const navItems = document.querySelectorAll('.nxl-item.nxl-hasmenu');
        
        navItems.forEach(item => {
            const link = item.querySelector('.nxl-link');
            const submenu = item.querySelector('.nxl-submenu');
            
            if (link && submenu) {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.toggleSubmenu(item);
                });
            }
        });

        // Mobile menu toggle
        const mobileToggle = document.getElementById('mobile-collapse');

        if (mobileToggle) {
            mobileToggle.addEventListener('click', () => {
                this.toggleMobileMenu();
            });
        }
    },

    setupSidebarResize() {
        // JupyterLab-like resizable sidebar using CSS variables
        const handle = document.getElementById('sidebar-resize-handle');
        const sidebar = document.querySelector('.nxl-navigation');

        if (!handle || !sidebar) return;

        let isResizing = false;
        let startX = 0;
        let startWidth = 0;
        const minWidth = 200;  // Minimum sidebar width
        const maxWidth = 600;  // Maximum sidebar width

        // Function to update CSS variable for sidebar width
        const setSidebarWidth = (width) => {
            document.documentElement.style.setProperty('--sidebar-width', width + 'px');
        };

        handle.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;

            // Get current width from CSS variable
            const currentWidth = getComputedStyle(document.documentElement)
                .getPropertyValue('--sidebar-width');
            startWidth = parseInt(currentWidth);

            // Add visual feedback
            handle.classList.add('resizing');
            document.body.classList.add('resizing-sidebar');

            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;

            const delta = e.clientX - startX;
            const newWidth = Math.min(Math.max(startWidth + delta, minWidth), maxWidth);

            // Update CSS variable - this updates all elements using var(--sidebar-width)
            setSidebarWidth(newWidth);

            e.preventDefault();
        });

        document.addEventListener('mouseup', () => {
            if (!isResizing) return;

            isResizing = false;
            handle.classList.remove('resizing');
            document.body.classList.remove('resizing-sidebar');

            // Save the width to localStorage
            const currentWidth = getComputedStyle(document.documentElement)
                .getPropertyValue('--sidebar-width');
            localStorage.setItem('omicverse.sidebarWidth', parseInt(currentWidth));
        });

        // Restore saved width on load
        const savedWidth = localStorage.getItem('omicverse.sidebarWidth');
        if (savedWidth) {
            const width = parseInt(savedWidth);
            if (width >= minWidth && width <= maxWidth) {
                setSidebarWidth(width);
            }
        }
    },

    setupNotebookManager() {
        const fileInput = document.getElementById('notebook-file-input');
        if (!fileInput) return;
        fileInput.addEventListener('change', (e) => {
            const files = e.target.files;
            if (!files || files.length === 0) return;
            this.importNotebookFile(files[0]);
            fileInput.value = '';
        });
        this.fetchFileTree();
        this.fetchKernelStats();
        this.fetchKernelVars();
        document.addEventListener('click', () => this.hideContextMenu());
    },

    setupThemeToggle() {
        // Setup click handlers for existing theme toggle buttons
        const themeToggle = document.getElementById('theme-toggle');

        if (themeToggle) {
            themeToggle.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleTheme();
            });
        }
    },

    setupGeneAutocomplete() {
        const geneInput = document.getElementById('gene-input');
        const autocompleteDiv = document.getElementById('gene-autocomplete');

        if (!geneInput || !autocompleteDiv) return;

        let geneList = [];
        let selectedIndex = -1;

        // Fetch gene list when data is loaded
        const fetchGeneList = () => {
            if (!this.currentData) return;

            fetch('/api/genes')
                .then(response => response.json())
                .then(data => {
                    if (data.genes) {
                        geneList = data.genes;
                        this._geneList = data.genes; // store for custom-axes datalists

                        // Populate datalists for custom axes gene selection
                        const opts = data.genes.map(g => `<option value="${g}">`).join('');
                        ['x-axis-gene-datalist', 'y-axis-gene-datalist'].forEach(id => {
                            const dl = document.getElementById(id);
                            if (dl) dl.innerHTML = opts;
                        });
                    }
                })
                .catch(error => {
                    console.log('Failed to fetch gene list:', error);
                });
        };

        // Input event listener
        geneInput.addEventListener('input', (e) => {
            const value = e.target.value.trim().toLowerCase();
            selectedIndex = -1;

            if (value.length < 1) {
                autocompleteDiv.style.display = 'none';
                return;
            }

            if (geneList.length === 0) {
                fetchGeneList();
                return;
            }

            // Filter genes
            const matches = geneList.filter(gene =>
                gene.toLowerCase().includes(value)
            ).slice(0, 20); // Limit to 20 results

            if (matches.length === 0) {
                autocompleteDiv.style.display = 'none';
                return;
            }

            // Display matches
            autocompleteDiv.innerHTML = matches.map((gene, index) =>
                `<button type="button" class="list-group-item list-group-item-action" data-index="${index}" data-gene="${gene}">
                    ${gene}
                </button>`
            ).join('');
            autocompleteDiv.style.display = 'block';

            // Add click handlers
            autocompleteDiv.querySelectorAll('button').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const gene = e.currentTarget.getAttribute('data-gene');
                    geneInput.value = gene;
                    autocompleteDiv.style.display = 'none';
                    this.colorByGene();
                });
            });
        });

        // Keyboard navigation
        geneInput.addEventListener('keydown', (e) => {
            const items = autocompleteDiv.querySelectorAll('button');

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                updateSelection(items);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, -1);
                updateSelection(items);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (selectedIndex >= 0 && items[selectedIndex]) {
                    const gene = items[selectedIndex].getAttribute('data-gene');
                    geneInput.value = gene;
                    autocompleteDiv.style.display = 'none';
                    this.colorByGene();
                } else {
                    this.colorByGene();
                }
            } else if (e.key === 'Escape') {
                autocompleteDiv.style.display = 'none';
                selectedIndex = -1;
            }
        });

        const updateSelection = (items) => {
            items.forEach((item, index) => {
                if (index === selectedIndex) {
                    item.classList.add('active');
                    item.scrollIntoView({ block: 'nearest' });
                } else {
                    item.classList.remove('active');
                }
            });
        };

        // Close autocomplete when clicking outside
        document.addEventListener('click', (e) => {
            if (!geneInput.contains(e.target) && !autocompleteDiv.contains(e.target)) {
                autocompleteDiv.style.display = 'none';
                selectedIndex = -1;
            }
        });

        // Store reference for later use
        this.fetchGeneList = fetchGeneList;
    },

    setupBeforeUnloadWarning() {
        // Warn user before leaving/refreshing if data is loaded
        window.addEventListener('beforeunload', (e) => {
            if (this.currentData) {
                // Modern browsers require returnValue to be set
                e.preventDefault();
                // Chrome requires returnValue to be set
                e.returnValue = '';
                // Some browsers show a custom message (though most modern browsers ignore it)
                return this.t('status.beforeLeave');
            }
        });
    },

    toggleSubmenu(item) {
        const isOpen = item.classList.contains('open');
        
        // Close all other submenus
        document.querySelectorAll('.nxl-item.nxl-hasmenu.open').forEach(openItem => {
            if (openItem !== item) {
                openItem.classList.remove('open');
            }
        });
        
        // Toggle current submenu
        if (isOpen) {
            item.classList.remove('open');
        } else {
            item.classList.add('open');
        }
    },

    toggleMobileMenu() {
        const navigation = document.querySelector('.nxl-navigation');
        navigation.classList.toggle('open');
    },

    toggleTheme() {
        const html = document.documentElement;
        const icon = document.getElementById('theme-toggle-icon');
        
        if (html.classList.contains('app-skin-dark')) {
            // Switch to light mode
            html.classList.remove('app-skin-dark');
            localStorage.setItem('app-skin-dark', 'app-skin-light');
            this.currentTheme = 'light';
            if (icon) {
                icon.classList.remove('feather-sun');
                icon.classList.add('feather-moon');
            }
        } else {
            // Switch to dark mode
            html.classList.add('app-skin-dark');
            localStorage.setItem('app-skin-dark', 'app-skin-dark');
            this.currentTheme = 'dark';
            if (icon) {
                icon.classList.remove('feather-moon');
                icon.classList.add('feather-sun');
            }
        }
        
        // Update Plotly theme, status bar theme, and terminal theme
        this.updatePlotlyTheme();
        this.updateStatusBarTheme();
        if (this._termMgr) this._termMgr.updateTheme();
        // Update CodeMirror theme for .py editor
        if (this._cmEditor) {
            const dark = document.documentElement.classList.contains('app-skin-dark') ||
                         document.body.classList.contains('app-skin-dark');
            this._cmEditor.setOption('theme', dark ? 'dracula' : 'default');
        }
        if (this._mdEditor) {
            const dark = document.documentElement.classList.contains('app-skin-dark') ||
                         document.body.classList.contains('app-skin-dark');
            this._mdEditor.setOption('theme', dark ? 'dracula' : 'default');
        }
    },

    updateUI(data) {
        // ── Reset all controls when switching datasets ───────────────────────
        const geneInput = document.getElementById('gene-input');
        if (geneInput) geneInput.value = '';

        const paletteSelect = document.getElementById('palette-select');
        if (paletteSelect) paletteSelect.value = 'default';

        const catPaletteSelect = document.getElementById('category-palette-select');
        if (catPaletteSelect) catPaletteSelect.value = 'default';

        // Clear any stale Plotly chart from the previous dataset
        const plotDiv = document.getElementById('plotly-div');
        if (plotDiv && typeof Plotly !== 'undefined') Plotly.purge(plotDiv);
        // Reset axis tracking so next plot starts fresh
        this.currentEmbedding = '';
        this._currentAxesKey = undefined;
        this._currentAxisLabels = null;
        // Hide and reset the legend panel
        const legendPanel = document.getElementById('viz-legend-panel');
        const legendContent = document.getElementById('viz-legend-content');
        if (legendPanel) legendPanel.style.display = 'none';
        if (legendContent) legendContent.innerHTML = '';
        this._legendSelected = new Set();
        this._legendData = null;

        // Reset point-size slider to auto mode
        const sizeSlider = document.getElementById('point-size-slider');
        if (sizeSlider) sizeSlider.dataset.auto = 'true';
        const densitySlider = document.getElementById('density-adjust-slider');
        const densityLabel = document.getElementById('density-adjust-value');
        const densityToggle = document.getElementById('density-enable-toggle');
        if (densitySlider) densitySlider.value = 1;
        if (densityLabel) densityLabel.textContent = '1.00';
        if (densityToggle) densityToggle.checked = false;
        if (this._setDensityControlState) {
            this._setDensityControlState(false, this.t('controls.densityDisabledByToggle'));
        }

        // Hide palette visibility rows (will be re-evaluated after plot)
        this.updatePaletteVisibility('');

        // ── Hide upload section ──────────────────────────────────────────────
        document.getElementById('upload-section').style.display = 'none';

        // Show data status
        const statusDiv = document.getElementById('data-status');
        statusDiv.classList.remove('d-none');
        document.getElementById('filename-display').textContent = data.filename;
        document.getElementById('cell-count').textContent = data.n_cells;
        document.getElementById('gene-count').textContent = data.n_genes;

        // Show controls and visualization
        document.getElementById('viz-controls').style.display = 'block';
        document.getElementById('viz-panel').style.display = 'block';

        // Init collapsible cards that were inside hidden containers on page load
        requestAnimationFrame(() => {
            const vizCtrl = document.getElementById('viz-controls');
            if (vizCtrl) this.initCollapsibleCards(vizCtrl);
        });

        // Sync left-panel height to match data-status + viz-panel
        requestAnimationFrame(() => this.syncPanelHeight());

        // Initialise point-size slider to auto default for this dataset
        this.initPointSizeSlider();

        // Update embedding options
        // data.embeddings now contains actual obsm keys (e.g. 'X_umap', 'UMAP').
        // Use the full key as the option value so the backend can look it up
        // exactly; strip the leading 'X_' only for the human-readable label.
        const embeddingSelect = document.getElementById('embedding-select');
        embeddingSelect.innerHTML = `<option value="">${this.t('controls.embeddingPlaceholder')}</option>`;
        data.embeddings.forEach(emb => {
            const option = document.createElement('option');
            option.value = emb;
            option.textContent = (emb.startsWith('X_') ? emb.slice(2) : emb).toUpperCase();
            embeddingSelect.appendChild(option);
        });

        // Update color options
        const colorSelect = document.getElementById('color-select');
        colorSelect.innerHTML = `<option value="">${this.t('controls.colorNone')}</option>`;
        data.obs_columns.forEach(col => {
            const option = document.createElement('option');
            option.value = 'obs:' + col;
            option.textContent = col;
            colorSelect.appendChild(option);
        });

        // Populate custom axis key selectors (obsm + obs options)
        this._customAxesData = {
            embeddings:  data.embeddings   || [],
            obs_columns: data.obs_columns  || [],
            obsm_ndims:  data.obsm_ndims   || {},
        };
        this._populateAxisKeySels('x');
        this._populateAxisKeySels('y');

        // Reset custom axes state when data changes
        this._customAxesActive = false;
        const customRow  = document.getElementById('custom-axes-row');
        const badge      = document.getElementById('custom-axes-badge');
        const embSel     = document.getElementById('embedding-select');
        const icon       = document.getElementById('custom-axes-icon');
        if (customRow) customRow.style.display  = 'none';
        if (badge)     badge.style.display       = 'none';
        if (embSel)    embSel.style.display      = '';
        if (icon)      { icon.classList.remove('fa-undo'); icon.classList.add('fa-pen-alt'); }

        // Update parameter panel to enable buttons
        this.updateParameterPanel();
        if (this.fetchGeneList) {
            this.fetchGeneList();
        }

        // Fetch gene list for autocomplete
        if (this.fetchGeneList) {
            this.fetchGeneList();
        }

        // Reset parameter panel back to tool-list view (clear any open tool form)
        if (this.currentCategory) {
            this.selectAnalysisCategory(this.currentCategory, { silent: true });
        } else {
            this.showParameterPlaceholder();
        }

        // Restore persisted dynamic inputs (embedding, color, etc.)
        const _restoredDynamic = this.restoreDynamicInputs ? this.restoreDynamicInputs() : new Set();

        // Auto-select first embedding only if nothing was restored from cache
        if (!_restoredDynamic.has('embedding-select') && data.embeddings.length > 0) {
            embeddingSelect.value = data.embeddings[0];
        }
        // Sync custom axes to match current embedding ONLY if custom axes were NOT restored
        // (if custom axes were restored, they're already set up correctly)
        if (embeddingSelect.value && !this._customAxesActive) {
            this._syncCustomAxesToPreset(embeddingSelect.value);
        }
        // Restore renderer after a short delay (plot needs to exist first)
        setTimeout(() => { if (this.restoreRenderer) this.restoreRenderer(); }, 300);
        
        // Trigger plot update after a brief delay to ensure all DOM updates are complete
        // This is especially important for custom axes restoration, where UI elements
        // need to be populated before getXYAxes() can return valid values
        setTimeout(() => {
            if (this._syncDensityControlStateBySelection) this._syncDensityControlStateBySelection();
            this.updatePlot();
        }, 50);
    },

    refreshDataFromKernel(data) {
        if (!data) return;
        this.currentData = data;

        // Show viz panel and hide upload section (mirrors updateUI behaviour)
        const uploadSection = document.getElementById('upload-section');
        if (uploadSection) uploadSection.style.display = 'none';
        const vizPanel = document.getElementById('viz-panel');
        if (vizPanel) vizPanel.style.display = 'block';
        const vizControls = document.getElementById('viz-controls');
        if (vizControls) vizControls.style.display = 'block';

        const statusDiv = document.getElementById('data-status');
        if (statusDiv) statusDiv.classList.remove('d-none');
        const filenameDisplay = document.getElementById('filename-display');
        if (filenameDisplay) filenameDisplay.textContent = data.filename || '';
        const cellCount = document.getElementById('cell-count');
        if (cellCount) cellCount.textContent = data.n_cells;
        const geneCount = document.getElementById('gene-count');
        if (geneCount) geneCount.textContent = data.n_genes;

        const embeddingSelect = document.getElementById('embedding-select');
        const colorSelect = document.getElementById('color-select');
        const prevEmbedding = embeddingSelect ? embeddingSelect.value : '';
        const prevColor = colorSelect ? colorSelect.value : '';

        if (embeddingSelect) {
            embeddingSelect.innerHTML = `<option value="">${this.t('controls.embeddingPlaceholder')}</option>`;
            data.embeddings.forEach(emb => {
                const option = document.createElement('option');
                option.value = emb;
                option.textContent = (emb.startsWith('X_') ? emb.slice(2) : emb).toUpperCase();
                embeddingSelect.appendChild(option);
            });
            if (data.embeddings.includes(prevEmbedding)) {
                embeddingSelect.value = prevEmbedding;
            } else if (data.embeddings.length > 0) {
                embeddingSelect.value = data.embeddings[0];
            }
        }

        if (colorSelect) {
            colorSelect.innerHTML = `<option value="">${this.t('controls.colorNone')}</option>`;
            data.obs_columns.forEach(col => {
                const option = document.createElement('option');
                option.value = 'obs:' + col;
                option.textContent = col;
                colorSelect.appendChild(option);
            });
            if (prevColor && prevColor.startsWith('obs:')) {
                const rawCol = prevColor.replace('obs:', '');
                if (data.obs_columns.includes(rawCol)) {
                    colorSelect.value = prevColor;
                }
            }
        }

        this.updateParameterPanel();

        if (embeddingSelect && embeddingSelect.value) {
            if (this.currentView === 'visualization') {
                this.updatePlot();
                this.pendingPlotRefresh = false;
            } else {
                this.pendingPlotRefresh = true;
            }
        }

        // Keep adata status panel in sync
        this.updateAdataStatus(data);
    },

    updateParameterPanel() {
        // Re-enable all parameter buttons now that data is loaded
        const buttons = document.querySelectorAll('#parameter-content button');
        buttons.forEach(button => {
            if (!button.onclick || !button.onclick.toString().includes('showComingSoon')) {
                button.disabled = false;
            }
        });
    },

    updatePlotlyTheme() {
        // If there's an existing plot, update it with new theme
        const plotDiv = document.getElementById('plotly-div');
        if (plotDiv && plotDiv.data) {
            const layout = this.getPlotlyLayout();
            const current = plotDiv.layout || {};
            if (current.xaxis && Array.isArray(current.xaxis.range) && current.xaxis.range.length === 2) {
                layout.xaxis = layout.xaxis || {};
                layout.xaxis.autorange = false;
                layout.xaxis.range = current.xaxis.range.slice();
            }
            if (current.yaxis && Array.isArray(current.yaxis.range) && current.yaxis.range.length === 2) {
                layout.yaxis = layout.yaxis || {};
                layout.yaxis.autorange = false;
                layout.yaxis.range = current.yaxis.range.slice();
            }
            Plotly.relayout(plotDiv, layout);
        }
    },

    syncPanelHeight() {
        const leftMain    = document.getElementById('left-main-panel');
        const dataStatus  = document.getElementById('data-status');
        const vizPanel    = document.getElementById('viz-panel');
        const adataCard   = document.getElementById('adata-status-section');
        if (!leftMain || !vizPanel) return;

        // If adata-status is collapsed (flex shrunken to auto), let the left
        // panel shrink naturally so the Analysis-Status card moves up and no
        // blank space remains at the bottom.
        const adataCollapsed = adataCard &&
            adataCard.querySelector('.card-collapse-btn.collapsed') !== null;

        if (adataCollapsed) {
            leftMain.style.minHeight = '';
            return;
        }

        const dsH = (dataStatus && !dataStatus.classList.contains('d-none'))
            ? dataStatus.offsetHeight : 0;
        const vpH = vizPanel.offsetHeight;
        leftMain.style.minHeight = (dsH + vpH > 0) ? (dsH + vpH) + 'px' : '';
    },

    checkStatus() {
        fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            if (!data.loaded) return;
            // Guard: ensure the response has the fields updateUI needs
            if (!Array.isArray(data.embeddings)) {
                console.warn('checkStatus: /api/status response missing embeddings field', data);
                return;
            }
            // Restore preview mode flag from server state
            this.isPreviewMode = !!data.preview_mode;
            // Server has adata in memory — restore full UI without re-uploading
            this.currentData = data;
            this.updateUI(data);
            this.updateAdataStatus(data);
            this.updatePreviewModeBanner(this.isPreviewMode);
            requestAnimationFrame(() => this.syncPanelHeight());
            this.addToLog(
                `${this.t('upload.successDetail')}: ${data.n_cells} ${this.t('status.cells')}, ${data.n_genes} ${this.t('status.genes')}`
            );
        })
        .catch(err => { console.warn('checkStatus error:', err); });
    },

    showLoading(text = null) {
        const loadingText = document.getElementById('loading-text');
        const loadingOverlay = document.getElementById('loading-overlay');

        const resolved = text || this.t('loading.processing');
        if (loadingText) loadingText.textContent = resolved;
        if (loadingOverlay) loadingOverlay.style.display = 'flex';
    },

    hideLoading() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) loadingOverlay.style.display = 'none';
    },

    addToLog(message, type = 'info') {
        const log = document.getElementById('analysis-log');
        if (!log) return;

        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');

        if (type === 'error') {
            logEntry.className = 'mb-1 text-danger';
            logEntry.innerHTML = `<small class="text-muted">[${timestamp}]</small> ${message}`;
        } else if (type === 'stdout') {
            // Render captured Python print output as monospace terminal block
            logEntry.className = 'mb-1';
            const pre = document.createElement('pre');
            pre.style.cssText = [
                'font-size:0.75rem',
                'margin:2px 0 2px 0',
                'padding:4px 8px',
                'background:var(--bs-light, #f8f9fa)',
                'border-left:3px solid #6c757d',
                'border-radius:0 4px 4px 0',
                'white-space:pre-wrap',
                'word-break:break-all',
                'color:#495057',
                'cursor:text',
                'user-select:text',
                '-webkit-user-select:text'
            ].join(';');
            pre.textContent = message;
            logEntry.appendChild(pre);
        } else {
            logEntry.className = 'mb-1 text-dark';
            logEntry.innerHTML = `<small class="text-muted">[${timestamp}]</small> ${message}`;
        }

        log.appendChild(logEntry);
        log.scrollTop = log.scrollHeight;
    },

    showStatus(message, showSpinner = false) {
        const statusBar = document.getElementById('status-bar');
        const statusText = document.getElementById('status-text');
        const statusSpinner = document.getElementById('status-spinner');
        const statusTime = document.getElementById('status-time');
        
        if (!statusBar || !statusText || !statusSpinner || !statusTime) return;
        
        // 应用主题样式
        this.updateStatusBarTheme();
        
        statusText.textContent = message;
        statusTime.textContent = new Date().toLocaleTimeString();
        
        if (showSpinner) {
            statusSpinner.style.display = 'inline-block';
        } else {
            statusSpinner.style.display = 'none';
        }
        
        statusBar.style.display = 'block';
    },

    hideStatus() {
        const statusBar = document.getElementById('status-bar');
        if (statusBar) {
            statusBar.style.display = 'none';
        }
    },

    updateStatus(message, showSpinner = false) {
        const statusText = document.getElementById('status-text');
        const statusSpinner = document.getElementById('status-spinner');
        const statusTime = document.getElementById('status-time');
        
        if (!statusText || !statusSpinner || !statusTime) return;
        
        statusText.textContent = message;
        statusTime.textContent = new Date().toLocaleTimeString();
        
        if (showSpinner) {
            statusSpinner.style.display = 'inline-block';
        } else {
            statusSpinner.style.display = 'none';
        }
    },

    updateStatusBarTheme() {
        const statusBar = document.getElementById('status-bar');
        const statusText = document.getElementById('status-text');
        const statusTime = document.getElementById('status-time');
        
        if (!statusBar || !statusText || !statusTime) return;
        
        const isDark = document.documentElement.classList.contains('app-skin-dark');
        
        if (isDark) {
            statusBar.style.backgroundColor = '#1f2937';
            statusBar.style.borderColor = '#374151';
            statusText.style.color = '#e5e7eb';
            statusTime.style.color = '#9ca3af';
        } else {
            statusBar.style.backgroundColor = '#ffffff';
            statusBar.style.borderColor = '#e5e7eb';
            statusText.style.color = '#283c50';
            statusTime.style.color = '#6b7280';
        }
    },

    showComingSoon() {
        alert(this.t('common.comingSoon'));
    },

    showPreviewModeAlert() {
        alert(this.t('preview.toolDisabledAlert') ||
            '⚠️ 预览模式下无法进行分析操作。\n\n如需分析，请点击数据状态栏中的「切换分析读取」按钮，\n以完整加载模式重新打开文件。');
    },

    switchView(view) {
        if (view === 'gateway' && typeof this.canAccessGateway === 'function' && !this.canAccessGateway()) {
            if (typeof this.updateGatewayAccess === 'function') {
                this.updateGatewayAccess({ redirectIfBlocked: false });
            }
            if (typeof this.openAuthModal === 'function') {
                this.openAuthModal('login');
            }
            return;
        }

        this.currentView = view;
        this.persistView(view); // persist across refreshes

        const vizView      = document.getElementById('visualization-view');
        const codeView     = document.getElementById('code-editor-view');
        const agentView    = document.getElementById('agent-view');
        const skillsView   = document.getElementById('skills-view');
        const accountView  = document.getElementById('account-view');
        const termView     = document.getElementById('terminal-view');
        const gatewayView  = document.getElementById('gateway-view');
        const vizBtn       = document.getElementById('view-viz-btn');
        const codeBtn      = document.getElementById('view-code-btn');
        const agentBtn     = document.getElementById('view-agent-btn');
        const skillsBtn    = document.getElementById('view-skills-btn');
        const termBtn      = document.getElementById('view-terminal-btn');
        const gatewayBtn   = document.getElementById('view-gateway-btn');
        const vizToolbar   = document.getElementById('viz-toolbar');
        const codeToolbarRow = document.getElementById('code-editor-toolbar-row');
        const pageTitle    = document.getElementById('page-title');
        const breadcrumbTitle = document.getElementById('breadcrumb-title');
        const analysisNav  = document.getElementById('analysis-nav');
        const agentConfigNav = document.getElementById('agent-config-nav');
        const skillsStoreNav = document.getElementById('skills-store-nav');
        const gatewayNav   = document.getElementById('gateway-nav');
        const fileManager  = document.getElementById('file-manager');
        const termNavPanel = document.getElementById('term-nav-panel');
        const navbarContent = document.querySelector('.navbar-content');

        // ── helper: reset all tab buttons to outline ──────────────────────
        const _deactivateAll = () => {
            [vizBtn, codeBtn, agentBtn, skillsBtn, termBtn, gatewayBtn].forEach(b => {
                if (!b) return;
                b.classList.remove('btn-primary');
                b.classList.add('btn-outline-primary');
            });
        };

        // Hide all views first
        [vizView, codeView, agentView, skillsView, accountView, termView, gatewayView].forEach(v => { if (v) v.style.display = 'none'; });
        _deactivateAll();
        if (vizToolbar)    vizToolbar.style.display    = 'none';
        if (codeToolbarRow) codeToolbarRow.style.display = 'none';
        if (analysisNav)   analysisNav.style.display   = 'none';
        if (agentConfigNav) agentConfigNav.style.display = 'none';
        if (skillsStoreNav) skillsStoreNav.style.display = 'none';
        if (gatewayNav)    gatewayNav.style.display    = 'none';
        if (fileManager)   fileManager.style.display   = 'none';
        // Hide terminal nav panel and restore navbar-content for non-terminal views
        if (termNavPanel)  termNavPanel.style.display  = 'none';
        if (navbarContent) navbarContent.style.display = '';
        // editor-tabs only belongs to the code view
        const editorTabs = document.getElementById('editor-tabs');
        if (editorTabs) editorTabs.style.display = 'none';

        // Toggle body class so CSS can zero out main-content padding in code view
        document.body.classList.toggle('view-code-active', view === 'code');

        if (view === 'visualization') {
            if (vizView) vizView.style.display = 'block';
            if (vizBtn)  { vizBtn.classList.remove('btn-outline-primary'); vizBtn.classList.add('btn-primary'); }
            if (vizToolbar) vizToolbar.style.display = 'flex';
            if (analysisNav) analysisNav.style.display = 'block';

            window.scrollTo({ top: 0, behavior: 'smooth' });
            if (pageTitle) pageTitle.textContent = this.t('breadcrumb.title');
            if (breadcrumbTitle) breadcrumbTitle.textContent = this.t('breadcrumb.title');

            if (this.pendingPlotRefresh) {
                const embeddingSelect = document.getElementById('embedding-select');
                if (embeddingSelect && embeddingSelect.value) this.updatePlot();
                this.pendingPlotRefresh = false;
            }

        } else if (view === 'code') {
            if (codeView) codeView.style.display = 'block';
            if (codeBtn)  { codeBtn.classList.remove('btn-outline-primary'); codeBtn.classList.add('btn-primary'); }
            if (codeToolbarRow) codeToolbarRow.style.display = 'flex';
            if (this.renderTabs) this.renderTabs();
            if (fileManager) fileManager.style.display = 'block';

            if (pageTitle) pageTitle.innerHTML = `<i class="feather-code me-2"></i>${this.t('view.codeTitle')}`;
            if (breadcrumbTitle) breadcrumbTitle.textContent = this.t('breadcrumb.code');

            if (!this.fileTreeLoaded) { this.fetchFileTree(); this.fileTreeLoaded = true; }
            this.fetchKernelStats();
            this.fetchKernelVars();
            if (this.currentData) fetch('/api/kernel/sync_odata', { method: 'POST' }).catch(() => {});
            if (this.openTabs.length === 0) this.openFileFromServer('default.ipynb');
            if (this.codeCells.length === 0) this.addCodeCell();

        } else if (view === 'terminal') {
            if (termView) termView.style.display = 'block';
            if (termBtn)  { termBtn.classList.remove('btn-outline-primary'); termBtn.classList.add('btn-primary'); }

            if (pageTitle) pageTitle.innerHTML = `<i class="feather-terminal me-2"></i>${this.t('terminal.label')}`;
            if (breadcrumbTitle) breadcrumbTitle.textContent = this.t('terminal.label');

            // Swap left sidebar: hide normal nav, show terminal session list
            if (navbarContent) navbarContent.style.display = 'none';
            if (termNavPanel)  termNavPanel.style.display  = 'flex';
            if (window.feather) feather.replace({ 'stroke-width': 2 });

            // Lazily create and open the terminal on first visit
            this.openTerminalView();

        } else if (view === 'agent') {
            if (agentView) agentView.style.display = 'block';
            if (agentBtn)  { agentBtn.classList.remove('btn-outline-primary'); agentBtn.classList.add('btn-primary'); }
            if (agentConfigNav) agentConfigNav.style.display = 'block';

            if (pageTitle) pageTitle.innerHTML = `<i class="feather-message-circle me-2"></i>${this.t('view.agentTitle')}`;
            if (breadcrumbTitle) breadcrumbTitle.textContent = this.t('breadcrumb.agent');
        } else if (view === 'skills') {
            if (skillsView) skillsView.style.display = 'block';
            if (skillsBtn)  { skillsBtn.classList.remove('btn-outline-primary'); skillsBtn.classList.add('btn-primary'); }
            if (skillsStoreNav) skillsStoreNav.style.display = 'block';

            if (pageTitle) pageTitle.innerHTML = `<i class="feather-grid me-2"></i>${this.t('view.skillsTitle')}`;
            if (breadcrumbTitle) breadcrumbTitle.textContent = this.t('view.skillsTitle');
            this.loadSkills();
        } else if (view === 'account') {
            if (accountView) accountView.style.display = 'block';
            if (pageTitle) pageTitle.innerHTML = `<i class="feather-user me-2"></i>${this.t('view.accountTitle')}`;
            if (breadcrumbTitle) breadcrumbTitle.textContent = this.t('breadcrumb.account');
            if (this.renderAccountCenter) this.renderAccountCenter();
        } else if (view === 'gateway') {
            if (gatewayView) gatewayView.style.display = 'block';
            if (gatewayBtn)  { gatewayBtn.classList.remove('btn-outline-primary'); gatewayBtn.classList.add('btn-primary'); }
            if (gatewayNav)  gatewayNav.style.display = 'block';
            if (pageTitle) pageTitle.innerHTML = `<i class="feather-share-2 me-2"></i>${this.t('view.gatewayTitle')}`;
            if (breadcrumbTitle) breadcrumbTitle.textContent = this.t('breadcrumb.gateway');
            // Load data if first visit or if refresh requested
            if (!this._gatewayLoaded) {
                this._gatewayActiveTab = 'overview';
                this.refreshGateway();
            }
        }
    },

    // ── Gateway Panel ──────────────────────────────────────────────────────

    _gatewayLoaded: false,
    _gatewayActiveTab: 'overview',
    _gatewayAutoRefreshTimer: null,
    _gatewayFolders: [],
    _gwChannelUIState: {},

    showGatewayTab(tab) {
        this._gatewayActiveTab = tab;
        ['overview', 'channels', 'sessions', 'memory'].forEach(t => {
            const pane = document.getElementById(`gw-tab-${t}`);
            const link = document.getElementById(`gw-nav-${t}`);
            if (pane) pane.style.display = t === tab ? '' : 'none';
            if (link) {
                link.classList.toggle('active', t === tab);
                // highlight active item
                link.style.fontWeight = t === tab ? '600' : '';
                link.style.color = t === tab ? 'var(--bs-primary)' : '';
            }
        });
        if (tab === 'memory' && !this._gatewayMemoryLoaded) {
            this._loadMemoryData();
        }
        if (tab === 'channels') {
            if (this._gwConfig) {
                this._refreshChannelStates();
            } else {
                this.loadChannelConfig();
            }
        }
    },

    refreshGateway() {
        this._gatewayLoaded = true;
        this._loadGatewayStatus();
        if (!this._gatewayAutoRefreshTimer) {
            this._gatewayAutoRefreshTimer = setInterval(() => {
                if (this._gatewayLoaded) this.refreshGateway();
            }, 5000);
        }
        if (this._gatewayActiveTab === 'memory') {
            this._loadMemoryData();
        }
        if (this._gatewayActiveTab === 'channels') {
            if (this._gwConfig) {
                this._refreshChannelStates();
            } else {
                this.loadChannelConfig();
            }
        }
    },

    _loadGatewayStatus() {
        // Load overview stats + channel/session lists in parallel
        Promise.all([
            fetch('/api/gateway/status').then(r => r.ok ? r.json() : null).catch(() => null),
            fetch('/api/gateway/sessions').then(r => r.ok ? r.json() : null).catch(() => null),
            fetch('/api/gateway/memory/stats').then(r => r.ok ? r.json() : null).catch(() => null),
        ]).then(([status, sessions, memStats]) => {
            this._renderGatewayOverview(status, sessions, memStats);
            this._renderGatewayChannels(status);
            this._renderGatewaySessions(sessions);
        });
    },

    _refreshChannelStates() {
        fetch('/api/gateway/channels/processes')
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data && Array.isArray(data.processes)) {
                    this._gwProcesses = data.processes;
                    this._renderChannelCards();
                }
            })
            .catch(() => {});
    },

    _gatewayStatusTheme(status) {
        const s = status || 'stopped';
        if (s === 'running') {
            return { bg: 'var(--bs-success-bg-subtle,#d1e7dd)', color: 'var(--bs-success-text,#0a3622)', label: this.t('gateway.status.running') };
        }
        if (s === 'starting') {
            return { bg: 'var(--bs-warning-bg-subtle,#fff3cd)', color: 'var(--bs-warning-text,#664d03)', label: this.t('gateway.status.starting') };
        }
        if (s === 'failed') {
            return { bg: 'var(--bs-danger-bg-subtle,#f8d7da)', color: 'var(--bs-danger-text,#842029)', label: this.t('gateway.status.failed') };
        }
        if (s === 'not_configured') {
            return { bg: 'var(--bs-dark-bg-subtle,#ced4da)', color: 'var(--bs-dark-text,#212529)', label: this.t('gateway.status.notConfigured') };
        }
        return { bg: 'var(--bs-secondary-bg-subtle,#e9ecef)', color: 'var(--bs-secondary-text,#495057)', label: s === 'stopped' ? this.t('gateway.status.stopped') : s };
    },

    _renderGatewayOverview(status, sessions, memStats) {
        const channels = (status && status.channels) ? status.channels : [];
        const activeChannels = channels.filter(ch => (typeof ch === 'object' ? (ch.status || 'connected') : 'connected') !== 'not_configured');
        const sessionList = (sessions && sessions.sessions) ? sessions.sessions : [];
        const memDocs = (memStats && memStats.total_documents != null) ? memStats.total_documents : '—';

        const el = id => document.getElementById(id);
        if (el('gw-stat-channels')) el('gw-stat-channels').textContent = activeChannels.length;
        if (el('gw-stat-sessions')) el('gw-stat-sessions').textContent = sessionList.length;
        if (el('gw-stat-memories')) el('gw-stat-memories').textContent = memDocs;

        // message count
        let msgCount = 0;
        sessionList.forEach(s => { msgCount += (s.message_count || 0); });
        if (el('gw-stat-messages')) el('gw-stat-messages').textContent = msgCount;

        // Status detail
        const detail = el('gw-status-detail');
        if (detail) {
            if (!status) {
                detail.innerHTML = `<span class="text-warning"><i class="feather-alert-circle me-1"></i>${this.t('gateway.webOnlyMode')}</span>`;
            } else {
                detail.innerHTML = `
                    <div class="row g-2">
                        ${channels.map(ch => {
                            const chName = (typeof ch === 'string') ? ch : (ch.name || ch.channel || '?');
                            const chStatus = (typeof ch === 'object') ? (ch.status || 'connected') : 'connected';
                            const theme = this._gatewayStatusTheme(chStatus);
                            const sesCount = (typeof ch === 'object') ? (ch.session_count || 0) : 0;
                            return `
                        <div class="col-auto">
                            <span class="badge" style="background:${theme.bg};color:${theme.color};font-size:0.82rem;padding:5px 10px;">
                                <i class="feather-radio me-1"></i>${chName}
                                <span class="ms-1 opacity-75">${chStatus === 'running' ? sesCount + ' ' + this.t('gateway.sessionsShort') : theme.label}</span>
                            </span>
                        </div>`;}).join('') || `<div class="text-muted small">${this.t('gateway.noChannelsConnected')}</div>`}
                    </div>
                    ${status.version ? `<div class="mt-2 text-muted small">${this.t('view.gatewayTitle')} v${status.version}</div>` : ''}
                `;
            }
        }
    },

    _renderGatewayChannels(status) {
        const el = document.getElementById('gw-channels-list');
        if (!el) return;
        const channels = (status && status.channels) ? status.channels : [];
        if (!channels.length) {
            el.innerHTML = `
                <div class="text-center py-5 text-muted">
                    <i class="feather-radio" style="font-size:2.5rem;opacity:.35;display:block;margin-bottom:12px;"></i>
                    <p>${this.t('gateway.noChannelsConnected')}<br><small>${this.t('gateway.noChannelsHint')}</small></p>
                </div>`;
            return;
        }
        el.innerHTML = `<div class="row g-3">${channels.map(ch => {
            const name = typeof ch === 'string' ? ch : (ch.name || ch.channel || JSON.stringify(ch));
            const status = typeof ch === 'object' ? (ch.status || 'connected') : 'connected';
            const sessions = typeof ch === 'object' ? (ch.session_count || 0) : 0;
            const theme = this._gatewayStatusTheme(status);
            return `
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-2">
                            <span class="badge me-2" style="background:${theme.bg};color:${theme.color};">${theme.label}</span>
                            <span class="fw-semibold text-capitalize">${name}</span>
                        </div>
                        <div class="text-muted small"><i class="feather-users me-1"></i>${sessions} ${this.t('gateway.sessionsLower')}</div>
                    </div>
                </div>
            </div>`;
        }).join('')}</div>`;
    },

    _renderGatewaySessions(sessionsData) {
        const el = document.getElementById('gw-sessions-list');
        if (!el) return;
        const sessions = (sessionsData && sessionsData.sessions) ? sessionsData.sessions : [];
        if (!sessions.length) {
            el.innerHTML = `<div class="text-muted text-center py-5"><i class="feather-users" style="font-size:2.5rem;opacity:.35;display:block;margin-bottom:12px;"></i><p>${this.t('gateway.noActiveSessions')}</p></div>`;
            return;
        }
        el.innerHTML = `
        <div class="table-responsive">
        <table class="table table-hover table-sm align-middle">
            <thead class="table-light"><tr>
                <th>${this.t('gateway.sessionId')}</th><th>${this.t('gateway.channel')}</th><th>${this.t('gateway.messages')}</th><th>${this.t('gateway.lastActive')}</th><th></th>
            </tr></thead>
            <tbody>
            ${sessions.map(s => `
            <tr>
                <td><code style="font-size:0.78rem;">${(s.session_id || s.id || '').slice(0,12)}…</code></td>
                <td><span class="badge bg-secondary text-capitalize">${s.channel || '—'}</span></td>
                <td>${s.message_count || 0}</td>
                <td class="text-muted small">${s.last_active ? new Date(s.last_active * 1000).toLocaleString() : '—'}</td>
                <td>
                    <button class="btn btn-xs btn-outline-danger" style="font-size:0.72rem;padding:1px 6px;"
                        onclick="singleCellApp.deleteGatewaySession('${s.session_id || s.id}')">
                        <i class="feather-trash-2"></i>
                    </button>
                </td>
            </tr>`).join('')}
            </tbody>
        </table>
        </div>`;
    },

    deleteGatewaySession(sid) {
        if (!confirm(`${this.t('gateway.deleteSessionConfirm')} ${sid}?`)) return;
        fetch(`/api/gateway/sessions/${sid}`, { method: 'DELETE' })
            .then(() => this._loadGatewayStatus())
            .catch(e => console.error(e));
    },

    // ── Memory ───────────────────────────────────────────────────────────

    _gatewayMemoryLoaded: false,
    _gatewayActiveFolderId: null,

    _loadMemoryData(folderId) {
        this._gatewayMemoryLoaded = true;
        this._gatewayActiveFolderId = folderId || null;
        // Load folders
        fetch('/api/gateway/memory/folders')
            .then(r => r.ok ? r.json() : { folders: [] })
            .then(data => {
                this._gatewayFolders = data.folders || [];
                this._renderFolderTree(this._gatewayFolders);
            })
            .catch(() => this._renderFolderTree([]));
        // Load documents
        const url = folderId ? `/api/gateway/memory/documents?folder_id=${folderId}` : '/api/gateway/memory/documents';
        fetch(url)
            .then(r => r.ok ? r.json() : { documents: [] })
            .then(data => this._renderMemoryDocs(data.documents || []))
            .catch(() => this._renderMemoryDocs([]));
    },

    _renderFolderTree(folders) {
        const el = document.getElementById('gw-folder-tree');
        if (!el) return;
        const allActive = !this._gatewayActiveFolderId;
        let html = `<a href="javascript:void(0)" class="d-block py-1 px-2 rounded small ${allActive ? 'fw-semibold text-primary' : 'text-muted'}"
                onclick="singleCellApp._loadMemoryData(null)">
                <i class="feather-inbox me-1"></i>${this.t('gateway.allDocuments')}</a>`;
        folders.forEach(f => {
            const active = this._gatewayActiveFolderId === f.id;
            html += `
            <div class="d-flex align-items-center py-1 px-2 rounded ${active ? 'bg-primary bg-opacity-10' : ''}">
                <a href="javascript:void(0)" class="flex-grow-1 small ${active ? 'fw-semibold text-primary' : 'text-muted text-decoration-none'}"
                    onclick="singleCellApp._loadMemoryData(${f.id})">
                    <i class="feather-folder me-1"></i>${this._esc(f.name)}
                    <span class="text-muted" style="font-size:0.7rem;">(${f.doc_count || 0})</span>
                </a>
            </div>`;
        });
        el.innerHTML = html;
    },

    _renderMemoryDocs(docs) {
        const el = document.getElementById('gw-memory-docs');
        if (!el) return;
        if (!docs.length) {
            el.innerHTML = `<div class="text-muted text-center py-5"><i class="feather-file-text" style="font-size:2rem;opacity:.3;display:block;margin-bottom:8px;"></i><p>${this.t('gateway.noDocumentsYet')}</p></div>`;
            return;
        }
        el.innerHTML = docs.map(doc => `
        <div class="card mb-2">
            <div class="card-body py-2 px-3">
                <div class="d-flex align-items-start justify-content-between">
                    <div>
                        <div class="fw-semibold small">${this._esc(doc.title || '(untitled)')}</div>
                        <div class="text-muted" style="font-size:0.77rem;">${this._esc((doc.content || '').slice(0, 120))}${(doc.content || '').length > 120 ? '…' : ''}</div>
                        <div class="mt-1">
                            ${(doc.tags || []).map(t => `<span class="badge bg-secondary me-1" style="font-size:0.7rem;">${this._esc(t)}</span>`).join('')}
                        </div>
                    </div>
                    <div class="d-flex gap-1 ms-2 flex-shrink-0">
                        <button class="btn btn-xs btn-outline-secondary" style="font-size:0.72rem;padding:2px 7px;" onclick="singleCellApp.editMemoryDoc(${doc.id})">
                            <i class="feather-edit-2"></i>
                        </button>
                        <button class="btn btn-xs btn-outline-danger" style="font-size:0.72rem;padding:2px 7px;" onclick="singleCellApp.deleteMemoryDoc(${doc.id})">
                            <i class="feather-trash-2"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>`).join('');
    },

    searchMemory(q) {
        if (!q || q.length < 2) { this._loadMemoryData(this._gatewayActiveFolderId); return; }
        clearTimeout(this._memSearchTimer);
        this._memSearchTimer = setTimeout(() => {
            fetch(`/api/gateway/memory/search?q=${encodeURIComponent(q)}`)
                .then(r => r.ok ? r.json() : { results: [] })
                .then(data => this._renderMemoryDocs(data.results || []))
                .catch(() => {});
        }, 300);
    },

    showMemoryDocModal(doc) {
        const modal = document.getElementById('gw-doc-modal');
        if (!modal) return;
        // Populate folder select
        const folderSel = document.getElementById('gw-doc-folder');
        if (folderSel) {
            folderSel.innerHTML = '<option value="">— root —</option>' +
                (this._gatewayFolders || []).map(f => `<option value="${f.id}">${this._esc(f.name)}</option>`).join('');
        }
        if (doc) {
            document.getElementById('gw-doc-modal-title').textContent = this.t('gateway.editDocument');
            document.getElementById('gw-doc-edit-id').value = doc.id;
            document.getElementById('gw-doc-title').value = doc.title || '';
            document.getElementById('gw-doc-folder').value = doc.folder_id || '';
            document.getElementById('gw-doc-tags').value = (doc.tags || []).join(', ');
            document.getElementById('gw-doc-content').value = doc.content || '';
        } else {
            document.getElementById('gw-doc-modal-title').textContent = this.t('gateway.newMemoryDocument');
            document.getElementById('gw-doc-edit-id').value = '';
            document.getElementById('gw-doc-title').value = '';
            document.getElementById('gw-doc-folder').value = this._gatewayActiveFolderId || '';
            document.getElementById('gw-doc-tags').value = '';
            document.getElementById('gw-doc-content').value = '';
        }
        modal.style.display = 'block';
    },

    hideMemoryDocModal() {
        const modal = document.getElementById('gw-doc-modal');
        if (modal) modal.style.display = 'none';
    },

    saveMemoryDoc() {
        const id = document.getElementById('gw-doc-edit-id').value;
        const body = {
            title: document.getElementById('gw-doc-title').value.trim(),
            folder_id: document.getElementById('gw-doc-folder').value || null,
            tags: document.getElementById('gw-doc-tags').value.split(',').map(t => t.trim()).filter(Boolean),
            content: document.getElementById('gw-doc-content').value,
        };
        if (!body.title) { alert(this.t('gateway.titleRequired')); return; }
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/gateway/memory/documents/${id}` : '/api/gateway/memory/documents';
        fetch(url, { method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) })
            .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(() => {
                this.hideMemoryDocModal();
                this._gatewayMemoryLoaded = false;
                this._loadMemoryData(this._gatewayActiveFolderId);
            })
            .catch(e => alert(`${this.t('gateway.saveFailed')}: ${e.message}`));
    },

    editMemoryDoc(id) {
        fetch(`/api/gateway/memory/documents/${id}`)
            .then(r => r.ok ? r.json() : null)
            .then(data => { if (data) this.showMemoryDocModal(data); })
            .catch(() => {});
    },

    deleteMemoryDoc(id) {
        if (!confirm(this.t('gateway.deleteDocumentConfirm'))) return;
        fetch(`/api/gateway/memory/documents/${id}`, { method: 'DELETE' })
            .then(() => { this._gatewayMemoryLoaded = false; this._loadMemoryData(this._gatewayActiveFolderId); })
            .catch(e => alert(`${this.t('gateway.deleteFailed')}: ${e.message}`));
    },

    showFolderModal() {
        const modal = document.getElementById('gw-folder-modal');
        if (modal) { document.getElementById('gw-folder-name').value = ''; modal.style.display = 'flex'; }
    },

    saveFolder() {
        const name = document.getElementById('gw-folder-name').value.trim();
        if (!name) { alert(this.t('gateway.nameRequired')); return; }
        fetch('/api/gateway/memory/folders', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name }),
        })
        .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(() => {
            document.getElementById('gw-folder-modal').style.display = 'none';
            this._gatewayMemoryLoaded = false;
            this._loadMemoryData(null);
        })
        .catch(e => alert(`${this.t('common.failed')}: ${e.message}`));
    },

    _esc(str) {
        return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    },

    // ── Shared error modal (singleton overlay) ─────────────────────────────

    _showErrorModal(title, message) {
        let overlay = document.getElementById('sc-error-modal');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'sc-error-modal';
            overlay.style.cssText = 'position:fixed;inset:0;background:rgba(15,16,26,0.6);display:flex;justify-content:center;align-items:center;z-index:2000;padding:1rem;';
            overlay.innerHTML = `
                <div class="card shadow" style="max-width:440px;width:100%;border:none;">
                    <div class="card-body p-3 position-relative">
                        <button type="button" class="btn-close position-absolute top-0 end-0 me-2 mt-2"
                            onclick="document.getElementById('sc-error-modal').style.display='none'"></button>
                        <h6 class="fw-semibold text-danger mb-2 sc-error-modal-title"></h6>
                        <div class="small sc-error-modal-body" style="white-space:pre-wrap;word-break:break-word;max-height:260px;overflow-y:auto;"></div>
                    </div>
                </div>`;
            document.body.appendChild(overlay);
            overlay.addEventListener('click', e => { if (e.target === overlay) overlay.style.display = 'none'; });
        }
        overlay.querySelector('.sc-error-modal-title').textContent = title;
        overlay.querySelector('.sc-error-modal-body').textContent = message;
        overlay.style.display = 'flex';
    },

    // ── Codex OAuth ────────────────────────────────────────────────────────

    _codexOAuthPoller: null,

    startCodexOAuth() {
        fetch('/api/gateway/channels/codex/oauth/start', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                if (!data.ok) { this._showErrorModal('Codex OAuth', data.error || this.t('common.unknownError')); return; }
                this._startCodexOAuthPoll();
            })
            .catch(e => this._showErrorModal('Codex OAuth', e.message));
    },

    importCodexAuth() {
        fetch('/api/gateway/channels/codex/oauth/import', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                if (!data.ok) { this._showErrorModal(this.t('gateway.codexImport'), data.error || this.t('common.unknownError')); return; }
                this._refreshCodexStatus();
                this.loadChannelConfig();
            })
            .catch(e => this._showErrorModal(this.t('gateway.codexImport'), e.message));
    },

    _startCodexOAuthPoll() {
        this._clearCodexOAuthPoll();
        const badge = document.getElementById('gw-codex-status');
        if (badge) { badge.textContent = this.t('gateway.codexPending'); badge.className = 'badge bg-warning'; badge.style.fontSize = '0.68rem'; }
        this._codexOAuthPoller = setInterval(() => {
            fetch('/api/gateway/channels/codex/oauth/status')
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'success') {
                        this._clearCodexOAuthPoll();
                        this._refreshCodexStatus();
                        this.loadChannelConfig();
                    } else if (data.status === 'error') {
                        this._clearCodexOAuthPoll();
                        this._showErrorModal('Codex OAuth', data.error || this.t('common.unknownError'));
                        this._refreshCodexStatus();
                    }
                })
                .catch(() => {});
        }, 2000);
    },

    _clearCodexOAuthPoll() {
        if (this._codexOAuthPoller) { clearInterval(this._codexOAuthPoller); this._codexOAuthPoller = null; }
    },

    _refreshCodexStatus() {
        fetch('/api/gateway/channels/codex/oauth/status')
            .then(r => r.json())
            .then(data => {
                const badge = document.getElementById('gw-codex-status');
                if (!badge) return;
                badge.style.fontSize = '0.68rem';
                if (data.linked && !data.expired) {
                    const label = data.account_id
                        ? `${this.t('gateway.codexLinked')}: ${data.account_id}`
                        : this.t('gateway.codexLinked');
                    badge.textContent = label;
                    badge.className = 'badge bg-success';
                } else if (data.linked && data.expired) {
                    badge.textContent = this.t('gateway.codexExpired');
                    badge.className = 'badge bg-warning';
                } else {
                    badge.textContent = this.t('gateway.codexNotLinked');
                    badge.className = 'badge bg-secondary';
                }
            })
            .catch(() => {});
    },

    // ── Channel Configuration ──────────────────────────────────────────────

    _gwConfig: null,          // cached raw config from server
    _gwProcesses: [],         // cached process list
    _gwSecretsSet: {},        // {section__field: bool}

    loadChannelConfig() {
        fetch('/api/gateway/channels/config')
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (!data) { this._renderChannelConfigError(); return; }
                this._gwConfig = data.config || {};
                this._gwProcesses = data.processes || [];
                this._gwSecretsSet = data.secrets_set || {};

                // Fill LLM fields (basic)
                const m = document.getElementById('gw-llm-model');
                const e = document.getElementById('gw-llm-endpoint');
                const badge = document.getElementById('gw-llm-key-badge');
                const pathEl = document.getElementById('gw-config-path');
                if (m) m.value = this._gwConfig.model || '';
                if (e) e.value = this._gwConfig.endpoint || '';
                if (badge) {
                    badge.textContent = data.api_key_set ? (this.t('gateway.apiKeySetPrefix') + (data.api_key_masked || '****')) : this.t('gateway.secret.notSet');
                    badge.className = 'badge ms-1 ' + (data.api_key_set ? 'bg-success' : 'bg-secondary');
                    badge.style.fontSize = '0.68rem';
                }
                if (pathEl) pathEl.textContent = data.config_path || '';

                // Fill extended LLM fields (temperature, top_p, max_tokens, timeout, system_prompt)
                const cfg = this._gwConfig;
                const setVal = (id, val) => { const el = document.getElementById(id); if (el && val != null) el.value = val; };
                setVal('gw-llm-temperature', cfg.temperature ?? 0.3);
                setVal('gw-llm-top-p', cfg.top_p ?? 1);
                setVal('gw-llm-max-tokens', cfg.max_tokens ?? 2048);
                setVal('gw-llm-timeout', cfg.timeout ?? 60);
                setVal('gw-llm-system-prompt', cfg.system_prompt ?? '');

                // Render channel cards
                this._renderChannelCards();
                this._refreshCodexStatus();
            })
            .catch(() => this._renderChannelConfigError());
    },

    _renderChannelConfigError() {
        const el = document.getElementById('gw-channel-cards');
        if (el) el.innerHTML = `<div class="alert alert-warning"><i class="feather-alert-circle me-2"></i>${this.t('gateway.loadingConfigError')}</div>`;
    },

    _channelState(ch) {
        return (this._gwProcesses || []).find(p => p.channel === ch) || null;
    },

    _channelRunning(ch) {
        const state = this._channelState(ch);
        return !!(state && state.status === 'running');
    },

    _renderChannelCards() {
        const channels = [
            { id: 'telegram',  label: this.t('gateway.channel.telegram'),  icon: 'feather-send',      color: '#2AABEE' },
            { id: 'discord',   label: this.t('gateway.channel.discord'),   icon: 'feather-hash',      color: '#5865F2' },
            { id: 'wechat',    label: this.t('gateway.channel.wechat'),    icon: 'feather-message-circle', color: '#07C160' },
            { id: 'feishu',    label: this.t('gateway.channel.feishu'), icon: 'feather-feather', color: '#3370FF' },
            { id: 'qq',        label: this.t('gateway.channel.qq'),    icon: 'feather-message-square', color: '#1AABE6' },
            { id: 'imessage',  label: this.t('gateway.channel.imessage'),  icon: 'feather-smartphone', color: '#34C759' },
        ];
        const el = document.getElementById('gw-channel-cards');
        if (!el) return;
        channels.forEach(ch => this._captureChannelUIState(ch.id));
        el.innerHTML = channels.map(ch => this._channelCardHTML(ch)).join('');
        channels.forEach(ch => this._restoreChannelUIState(ch.id));
        if (window.feather) feather.replace({ 'stroke-width': 2 });
    },

    _channelCardHTML(ch) {
        const state = this._channelState(ch.id) || {};
        const status = state.status || (state.configured ? 'stopped' : 'not_configured');
        const running = status === 'running';
        const failed = status === 'failed';
        const starting = status === 'starting';
        const canStart = !!state.can_start || (state.configured && !running && !starting && status !== 'not_configured');
        const cfg = (this._gwConfig || {})[ch.id] || {};
        const statusBadge = running
            ? `<span class="badge bg-success">${this.t('gateway.status.running')}</span>`
            : failed
                ? `<span class="badge bg-danger">${this.t('gateway.status.failed')}</span>`
                : starting
                    ? `<span class="badge bg-warning text-dark">${this.t('gateway.status.starting')}</span>`
                    : state.configured
                        ? `<span class="badge bg-secondary">${this.t('gateway.status.stopped')}</span>`
                        : `<span class="badge bg-dark">${this.t('gateway.status.notConfigured')}</span>`;
        const primaryBtn = running
            ? `<button class="btn btn-sm btn-secondary" disabled><i class="feather-play me-1"></i>${this.t('gateway.button.running')}</button>`
            : canStart
                ? `<button class="btn btn-sm ${failed ? 'btn-warning' : 'btn-primary'}" onclick="singleCellApp.startChannel('${ch.id}')"><i class="feather-play me-1"></i>${this.t('common.run')}</button>`
                : `<button class="btn btn-sm btn-secondary" disabled><i class="feather-play me-1"></i>${state.configured ? this.t('gateway.button.stopped') : this.t('gateway.button.notConfigured')}</button>`;

        return `
        <div class="card mb-3" id="gw-card-${ch.id}">
            <div class="card-header py-2 d-flex align-items-center justify-content-between"
                 style="cursor:pointer;" onclick="singleCellApp._toggleChannelCard('${ch.id}')">
                <div class="d-flex align-items-center gap-2">
                    <i class="${ch.icon}" style="color:${ch.color};"></i>
                    <span class="fw-semibold small">${ch.label}</span>
                    ${statusBadge}
                </div>
                <div class="d-flex align-items-center gap-2" onclick="event.stopPropagation()">
                    <button class="btn btn-sm btn-outline-secondary" onclick="singleCellApp.testChannel('${ch.id}')">
                        <i class="feather-zap me-1"></i>${this.t('gateway.button.test')}
                    </button>
                    ${running ? `<button class="btn btn-sm btn-danger" onclick="singleCellApp.stopChannel('${ch.id}')"><i class="feather-square me-1"></i>${this.t('gateway.button.stop')}</button>` : primaryBtn}
                    <i class="feather-chevron-down" id="gw-chevron-${ch.id}"></i>
                </div>
            </div>
            <div id="gw-body-${ch.id}" class="card-body p-3" style="display:none;">
                ${this._channelFormHTML(ch.id, cfg)}
                <div id="gw-ch-result-${ch.id}" class="mt-2" style="font-size:0.82rem;display:none;"></div>
                <div class="mt-3 d-flex justify-content-between align-items-center">
                    <button class="btn btn-sm btn-outline-secondary" onclick="singleCellApp.toggleChannelLogs('${ch.id}')">
                        <i class="feather-terminal me-1"></i>${this.t('gateway.button.logs')}
                    </button>
                    <div class="d-flex gap-2">
                        <button class="btn btn-sm btn-outline-primary" onclick="singleCellApp.testChannel('${ch.id}')">
                            <i class="feather-zap me-1"></i>${this.t('gateway.button.testConnection')}
                        </button>
                        <button class="btn btn-sm btn-primary" onclick="singleCellApp.saveChannelConfig('${ch.id}')">
                            <i class="feather-save me-1"></i>${this.t('gateway.button.save')}
                        </button>
                    </div>
                </div>
                <!-- Log panel (hidden by default) -->
                <div id="gw-log-${ch.id}" style="display:none;margin-top:10px;">
                    <div style="background:#1a1a2e;color:#a8d8a8;font-size:0.73rem;font-family:monospace;
                                border-radius:6px;padding:10px 12px;max-height:220px;overflow-y:auto;
                                white-space:pre-wrap;word-break:break-all;cursor:text;
                                user-select:text;-webkit-user-select:text;" id="gw-log-body-${ch.id}">
                        ${this.t('gateway.noOutputYet')}
                    </div>
                </div>
            </div>
        </div>`;
    },

    _channelFormHTML(ch, cfg) {
        const secrets = this._gwSecretsSet || {};
        const isSet = (section, f) => secrets[`${section}__${f}`] || false;

        // Regular text field
        const field = (id, label, type, val, placeholder, hint) => `
            <div class="col-md-6">
                <label class="form-label small fw-semibold mb-1">${label}</label>
                <input type="${type}" id="gw-field-${ch}-${id}" class="form-control form-control-sm"
                       value="${this._esc(val || '')}" placeholder="${this._esc(placeholder || '')}">
                ${hint ? `<div class="form-text" style="font-size:0.72rem;">${hint}</div>` : ''}
            </div>`;

        // Secret field — always blank; shows "already set" badge if configured
        const secret = (id, label, section, hint) => {
            const already = isSet(section, id);
            return `
            <div class="col-md-6">
                <label class="form-label small fw-semibold mb-1">${label}
                    ${already ? `<span class=\"badge bg-success ms-1\" style=\"font-size:0.65rem;\">${this.t('gateway.secret.set')}</span>` : `<span class=\"badge bg-warning text-dark ms-1\" style=\"font-size:0.65rem;\">${this.t('gateway.secret.notSet')}</span>`}
                </label>
                <input type="password" id="gw-field-${ch}-${id}" class="form-control form-control-sm"
                       value="" placeholder="${already ? this.t('gateway.secret.keepExisting') : this.t('gateway.secret.enterValue')}">
                ${hint ? `<div class="form-text" style="font-size:0.72rem;">${hint}</div>` : ''}
            </div>`;
        };

        const checkbox = (id, label, checked) => `
            <div class="col-md-6 d-flex align-items-center pt-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="gw-field-${ch}-${id}" ${checked ? 'checked' : ''}>
                    <label class="form-check-label small" for="gw-field-${ch}-${id}">${label}</label>
                </div>
            </div>`;
        const select = (id, label, options, val) => `
            <div class="col-md-6">
                <label class="form-label small fw-semibold mb-1">${label}</label>
                <select id="gw-field-${ch}-${id}" class="form-select form-select-sm">
                    ${options.map(o => `<option value="${o}" ${val===o?'selected':''}>${o}</option>`).join('')}
                </select>
            </div>`;

        if (ch === 'telegram') return `<div class="row g-2">
            ${secret('token',this.t('gateway.telegram.token'),'telegram',this.t('gateway.telegram.tokenHint'))}
            ${field('allowed_users',this.t('gateway.telegram.allowedUsers'),'text', (cfg.allowed_users||[]).join(', '), this.t('gateway.telegram.allowedUsersPlaceholder'), this.t('gateway.telegram.allowedUsersHint'))}
        </div>`;

        if (ch === 'discord') return `<div class="row g-2">
            ${secret('token',this.t('gateway.discord.token'),'discord',this.t('gateway.discord.tokenHint'))}
        </div>`;

        if (ch === 'wechat') return `<div class="row g-2">
            ${secret('token',this.t('gateway.wechat.token'),'wechat',this.t('gateway.wechat.tokenHint'))}
            ${field('base_url',this.t('gateway.wechat.baseUrl'),'text', cfg.base_url||'https://ilinkai.weixin.qq.com', 'https://ilinkai.weixin.qq.com', this.t('gateway.wechat.baseUrlHint'))}
            ${field('allow_from',this.t('gateway.wechat.allowFrom'),'text', (cfg.allow_from||[]).join(', '), 'user@im.wechat', this.t('gateway.wechat.allowFromHint'))}
            <div class="col-12">
                <button type="button" class="btn btn-sm btn-outline-primary w-100" onclick="event.stopPropagation(); singleCellApp.startWechatLogin();">
                    <i class="feather-scan me-1"></i>${this.t('gateway.wechat.loginButton')}
                </button>
            </div>
        </div>`;

        if (ch === 'feishu') return `<div class="row g-2">
            ${field('app_id',this.t('gateway.feishu.appId'),'text', cfg.app_id||'', 'cli_xxxxxxxxxx', '')}
            ${secret('app_secret',this.t('gateway.feishu.appSecret'),'feishu','Set FEISHU_APP_SECRET env var or enter here')}
            ${select('connection_mode',this.t('gateway.feishu.connectionMode'),['websocket','webhook'], cfg.connection_mode||'websocket')}
            ${secret('verification_token',this.t('gateway.feishu.verificationToken'),'feishu',this.t('gateway.feishu.verificationTokenHint'))}
            ${secret('encrypt_key',this.t('gateway.feishu.encryptKey'),'feishu',this.t('gateway.feishu.encryptKeyHint'))}
            ${field('host',this.t('gateway.feishu.webhookHost'),'text', cfg.host||'0.0.0.0', '0.0.0.0', this.t('gateway.feishu.webhookHostHint'))}
            ${field('port',this.t('gateway.feishu.webhookPort'),'number', cfg.port||8080, '8080', '')}
            ${field('path',this.t('gateway.feishu.webhookPath'),'text', cfg.path||'/feishu/events', '/feishu/events', '')}
        </div>`;

        if (ch === 'qq') return `<div class="row g-2">
            ${field('app_id',this.t('gateway.qq.appId'),'text', cfg.app_id||'', 'QQ Bot AppID (numeric)', this.t('gateway.qq.appIdHint'))}
            ${secret('client_secret',this.t('gateway.qq.clientSecret'),'qq',this.t('gateway.qq.clientSecretHint'))}
            ${field('image_host',this.t('gateway.qq.imageHost'),'text', cfg.image_host||'', 'http://YOUR_IP:8081', this.t('gateway.qq.imageHostHint'))}
            ${field('image_server_port',this.t('gateway.qq.imageServerPort'),'number', cfg.image_server_port||8081, '8081', '')}
            ${checkbox('markdown',this.t('gateway.qq.markdown'), cfg.markdown)}
        </div>`;

        if (ch === 'imessage') return `<div class="row g-2">
            ${field('cli_path',this.t('gateway.imessage.cliPath'),'text', cfg.cli_path||'imsg', 'imsg', this.t('gateway.imessage.cliPathHint'))}
            ${field('db_path',this.t('gateway.imessage.dbPath'),'text', cfg.db_path||'~/Library/Messages/chat.db', '~/Library/Messages/chat.db', '')}
            ${checkbox('include_attachments',this.t('gateway.imessage.includeAttachments'), cfg.include_attachments)}
        </div>`;

        return '';
    },

    _toggleChannelCard(ch) {
        const body = document.getElementById(`gw-body-${ch}`);
        const chevron = document.getElementById(`gw-chevron-${ch}`);
        if (!body) return;
        const open = body.style.display !== 'none';
        body.style.display = open ? 'none' : 'block';
        this._ensureChannelUIState(ch).cardOpen = !open;
        if (chevron) {
            chevron.className = open ? 'feather-chevron-down' : 'feather-chevron-up';
            if (window.feather) feather.replace({ 'stroke-width': 2 });
        }
    },

    _ensureChannelUIState(ch) {
        if (!this._gwChannelUIState) this._gwChannelUIState = {};
        if (!this._gwChannelUIState[ch]) {
            this._gwChannelUIState[ch] = {
                cardOpen: false,
                logsOpen: false,
                formValues: null,
                resultHTML: '',
                resultVisible: false,
                logText: '',
            };
        }
        return this._gwChannelUIState[ch];
    },

    _captureChannelUIState(ch) {
        const state = this._ensureChannelUIState(ch);
        const body = document.getElementById(`gw-body-${ch}`);
        const logPanel = document.getElementById(`gw-log-${ch}`);
        const resultEl = document.getElementById(`gw-ch-result-${ch}`);
        const logBody = document.getElementById(`gw-log-body-${ch}`);
        if (body) state.cardOpen = body.style.display !== 'none';
        if (logPanel) state.logsOpen = logPanel.style.display !== 'none';
        state.formValues = this._getChannelFormValues(ch);
        if (resultEl) {
            state.resultHTML = resultEl.innerHTML || '';
            state.resultVisible = resultEl.style.display !== 'none';
        }
        if (logBody) state.logText = logBody.textContent || '';
    },

    _restoreChannelUIState(ch) {
        const state = this._ensureChannelUIState(ch);
        const body = document.getElementById(`gw-body-${ch}`);
        const chevron = document.getElementById(`gw-chevron-${ch}`);
        const logPanel = document.getElementById(`gw-log-${ch}`);
        const resultEl = document.getElementById(`gw-ch-result-${ch}`);
        const logBody = document.getElementById(`gw-log-body-${ch}`);
        if (body) body.style.display = state.cardOpen ? 'block' : 'none';
        if (chevron) chevron.className = state.cardOpen ? 'feather-chevron-up' : 'feather-chevron-down';
        if (logPanel) logPanel.style.display = state.logsOpen ? 'block' : 'none';
        if (resultEl) {
            resultEl.innerHTML = state.resultHTML || '';
            resultEl.style.display = state.resultVisible ? 'block' : 'none';
        }
        if (logBody && state.logText) {
            logBody.textContent = state.logText;
        }
        const values = state.formValues || {};
        Object.entries(values).forEach(([key, value]) => {
            const field = document.getElementById(`gw-field-${ch}-${key}`);
            if (!field) return;
            if (field.type === 'checkbox') {
                field.checked = !!value;
            } else if (Array.isArray(value)) {
                field.value = value.join(', ');
            } else if (value !== null && value !== undefined) {
                field.value = value;
            }
        });
        if (state.logsOpen) {
            if (!this._logPollers[ch]) {
                this._startChannelLogPolling(ch);
            }
        } else if (this._logPollers[ch]) {
            clearInterval(this._logPollers[ch]);
            delete this._logPollers[ch];
        }
    },

    _getChannelFormValues(ch) {
        const val = id => {
            const el = document.getElementById(`gw-field-${ch}-${id}`);
            if (!el) return null;
            return el.type === 'checkbox' ? el.checked : el.value;
        };
        if (ch === 'telegram') return {
            token: val('token'),
            allowed_users: (val('allowed_users') || '').split(',').map(s => s.trim()).filter(Boolean),
        };
        if (ch === 'discord') return {
            token: val('token'),
        };
        if (ch === 'wechat') return {
            token: val('token'),
            base_url: val('base_url'),
            allow_from: (val('allow_from') || '').split(',').map(s => s.trim()).filter(Boolean),
        };
        if (ch === 'feishu') return {
            app_id: val('app_id'), app_secret: val('app_secret'),
            connection_mode: val('connection_mode'),
            verification_token: val('verification_token'), encrypt_key: val('encrypt_key'),
            host: val('host'), port: parseInt(val('port')) || 8080, path: val('path'),
        };
        if (ch === 'qq') return {
            app_id: val('app_id'), client_secret: val('client_secret'),
            image_host: val('image_host'),
            image_server_port: parseInt(val('image_server_port')) || 8081,
            markdown: val('markdown'),
        };
        if (ch === 'imessage') return {
            cli_path: val('cli_path'), db_path: val('db_path'),
            include_attachments: val('include_attachments'),
        };
        return {};
    },

    _showChResult(ch, ok, msg) {
        const el = document.getElementById(`gw-ch-result-${ch}`);
        if (!el) return;
        el.style.display = 'block';
        el.innerHTML = `<span class="${ok ? 'text-success' : 'text-danger'}">
            <i class="${ok ? 'feather-check-circle' : 'feather-x-circle'} me-1"></i>${this._esc(msg)}</span>`;
        const state = this._ensureChannelUIState(ch);
        state.resultHTML = el.innerHTML;
        state.resultVisible = true;
        if (window.feather) feather.replace({ 'stroke-width': 2 });
    },

    _wechatLoginDialogEl: null,
    _wechatLoginPoller: null,

    startWechatLogin() {
        const cfg = this._getChannelFormValues('wechat');
        const baseUrl = cfg.base_url || 'https://ilinkai.weixin.qq.com';
        const resultEl = document.getElementById('gw-ch-result-wechat');
        if (resultEl) {
            resultEl.style.display = 'block';
            resultEl.innerHTML = `<span class="text-info"><i class="feather-loader me-1"></i>${this.t('gateway.wechat.loginFetching')}</span>`;
        }
        fetch('/api/gateway/channels/wechat/login/qr', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ base_url: baseUrl }),
        })
        .then(r => r.json())
        .then(data => {
            if (!data.ok) throw new Error(data.error || this.t('gateway.saveFailed'));
            this._showWechatLoginDialog(data, baseUrl);
        })
        .catch(err => {
            this._showChResult('wechat', false, err.message);
        });
    },

    _showWechatLoginDialog(payload, baseUrl) {
        const dialog = this._ensureWechatLoginDialog();
        const img = dialog.querySelector('.gw-wechat-qr-img');
        const status = dialog.querySelector('.gw-wechat-qr-status');
        const helper = dialog.querySelector('.gw-wechat-qr-helper');
        img.src = payload.image || '';
        dialog.dataset.qrcode = payload.qrcode || '';
        dialog.dataset.baseUrl = baseUrl;
        status.textContent = this.t('gateway.wechat.loginScanning');
        helper.textContent = payload.message || this.t('gateway.wechat.loginHint');
        dialog.style.display = 'flex';
        this._startWechatLoginPoll(payload.qrcode, baseUrl);
    },

    _ensureWechatLoginDialog() {
        if (this._wechatLoginDialogEl) return this._wechatLoginDialogEl;
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(15,16,26,0.6);display:flex;justify-content:center;align-items:center;z-index:1050;padding:1rem;';
        overlay.id = 'gw-wechat-login-modal';
        overlay.innerHTML = `
            <div class="card shadow" style="max-width:380px;width:100%;border:none;">
                <div class="card-body p-3 text-center position-relative">
                    <button type="button" class="btn-close position-absolute top-0 end-0 me-2 mt-2" aria-label="Close" onclick="singleCellApp._hideWechatLoginDialog()"></button>
                    <h5 class="card-title">${this.t('gateway.wechat.loginTitle')}</h5>
                    <img class="gw-wechat-qr-img my-3" src="" alt="WeChat QR" style="width:220px;height:220px;object-fit:contain;">
                    <div class="fw-semibold gw-wechat-qr-status mb-1">${this.t('gateway.wechat.loginPrompt')}</div>
                    <div class="text-muted small gw-wechat-qr-helper">${this.t('gateway.wechat.loginHint')}</div>
                </div>
            </div>`;
        document.body.appendChild(overlay);
        this._wechatLoginDialogEl = overlay;
        return overlay;
    },

    _startWechatLoginPoll(qrcode, baseUrl) {
        if (!qrcode) return;
        this._clearWechatLoginPoll();
        const statusEl = this._wechatLoginDialogEl?.querySelector('.gw-wechat-qr-status');
        const helperEl = this._wechatLoginDialogEl?.querySelector('.gw-wechat-qr-helper');
        const poll = () => {
            fetch(`/api/gateway/channels/wechat/login/status?qrcode=${encodeURIComponent(qrcode)}&base_url=${encodeURIComponent(baseUrl)}`)
                .then(r => r.json())
                .then(data => {
                    if (!data.ok) {
                        // Fatal protocol errors (e.g. invalid qrcode) — stop polling.
                        if (statusEl) statusEl.textContent = this.t('gateway.wechat.loginError');
                        if (helperEl) helperEl.textContent = data.error || '';
                        this._clearWechatLoginPoll();
                        return;
                    }
                    if (data.status === 'confirmed') {
                        this._clearWechatLoginPoll();
                        this._applyWechatLoginResult(data);
                        this._hideWechatLoginDialog();
                        return;
                    }
                    if (data.status === 'expired') {
                        if (statusEl) statusEl.textContent = this.t('gateway.wechat.loginError');
                        this._clearWechatLoginPoll();
                        return;
                    }
                    // "wait" / "scaned" / other — keep polling, update status text.
                    if (statusEl && data.status && data.status !== 'wait') {
                        let text = this.t('gateway.wechat.loginStatus');
                        statusEl.textContent = text.replace('{status}', data.status);
                    }
                })
                .catch(() => {
                    // Network / timeout errors are transient — keep polling silently.
                });
        };
        poll();
        this._wechatLoginPoller = setInterval(poll, 2000);
    },

    _clearWechatLoginPoll() {
        if (this._wechatLoginPoller) {
            clearInterval(this._wechatLoginPoller);
            this._wechatLoginPoller = null;
        }
    },

    _hideWechatLoginDialog() {
        this._clearWechatLoginPoll();
        if (this._wechatLoginDialogEl) {
            this._wechatLoginDialogEl.style.display = 'none';
        }
    },

    _applyWechatLoginResult(data) {
        const tokenField = document.getElementById('gw-field-wechat-token');
        if (tokenField && data.bot_token) tokenField.value = data.bot_token;
        const baseField = document.getElementById('gw-field-wechat-base_url');
        if (baseField && data.baseurl) baseField.value = data.baseurl;
        this._gwSecretsSet = this._gwSecretsSet || {};
        this._gwSecretsSet['wechat__token'] = true;
        this._gwConfig = this._gwConfig || {};
        this._gwConfig.wechat = this._gwConfig.wechat || {};
        if (data.bot_token) this._gwConfig.wechat.token = data.bot_token;
        if (data.baseurl) this._gwConfig.wechat.base_url = data.baseurl;
        this._showChResult('wechat', true, this.t('gateway.wechat.loginSuccess'));
        const state = this._ensureChannelUIState('wechat');
        state.formValues = this._getChannelFormValues('wechat');
    },

    _collectLLMFormValues() {
        const gv = id => (document.getElementById(id) || {}).value || '';
        const gn = (id, fallback) => { const v = parseFloat(gv(id)); return isNaN(v) ? fallback : v; };
        const gi = (id, fallback) => { const v = parseInt(gv(id), 10); return isNaN(v) ? fallback : v; };
        return {
            model: gv('gw-llm-model'),
            endpoint: gv('gw-llm-endpoint') || null,
            temperature: gn('gw-llm-temperature', 0.3),
            top_p: gn('gw-llm-top-p', 1),
            max_tokens: gi('gw-llm-max-tokens', 2048),
            timeout: gi('gw-llm-timeout', 60),
            system_prompt: gv('gw-llm-system-prompt'),
        };
    },

    testLLMConfig() {
        const apiKey = (document.getElementById('gw-llm-api-key') || {}).value || '';
        const endpoint = (document.getElementById('gw-llm-endpoint') || {}).value || '';
        const resultEl = document.getElementById('gw-llm-save-result');
        if (resultEl) {
            resultEl.style.display = 'block';
            resultEl.innerHTML = `<span class="text-info"><i class="feather-loader me-1"></i>${this.t('gateway.testing')}</span>`;
            if (window.feather) feather.replace({ 'stroke-width': 2 });
        }
        fetch('/api/gateway/channels/llm/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey || undefined, endpoint: endpoint || undefined }),
        })
        .then(r => r.json())
        .then(data => {
            if (resultEl) {
                resultEl.style.display = 'block';
                resultEl.innerHTML = data.ok
                    ? `<span class="text-success"><i class="feather-check-circle me-1"></i>${this.t('gateway.keyValid')}</span>`
                    : `<span class="text-danger"><i class="feather-x-circle me-1"></i>${this._esc(data.error || this.t('common.failed'))}</span>`;
                if (window.feather) feather.replace({ 'stroke-width': 2 });
            }
            if (!data.ok) {
                this._showErrorModal(this.t('gateway.testFailed'), data.error || this.t('common.unknownError'));
            }
        })
        .catch(e => {
            if (resultEl) { resultEl.style.display = 'block'; resultEl.innerHTML = `<span class="text-danger">${this._esc(e.message)}</span>`; }
            this._showErrorModal(this.t('gateway.testFailed'), e.message);
        });
    },

    saveLLMConfig() {
        const apiKey = (document.getElementById('gw-llm-api-key') || {}).value || '';
        const llmVals = this._collectLLMFormValues();
        const cfg = Object.assign({}, this._gwConfig || {}, llmVals);
        const resultEl = document.getElementById('gw-llm-save-result');

        const doSave = () => {
            if (resultEl) { resultEl.style.display = 'none'; }
            fetch('/api/gateway/channels/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config: cfg, api_key: apiKey }),
            })
            .then(r => r.json())
            .then(data => {
                if (resultEl) {
                    resultEl.style.display = 'block';
                    resultEl.innerHTML = data.ok
                        ? `<span class="text-success"><i class="feather-check-circle me-1"></i>${this.t('gateway.savedTo')} ${data.path}</span>`
                        : `<span class="text-danger"><i class="feather-x-circle me-1"></i>${this._esc(data.error || this.t('gateway.saveFailed'))}</span>`;
                    if (window.feather) feather.replace({ 'stroke-width': 2 });
                }
                if (data.ok) {
                    this._gwConfig = cfg;
                    if (apiKey) document.getElementById('gw-llm-api-key').value = '';
                    this.loadChannelConfig(); // refresh badge + extended fields
                    // Propagate api_key change to the Agent panel without a new server fetch
                    if (apiKey) {
                        const agentKeyEl = document.getElementById('agent-api-key');
                        if (agentKeyEl) {
                            agentKeyEl.value = apiKey;
                            sessionStorage.setItem('omicverse.agentApiKey', apiKey);
                        }
                    }
                }
            })
            .catch(e => {
                if (resultEl) { resultEl.style.display = 'block'; resultEl.innerHTML = `<span class="text-danger">${this._esc(e.message)}</span>`; }
            });
        };

        // If a new API key is entered, test it first before saving
        if (apiKey) {
            if (resultEl) {
                resultEl.style.display = 'block';
                resultEl.innerHTML = `<span class="text-info"><i class="feather-loader me-1"></i>${this.t('gateway.testing')}</span>`;
                if (window.feather) feather.replace({ 'stroke-width': 2 });
            }
            fetch('/api/gateway/channels/llm/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: apiKey, endpoint: llmVals.endpoint || undefined }),
            })
            .then(r => r.json())
            .then(data => {
                if (data.ok) {
                    doSave();
                } else {
                    if (resultEl) {
                        resultEl.style.display = 'block';
                        resultEl.innerHTML = `<span class="text-danger"><i class="feather-x-circle me-1"></i>${this._esc(data.error || this.t('common.failed'))}</span>`;
                        if (window.feather) feather.replace({ 'stroke-width': 2 });
                    }
                    this._showErrorModal(this.t('gateway.testFailed'), data.error || this.t('common.unknownError'));
                }
            })
            .catch(e => {
                if (resultEl) { resultEl.style.display = 'block'; resultEl.innerHTML = `<span class="text-danger">${this._esc(e.message)}</span>`; }
                this._showErrorModal(this.t('gateway.testFailed'), e.message);
            });
        } else {
            doSave();
        }
    },

    saveChannelConfig(ch) {
        const chVals = this._getChannelFormValues(ch);
        const cfg = Object.assign({}, this._gwConfig || {});
        cfg[ch] = Object.assign({}, cfg[ch] || {}, chVals);
        fetch('/api/gateway/channels/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ config: cfg }),
        })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                this._gwConfig = cfg;
                this._showChResult(ch, true, `${this.t('gateway.savedTo')} ${data.path}`);
                this.loadChannelConfig();
            } else {
                this._showChResult(ch, false, data.error || this.t('gateway.saveFailed'));
            }
        })
        .catch(e => this._showChResult(ch, false, e.message));
    },

    testChannel(ch) {
        // Open the card first so the result is visible
        const body = document.getElementById(`gw-body-${ch}`);
        if (body && body.style.display === 'none') this._toggleChannelCard(ch);

        const resultEl = document.getElementById(`gw-ch-result-${ch}`);
        if (resultEl) {
            resultEl.style.display = 'block';
            resultEl.innerHTML = `<span class="text-muted"><i class="feather-loader me-1"></i>${this.t('gateway.testing')}</span>`;
            if (window.feather) feather.replace({ 'stroke-width': 2 });
        }
        const body_ = this._getChannelFormValues(ch);
        fetch(`/api/gateway/channels/${ch}/test`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body_),
        })
        .then(r => r.json())
        .then(data => this._showChResult(ch, data.ok, data.message || data.error || ''))
        .catch(e => this._showChResult(ch, false, e.message));
    },

    startChannel(ch) {
        const btn = document.querySelector(`#gw-card-${ch} button[onclick*="startChannel"]`);
        if (btn) { btn.disabled = true; btn.innerHTML = `<i class=\"feather-loader me-1\"></i>${this.t('gateway.startingEllipsis')}`; if (window.feather) feather.replace({ 'stroke-width': 2 }); }
        // Save current form values first, then start
        const chVals = this._getChannelFormValues(ch);
        const cfg = Object.assign({}, this._gwConfig || {});
        cfg[ch] = Object.assign({}, cfg[ch] || {}, chVals);
        fetch('/api/gateway/channels/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ config: cfg }),
        })
        .then(() => fetch(`/api/gateway/channels/${ch}/start`, { method: 'POST' }))
        .then(r => r.json())
        .then(data => {
            const prev = this._channelState(ch) || {};
            if (data.ok) {
                this._gwProcesses = this._gwProcesses.filter(p => p.channel !== ch);
                this._gwProcesses.push({
                    channel: ch,
                    running: true,
                    status: 'running',
                    pid: data.pid,
                    can_start: false,
                    configured: prev.configured !== undefined ? prev.configured : true,
                });
                this._showChResult(ch, true, data.message || `${this.t('gateway.started')} (pid=${data.pid})`);
            } else {
                this._gwProcesses = this._gwProcesses.filter(p => p.channel !== ch);
                this._gwProcesses.push({
                    channel: ch,
                    running: false,
                    status: 'failed',
                    error: data.error || this.t('gateway.startFailed'),
                    can_start: true,
                    configured: prev.configured !== undefined ? prev.configured : true,
                });
                this._showChResult(ch, false, data.error || this.t('gateway.startFailed'));
            }
            this._renderChannelCards();
        })
        .catch(e => {
            const prev = this._channelState(ch) || {};
            this._gwProcesses = this._gwProcesses.filter(p => p.channel !== ch);
            this._gwProcesses.push({
                channel: ch,
                running: false,
                status: 'failed',
                error: e.message,
                can_start: true,
                configured: prev.configured !== undefined ? prev.configured : true,
            });
            this._showChResult(ch, false, e.message);
            this._renderChannelCards();
        });
    },

    stopChannel(ch) {
        fetch(`/api/gateway/channels/${ch}/stop`, { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                const prev = this._channelState(ch) || {};
                this._gwProcesses = this._gwProcesses.filter(p => p.channel !== ch);
                this._gwProcesses.push({
                    channel: ch,
                    running: false,
                    status: 'stopped',
                    can_start: prev.configured !== undefined ? prev.configured : true,
                    configured: prev.configured !== undefined ? prev.configured : true,
                });
                this._showChResult(ch, data.ok, data.message || data.error || '');
                // Stop log polling
                if (this._logPollers && this._logPollers[ch]) {
                    clearInterval(this._logPollers[ch]);
                    delete this._logPollers[ch];
                }
                this._renderChannelCards();
            })
            .catch(e => this._showChResult(ch, false, e.message));
    },

    _logPollers: {},

    _startChannelLogPolling(ch) {
        const fetchLogs = () => {
            fetch(`/api/gateway/channels/${ch}/logs`)
                .then(r => r.ok ? r.json() : null)
                .then(data => {
                    const body = document.getElementById(`gw-log-body-${ch}`);
                    if (!body) return;
                    if (!data) { body.textContent = this.t('gateway.logUnavailable'); return; }
                    if (data.logs) {
                        const status = data.running ? '' : '\n[process has exited]';
                        body.textContent = data.logs + status;
                        body.scrollTop = body.scrollHeight;
                        this._ensureChannelUIState(ch).logText = body.textContent;
                        if (!data.running) {
                            if (this._logPollers[ch]) { clearInterval(this._logPollers[ch]); delete this._logPollers[ch]; }
                        }
                    } else if (!data.running) {
                        body.textContent = this.t('gateway.processNotRunning');
                        this._ensureChannelUIState(ch).logText = body.textContent;
                        if (this._logPollers[ch]) { clearInterval(this._logPollers[ch]); delete this._logPollers[ch]; }
                    } else {
                        body.textContent = this.t('gateway.waitingOutput');
                        this._ensureChannelUIState(ch).logText = body.textContent;
                    }
                })
                .catch(() => {});
        };
        fetchLogs();
        this._logPollers[ch] = setInterval(fetchLogs, 2000);
    },

    toggleChannelLogs(ch) {
        const panel = document.getElementById(`gw-log-${ch}`);
        if (!panel) return;
        const open = panel.style.display !== 'none';
        panel.style.display = open ? 'none' : 'block';
        this._ensureChannelUIState(ch).logsOpen = !open;
        if (open) {
            // Stop polling
            if (this._logPollers[ch]) { clearInterval(this._logPollers[ch]); delete this._logPollers[ch]; }
            return;
        }
        this._startChannelLogPolling(ch);
    },

    loadSkills(force = false) {
        if (this.skillsLoaded && !force) {
            this.renderSkills();
            return;
        }
        const headers = this.getAccountHeaders ? this.getAccountHeaders() : {};
        fetch('/api/skills/list', { headers })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                this.skills = Array.isArray(data.skills) ? data.skills : [];
                this.localSkillCount = Number(data.local_count || 0);
                this.onlineSkillCount = Number(data.online_count || 0);
                this.onlineRequiresAuth = !!data.online_requires_auth;
                this.skillsLoaded = true;
                if (data.online_error) {
                    this.showStatus(`${this.t('skills.onlineLoadFailed')}: ${data.online_error}`, false);
                }
                const searchInput = document.getElementById('skills-search-input');
                this.filterSkills(searchInput ? searchInput.value : '');
            })
            .catch(error => {
                const grid = document.getElementById('skills-store-grid');
                if (grid) {
                    grid.innerHTML = `
                        <div class="skills-empty-state">
                            <div class="skills-empty-icon"><i class="feather-alert-circle"></i></div>
                            <h3>${this.t('skills.loadFailed')}</h3>
                            <p>${error.message || this.t('common.noData')}</p>
                        </div>
                    `;
                }
            });
    },

    refreshSkills() {
        this.skillsLoaded = false;
        this.loadSkills(true);
    },

    getSkillsSourceFilter() {
        if (!this.skillsSourceFilter) {
            this.skillsSourceFilter = localStorage.getItem('omicverse.skillsSourceFilter') || 'all';
        }
        if (!['all', 'local', 'online'].includes(this.skillsSourceFilter)) {
            this.skillsSourceFilter = 'all';
        }
        return this.skillsSourceFilter;
    },

    setSkillsSourceFilter(source) {
        const next = ['all', 'local', 'online'].includes(source) ? source : 'all';
        this.skillsSourceFilter = next;
        localStorage.setItem('omicverse.skillsSourceFilter', next);
        const searchInput = document.getElementById('skills-search-input');
        this.filterSkills(searchInput ? searchInput.value : '');
    },

    getSkillsLayout() {
        if (!this.skillsLayout) {
            this.skillsLayout = localStorage.getItem('omicverse.skillsLayout') || 'card';
        }
        return this.skillsLayout;
    },

    setSkillsLayout(layout) {
        const next = layout === 'list' ? 'list' : 'card';
        this.skillsLayout = next;
        localStorage.setItem('omicverse.skillsLayout', next);
        this.renderSkills();
    },

    filterSkills(query = '') {
        const term = String(query || '').trim().toLowerCase();
        const sourceFilter = this.getSkillsSourceFilter();
        this.filteredSkills = this.skills.filter(skill => {
            const source = skill && skill.source === 'online' ? 'online' : 'local';
            if (sourceFilter !== 'all' && source !== sourceFilter) {
                return false;
            }
            if (!term) {
                return true;
            }
            const haystack = [
                skill.name,
                skill.slug,
                skill.description,
                skill.summary,
                skill.root_label,
                skill.relative_path,
                skill.reference_excerpt,
                skill.reference_relative_path,
                skill.author,
                skill.package_name,
                skill.install_command,
                Array.isArray(skill.tags) ? skill.tags.join(' ') : '',
                skill.source,
            ].join(' ').toLowerCase();
            return haystack.includes(term);
        });
        this.renderSkills();
    },

    renderSkills() {
        const grid = document.getElementById('skills-store-grid');
        const meta = document.getElementById('skills-store-meta');
        const cardBtn = document.getElementById('skills-layout-card-btn');
        const listBtn = document.getElementById('skills-layout-list-btn');
        const allBtn = document.getElementById('skills-source-all-btn');
        const localBtn = document.getElementById('skills-source-local-btn');
        const onlineBtn = document.getElementById('skills-source-online-btn');
        const allCount = document.getElementById('skills-source-all-count');
        const localCount = document.getElementById('skills-source-local-count');
        const onlineCount = document.getElementById('skills-source-online-count');
        if (!grid) return;
        const layout = this.getSkillsLayout();
        const sourceFilter = this.getSkillsSourceFilter();

        // Show auth gate when user is not logged in and tries to view online skills
        if (sourceFilter === 'online' && this.onlineRequiresAuth) {
            grid.classList.remove('list');
            grid.innerHTML = `
                <div class="skills-auth-gate">
                    <div class="skills-auth-gate-icon"><i class="feather-lock"></i></div>
                    <h3>登录 / 注册以访问在线技能商店 · Sign in to Access the Online Store</h3>
                    <p>注册账户，即可获取在线技能商店的完整内容。<br>
                    Create an account to access the online skill store.</p>
                    <div class="skills-auth-gate-actions">
                        <button type="button" class="btn btn-primary" onclick="singleCellApp.openAuthModal('login')">
                            <i class="feather-log-in me-1"></i>登录
                        </button>
                        <button type="button" class="btn btn-outline-primary" onclick="singleCellApp.openAuthModal('register')">
                            <i class="feather-user-plus me-1"></i>注册账户
                        </button>
                    </div>
                </div>
            `;
            if (window.feather) feather.replace({ 'stroke-width': 2 });
            return;
        }

        grid.classList.toggle('list', layout === 'list');
        if (cardBtn) cardBtn.classList.toggle('active', layout === 'card');
        if (listBtn) listBtn.classList.toggle('active', layout === 'list');
        if (allBtn) allBtn.classList.toggle('active', sourceFilter === 'all');
        if (localBtn) localBtn.classList.toggle('active', sourceFilter === 'local');
        if (onlineBtn) onlineBtn.classList.toggle('active', sourceFilter === 'online');
        if (allCount) allCount.textContent = String(Array.isArray(this.skills) ? this.skills.length : 0);
        if (localCount) localCount.textContent = String(this.localSkillCount || 0);
        if (onlineCount) onlineCount.textContent = String(this.onlineSkillCount || 0);

        const skills = Array.isArray(this.filteredSkills) ? this.filteredSkills : [];
        if (meta) {
            meta.textContent = `${skills.length} / ${this.skills.length} · ${this.t('skills.local')}: ${this.localSkillCount || 0} · ${this.t('skills.online')}: ${this.onlineSkillCount || 0}`;
        }
        if (!skills.length && sourceFilter === 'online') {
            grid.classList.remove('list');
            grid.innerHTML = `
                <div class="skills-auth-gate">
                    <div class="skills-auth-gate-icon"><i class="feather-clock"></i></div>
                    <h3>在线技能商店即将推出 · Coming Soon</h3>
                    <p>每一个技能都经过验证，而不是从网上随意收集，敬请期待。<br>
                    Every skill is carefully verified — not scraped from the web. Stay tuned.</p>
                </div>
            `;
            if (window.feather) feather.replace({ 'stroke-width': 2 });
            return;
        }
        if (!skills.length) {
            grid.innerHTML = `
                <div class="skills-empty-state">
                    <div class="skills-empty-icon"><i class="feather-grid"></i></div>
                    <h3>${this.t('skills.emptyTitle')}</h3>
                    <p>${this.t('skills.emptyBody')}</p>
                </div>
            `;
            if (window.feather) feather.replace({ 'stroke-width': 2 });
            return;
        }

        const esc = (value) => String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');

        const skillButtonLabel = (skill) => skill && skill.editable === false
            ? (skill.source === 'online' ? this.t('skills.viewDetail') : this.t('skills.viewSkill'))
            : this.t('skills.modifySkill');
        const referenceButtonLabel = (skill) => {
            if (skill && skill.source === 'online') {
                return this.t('skills.openHomepage');
            }
            return skill && skill.editable === false
                ? this.t('skills.viewReference')
                : this.t('skills.modifyReference');
        };
        const buildReferenceBlock = (skill) => {
            if (layout === 'list') {
                return '';
            }
            if (skill.reference_excerpt) {
                return `
                    <div class="skill-card-reference">
                        <div class="skill-card-reference-title">${this.t('skills.reference')}</div>
                        <p class="skill-card-reference-body">${esc(skill.reference_excerpt)}</p>
                    </div>
                `;
            }
            return `
                <div class="skill-card-reference empty">
                    <div class="skill-card-reference-title">${this.t('skills.reference')}</div>
                    <p class="skill-card-reference-body">${this.t('skills.referenceEmpty')}</p>
                </div>
            `;
        };

        grid.innerHTML = skills.map(skill => `
            <article class="skill-card ${layout === 'list' ? 'skill-row' : ''}">
                <div class="${layout === 'list' ? 'skill-row-main' : ''}">
                    <div class="skill-card-head">
                        <div>
                            <h3 class="skill-card-title">${esc(skill.name)}</h3>
                            <div class="skill-card-slug">${esc(skill.slug)}</div>
                        </div>
                        <span class="skill-chip primary">${esc(skill.source === 'online' ? this.t('skills.online') : (skill.root_label || this.t('skills.location')))}</span>
                    </div>
                    <p class="skill-card-desc">${esc(skill.description || 'No description provided.')}</p>
                    <div class="skill-card-meta">
                        <span class="skill-chip">${this.t('skills.path')}: ${esc(skill.relative_path || 'SKILL.md')}</span>
                        ${skill.author ? `<span class="skill-chip">${this.t('skills.author')}: ${esc(skill.author)}</span>` : ''}
                        ${skill.package_name ? `<span class="skill-chip">${this.t('skills.package')}: ${esc(skill.package_name)}</span>` : ''}
                        ${Array.isArray(skill.tags) && skill.tags.length ? `<span class="skill-chip">${this.t('skills.tags')}: ${esc(skill.tags.join(', '))}</span>` : ''}
                        ${layout !== 'list' && skill.reference_relative_path ? `<span class="skill-chip">${this.t('skills.reference')}: ${esc(skill.reference_relative_path)}</span>` : ''}
                        ${skill.version ? `<span class="skill-chip">${this.t('skills.version')}: ${esc(skill.version)}</span>` : ''}
                        ${skill.editable === false ? `<span class="skill-chip muted">${this.t('skills.readOnly')}</span>` : ''}
                    </div>
                    ${buildReferenceBlock(skill)}
                    <div class="skill-card-path">${esc(skill.path)}</div>
                </div>
                <div class="skill-card-footer ${layout === 'list' ? 'skill-row-actions' : ''}">
                    <button
                        type="button"
                        class="btn btn-sm btn-primary"
                        onclick="${skill.source === 'online'
                            ? `singleCellApp.viewRemoteSkill(decodeURIComponent('${encodeURIComponent(String(skill.remote_slug || skill.slug || ''))}'))`
                            : `singleCellApp.editSkill(decodeURIComponent('${encodeURIComponent(String(skill.path || ''))}'))`}">
                        <i class="feather-edit-3 me-1"></i>${skillButtonLabel(skill)}
                    </button>
                    ${skill.source === 'online'
                        ? (skill.homepage_url ? `
                    <button
                        type="button"
                        class="btn btn-sm btn-outline-primary"
                        onclick="singleCellApp.openExternalLink(decodeURIComponent('${encodeURIComponent(String(skill.homepage_url || ''))}'))">
                        <i class="feather-external-link me-1"></i>${referenceButtonLabel(skill)}
                    </button>
                    ` : '')
                        : `
                    <button
                        type="button"
                        class="btn btn-sm btn-outline-primary"
                        onclick="singleCellApp.editSkillReference(decodeURIComponent('${encodeURIComponent(String(skill.path || ''))}'))">
                        <i class="feather-file-text me-1"></i>${referenceButtonLabel(skill)}
                    </button>
                    `}
                </div>
            </article>
        `).join('');

        if (window.feather) feather.replace({ 'stroke-width': 2 });
    },

    createSkill() {
        const name = prompt(this.t('skills.createPrompt'));
        if (!name) return;
        const description = prompt(this.t('skills.descriptionPrompt')) || '';
        fetch('/api/skills/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            this.refreshSkills();
            if (data.skill && data.skill.path) {
                this.editSkill(data.skill.path);
            }
        })
        .catch(error => {
            alert(`${this.t('skills.createFailed')}: ${error.message}`);
        });
    },

    triggerSkillImport() {
        const input = document.getElementById('skill-import-input');
        if (!input) return;
        input.value = '';
        input.click();
    },

    handleSkillImportFile(event) {
        const input = event && event.target;
        const file = input && input.files ? input.files[0] : null;
        if (!file) return;

        const defaultName = file.name.replace(/\.[^.]+$/, '') || 'imported-skill';
        const name = prompt(this.t('skills.createPrompt'), defaultName);
        if (!name) {
            input.value = '';
            return;
        }
        const description = prompt(this.t('skills.descriptionPrompt')) || '';
        const reader = new FileReader();
        reader.onload = () => {
            fetch('/api/skills/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    description,
                    content: String(reader.result || ''),
                }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                this.refreshSkills();
                if (data.skill && data.skill.path) {
                    this.editSkill(data.skill.path);
                }
            })
            .catch(error => {
                alert(`${this.t('skills.createFailed')}: ${error.message}`);
            })
            .finally(() => {
                input.value = '';
            });
        };
        reader.onerror = () => {
            alert(`${this.t('skills.createFailed')}: ${file.name}`);
            input.value = '';
        };
        reader.readAsText(file, 'utf-8');
    },

    editSkill(path) {
        if (!path) return;
        fetch('/api/skills/open', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            if (this.openSkillTab) {
                this.openSkillTab({
                    name: data.filename || 'SKILL.md',
                    path: data.path,
                    content: data.content || '',
                    referenceContent: data.reference_content || '',
                    referencePath: data.reference_path || '',
                    editable: data.editable !== false,
                });
            }
            this.switchView('code');
        })
        .catch(error => {
            alert(`${this.t('status.openFailed')}: ${error.message}`);
        });
    },

    editSkillReference(path) {
        if (!path) return;
        fetch('/api/skills/open_reference', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            if (this.openSkillTab) {
                this.openSkillTab({
                    name: data.filename || 'reference.md',
                    path: data.path,
                    content: data.content || '',
                    editable: data.editable !== false,
                });
            }
            this.switchView('code');
        })
        .catch(error => {
            alert(`${this.t('status.openFailed')}: ${error.message}`);
        });
    },

    viewRemoteSkill(slug) {
        if (!slug) return;
        fetch('/api/skills/open_remote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ slug }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            if (this.openSkillTab) {
                this.openSkillTab({
                    name: data.filename || `${slug}.md`,
                    path: data.path,
                    content: data.content || '',
                    editable: false,
                });
            }
            this.switchView('code');
        })
        .catch(error => {
            alert(`${this.t('status.openFailed')}: ${error.message}`);
        });
    },

    openExternalLink(url) {
        if (!url) return;
        window.open(url, '_blank', 'noopener,noreferrer');
    },

    applyCodeFontSize() {
        const size = `${this.codeFontSize}px`;
        document.querySelectorAll('.code-input').forEach(el => {
            el.style.fontSize = size;
        });
        document.querySelectorAll('.code-highlight').forEach(el => {
            el.style.fontSize = size;
        });
        document.querySelectorAll('.code-highlight code').forEach(el => {
            el.style.fontSize = size;
        });
        document.querySelectorAll('.code-cell-output').forEach(el => {
            el.style.fontSize = size;
        });
        const textEditor = document.getElementById('text-file-editor');
        if (textEditor) {
            textEditor.style.fontSize = size;
        }
    },

    adjustFontSize(delta) {
        const next = Math.min(20, Math.max(10, this.codeFontSize + delta));
        this.codeFontSize = next;
        this.applyCodeFontSize();
    },

    getDataFramePreviewLimits() {
        const rowsInput = document.getElementById('df-preview-max-rows');
        const colsInput = document.getElementById('df-preview-max-cols');

        let rows = rowsInput ? parseInt(rowsInput.value, 10) : 50;
        let cols = colsInput ? parseInt(colsInput.value, 10) : 20;

        if (!Number.isFinite(rows)) rows = 50;
        if (!Number.isFinite(cols)) cols = 20;

        rows = Math.min(500, Math.max(1, rows));
        cols = Math.min(200, Math.max(1, cols));

        if (rowsInput && String(rowsInput.value) !== String(rows)) rowsInput.value = String(rows);
        if (colsInput && String(colsInput.value) !== String(cols)) colsInput.value = String(cols);

        return { rows, cols };
    },

    // ── Memory Bar ──────────────────────────────────────────────────────────

    startMemoryMonitor() {
        // Fetch immediately, then poll every 5 seconds
        this.updateMemoryBar();
        setInterval(() => this.updateMemoryBar(), 5000);
    },

    updateMemoryBar() {
        fetch('/api/memory')
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (!data) return;
                const processMb = data.process_mb;
                const totalMb   = data.total_mb;
                const usedMb    = data.used_mb;   // total system used (includes this process)

                const fmtGb = mb => mb != null ? (mb / 1024).toFixed(1) + ' GB' : '--';

                const barProcess = document.getElementById('memory-bar-process');
                const barOther   = document.getElementById('memory-bar-other');
                const barText    = document.getElementById('memory-bar-text');
                const lblProcess = document.getElementById('memory-label-process');
                const lblOther   = document.getElementById('memory-label-other');

                if (!barProcess || !barOther || !barText) return;

                const isDark = document.documentElement.classList.contains('app-skin-dark');
                const otherColor = isDark ? '#5a6172' : '#adb5bd';

                // Sync legend dot color with current theme
                const otherDot = document.getElementById('memory-other-dot');
                if (otherDot) otherDot.style.background = otherColor;
                if (barOther) barOther.style.background = otherColor;

                if (totalMb && processMb != null) {
                    // Green  = this process
                    // Gray   = rest of system used (usedMb - processMb)
                    const otherMb = Math.max(0, (usedMb || 0) - processMb);
                    const pPct = Math.min(100, (processMb / totalMb) * 100);
                    const oPct = Math.min(100 - pPct, (otherMb  / totalMb) * 100);

                    barProcess.style.width = pPct.toFixed(1) + '%';
                    barOther.style.left    = pPct.toFixed(1) + '%';
                    barOther.style.width   = oPct.toFixed(1) + '%';

                    // Top text: "已用 Y.Y GB / 总 Z.Z GB"
                    barText.textContent = fmtGb(usedMb) + ' / ' + fmtGb(totalMb);

                    // Bottom labels:
                    //   绿色 → 本程序占用 (e.g. "0.8 GB")
                    //   灰色 → 本机已用   (total used, e.g. "6.2 GB")
                    if (lblProcess) lblProcess.textContent = fmtGb(processMb);
                    if (lblOther)   lblOther.textContent   = fmtGb(usedMb);
                } else if (processMb != null) {
                    // No system total available — just show process usage
                    barProcess.style.width = '100%';
                    barOther.style.width   = '0%';
                    barText.textContent    = fmtGb(processMb);
                    if (lblProcess) lblProcess.textContent = fmtGb(processMb);
                    if (lblOther)   lblOther.textContent   = '--';
                }
            })
            .catch(() => {/* silent fail */});
    },

    // ── Collapsible Cards ─────────────────────────────────────────────────────
    /**
     * initCollapsibleCards([root])
     *
     * Scans every `.card` inside `root` (default: document) that has both a
     * `.card-header` and a `.card-body`, and injects a toggle button that lets
     * the user collapse / expand the card body.
     *
     * Cards opt-out with the  data-no-collapse  attribute.
     * State is persisted in localStorage so panels remember their position
     * after a soft refresh.
     *
     * Safe to call multiple times — already-initialised cards are skipped.
     */
    initCollapsibleCards(root) {
        root = root || document;
        root.querySelectorAll('.card').forEach((card, idx) => {
            // ── opt-out ────────────────────────────────────────────────────
            if ('noCollapse' in card.dataset) return;

            const header = card.querySelector(':scope > .card-header');
            const body   = card.querySelector(':scope > .card-body');
            if (!header || !body) return;

            // Already initialised?
            if (header.querySelector('.card-collapse-btn')) return;

            // ── stable unique ID for localStorage ──────────────────────────
            // Walk up to find a real id, or assign a data-cc-id to the card.
            if (!card.dataset.ccId) {
                card.dataset.ccId = card.id || `cc-${Date.now()}-${idx}`;
            }
            const storageKey = `ov:a:cc-${card.dataset.ccId}`;

            // ── inject toggle button ───────────────────────────────────────
            const btn = document.createElement('button');
            btn.type      = 'button';
            btn.className = 'card-collapse-btn';
            btn.setAttribute('aria-label', 'Toggle card');
            btn.innerHTML = '<span class="cc-chevron"><i class="fas fa-chevron-up"></i></span>';

            header.classList.add('cc-header');
            header.appendChild(btn);

            // ── prepare body for CSS transition ───────────────────────────
            body.classList.add('cc-animated');

            // ── save original flex value so we can restore it on expand ──
            // Cards with flex:1 (e.g. adata-status) must shrink when collapsed
            // so sibling cards below them can move up.
            const origFlex = card.style.flex || '';

            // ── toggle logic (shared by button and header click) ──────────
            const toggle = () => {
                const isCollapsed = btn.classList.contains('collapsed');
                if (isCollapsed) {
                    // Expand: restore flex first so the card can grow
                    card.style.flex          = origFlex;
                    body.style.paddingTop    = '';
                    body.style.paddingBottom = '';
                    body.style.maxHeight     = body.scrollHeight + 'px';
                    btn.classList.remove('collapsed');
                    localStorage.removeItem(storageKey);
                    // After animation, remove max-height so dynamic content can grow
                    body.addEventListener('transitionend', function onEnd() {
                        if (!btn.classList.contains('collapsed')) {
                            body.style.maxHeight = '';
                            requestAnimationFrame(() => this.syncPanelHeight());
                        }
                        body.removeEventListener('transitionend', onEnd);
                    }.bind(this));
                } else {
                    // Collapse: pin current height first, then animate to 0
                    body.style.maxHeight = body.scrollHeight + 'px';
                    requestAnimationFrame(() => requestAnimationFrame(() => {
                        body.style.maxHeight     = '0';
                        body.style.paddingTop    = '0';
                        body.style.paddingBottom = '0';
                    }));
                    btn.classList.add('collapsed');
                    localStorage.setItem(storageKey, '1');
                    // After animation: shrink card and re-sync panel height
                    body.addEventListener('transitionend', function onEnd() {
                        if (btn.classList.contains('collapsed')) {
                            card.style.flex = '0 0 auto';
                            // Let layout reflow, then recalculate min-height
                            requestAnimationFrame(() => this.syncPanelHeight());
                        }
                        body.removeEventListener('transitionend', onEnd);
                    }.bind(this));
                }
            };

            btn.addEventListener('click', e => { e.stopPropagation(); toggle(); });

            // Clicking the header itself (not interactive child elements) also toggles
            header.addEventListener('click', e => {
                if (e.target.closest('button:not(.card-collapse-btn), input, select, a, label')) return;
                toggle();
            });

            // ── restore persisted collapsed state ─────────────────────────
            // Do this AFTER wiring events so the card is fully set up.
            // If the card is inside a hidden container (scrollHeight === 0),
            // skip setting maxHeight – it will be initialised on first interaction.
            if (localStorage.getItem(storageKey) === '1') {
                body.style.maxHeight     = '0';
                body.style.paddingTop    = '0';
                body.style.paddingBottom = '0';
                btn.classList.add('collapsed');
                // Immediately shrink the card so siblings are not pushed down
                card.style.flex = '0 0 auto';
            }
        });
    },

    // ── Custom X/Y Axes ──────────────────────────────────────────────────────

    /**
     * Toggle the custom axes row visibility.
     */
    toggleCustomAxes(event) {
        if (event) event.preventDefault();
        const row     = document.getElementById('custom-axes-row');
        const embSel  = document.getElementById('embedding-select');
        const icon    = document.getElementById('custom-axes-icon');
        if (!row) return;

        const isOpen = row.style.display !== 'none' && row.style.display !== '';

        if (!isOpen) {
            // ── Open custom axes ────────────────────────────────────────────
            row.style.display = '';
            // Sync selectors to current embedding as a starting point (once only)
            if (!this._customAxesActive) {
                const emb = (embSel || {}).value;
                if (emb && emb !== 'random') this._syncCustomAxesToPreset(emb);
            }
            // Hide the embedding select to make it clear it's not used
            if (embSel) embSel.style.display = 'none';
            if (icon)   { icon.classList.remove('fa-pen-alt'); icon.classList.add('fa-undo'); }
            this._customAxesActive = true;
            // Persist activation state
            try { localStorage.setItem(this._PERSIST_NS_SESSION + '__custom-axes-active', 'true'); } catch(_) {}
        } else {
            // ── Close custom axes — revert to preset mode ───────────────────
            row.style.display = 'none';
            this._customAxesActive = false;
            if (embSel) embSel.style.display = '';
            if (icon)   { icon.classList.remove('fa-undo'); icon.classList.add('fa-pen-alt'); }
            const badge = document.getElementById('custom-axes-badge');
            if (badge) badge.style.display = 'none';
            // Clear activation state
            try { localStorage.removeItem(this._PERSIST_NS_SESSION + '__custom-axes-active'); } catch(_) {}
            // Re-trigger plot with the preset
            const emb = (embSel || {}).value;
            if (emb) this.updatePlot();
        }
    },

    /**
     * Called when the user picks a quick embedding preset.
     * Syncs the custom X/Y pickers to match and triggers a plot update.
     */
    onEmbeddingPresetChange() {
        const embSel = document.getElementById('embedding-select');
        const emb    = (embSel || {}).value;
        if (!emb) return;
        // Sync custom pickers to this embedding (if it's a real obsm key, not random)
        if (emb !== 'random') this._syncCustomAxesToPreset(emb);
        // Clear custom mode — user is back to preset
        this._customAxesActive = false;
        const badge = document.getElementById('custom-axes-badge');
        const row   = document.getElementById('custom-axes-row');
        const icon  = document.getElementById('custom-axes-icon');
        if (badge) badge.style.display = 'none';
        if (row)   row.style.display   = 'none';
        if (icon)  { icon.classList.remove('fa-undo'); icon.classList.add('fa-pen-alt'); }
        if (embSel) embSel.style.display = '';  // ensure visible
        this.updatePlot();
    },

    /**
     * Sync the custom X/Y selectors to obsm:embKey:0 / obsm:embKey:1.
     */
    _syncCustomAxesToPreset(embKey) {
        for (const ax of ['x', 'y']) {
            const srcSel = document.getElementById(`${ax}-axis-source`);
            const dimSel = document.getElementById(`${ax}-axis-dim`);
            if (srcSel) srcSel.value = 'obsm';
            this._populateAxisKeySels(ax);  // re-fill with obsm keys
            const keySel = document.getElementById(`${ax}-axis-key-select`);
            if (keySel) keySel.value = embKey;
            this._updateAxisDims(ax, embKey);
            if (dimSel) dimSel.value = ax === 'x' ? '0' : '1';
            // Show select, hide input
            const inp = document.getElementById(`${ax}-axis-key-input`);
            if (keySel) keySel.style.display = '';
            if (inp)    inp.style.display    = 'none';
            if (dimSel) dimSel.style.display = '';
        }
    },

    /**
     * Populate the key select for a given axis based on the current source type.
     */
    _populateAxisKeySels(ax) {
        const source  = (document.getElementById(`${ax}-axis-source`) || {}).value || 'obsm';
        const keySel  = document.getElementById(`${ax}-axis-key-select`);
        const keyInp  = document.getElementById(`${ax}-axis-key-input`);
        const dimSel  = document.getElementById(`${ax}-axis-dim`);
        const data    = this._customAxesData || {};

        if (!keySel) return;

        if (source === 'obsm') {
            keySel.style.display = '';
            if (keyInp) keyInp.style.display = 'none';
            if (dimSel) dimSel.style.display = '';
            keySel.innerHTML = (data.embeddings || [])
                .map(e => `<option value="${e}">${(e.startsWith('X_') ? e.slice(2) : e).toUpperCase()}</option>`)
                .join('');
            // Fill dims for first item
            const firstEmb = (data.embeddings || [])[0] || '';
            this._updateAxisDims(ax, firstEmb);
        } else if (source === 'obs') {
            keySel.style.display = '';
            if (keyInp) keyInp.style.display = 'none';
            if (dimSel) dimSel.style.display = 'none';
            keySel.innerHTML = (data.obs_columns || [])
                .map(c => `<option value="${c}">${c}</option>`)
                .join('');
        } else {
            // gene
            keySel.style.display = 'none';
            if (keyInp) keyInp.style.display = '';
            if (dimSel) dimSel.style.display = 'none';
        }
    },

    /**
     * Fill the dimension picker for an obsm key (infer ndim from adata or default to 0/1/2).
     */
    _updateAxisDims(ax, embKey) {
        const dimSel = document.getElementById(`${ax}-axis-dim`);
        if (!dimSel) return;
        // Try to get ndim from stored currentData obsm info (if available)
        const ndim = (this._customAxesData && this._customAxesData.obsm_ndims && embKey)
            ? (this._customAxesData.obsm_ndims[embKey] || 10)
            : 10;
        const count = Math.min(ndim, 10);  // Show up to 10 dims
        dimSel.innerHTML = Array.from({ length: count }, (_, i) =>
            `<option value="${i}">${i + 1}</option>`
        ).join('');
    },

    /**
     * Called when the axis source (obsm/obs/gene) changes.
     */
    onAxisSourceChange(ax) {
        this._populateAxisKeySels(ax);
        this._markCustomAxes();
        this.onCustomAxisApply();
    },

    /**
     * Called when the key select changes (for obsm: update dims).
     */
    onAxisKeyChange(ax) {
        const source = (document.getElementById(`${ax}-axis-source`) || {}).value;
        if (source === 'obsm') {
            const key = (document.getElementById(`${ax}-axis-key-select`) || {}).value;
            this._updateAxisDims(ax, key);
        }
        this._markCustomAxes();
        this.onCustomAxisApply();
    },

    /**
     * Show the "Custom" badge on the embedding preset and mark custom mode active.
     */
    _markCustomAxes() {
        this._customAxesActive = true;
        const badge  = document.getElementById('custom-axes-badge');
        const preset = document.getElementById('embedding-select');
        const icon   = document.getElementById('custom-axes-icon');
        // Show badge, ensure embedding select is hidden (it's irrelevant)
        if (badge)  badge.style.display = '';
        if (preset) preset.style.display = 'none';
        if (icon)   { icon.classList.remove('fa-pen-alt'); icon.classList.add('fa-undo'); }
    },

    /**
     * Trigger a plot update when any custom axis changes.
     */
    onCustomAxisApply() {
        // Small debounce for text inputs
        clearTimeout(this._customAxesTimer);
        this._customAxesTimer = setTimeout(() => this.updatePlot(), 300);
    },

    /**
     * Return the current x_axis / y_axis encoded strings for the backend.
     * Format:  obsm:<key>:<dim>   obs:<col>   gene:<name>
     * Returns null if not in custom mode or no valid selection.
     */
    getXYAxes() {
        const row = document.getElementById('custom-axes-row');
        const customVisible = row && row.style.display !== 'none';
        if (!customVisible && !this._customAxesActive) return null;

        const _encode = (ax) => {
            const source = (document.getElementById(`${ax}-axis-source`) || {}).value || 'obsm';
            if (source === 'obsm') {
                const key = (document.getElementById(`${ax}-axis-key-select`) || {}).value;
                const dim = (document.getElementById(`${ax}-axis-dim`) || {}).value || '0';
                if (!key) return null;
                return `obsm:${key}:${dim}`;
            } else if (source === 'obs') {
                const key = (document.getElementById(`${ax}-axis-key-select`) || {}).value;
                if (!key) return null;
                return `obs:${key}`;
            } else {
                const gene = ((document.getElementById(`${ax}-axis-key-input`) || {}).value || '').trim();
                if (!gene) return null;
                return `gene:${gene}`;
            }
        };

        const x = _encode('x');
        const y = _encode('y');
        if (!x || !y) return null;
        return { x_axis: x, y_axis: y };
    },

});

// ============================================================================
// ── Input & State Persistence ────────────────────────────────────────────────
// Comprehensive localStorage-based persistence for all user inputs and UI state.
// Namespace  ov:a:  → always kept (agent/env settings, view, etc.)
// Namespace  ov:s:  → session (cleared on explicit "Reset" click)
// ============================================================================
Object.assign(SingleCellAnalysis.prototype, {

    // ── initialisation ───────────────────────────────────────────────────────

    /**
     * Call once on startup (before data loads).
     * Initialises constants as OWN properties (avoids prototype-chain lookup
     * inside event callbacks), restores all static persisted inputs, and
     * wires event listeners for future saves.
     */
    initInputPersistence() {
        // ── constants as own instance properties ───────────────────────────
        this._PERSIST_NS_ALWAYS  = 'ov:a:';
        this._PERSIST_NS_SESSION = 'ov:s:';

        /** IDs that must NEVER be persisted */
        this._PERSIST_EXCLUDE = new Set([
            'fileInput', 'fileInputPreview', 'notebook-file-input',
            'agent-input',          // temporary query textarea
            'text-file-editor', 'md-file-editor',  // file content editors
            'kernel-select',        // depends on live kernels
        ]);

        /**
         * IDs whose <option> list is built dynamically from loaded data.
         * Restored AFTER updateUI() populates the options.
         */
        this._PERSIST_DYNAMIC_IDS = new Set([
            'embedding-select', 'color-select',
            'traj-pseudotime-col', 'traj-basis', 'traj-paga-groups',
            'traj-heatmap-pseudotime', 'traj-heatmap-layer',
            'deg-violin-groupby', 'deg-violin-layer',
            // Note: x-axis-key-select, y-axis-key-select are restored in custom axes logic
        ]);

        /** IDs in the ALWAYS namespace (never cleared by clearPersistedSession) */
        this._PERSIST_ALWAYS_IDS = new Set([
            'agent-api-base', 'agent-api-key', 'agent-model',
            'agent-temperature', 'agent-top-p', 'agent-max-tokens',
            'agent-timeout', 'agent-system-prompt',
            'env-mirror-select', 'env-pip-extra',
            'env-custom-channel', 'env-conda-extra',
        ]);

        // 1. Restore static (non-dynamic) inputs right away
        this._restoreAllStatic();

        // 2. Restore extra UI state (active view, renderer, etc.)
        this._restoreUIState();

        // 3. Wire save listeners on every input/change event (capture phase
        //    so we catch events before any stopPropagation in components)
        document.addEventListener('change', e => this._persistOnEvent(e), true);
        document.addEventListener('input',  e => this._persistOnEvent(e), true);
    },

    // ── event handler ────────────────────────────────────────────────────────

    _persistOnEvent(e) {
        const el = e.target;
        if (!el || !el.id) return;
        if (this._PERSIST_EXCLUDE.has(el.id)) return;
        if (!['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) return;
        this._persistSaveEl(el);
    },

    // ── low-level save / restore ─────────────────────────────────────────────

    /** Save one element's current value to localStorage */
    _persistSaveEl(el) {
        try {
            const val = (el.type === 'checkbox') ? String(el.checked) : el.value;
            const ns  = this._PERSIST_ALWAYS_IDS.has(el.id)
                ? this._PERSIST_NS_ALWAYS
                : this._PERSIST_NS_SESSION;
            localStorage.setItem(ns + el.id, val);
        } catch (_) {}
    },

    /** Save an arbitrary key/value into the session namespace */
    persistStateVal(key, val) {
        try {
            localStorage.setItem(this._PERSIST_NS_SESSION + '__' + key, String(val));
        } catch (_) {}
    },

    /** Load an arbitrary key from session namespace */
    loadStateVal(key, defaultVal = null) {
        try {
            const v = localStorage.getItem(this._PERSIST_NS_SESSION + '__' + key);
            return (v !== null) ? v : defaultVal;
        } catch (_) { return defaultVal; }
    },

    /** Save an arbitrary key/value into the always namespace */
    persistAlwaysVal(key, val) {
        try {
            localStorage.setItem(this._PERSIST_NS_ALWAYS + '__' + key, String(val));
        } catch (_) {}
    },

    loadAlwaysVal(key, defaultVal = null) {
        try {
            const v = localStorage.getItem(this._PERSIST_NS_ALWAYS + '__' + key);
            return (v !== null) ? v : defaultVal;
        } catch (_) { return defaultVal; }
    },

    /**
     * Restore one element by id.
     * For <select>, only restores if the saved value actually exists
     * in the current options (guards against stale data).
     */
    _persistRestoreOne(id, ns) {
        try {
            const el  = document.getElementById(id);
            const val = localStorage.getItem(ns + id);
            if (!el || val === null) return false;
            if (el.type === 'checkbox') {
                el.checked = (val === 'true');
            } else if (el.tagName === 'SELECT') {
                if ([...el.options].some(o => o.value === val)) {
                    el.value = val;
                } else {
                    return false;
                }
            } else {
                el.value = val;
            }
            return true;
        } catch (_) { return false; }
    },

    // ── batch restore helpers ────────────────────────────────────────────────

    /** Restore all persisted static (non-dynamic) inputs from localStorage */
    _restoreAllStatic() {
        try {
            const skipIds = new Set([
                ...this._PERSIST_EXCLUDE,
                ...this._PERSIST_DYNAMIC_IDS,
            ]);
            for (const ns of [this._PERSIST_NS_SESSION, this._PERSIST_NS_ALWAYS]) {
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    if (!key || !key.startsWith(ns)) continue;
                    const id = key.slice(ns.length);
                    if (id.startsWith('__')) continue;  // state keys, not element ids
                    if (skipIds.has(id)) continue;
                    this._persistRestoreOne(id, ns);
                }
            }
        } catch (_) {}
    },

    /**
     * Restore data-dependent selects AND controls that are programmatically
     * reset by updateUI() (e.g. point-size-slider via initPointSizeSlider).
     * Called at the END of updateUI(), after options have been populated.
     * Returns a Set of IDs that were successfully restored.
     */
    restoreDynamicInputs() {
        const ns = this._PERSIST_NS_SESSION;
        const restored = new Set();

        // ── data-dependent selects ────────────────────────────────────────
        for (const id of this._PERSIST_DYNAMIC_IDS) {
            if (this._persistRestoreOne(id, ns)) restored.add(id);
        }

        // ── custom axes text/select inputs ────────────────────────────────
        // Step 1: Restore source values first (needed to determine which UI to show)
        const xSourceRestored = this._persistRestoreOne('x-axis-source', ns);
        const ySourceRestored = this._persistRestoreOne('y-axis-source', ns);
        const hasCustomAxes = xSourceRestored || ySourceRestored;

        // Step 2: Check if custom axes mode was active
        const wasActive = localStorage.getItem(ns + '__custom-axes-active') === 'true';

        // Step 3: If custom axes were used, restore the full UI state
        if (hasCustomAxes && wasActive) {
            // Activate custom axes mode
            const customRow = document.getElementById('custom-axes-row');
            const embSelect = document.getElementById('embedding-select');
            const badge     = document.getElementById('custom-axes-badge');
            const icon      = document.getElementById('custom-axes-icon');
            const toggleBtn = document.getElementById('custom-axes-toggle');

            if (customRow) customRow.style.display = '';
            if (embSelect) embSelect.style.display = 'none';
            if (badge)     badge.style.display = '';
            if (icon)      { icon.classList.remove('fa-pen-alt'); icon.classList.add('fa-undo'); }
            if (toggleBtn) toggleBtn.innerHTML = '<i class="fas fa-undo-alt me-1"></i>';
            this._customAxesActive = true;

            // Step 4: For each axis, populate UI based on source, then restore values
            ['x', 'y'].forEach(ax => {
                // Populate options based on restored source
                this._populateAxisKeySels(ax);
                // Restore key-select/key-input value AFTER populating options
                const source = (document.getElementById(`${ax}-axis-source`) || {}).value;
                if (source === 'obsm' || source === 'obs') {
                    if (this._persistRestoreOne(`${ax}-axis-key-select`, ns)) {
                        restored.add(`${ax}-axis-key-select`);
                    }
                    // If obsm, also restore dim and update dim options
                    if (source === 'obsm') {
                        const key = (document.getElementById(`${ax}-axis-key-select`) || {}).value;
                        if (key) this._updateAxisDims(ax, key);
                        if (this._persistRestoreOne(`${ax}-axis-dim`, ns)) {
                            restored.add(`${ax}-axis-dim`);
                        }
                    }
                } else if (source === 'gene') {
                    if (this._persistRestoreOne(`${ax}-axis-key-input`, ns)) {
                        restored.add(`${ax}-axis-key-input`);
                    }
                }
            });
            // Mark that custom axes were restored
            restored.add('custom-axes');
        } else {
            // If custom axes were not active, still restore the values (for future use)
            // but don't activate the UI
            ['x-axis-key-input', 'y-axis-key-input',
             'x-axis-dim',       'y-axis-dim'].forEach(id => {
                this._persistRestoreOne(id, ns);
            });
        }

        // ── point-size slider (reset to auto by initPointSizeSlider) ─────
        try {
            const sizeSlider = document.getElementById('point-size-slider');
            const sizeLabel  = document.getElementById('point-size-value');
            const savedSize  = localStorage.getItem(ns + 'point-size-slider');
            const isAuto     = localStorage.getItem(ns + '__point-size-auto') !== 'false';
            if (sizeSlider && savedSize !== null && !isAuto) {
                sizeSlider.value       = savedSize;
                sizeSlider.dataset.auto = 'false';
                if (sizeLabel) sizeLabel.textContent = parseFloat(savedSize).toFixed(1);
                restored.add('point-size-slider');
            }
        } catch (_) {}

        // ── opacity slider (update display label after restore) ───────────
        try {
            const opacitySlider = document.getElementById('opacity-slider');
            const opacityLabel  = document.getElementById('opacity-value');
            const savedOpacity  = localStorage.getItem(ns + 'opacity-slider');
            if (opacitySlider && savedOpacity !== null) {
                opacitySlider.value = savedOpacity;
                if (opacityLabel) opacityLabel.textContent = parseFloat(savedOpacity).toFixed(2);
                restored.add('opacity-slider');
            }
        } catch (_) {}

        // ── density adjust slider (label + control state) ─────────────────
        try {
            const densitySlider = document.getElementById('density-adjust-slider');
            const densityLabel  = document.getElementById('density-adjust-value');
            const densityToggle = document.getElementById('density-enable-toggle');
            const savedDensity  = localStorage.getItem(ns + 'density-adjust-slider');
            const savedEnabled  = localStorage.getItem(ns + 'density-enable-toggle');
            if (densitySlider && savedDensity !== null) {
                densitySlider.value = savedDensity;
                if (densityLabel) densityLabel.textContent = parseFloat(savedDensity).toFixed(2);
                restored.add('density-adjust-slider');
            } else if (densityLabel) {
                densityLabel.textContent = parseFloat((densitySlider && densitySlider.value) || '1').toFixed(2);
            }
            if (densityToggle && savedEnabled !== null) {
                densityToggle.checked = (savedEnabled === 'true');
                restored.add('density-enable-toggle');
            } else if (densityToggle) {
                densityToggle.checked = false;
            }
            if (this._syncDensityControlStateBySelection) this._syncDensityControlStateBySelection();
        } catch (_) {}

        // ── static controls that need label updates ───────────────────────
        // (vmin-input, vmax-input, gene-input, palette-select, category-palette-select
        //  are restored by _restoreAllStatic() on page load and are stable here)

        return restored;
    },

    // ── extra UI state (view, renderer, custom-axes) ─────────────────────────

    _restoreUIState() {
        // Restore active view tab
        const view = this.loadAlwaysVal('activeView');
        if (view && view !== 'visualization') {
            // Defer to after DOM is ready
            requestAnimationFrame(() => {
                if (this.switchView) this.switchView(view);
            });
        }
        // Renderer is restored after data loads (see restoreDynamicInputs)
    },

    /** Persist the active view name whenever it changes */
    persistView(view) {
        this.persistAlwaysVal('activeView', view);
    },

    /** Persist renderer mode whenever it changes */
    persistRenderer(mode) {
        this.persistStateVal('renderer', mode || 'auto');
    },

    /** Restore renderer mode — called after data loads */
    restoreRenderer() {
        const mode = this.loadStateVal('renderer', 'auto');
        if (mode && mode !== 'auto' && this.setRenderer) {
            // Use requestAnimationFrame to ensure the plot is ready
            requestAnimationFrame(() => this.setRenderer(mode));
        }
    },

    // ── clear session (called on Reset) ──────────────────────────────────────

    /**
     * Remove all session-scoped keys from localStorage.
     * Always-scoped keys (agent/env settings) are kept.
     * Card collapse states are also reset.
     */
    clearPersistedSession() {
        try {
            const keys = [];
            for (let i = 0; i < localStorage.length; i++) {
                const k = localStorage.key(i);
                if (k && k.startsWith(this._PERSIST_NS_SESSION)) keys.push(k);
            }
            keys.forEach(k => localStorage.removeItem(k));
        } catch (_) {}
    },
});
