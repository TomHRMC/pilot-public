const baseUrl = "http://localhost:8000";

// Retrieve the IDs passed from the YAML flow
const customerId = env.CUSTOMER_ID;
const siteId = env.SITE_ID;

console.log("Tearing down test data...");

// 1. Soft-delete the Site
if (siteId) {
  http.request(baseUrl + "/api/v1/sites/" + siteId + "/test", {
    method: "DELETE",
  });
  console.log("Deleted Site: " + siteId);
}

// 2. Soft-delete the Customer
if (customerId) {
  http.request(baseUrl + "/api/v1/customers/" + customerId + "/test", {
    method: "DELETE",
  });
  console.log("Deleted Customer: " + customerId);
}

// Note: A dedicated DELETE endpoint for quotes/test doesn't exist in your openapi.json.
// Relying on the customer/site soft-deletion to effectively hide this data from the UI.
