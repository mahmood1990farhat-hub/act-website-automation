export const FILE_TYPES = [
  { value: "TERMS_AND_CONDITIONS", label_en: "Terms and Conditions", label_ar: "الشروط والأحكام" },
  { value: "FAQ", label_en: "FAQ", label_ar: "الأسئلة الشائعة" },
  { value: "PRIVACY_POLICY", label_en: "Privacy Policy", label_ar: "سياسة الخصوصية" },
  { value: "DRIVER_GUIDELINES", label_en: "Driver Guidelines", label_ar: "إرشادات السائق" },
  { value: "PASSENGER_GUIDELINES", label_en: "Passenger Guidelines", label_ar: "إرشادات الركاب" },
  { value: "OTHER", label_en: "Other", label_ar: "أخرى" },
] as const;

export type FileTypeValue = typeof FILE_TYPES[number]["value"];
