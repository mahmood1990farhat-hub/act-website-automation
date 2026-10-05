const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const chooseCar = fs.readFileSync(path.join(root, "src/components/_components/bookTaxi/ChooseCar.tsx"), "utf8");
const review = fs.readFileSync(path.join(root, "src/components/_components/bookTaxi/ConfirmFlightDetails.tsx"), "utf8");
const myTrips = fs.readFileSync(path.join(root, "src/components/_components/Trips/MyTripsCard.tsx"), "utf8");

function expect(condition, message) {
  if (!condition) {
    console.error(message);
    process.exit(1);
  }
}

expect(chooseCar.includes("3 hours before pickup"), "Vehicle selection must show the approved 3-hour cancellation rule.");
expect(review.includes("3 hours before your scheduled pickup"), "Booking review must show the approved 3-hour cancellation rule.");
expect(!chooseCar.includes("24 hours before pickup"), "Vehicle selection must not retain the superseded 24-hour cancellation rule.");
expect(!review.includes("24 hours before your scheduled pickup"), "Booking review must not retain the superseded 24-hour cancellation rule.");
expect(myTrips.includes("/api/trips/"), "Passenger My Trips must retain a working cancellation action through the unified backend route.");

console.log("Three-hour cancellation presentation guard passed.");
