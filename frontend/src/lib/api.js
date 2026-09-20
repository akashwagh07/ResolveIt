/**
 * API client wrapper for ResolveIt backend.
 */

const BASE_URL = import.meta.env.VITE_API_URL || '';

function getAuthHeaders() {
  const headers = {};
  try {
    const raw = localStorage.getItem('resolveit_demo_session');
    if (raw) {
      const session = JSON.parse(raw);
      if (session.role) {
        headers['X-Demo-Role'] = session.role;
      }
      if (session.role === 'CITIZEN' && session.citizenContact) {
        headers['X-Citizen-Contact'] = session.citizenContact;
      }
      if ((session.role === 'OFFICER' || session.role === 'ADMIN') && (session.userId || session.user_id)) {
        headers['X-Demo-User-Id'] = String(session.userId || session.user_id);
      }
    }
    const passcode = sessionStorage.getItem('resolveit_demo_passcode');
    if (passcode) {
      headers['X-Demo-Passcode'] = passcode;
    }
  } catch {
    // Ignore parse errors
  }
  return headers;
}

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const authHeaders = getAuthHeaders();
  try {
    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...authHeaders,
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      let errorMessage = `API error (${response.status}): ${response.statusText}`;
      try {
        const errJson = await response.json();
        if (errJson && errJson.detail) {
          errorMessage = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
        }
      } catch {
        // Fall back to HTTP status
      }

      if (response.status === 401) {
        errorMessage = 'Wrong passcode. Ask the team for the demo passcode.';
        try {
          localStorage.removeItem('resolveit_demo_session');
          sessionStorage.removeItem('resolveit_demo_passcode');
          window.dispatchEvent(new CustomEvent('resolveit:auth_error', { detail: errorMessage }));
        } catch {
          // ignore
        }
      }

      const err = new Error(errorMessage);
      err.status = response.status;
      throw err;
    }

    return await response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Unable to reach ResolveIt backend. Please check if the server is running on port 8000.');
    }
    throw error;
  }
}

export async function getUsers(role) {
  const query = role ? `?role=${encodeURIComponent(role)}` : '';
  return await request(`/api/users${query}`);
}

export async function whoami(customHeaders = null) {
  const options = customHeaders ? { headers: customHeaders } : {};
  return await request('/api/auth/whoami', options);
}

export async function getActions(id) {
  if (!id) throw new Error('Complaint ID is required');
  return await request(`/api/complaints/${encodeURIComponent(id)}/actions`);
}

export async function runAction(id, action, params = {}) {
  if (!id) throw new Error('Complaint ID is required');
  if (!action) throw new Error('Action name is required');
  return await request(
    `/api/complaints/${encodeURIComponent(id)}/actions/${encodeURIComponent(action)}`,
    {
      method: 'POST',
      body: JSON.stringify(params),
    }
  );
}

export async function submitResolution(id, formData) {
  if (!id) throw new Error('Complaint ID is required');
  const authHeaders = getAuthHeaders();
  const url = `${BASE_URL}/api/complaints/${encodeURIComponent(id)}/resolution`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      ...authHeaders,
    },
    body: formData,
  });

  if (!response.ok) {
    let errorMessage = `Server error (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        errorMessage = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      if (response.statusText) errorMessage = `Error (${response.status}): ${response.statusText}`;
    }
    if (response.status === 401) {
      errorMessage = 'Wrong passcode. Ask the team for the demo passcode.';
      try {
        localStorage.removeItem('resolveit_demo_session');
        sessionStorage.removeItem('resolveit_demo_passcode');
        window.dispatchEvent(new CustomEvent('resolveit:auth_error', { detail: errorMessage }));
      } catch {
        // ignore
      }
    }
    const err = new Error(errorMessage);
    err.status = response.status;
    throw err;
  }

  return await response.json();
}

export async function getComplaints(filters = {}) {
  const params = new URLSearchParams();

  // Ensure empty or whitespace-only parameters are never sent to the backend
  const isValidParam = (val) => {
    if (val === null || val === undefined) return false;
    return String(val).trim().length > 0;
  };

  if (isValidParam(filters.status)) params.append('status', String(filters.status).trim());
  if (isValidParam(filters.category)) params.append('category', String(filters.category).trim());
  if (isValidParam(filters.department_id)) params.append('department_id', String(filters.department_id).trim());
  if (isValidParam(filters.assigned_officer_id)) params.append('assigned_officer_id', String(filters.assigned_officer_id).trim());
  if (isValidParam(filters.needs_review)) params.append('needs_review', String(filters.needs_review).trim());
  if (isValidParam(filters.citizen_contact)) params.append('citizen_contact', String(filters.citizen_contact).trim());
  if (isValidParam(filters.limit)) params.append('limit', String(filters.limit).trim());

  const queryString = params.toString();
  const endpoint = `/api/complaints${queryString ? `?${queryString}` : ''}`;
  const response = await request(endpoint);

  // Contract: GET /api/complaints returns an array of ComplaintSummary objects.
  return Array.isArray(response) ? response : (response?.complaints || []);
}

export async function getComplaint(id) {
  if (!id) throw new Error('Complaint ID is required');
  return await request(`/api/complaints/${encodeURIComponent(id)}`);
}

export async function getComplaintEvents(id) {
  if (!id) throw new Error('Complaint ID is required');
  return await request(`/api/complaints/${encodeURIComponent(id)}/events`);
}

export async function getDepartments() {
  return await request('/api/departments');
}

/**
 * Submit citizen complaint with optional media.
 * Posts multipart/form-data to /api/complaints without manual Content-Type header.
 * Uses an AbortController with 90s timeout.
 */
export async function createComplaint(formData, { signal: externalSignal } = {}) {
  const controller = new AbortController();
  let timedOut = false;
  const timeoutId = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, 90000); // 90 seconds timeout

  if (externalSignal) {
    if (externalSignal.aborted) {
      clearTimeout(timeoutId);
      controller.abort();
    } else {
      externalSignal.addEventListener('abort', () => {
        clearTimeout(timeoutId);
        controller.abort();
      });
    }
  }

  // Clean form data: do not send empty or placeholder fields
  const cleanedFormData = new FormData();
  for (const [key, val] of formData.entries()) {
    if (val === null || val === undefined) continue;
    if (typeof val === 'string') {
      const trimmed = val.trim();
      if (trimmed === '') continue;
      // Omit language when "auto"
      if (key === 'language' && trimmed.toLowerCase() === 'auto') continue;
      // Omit empty address
      if (key === 'address_text' && trimmed === '') continue;
      cleanedFormData.append(key, trimmed);
    } else if (val instanceof Blob || val instanceof File) {
      if (val.size > 0) {
        cleanedFormData.append(key, val);
      }
    } else {
      cleanedFormData.append(key, val);
    }
  }

  let requestInitiated = false;
  let requestSent = false;

  try {
    requestInitiated = true;
    const url = `${BASE_URL}/api/complaints`;

    // Note: Do NOT set Content-Type header manually; fetch will generate multipart boundary
    const authHeaders = getAuthHeaders();
    const response = await fetch(url, {
      method: 'POST',
      body: cleanedFormData,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...authHeaders,
      },
    });

    requestSent = true;
    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = `Server error (${response.status})`;
      try {
        const errJson = await response.json();
        if (errJson && errJson.detail) {
          if (typeof errJson.detail === 'string') {
            errorMessage = errJson.detail;
          } else if (Array.isArray(errJson.detail)) {
            // FastAPI 422 array of {loc, msg}
            errorMessage = errJson.detail
              .map((d) => {
                const locParts = Array.isArray(d.loc)
                  ? d.loc.filter((k) => k !== 'body' && k !== 'formData')
                  : [];
                const field = locParts.join(' ').replace(/_/g, ' ');
                return field ? `${field}: ${d.msg}` : d.msg;
              })
              .join(', ');
          } else {
            errorMessage = JSON.stringify(errJson.detail);
          }
        }
      } catch {
        if (response.statusText) {
          errorMessage = `Error (${response.status}): ${response.statusText}`;
        }
      }
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);

    if (error.name === 'AbortError') {
      if (timedOut) {
        throw new Error(
          'The server timed out while analyzing your complaint (90s limit). Please check your connection and try again.'
        );
      }
      if (externalSignal?.aborted) {
        throw new Error('Complaint submission was cancelled.');
      }
    }

    if (error instanceof TypeError && (error.message.includes('fetch') || error.message.includes('network') || error.message.includes('Failed to fetch'))) {
      if (!requestSent) {
        throw new Error(
          'The server could not be reached. Your report was not sent. Please verify the server is running and try again.'
        );
      } else {
        throw new Error('Network connection was interrupted while awaiting server response.');
      }
    }

    throw error;
  }
}

