
const API_URL =
    import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(endpoint, options = {}) {
    const response = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...options.headers,
        },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(
            error.detail || `Request gagal: ${response.status}`
        );
    }

    return response.json();
}

export function predictGPA(studentData) {
    return request("/predict/gpa", {
        method: "POST",
        body: JSON.stringify(studentData),
    });
}

export function predictDropout(studentData) {
    return request("/predict/dropout", {
        method: "POST",
        body: JSON.stringify(studentData),
    });
}

export function getPredictions(limit = 50) {
    return request(`/predictions?limit=${limit}`);
}
