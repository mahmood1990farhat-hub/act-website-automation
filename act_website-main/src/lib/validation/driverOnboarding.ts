import { z } from "zod";

export const preferredCommunicationEnum = z.enum([
  "phone",
  "sms",
  "email",
  "whatsapp",
]);

export const yearsExperienceEnum = z.enum([
  "less_than_1",
  "1_to_3",
  "3_to_5",
  "5_plus",
]);

export const vehicleOwnershipEnum = z.enum([
  "phv_owner",
  "hiring_a_phv",
  "do_not_have_a_phv",
  "other",
]);

export const fuelTypeEnum = z.enum([
  "petrol",
  "diesel",
  "ev",
  "plug_in_hybrid",
  "hybrid",
]);

export const vehicleTypeEnum = z.enum([
  "5_seater_standard",
  "7_seaters",
  "van_transporter",
  "other",
]);

export const availabilityEnum = z.enum([
  "full_time",
  "part_time",
  "weekdays",
  "weekends",
  "nights",
  "flexible",
]);

export const notificationMethodEnum = z.enum(["app", "sms", "email", "no_preference"]);

export const driverOnboardingSchema = z
  .object({
    first_name: z.string().min(1, "First name is required"),
    last_name: z.string().min(1, "Last name is required"),
    mobile_number: z.string().min(1, "Phone is required").max(15, "Must be less than 15 characters"),
    email_address: z.string().email("Invalid email"),
    home_postcode: z
      .string()
      .min(1, "Home postcode is required")
      .max(100, "Must be less than 100 characters"),
    preferred_communication: preferredCommunicationEnum,
    username: z.string().min(1, "Username is required").max(100, "Must be less than 10 characters"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirm_password: z.string(),

    years_experience: yearsExperienceEnum,
    previous_companies: z.string().optional().default(""),
    familiar_areas: z.array(z.string()).min(1, "Please specify familiar areas"),
    preferred_journey_types: z.array(z.string()).min(1, "Select at least one"),

    vehicle_ownership: vehicleOwnershipEnum,
    vehicle_type: vehicleTypeEnum,
    fuel_type: fuelTypeEnum,

    preferred_locations: z
      .string()
      .optional()
      .default(""),
    availability: availabilityEnum,
    notification_method: notificationMethodEnum,

    has_tfl_licence: z.boolean().refine((v) => v === true, {
      message: "You must have a TfL licence",
    }),
    willing_dbs_check: z.boolean().refine((v) => v === true, {
      message: "DBS check is required",
    }),
    agrees_policies: z.boolean().refine((v) => v === true, {
      message: "You must agree to the terms and policies",
    }),
  })
  .refine((data) => data.password === data.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords do not match",
  });

export type DriverOnboardingInput = z.infer<typeof driverOnboardingSchema>;


