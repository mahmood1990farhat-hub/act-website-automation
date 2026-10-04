import { runtimeText, type RuntimeKey } from "@/lib/customer-runtime";

const exampleKeyByCode: Record<string, RuntimeKey> = {
  comfort: "vehicleExampleComfort",
  comfort_xl: "vehicleExampleComfortXl",
  executive: "vehicleExampleExecutive",
  executive_xl: "vehicleExampleExecutiveXl",
  first_class: "vehicleExampleFirst",
};

export function vehicleExample(locale: string, code?: string): string {
  const key = code ? exampleKeyByCode[code] : undefined;
  return key ? runtimeText(locale, key) : "";
}

export function passengerCapacityLabel(locale: string, count: number): string {
  return runtimeText(locale, "upToPassengers").replace("{count}", String(count));
}
