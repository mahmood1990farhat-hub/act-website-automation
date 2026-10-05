const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const chooseCar = fs.readFileSync(
  path.join(root, "src/components/_components/bookTaxi/ChooseCar.tsx"),
  "utf8",
);
const booking = fs.readFileSync(
  path.join(root, "src/components/_components/bookTaxi/index.tsx"),
  "utf8",
);

function expect(condition, message) {
  if (!condition) {
    console.error(message);
    process.exit(1);
  }
}

expect(
  booking.includes("icon_url: string | null"),
  "Vehicle quote type must allow a missing image URL returned by the backend.",
);
expect(
  chooseCar.includes("car.icon_url ? ("),
  "Choose Car must guard the Next Image component when a vehicle image is missing.",
);
expect(
  chooseCar.includes("<CarFront"),
  "Choose Car must provide a usable visual fallback for a missing class image.",
);
expect(
  chooseCar.includes("localizedVehicleValue(car, \"name\", locale)"),
  "Missing-image fallback must retain the localized vehicle class name.",
);

console.log("Vehicle image fallback guard passed.");
