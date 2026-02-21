export type VehicleType = {
  id: number;
  name_en: string;
  name_ar: string;
};

export const VEHICLE_TYPES: VehicleType[] = [
  {
    id: 1,
    name_en: "Standard PHV",
    name_ar: "Standard PHV",
  },
  {
    id: 2,
    name_en: "7 Seaters PHV",
    name_ar: "سيارة 7 ركاب",
  },
  {
    id: 3,
    name_en: "Luxury",
    name_ar: "فاخرة",
  },
  {
    id: 4,
    name_en: "Luxury Van",
    name_ar: "فان فاخر",
  },
  {
    id: 5,
    name_en: "VIP Business PHV",
    name_ar: "VIP أعمال",
  },
] as const;
