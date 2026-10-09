// Seeded demo accounts. The shared password lives server-side in DEMO_PASSWORD, never in the bundle.
export const PERSONAS = [
  { email: "sara@acme.test", name: "Sara Ahmed", role: "HR Admin", tenant: "Acme" },
  { email: "bilal@acme.test", name: "Bilal Khan", role: "Manager", tenant: "Acme" },
  { email: "ayesha@acme.test", name: "Ayesha Malik", role: "Employee", tenant: "Acme" },
  { email: "nadia@globex.test", name: "Nadia Hassan", role: "HR Admin", tenant: "Globex" },
  { email: "omar@globex.test", name: "Omar Sheikh", role: "Employee", tenant: "Globex" },
  { email: "admin@platform.test", name: "Platform", role: "Super Admin", tenant: "All tenants" },
];
