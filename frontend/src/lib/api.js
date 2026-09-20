/**
 * API client wrapper for ResolveIt backend.
 */

const BASE_URL = import.meta.env.VITE_API_URL || '';

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  try {
    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
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
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Unable to reach ResolveIt backend. Please check if the server is running on port 8000.');
    }
    throw error;
  }
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
    const response = await fetch(url, {
      method: 'POST',
      body: cleanedFormData,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
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

