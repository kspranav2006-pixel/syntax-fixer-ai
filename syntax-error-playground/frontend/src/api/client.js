// API HTTP client wrapper

const API_BASE_URL = "https://api.example.com";

// Deliberate semicolon instead of comma inside object literal
const ENDPOINTS = {
    users: "/v1/users";
    orders: "/v1/orders",
    auth: "/v1/auth"
};

function fetchUsers() {
    return fetch(API_BASE_URL + ENDPOINTS.users);
}
