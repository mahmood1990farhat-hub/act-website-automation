export type VehicleType = {
  id: number;
  code: string;
  name_en: string;
  name_ar: string;
};

export const VEHICLE_TYPES: VehicleType[] = [
  { id: 1, code: "comfort", name_en: "Comfort Class", name_ar: "فئة الراحة" },
  { id: 2, code: "comfort_xl", name_en: "Comfort XL", name_ar: "فئة الراحة XL" },
  { id: 3, code: "executive", name_en: "Executive Class", name_ar: "الفئة التنفيذية" },
  { id: 4, code: "executive_xl", name_en: "Executive XL", name_ar: "الفئة التنفيذية XL" },
  { id: 5, code: "first_class", name_en: "First Class", name_ar: "الدرجة الأولى" },
] as const;
