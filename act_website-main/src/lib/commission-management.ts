export type CommissionDriver = {
  id: number;
  name: string;
  category: "global" | "individual" | "group" | "conflict";
  group_id: number | null;
  company_percentage: string;
  driver_percentage: string;
};
export type CommissionGroup = { id: number; name: string; is_active: boolean; company_percentage: string };
export type CommissionSnapshot = {
  global_percentage: string;
  global_is_configured: boolean;
  drivers: CommissionDriver[];
  groups: CommissionGroup[];
  legacy_vehicle_rules: { id: number; vehicle_type_id: number; company_percentage: string }[];
  conflicting_driver_ids: number[];
  multiple_global_rules: boolean;
  revision: string;
  writes_enabled: boolean;
  write_lock_reason: string;
};

export function commissionLists(data: CommissionSnapshot) {
  const seen = new Set<number>();
  for (const driver of data.drivers) {
    if (seen.has(driver.id)) throw new Error("Duplicate driver in commission response.");
    seen.add(driver.id);
  }
  return {
    global: data.drivers.filter((driver) => driver.category === "global"),
    individual: data.drivers.filter((driver) => driver.category === "individual"),
    grouped: data.drivers.filter((driver) => driver.category === "group"),
    conflicts: data.drivers.filter((driver) => driver.category === "conflict"),
  };
}

export function validCommissionPercentage(value: string): boolean {
  return /^(?:\d{1,2}(?:\.\d{1,2})?|100(?:\.0{1,2})?)$/.test(value.trim());
}

// CSV is an Excel-compatible export, not a second source of commission records.
export function commissionCsv(data: CommissionSnapshot): string {
  commissionLists(data);
  const cell = (value: string | number) => {
    let text = String(value);
    if (/^[=+\-@\t\r\n]/.test(text) || /^[\s]+[=+\-@]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  };
  const rows: (string | number)[][] = [["Driver ID", "Driver", "Commission category", "Group", "ACT deduction (%)", "Driver share (%)"]];
  for (const driver of data.drivers) {
    rows.push([driver.id, driver.name, driver.category,
      data.groups.find((group) => group.id === driver.group_id)?.name ?? "",
      driver.company_percentage, driver.driver_percentage]);
  }
  return "\uFEFF" + rows.map((row) => row.map(cell).join(",")).join("\r\n") + "\r\n";
}
