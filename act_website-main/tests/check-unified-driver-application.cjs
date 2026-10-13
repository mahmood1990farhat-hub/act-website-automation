const fs = require("fs");
const path = require("path");
const root = path.resolve(__dirname, "..");
const read = relative => fs.readFileSync(path.join(root, relative), "utf8");
const form = read("src/components/_components/auth/captain/UnifiedDriverApplication.tsx");
const auth = read("src/components/_components/auth/Auth.tsx");
const login = read("src/components/_components/auth/Login.tsx");
const setup = read("src/components/_components/auth/captain/DriverPasswordSetup.tsx");
const review = read("src/components/_components/dashboard/UnifiedDriverReview.tsx");
const admin = read("src/components/_components/dashboard/DriverOnboardingRequests.tsx");

function check(value, message) {
  if (!value) { console.error(message); process.exit(1); }
}

check(auth.includes("<UnifiedDriverApplication locale={locale} />"),
  "New applicants must use the one-form entry point, not legacy Stage 1");
check(form.includes("/api/drivers/onboarding/apply/") &&
  form.includes('method: "POST"') && form.includes("new FormData()"),
  "One multipart submission to the unified backend is required");
for (const key of [
  "first_name", "last_name", "date_of_birth", "phone_number",
  "email", "address", "postcode", "pco_badge_number",
  "pco_badge_expiry", "years_experience", "pco_front", "pco_back",
  "dvla_front", "dvla_back", "driver_photo", "vehicle_ownership",
  "vehicle_class_code", "vehicle_make", "vehicle_model", "vehicle_year",
  "vehicle_registration", "vehicle_colour", "mot_expiry", "insurance_expiry",
  "accepts_pets", "mot", "insurance", "v5c", "vehicle_phv",
  "hire_agreement", "dbs_consent", "agrees_policies",
]) check(form.includes(key), "Missing approved one-form field: " + key);
check(form.includes("do_not_have_a_phv") && form.includes("hasVehicle"),
  "No-vehicle applications must have a conditional evidence path");
check(!form.includes("localStorage") && !form.includes("sessionStorage"),
  "Do not persist regulated identity files in browser storage");
check(setup.includes('window.location.hash.slice(1)') &&
  setup.includes('window.history.replaceState') &&
  setup.includes("/api/drivers/onboarding/set-password/"),
  "One-time password tokens must remain in URL fragments and be removed from history");
check(login.includes('onboardingStatus?.submission_mode === "unified"') &&
  login.includes("driver-application-status"),
  "New pending drivers must enter status-only portal, not Stage 2/trip offers");
check(admin.includes("Review unified application and private evidence") &&
  admin.includes('selectedRequest?.submission_mode !== "unified"'),
  "Unified applications must not be approved using the old Stage-1 buttons");
check(review.includes("admin/unified-applications/") &&
  review.includes('documents_reviewed: docsReviewed') &&
  review.includes('dbs_cleared: dbsCleared') &&
  review.includes("photo_disclosure_consent: photoConsent"),
  "Approval must be a gated admin-only confirmation");
console.log("ACT unified driver application UI and approval wiring checks passed.");
