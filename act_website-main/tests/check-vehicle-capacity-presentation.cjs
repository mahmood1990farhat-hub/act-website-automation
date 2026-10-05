const fs = require("fs");
const path = require("path");
const root = path.resolve(__dirname, "..");
const chooseCar = fs.readFileSync(path.join(root, "src/components/_components/bookTaxi/ChooseCar.tsx"), "utf8");
const booking = fs.readFileSync(path.join(root, "src/components/_components/bookTaxi/index.tsx"), "utf8");

function expect(condition, message) {
  if (!condition) {
    console.error(message);
    process.exit(1);
  }
}

expect(booking.includes("luggage_patterns: [number, number][]"), "Vehicle quote must expose capacity patterns.");
expect(chooseCar.includes("car.luggage_patterns?.length > 0"), "Vehicle cards must show capacity patterns.");
expect(chooseCar.includes('join(" / ")'), "Alternative approved patterns must be visibly separated.");
expect(booking.includes("largeSuitcaseLabel={home.Book_Taxi.form.largeSuitcase}"), "Large item label must follow selected language.");
expect(booking.includes("smallSuitcaseLabel={home.Book_Taxi.form.smallSuitcase}"), "Small item label must follow selected language.");

console.log("Vehicle capacity presentation guard passed.");
