// Maestro global 'http' client is used to hit your /test endpoints
const baseUrl = "http://localhost:8000";

// 1. Create a baseline Customer in the test tenant
const customerRes = http.post(baseUrl + "/api/v1/customers/test", {
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    display_name: "E2E Mobile Customer",
    type: "person",
    email: "e2e-customer@example.com",
  }),
});

const customer = json(customerRes.body);

// 2. Create a Site tied to the new Customer
const siteRes = http.post(baseUrl + "/api/v1/sites/test", {
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    customer_id: customer.id,
    name: "E2E Test Site",
  }),
});

const site = json(siteRes.body);

// 3. Create a Quote tied to both the Customer and the Site
const quoteRes = http.post(baseUrl + "/api/v1/quotes/test", {
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    customer_id: customer.id,
    site_id: site.id,
    currency: "USD",
  }),
});

const quote = json(quoteRes.body);

// 4. Export the data to Maestro's YAML context so UI tests and Teardown can use them
output.customerId = customer.id;
output.siteId = site.id;
output.quoteId = quote.id;
output.quoteCustomerName = customer.display_name;

console.log("Seeded Quote ID: " + quote.id);
