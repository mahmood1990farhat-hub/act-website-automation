const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const home = fs.readFileSync(path.join(root, "src/dictionaries/en/home.json"), "utf8");
const review = fs.readFileSync(path.join(root, "src/components/_components/bookTaxi/ConfirmFlightDetails.tsx"), "utf8");
const myTrips = fs.readFileSync(path.join(root, "src/components/_components/Trips/MyTripsCard.tsx"), "utf8");
const complaints = fs.readFileSync(path.join(root, "src/components/_components/Complaints/index.tsx"), "utf8");

function expect(condition, message) {
  if (!condition) {
    console.error(message);
    process.exit(1);
  }
}

expect(home.includes("Cancellation received at least 3 hours before pickup"), "Customer policy content must show the approved 3-hour cancellation rule.");
expect(review.includes("3 hours before your scheduled pickup"), "Booking review must show the approved 3-hour cancellation rule.");
expect(!home.includes("Cancellation received at least 24 hours before pickup"), "Customer policy content must not retain the superseded 24-hour cancellation rule.");
expect(!review.includes("24 hours before your scheduled pickup"), "Booking review must not retain the superseded 24-hour cancellation rule.");
expect(myTrips.includes("/api/trips/"), "Passenger My Trips must retain a working cancellation action through the unified backend route.");
expect(myTrips.includes('accountText(locale, "cancelTripPolicy")'), "Cancellation confirmation must explain the three-hour rule before submission.");
expect(myTrips.includes('cancelTripRefunded') && myTrips.includes('cancelTripReview'), "Passenger cancellation result must distinguish processed refunds from support review.");
expect(complaints.includes('trip?.status === "cancelled"'), "Cancelled bookings requiring refund review must be selectable in passenger support.");

console.log("Three-hour cancellation presentation guard passed.");
