const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const admin = fs.readFileSync(
  path.join(root, "src/components/_components/dashboard/TripsDashboard.tsx"),
  "utf8",
);
const driverTrips = fs.readFileSync(
  path.join(root, "src/components/_components/driver/TripsDriver.tsx"),
  "utf8",
);
const tripDetails = fs.readFileSync(
  path.join(root, "src/components/_components/driver/TripDetails.tsx"),
  "utf8",
);

function expect(condition, message) {
  if (!condition) {
    console.error(message);
    process.exit(1);
  }
}

expect(
  admin.includes("/assign-driver/"),
  "Admin must use the guarded ACT-driver assignment endpoint.",
);
expect(
  admin.includes('driver?.vehicle?.vehicle_type?.id ==='),
  "Admin must only present drivers with the booking vehicle class.",
);
expect(
  admin.includes("Assign ACT driver") && admin.includes("Assign external driver"),
  "Admin must distinguish registered ACT drivers from external fallback drivers.",
);
expect(
  driverTrips.includes('detailsTrips?.status === "pending"') &&
    driverTrips.includes('? "newRequests"'),
  "Assigned pending bookings must expose the driver acceptance action.",
);
expect(
  tripDetails.includes("/accept/") &&
    tripDetails.includes("/driver/acceptable-trips"),
  "Successful driver acceptance must enter the accepted-booking flow.",
);

console.log("Driver assignment lifecycle frontend guard passed.");
