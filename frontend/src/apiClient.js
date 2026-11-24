/**
 * UniMind AI & AegisOps Unified Enterprise Frontend API Client
 * Automatically provides:
 * - Active tenant context injection via 'X-Tenant-ID'
 * - Bearer authorization token propagation
 * - Custom event notifications upon tenant switching
 * - Standardized RFC 7807 Problem Details parsing & error handling
 */

export function getTenantId() {
  return localStorage.getItem('unimind_tenant_id') || '1';
}

export function setTenantId(tid) {
  const normalized = String(tid || '1');
  localStorage.setItem('unimind_tenant_id', normalized);
  if (typeof window !== 'undefined') {
    window.dispatchEvent(
      new CustomEvent('unimind:tenant_change', {
        detail: { tenantId: normalized },
      })
    );
  }
}

export function getAuthToken() {
  return localStorage.getItem('token') || localStorage.getItem('unimind_auth_token') || '';
}

export function setAuthToken(token) {
  localStorage.setItem('token', token || '');
  localStorage.setItem('unimind_auth_token', token || '');
}

export async function apiFetch(endpoint, options = {}) {
  const headers = {
    'X-Tenant-ID': getTenantId(),
    ...(options.headers || {}),
  };

  const token = getAuthToken();
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(endpoint, {
    ...options,
    headers,
  });

  return res;
}

export async function parseApiError(response) {
  try {
    const data = await response.json();
    return {
      title: data.title || 'API Request Failed',
      detail: data.detail || data.error?.message || `HTTP ${response.status}: Unexpected error occurred.`,
      status: data.status || response.status,
      type: data.type || null,
      requestId: data.request_id || null,
    };
  } catch {
    return {
      title: 'Network / Parse Error',
      detail: `Server responded with HTTP ${response.status}.`,
      status: response.status,
      type: null,
      requestId: null,
    };
  }
}
