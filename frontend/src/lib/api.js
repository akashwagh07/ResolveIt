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
  if (filters.status) params.append('status', filters.status);
  if (filters.category) params.append('category', filters.category);
  if (filters.department_id) params.append('department_id', filters.department_id);
  if (filters.citizen_contact) params.append('citizen_contact', filters.citizen_contact);
  if (filters.limit) params.append('limit', filters.limit);

  const queryString = params.toString();
  const endpoint = `/api/complaints${queryString ? `?${queryString}` : ''}`;
  return await request(endpoint);
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
