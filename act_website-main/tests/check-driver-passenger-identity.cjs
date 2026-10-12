const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const screen = fs.readFileSync(
  path.join(root, "src/components/_components/dashboard/AllDriversDashboard.tsx"),
  "utf8",
);
const editor = fs.readFileSync(
  path.join(root, "src/components/_components/dashboard/DriverPassengerDetailsEditor.tsx"),
  "utf8",
);

function expect(condition, message) {
  if (!condition) {
    console.error(message);
    process.exit(1);
  }
}

expect(
  screen.includes("DriverPassengerDetailsEditor") &&
    screen.includes("setEditingDriverPassengerDetails(driverItem)"),
  "Both ACT admin driver tables must open the existing-driver identity editor.",
);
expect(
  editor.includes("/api/admin-panel/drivers/") &&
    editor.includes("/update/") &&
    editor.includes("isFormData: true"),
  "The driver identity edit must use the existing protected admin PATCH endpoint.",
);
for (const field of [
  "pco_licence_number", "vehicle_make", "vehicle_model",
  "vehicle_color", "driver_photo",
]) {
  expect(
    editor.includes('data.append("' + field + '"'),
    "Missing secure driver identity/vehicle field: " + field,
  );
}
expect(
  editor.includes('image/png') && editor.includes('image/jpeg') &&
    editor.includes("5 * 1024 * 1024"),
  "ACT admin must validate driver photo type and maximum size before upload.",
);
expect(
  editor.includes("driver.id") &&
    editor.includes("vehicle?.vehicle_number") &&
    !editor.includes("localStorage"),
  "Editing must preserve the selected registered driver and not store identity files in localStorage.",
);

console.log("Driver passenger-facing identity editor regression guards passed.");
