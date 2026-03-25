/**
 * OmicVerse Single Cell Analysis - Personal Center only
 */

Object.assign(SingleCellAnalysis.prototype, {

    setupAccountCenter() {
        this.accountTokenStorageKey = 'omicverse.accountToken';
        this.accountProfileStorageKey = 'omicverse.accountProfile';
        this.accountConfigured = true;
        this.accountAuthHydrated = false;
        this.accountUser = this.readCachedAccountProfile();
        this.accountMenuOpen = false;
        this.accountCenterEditable = false;
        this.runtimeConfig = this.getRuntimeConfigDefaults();
        this.bindAccountCenterEvents();
        this.applyRuntimeBranding();
        this.updateAccountMenu();
        this.updateGatewayAccess({ redirectIfBlocked: false });
        this.refreshAccountProfile();
        this.loadRuntimeConfig();
    },

    bindAccountCenterEvents() {
        const byId = (id) => document.getElementById(id);
        const dropdown = byId('account-menu-dropdown');
        const toggle = byId('account-menu-toggle');
        const panel = byId('account-menu-panel');
        const authModal = byId('accountAuthModal');

        if (toggle) {
            toggle.addEventListener('click', (event) => {
                event.preventDefault();
                event.stopPropagation();
                this.toggleAccountMenu();
            });
        }

        if (panel) {
            panel.addEventListener('click', (event) => {
                event.stopPropagation();
            });
        }

        document.addEventListener('click', (event) => {
            if (!this.accountMenuOpen || !dropdown) return;
            if (!dropdown.contains(event.target)) {
                this.closeAccountMenu();
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && this.accountMenuOpen) {
                this.closeAccountMenu();
            }
        });

        const clickHandlers = [
            ['account-login-link', () => this.openAuthModal('login')],
            ['account-register-link', () => this.openAuthModal('register')],
            ['account-profile-link', () => this.openAccountCenter(false)],
            ['account-settings-link', () => this.openAccountCenter(true)],
            ['account-help-link', () => this.openAccountHelp()],
            ['account-logout-link', () => this.logoutAccount()],
        ];

        clickHandlers.forEach(([id, handler]) => {
            const element = byId(id);
            if (!element) return;
            element.addEventListener('click', (event) => {
                event.preventDefault();
                handler();
            });
        });

        const loginForm = byId('account-login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', (event) => this.submitLogin(event));
        }

        const registerForm = byId('account-register-form');
        if (registerForm) {
            registerForm.addEventListener('submit', (event) => this.submitRegister(event));
        }

        ['account-login-tab', 'account-register-tab'].forEach((id) => {
            const element = byId(id);
            if (!element) return;
            element.addEventListener('shown.bs.tab', () => this.applyRuntimeBranding());
        });

        const profileForm = byId('account-profile-form');
        if (profileForm) {
            profileForm.addEventListener('submit', (event) => this.submitProfileUpdate(event));
        }

        const accountCenterForm = byId('account-center-form');
        if (accountCenterForm) {
            accountCenterForm.addEventListener('submit', (event) => this.submitAccountCenterUpdate(event));
        }

        if (authModal) {
            authModal.addEventListener('hidden.bs.modal', () => {
                this._authReturnView = null;
                this.updateGatewayAccess();
            });
        }
    },

    getRuntimeConfigDefaults() {
        return {
            launcher: 'omicverse',
            force_login: false,
            brand: {
                product_name: 'OmicVerse',
                tag: 'OmicVerse',
                logo_url: 'static/picture/logo.png',
            },
        };
    },

    async loadRuntimeConfig() {
        try {
            const response = await fetch('/api/runtime-config');
            const data = await response.json();
            if (response.ok && data) {
                const defaults = this.getRuntimeConfigDefaults();
                this.runtimeConfig = {
                    ...defaults,
                    ...data,
                    brand: {
                        ...defaults.brand,
                        ...(data.brand || {}),
                    },
                };
            }
        } catch (_) {
            this.runtimeConfig = this.runtimeConfig || this.getRuntimeConfigDefaults();
        }
        this.applyRuntimeBranding();
        this.maybeEnforceLogin();
    },

    isOmicClawLauncher() {
        return String(this.runtimeConfig?.launcher || '').toLowerCase() === 'omicclaw';
    },

    applyRuntimeBranding() {
        const brand = this.runtimeConfig?.brand || this.getRuntimeConfigDefaults().brand;
        const productName = brand.product_name || 'OmicVerse';
        const logoUrl = brand.logo_url || 'static/picture/logo.png';
        const isClaw = this.isOmicClawLauncher();
        const brandTitle = this.t(isClaw ? 'account.brandWorkspaceTitleClaw' : 'account.brandWorkspaceTitle');
        const brandSubtitle = this.t(isClaw ? 'account.brandWorkspaceSubtitleClaw' : 'account.brandWorkspaceSubtitle');

        document.querySelectorAll('[data-brand-logo]').forEach((img) => {
            img.setAttribute('src', logoUrl);
            img.setAttribute('alt', productName);
        });

        const brandTag = document.getElementById('account-auth-brand-tag');
        const brandTitleEl = document.getElementById('account-auth-brand-title');
        const brandSubtitleEl = document.getElementById('account-auth-brand-subtitle');
        if (brandTag) brandTag.textContent = brand.tag || productName;
        if (brandTitleEl) brandTitleEl.textContent = brandTitle;
        if (brandSubtitleEl) brandSubtitleEl.textContent = brandSubtitle;

        document.body.dataset.launcher = String(this.runtimeConfig?.launcher || 'omicverse');
    },

    maybeEnforceLogin() {
        if (!this.runtimeConfig?.force_login || this.accountUser || this._forceLoginPrompted) {
            return;
        }
        this._forceLoginPrompted = true;
        this.openAuthModal('login');
    },

    getAccountFieldMap(prefix) {
        const maps = {
            register: {
                display_name: 'account-register-name',
                full_name: 'account-register-full-name',
                institution: 'account-register-institution',
                research_area: 'account-register-research-area',
                usage_purpose: 'account-register-usage-purpose',
                email: 'account-register-email',
                password: 'account-register-password',
            },
            profile: {
                display_name: 'account-profile-display-name',
                full_name: 'account-profile-full-name',
                institution: 'account-profile-institution',
                research_area: 'account-profile-research-area',
                usage_purpose: 'account-profile-usage-purpose',
                email: 'account-profile-email',
            },
            center: {
                display_name: 'account-center-display-name',
                full_name: 'account-center-full-name',
                institution: 'account-center-institution',
                research_area: 'account-center-research-area',
                usage_purpose: 'account-center-usage-purpose',
                email: 'account-center-email',
            },
        };
        return maps[prefix] || {};
    },

    readAccountField(id) {
        const el = document.getElementById(id);
        return el ? String(el.value || '').trim() : '';
    },

    collectAccountProfilePayload(prefix) {
        const map = this.getAccountFieldMap(prefix);
        return {
            display_name: this.readAccountField(map.display_name),
            full_name: this.readAccountField(map.full_name),
            institution: this.readAccountField(map.institution),
            research_area: this.readAccountField(map.research_area),
            usage_purpose: this.readAccountField(map.usage_purpose),
        };
    },

    populateAccountProfileFields(prefix, user = {}, editable = false) {
        const map = this.getAccountFieldMap(prefix);
        const values = {
            display_name: user.display_name || '',
            full_name: user.full_name || '',
            institution: user.institution || '',
            research_area: user.research_area || '',
            usage_purpose: user.usage_purpose || '',
            email: user.email || '',
        };

        Object.entries(map).forEach(([key, id]) => {
            const element = document.getElementById(id);
            if (!element) return;
            element.value = values[key] || '';
            if (key === 'email') {
                element.readOnly = true;
                return;
            }
            if (prefix !== 'register') {
                element.readOnly = !editable;
            }
        });
    },

    formatAccountValue(value, fallback = '-') {
        const text = String(value || '').trim();
        return text || fallback;
    },

    toggleAccountMenu() {
        if (this.accountMenuOpen) {
            this.closeAccountMenu();
        } else {
            this.openAccountMenu();
        }
    },

    openAccountMenu() {
        const dropdown = document.getElementById('account-menu-dropdown');
        const toggle = document.getElementById('account-menu-toggle');
        const panel = document.getElementById('account-menu-panel');
        if (!dropdown || !toggle || !panel) return;
        dropdown.classList.add('show');
        panel.classList.add('show');
        toggle.setAttribute('aria-expanded', 'true');
        this.accountMenuOpen = true;
    },

    closeAccountMenu() {
        const dropdown = document.getElementById('account-menu-dropdown');
        const toggle = document.getElementById('account-menu-toggle');
        const panel = document.getElementById('account-menu-panel');
        if (dropdown) dropdown.classList.remove('show');
        if (panel) panel.classList.remove('show');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');
        this.accountMenuOpen = false;
    },

    getAccountToken() {
        return localStorage.getItem(this.accountTokenStorageKey) || '';
    },

    setAccountToken(token) {
        if (token) {
            localStorage.setItem(this.accountTokenStorageKey, token);
        } else {
            localStorage.removeItem(this.accountTokenStorageKey);
        }
    },

    readCachedAccountProfile() {
        try {
            const raw = localStorage.getItem(this.accountProfileStorageKey);
            return raw ? JSON.parse(raw) : null;
        } catch (_) {
            return null;
        }
    },

    cacheAccountProfile(user) {
        if (user) {
            localStorage.setItem(this.accountProfileStorageKey, JSON.stringify(user));
        } else {
            localStorage.removeItem(this.accountProfileStorageKey);
        }
    },

    getAccountHeaders(includeJson = false) {
        const headers = {};
        if (includeJson) {
            headers['Content-Type'] = 'application/json';
        }
        const token = this.getAccountToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    },

    canAccessGateway() {
        if (!this.accountAuthHydrated && !this.accountUser) {
            return true;
        }
        return !!(this.accountUser || this.getAccountToken());
    },

    updateGatewayAccess({ redirectIfBlocked = true } = {}) {
        const gatewayBtn = document.getElementById('view-gateway-btn');
        const gatewayNav = document.getElementById('gateway-nav');
        const allowed = this.canAccessGateway();

        if (gatewayBtn) {
            gatewayBtn.style.display = allowed ? '' : 'none';
        }
        if (!allowed && gatewayNav) {
            gatewayNav.style.display = 'none';
        }
        if (!allowed && redirectIfBlocked && this.currentView === 'gateway' && this.switchView) {
            this.switchView('visualization');
        }
    },

    updateAccountMenu() {
        const title = document.getElementById('account-menu-title');
        const subtitle = document.getElementById('account-menu-subtitle');
        const avatar = document.getElementById('account-avatar-letter');
        const menuAvatar = document.getElementById('account-menu-avatar-letter');
        const authOnlyIds = ['account-profile-link', 'account-settings-link', 'account-logout-link'];
        const guestOnlyIds = ['account-login-link', 'account-register-link'];
        const isAuthenticated = !!this.accountUser;
        const name = isAuthenticated
            ? (this.accountUser.display_name || this.accountUser.email || 'U')
            : this.t('account.guest');
        const subtitleText = !this.accountConfigured
            ? this.t('account.serverOffline')
            : (isAuthenticated ? (this.accountUser.email || '') : this.t('account.guestHint'));

        if (title) title.textContent = isAuthenticated ? name : this.t('account.center');
        if (subtitle) subtitle.textContent = subtitleText;
        if (avatar) avatar.textContent = String(name || 'G').trim().charAt(0).toUpperCase() || 'G';
        if (menuAvatar) menuAvatar.textContent = String(name || 'G').trim().charAt(0).toUpperCase() || 'G';

        authOnlyIds.forEach((id) => {
            const element = document.getElementById(id);
            if (!element) return;
            element.style.display = isAuthenticated ? '' : 'none';
        });

        guestOnlyIds.forEach((id) => {
            const element = document.getElementById(id);
            if (!element) return;
            element.style.display = isAuthenticated ? 'none' : '';
        });

        this.updateGatewayAccess();
    },

    showAccountMessage(id, message = '', tone = 'danger') {
        const box = document.getElementById(id);
        if (!box) return;
        if (!message) {
            box.style.display = 'none';
            box.textContent = '';
            box.className = 'alert d-none';
            return;
        }
        box.className = `alert alert-${tone}`;
        box.textContent = message;
        box.style.display = '';
    },

    showResendButton(email) {
        this._resendEmail = email;
        const wrap = document.getElementById('account-resend-wrap');
        if (wrap) wrap.style.display = '';
        this._startResendCooldown();
    },

    hideResendButton() {
        const wrap = document.getElementById('account-resend-wrap');
        if (wrap) wrap.style.display = 'none';
        if (this._resendTimer) {
            clearInterval(this._resendTimer);
            this._resendTimer = null;
        }
    },

    _startResendCooldown() {
        const btn = document.getElementById('account-resend-btn');
        if (!btn) return;
        let remaining = 60;
        btn.disabled = true;
        btn.textContent = this.formatResendActivationLabel(remaining);
        if (this._resendTimer) clearInterval(this._resendTimer);
        this._resendTimer = setInterval(() => {
            remaining -= 1;
            if (remaining <= 0) {
                clearInterval(this._resendTimer);
                this._resendTimer = null;
                btn.disabled = false;
                btn.textContent = this.formatResendActivationLabel();
            } else {
                btn.textContent = this.formatResendActivationLabel(remaining);
            }
        }, 1000);
    },

    formatResendActivationLabel(seconds = null) {
        const key = seconds == null ? 'account.resendActivation' : 'account.resendActivationCountdown';
        return this.t(key).replace('{seconds}', String(seconds ?? ''));
    },

    rememberAuthReturnView() {
        if (this.currentView) {
            this._authReturnView = this.currentView;
            return;
        }
        if (typeof this.loadAlwaysVal === 'function') {
            this._authReturnView = this.loadAlwaysVal('activeView') || 'visualization';
            return;
        }
        this._authReturnView = 'visualization';
    },

    consumeAuthReturnView(fallback = 'visualization') {
        const view = this._authReturnView || fallback;
        this._authReturnView = null;
        return view;
    },

    async resendActivation() {
        const email = this._resendEmail || document.getElementById('account-login-email')?.value?.trim() || '';
        if (!email) {
            this.showAccountMessage('account-auth-message', this.t('account.activationEmailPrompt'));
            return;
        }
        this._startResendCooldown();
        try {
            const response = await fetch('/api/account/resend-activation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });
            const data = await response.json();
            if (!response.ok || data.error) {
                throw new Error(data.error || this.t('account.activationResendFailed'));
            }
            this.showAccountMessage('account-auth-message', this.t('account.activationEmailSent'), 'success');
        } catch (error) {
            this.showAccountMessage(
                'account-auth-message',
                error.message || this.t('account.activationResendFailed')
            );
        }
    },

    openAuthModal(mode = 'login') {
        this.closeAccountMenu();
        this.rememberAuthReturnView();
        this.applyRuntimeBranding();
        this.hideResendButton();
        this.showAccountMessage(
            'account-auth-message',
            this.accountConfigured ? '' : this.t('account.serverOffline'),
            this.accountConfigured ? 'danger' : 'warning'
        );
        const targetId = mode === 'register' ? 'account-register-tab' : 'account-login-tab';
        const target = document.getElementById(targetId);
        if (target && window.bootstrap && bootstrap.Tab) {
            bootstrap.Tab.getOrCreateInstance(target).show();
        }
        const modalEl = document.getElementById('accountAuthModal');
        if (modalEl && window.bootstrap) {
            bootstrap.Modal.getOrCreateInstance(modalEl).show();
        } else if (!this.accountConfigured) {
            alert(this.t('account.serverOffline'));
        }
    },

    openProfileModal(editable = false) {
        this.closeAccountMenu();
        if (!this.accountUser) {
            this.openAuthModal('login');
            return;
        }
        const title = document.getElementById('account-profile-modal-title');
        const displayName = document.getElementById('account-profile-display-name');
        const email = document.getElementById('account-profile-email');
        const hint = document.getElementById('account-profile-hint');
        const saveBtn = document.getElementById('account-profile-save-btn');

        if (title) {
            title.textContent = editable ? this.t('account.settings') : this.t('account.profile');
        }
        this.populateAccountProfileFields('profile', this.accountUser, editable);
        if (hint) {
            hint.textContent = editable ? this.t('account.profileHintEditable') : this.t('account.profileHintReadonly');
        }
        if (saveBtn) {
            saveBtn.style.display = editable ? '' : 'none';
        }

        this.showAccountMessage('account-profile-message', '');
        const modalEl = document.getElementById('accountProfileModal');
        if (modalEl && window.bootstrap) {
            bootstrap.Modal.getOrCreateInstance(modalEl).show();
        }
    },

    openAccountCenter(editable = false) {
        this.closeAccountMenu();
        if (!this.accountUser) {
            this.openAuthModal('login');
            return;
        }
        this.accountCenterEditable = !!editable;
        if (this.switchView) {
            this.switchView('account');
        } else {
            this.renderAccountCenter();
        }
    },

    renderAccountCenter() {
        const user = this.accountUser;
        const editable = !!this.accountCenterEditable;
        const title = document.getElementById('account-view-title');
        const subtitle = document.getElementById('account-view-subtitle');
        const avatar = document.getElementById('account-view-avatar');
        const email = document.getElementById('account-view-email');
        const created = document.getElementById('account-view-created');
        const status = document.getElementById('account-view-status');
        const fullName = document.getElementById('account-view-full-name');
        const institution = document.getElementById('account-view-institution');
        const researchArea = document.getElementById('account-view-research-area');
        const panelTitle = document.getElementById('account-panel-title');
        const panelSubtitle = document.getElementById('account-panel-subtitle');
        const hint = document.getElementById('account-center-hint');
        const saveBtn = document.getElementById('account-center-save-btn');
        const editBtn = document.getElementById('account-center-edit-btn');

        if (!user) {
            if (title) title.textContent = this.t('account.center');
            if (subtitle) subtitle.textContent = this.t('account.guestHint');
            if (avatar) avatar.textContent = 'G';
            if (email) email.textContent = '-';
            if (created) created.textContent = this.t('account.serverOffline');
            if (status) status.textContent = this.t('account.guest');
            if (fullName) fullName.textContent = '-';
            if (institution) institution.textContent = '-';
            if (researchArea) researchArea.textContent = '-';
            return;
        }

        const name = user.display_name || user.email || this.t('account.center');
        if (title) title.textContent = name;
        if (subtitle) subtitle.textContent = user.email || '';
        if (avatar) avatar.textContent = String(name).trim().charAt(0).toUpperCase() || 'U';
        if (email) email.textContent = user.email || '-';
        if (created) created.textContent = `${this.t('account.memberSince')}: ${this.formatAccountDate(user.created_at)}`;
        if (status) status.textContent = editable ? this.t('account.editing') : this.t('account.active');
        if (fullName) fullName.textContent = this.formatAccountValue(user.full_name, this.formatAccountValue(user.display_name));
        if (institution) institution.textContent = this.formatAccountValue(user.institution);
        if (researchArea) researchArea.textContent = this.formatAccountValue(user.research_area);
        if (panelTitle) panelTitle.textContent = editable ? this.t('account.settings') : this.t('account.profile');
        if (panelSubtitle) panelSubtitle.textContent = this.t('account.profileIntro');
        this.populateAccountProfileFields('center', user, editable);
        if (hint) {
            hint.textContent = editable ? this.t('account.profileHintEditable') : this.t('account.profileHintReadonly');
        }
        if (saveBtn) {
            saveBtn.style.display = editable ? '' : 'none';
        }
        if (editBtn) {
            editBtn.style.display = editable ? 'none' : '';
        }
        this.showAccountMessage('account-center-message', '');
    },

    formatAccountDate(value) {
        if (!value) return '-';
        try {
            return new Date(value).toLocaleDateString();
        } catch (_) {
            return String(value);
        }
    },

    async refreshAccountProfile() {
        try {
            const response = await fetch('/api/account/me', {
                headers: this.getAccountHeaders(false),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Account request failed');
            }
            this.accountConfigured = data.configured !== false;
            if (data.authenticated && data.user) {
                this.accountUser = data.user;
                this.cacheAccountProfile(data.user);
            } else {
                this.accountUser = null;
                this.cacheAccountProfile(null);
                if (data.configured !== false) {
                    this.setAccountToken('');
                }
            }
        } catch (_) {
            this.accountConfigured = false;
        } finally {
            this.accountAuthHydrated = true;
        }
        this.updateAccountMenu();
        if (this.currentView === 'account') {
            this.renderAccountCenter();
        }
        this.maybeEnforceLogin();
    },

    async submitLogin(event) {
        event.preventDefault();
        const email = document.getElementById('account-login-email')?.value?.trim() || '';
        const password = document.getElementById('account-login-password')?.value || '';

        if (!this.accountConfigured) {
            this.showAccountMessage('account-auth-message', this.t('account.serverOffline'), 'warning');
            return;
        }

        try {
            const response = await fetch('/api/account/login', {
                method: 'POST',
                headers: this.getAccountHeaders(true),
                body: JSON.stringify({ email, password }),
            });
            const data = await response.json();
            if (!response.ok || data.error) {
                const msg = data.error || this.t('account.loginFailed');
                if (data.email_verification_required) {
                    this.showAccountMessage('account-auth-message', this.t('account.activationCheckEmail'), 'warning');
                    this.showResendButton(email);
                    return;
                }
                throw new Error(msg);
            }
            this.setAccountToken(data.token || '');
            this.accountUser = data.user || null;
            this.cacheAccountProfile(this.accountUser);
            this.updateAccountMenu();
            const modalEl = document.getElementById('accountAuthModal');
            if (modalEl && window.bootstrap) {
                bootstrap.Modal.getOrCreateInstance(modalEl).hide();
            }
            this.skillsLoaded = false;
            const nextView = this.consumeAuthReturnView();
            if (nextView === 'account') {
                this.openAccountCenter(false);
            } else if (this.switchView) {
                this.switchView(nextView);
            }
            this.showStatus(this.t('account.loginSuccess'), false);
        } catch (error) {
            this.showAccountMessage('account-auth-message', error.message || this.t('account.loginFailed'));
        }
    },

    async submitRegister(event) {
        event.preventDefault();
        const payload = this.collectAccountProfilePayload('register');
        const email = document.getElementById('account-register-email')?.value?.trim() || '';
        const password = document.getElementById('account-register-password')?.value || '';

        if (!this.accountConfigured) {
            this.showAccountMessage('account-auth-message', this.t('account.serverOffline'), 'warning');
            return;
        }

        try {
            const response = await fetch('/api/account/register', {
                method: 'POST',
                headers: this.getAccountHeaders(true),
                body: JSON.stringify({ ...payload, email, password }),
            });
            const data = await response.json();
            if (!response.ok || data.error) {
                throw new Error(data.error || this.t('account.registerFailed'));
            }
            // Email verification required — no token issued yet
            if (data.email_verification_required) {
                this.showAccountMessage('account-auth-message', this.t('account.activationCheckEmail'), 'success');
                this.showResendButton(email);
                return;
            }
            this.setAccountToken(data.token || '');
            this.accountUser = data.user || null;
            this.cacheAccountProfile(this.accountUser);
            this.updateAccountMenu();
            const modalEl = document.getElementById('accountAuthModal');
            if (modalEl && window.bootstrap) {
                bootstrap.Modal.getOrCreateInstance(modalEl).hide();
            }
            this.skillsLoaded = false;
            const nextView = this.consumeAuthReturnView();
            if (nextView === 'account') {
                this.openAccountCenter(true);
            } else if (this.switchView) {
                this.switchView(nextView);
            }
            this.showStatus(this.t('account.registerSuccess'), false);
        } catch (error) {
            this.showAccountMessage('account-auth-message', error.message || this.t('account.registerFailed'));
        }
    },

    async submitProfileUpdate(event) {
        event.preventDefault();
        if (!this.accountUser) return;

        const payload = this.collectAccountProfilePayload('profile');
        try {
            const response = await fetch('/api/account/profile', {
                method: 'PATCH',
                headers: this.getAccountHeaders(true),
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (!response.ok || data.error) {
                throw new Error(data.error || this.t('account.profileSaveFailed'));
            }
            this.accountUser = data.user || this.accountUser;
            this.cacheAccountProfile(this.accountUser);
            this.updateAccountMenu();
            this.renderAccountCenter();
            this.showAccountMessage('account-profile-message', this.t('account.profileSaved'), 'success');
            this.showStatus(this.t('account.profileSaved'), false);
        } catch (error) {
            this.showAccountMessage('account-profile-message', error.message || this.t('account.profileSaveFailed'));
        }
    },

    async submitAccountCenterUpdate(event) {
        event.preventDefault();
        if (!this.accountCenterEditable) return;
        const payload = this.collectAccountProfilePayload('center');
        try {
            const response = await fetch('/api/account/profile', {
                method: 'PATCH',
                headers: this.getAccountHeaders(true),
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (!response.ok || data.error) {
                throw new Error(data.error || this.t('account.profileSaveFailed'));
            }
            this.accountUser = data.user || this.accountUser;
            this.cacheAccountProfile(this.accountUser);
            this.accountCenterEditable = false;
            this.updateAccountMenu();
            this.renderAccountCenter();
            this.showAccountMessage('account-center-message', this.t('account.profileSaved'), 'success');
            this.showStatus(this.t('account.profileSaved'), false);
        } catch (error) {
            this.showAccountMessage('account-center-message', error.message || this.t('account.profileSaveFailed'));
        }
    },

    async logoutAccount() {
        try {
            await fetch('/api/account/logout', {
                method: 'POST',
                headers: this.getAccountHeaders(false),
            });
        } catch (_) {
            // Ignore network failure during local logout.
        }
        this.setAccountToken('');
        this.accountUser = null;
        this.cacheAccountProfile(null);
        this.accountAuthHydrated = true;
        this.accountCenterEditable = false;
        this.skillsLoaded = false;
        this.updateAccountMenu();
        if (this.currentView === 'account' && this.switchView) {
            this.switchView('visualization');
        }
        this.showStatus(this.t('account.logoutSuccess'), false);
    },

    openAccountHelp() {
        this.closeAccountMenu();
        alert(this.t('account.helpText'));
    },
});
