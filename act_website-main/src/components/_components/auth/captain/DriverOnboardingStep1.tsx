"use client";
import React, { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import {
  driverOnboardingSchema,
  DriverOnboardingInput,
  preferredCommunicationEnum,
  yearsExperienceEnum,
  vehicleOwnershipEnum,
  vehicleTypeEnum,
  fuelTypeEnum,
  availabilityEnum,
  notificationMethodEnum,
} from "@/lib/validation/driverOnboarding";

// Local lightweight zod resolver to avoid external dependency issues
const zodResolverLocal = (schema: any) => async (values: any) => {
  const result = schema.safeParse(values);
  if (result.success) {
    return { values: result.data, errors: {} };
  }
  const formErrors: Record<string, any> = {};
  for (const issue of result.error.errors) {
    const path =
      (issue.path || []).join(".") ||
      (issue as any).path?.toString?.() ||
      "";
    if (!formErrors[path]) {
      formErrors[path] = { type: "validation", message: issue.message };
    }
  }
  return { values: {}, errors: formErrors };
};

import { Button } from "@/components/ui/button";
import InputField from "../InputField";
import PasswordField from "../PasswordField";
import { IoLocation, IoMail } from "react-icons/io5";
import { BsFillTelephoneFill } from "react-icons/bs";
import PhoneInputWithCountrySelect from "react-phone-number-input";
import { isValidPhoneNumber } from "react-phone-number-input";
import { postData } from "@/lib/api/postData";
import { useMutation } from "@tanstack/react-query";
import { Locale } from "../../../../../i18n.config";
import GlobalModal from "../../GlobalModal";
import { FaCheckCircle, FaCheck } from "react-icons/fa";
import LocationSelector, {
  PlaceSuggestion,
} from "@/components/_components/bookTaxi/LocationSelector";

// Reusable MultiSelect kept at module scope to preserve state across parent re-renders
const MultiSelect: React.FC<{
  label: string;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  minMenuHeight?: number;
}> = ({
  label,
  options,
  selected,
  onChange,
  placeholder = "Select...",
  minMenuHeight = 160,
}) => {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const toggle = (value: string) => {
    onChange(
      selected.includes(value)
        ? selected.filter((v) => v !== value)
        : [...selected, value]
    );
  };

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return (
    <div className="w-full relative" ref={containerRef}>
      <label className="text-sm font-medium mb-1 block">
        {label} <span className="text-primary">*</span>
      </label>
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen((s) => !s)}
          className="w-full p-3 border-2 bg-foreground border-muted rounded-lg text-left focus:outline-none focus:border-primary"
        >
          {selected.length === 0 ? (
            <span className="text-gray-400">{placeholder}</span>
          ) : (
            <span className="flex flex-wrap gap-2">
              {selected.map((s) => (
                <span
                  key={s}
                  className="px-2 py-0.5 rounded-full bg-primary/20 text-primary text-xs"
                >
                  {s}
                </span>
              ))}
            </span>
          )}
        </button>
        {open && (
          <div
            className="absolute left-0 right-0 z-20 mt-2 w-full max-h-64 overflow-auto rounded-lg border border-gray-600 bg-foreground shadow-lg"
            style={{ minHeight: minMenuHeight }}
          >
            {options.map((opt) => {
              const isSelected = selected.includes(opt);
              return (
                <button
                  type="button"
                  key={opt}
                  onClick={() => toggle(opt)}
                  className={`w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-700/40 ${
                    isSelected ? "bg-gray-700/40" : ""
                  }`}
                >
                  <span>{opt}</span>
                  {isSelected && <FaCheck className="text-yellow-400" />}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

type FormData = {
  full_name: string;
  mobile_number: string;
  email_address: string;
  home_postcode: string;
  preferred_communication: "phone_call" | "sms" | "email" | "whatsapp";
  username: string;
  password: string;
  confirm_password: string;

  // Driving Experience
  years_experience: "less_than_1" | "1_to_3" | "3_to_5" | "plus_5";
  previous_companies: string;
  familiar_areas: string;
  preferred_journey_types: string[];

  // Vehicle Information
  vehicle_ownership: "own" | "rent" | "not_yet";
  vehicle_type:
    | "standard_phv"
    | "seven_seaters_phv"
    | "luxury"
    | "luxury_van"
    | "vip_business_phv";
  fuel_type: "petrol" | "diesel" | "hybrid" | "electric";

  // Preferences & Availability
  preferred_locations: string;
  availability: "app" | "sms" | "email";
  notification_method: "app" | "sms" | "email";

  // Compliance & Safety
  has_tfl_licence: boolean;
  willing_dbs_check: boolean;
  agrees_policies: boolean;
};

export default function DriverOnboardingStep1({
  setTapAction,
  locale,
  trans,
  onSuccess,
}: {
  setTapAction: (tap: number) => void;
  locale: Locale;
  trans: any;
  onSuccess?: (requestId: number) => void;
}) {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [phone, setPhone] = useState<string>("");
  const [phoneError, setPhoneError] = useState<string>("");
  const [successModal, setSuccessModal] = useState(false);
  const [selectedJourneyTypes, setSelectedJourneyTypes] = useState<string[]>(
    []
  );
  const [previousCompanies, setPreviousCompanies] = useState<string[]>([]);
  const [preferredLocations, setPreferredLocations] = useState<string[]>([]);
  const [familiarAreas, setFamiliarAreas] = useState<string[]>([]);
  const [newCompany, setNewCompany] = useState<string>("");
  const [newLocation, setNewLocation] = useState<string>("");
  const [newArea, setNewArea] = useState<string>("");

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    trigger,
    formState: { errors },
  } = useForm<DriverOnboardingInput>({
    resolver: zodResolverLocal(driverOnboardingSchema) as any,
    defaultValues: {
      preferred_journey_types: [],
      familiar_areas: [],
      previous_companies: "",
      preferred_locations: "",
      has_tfl_licence: false,
      willing_dbs_check: false,
      agrees_policies: false,
    },
  });

  const password = watch("password");

  // Keep form in sync with controlled phone value so zod has mobile_number
  useEffect(() => {
    setValue("mobile_number", phone as any, {
      shouldValidate: true,
      shouldDirty: true,
    });
  }, [phone, setValue]);

  const [currentStep, setCurrentStep] = useState<number>(1);

  const formatEnumOption = (value: string) => {
    return value
      .split("_")
      .map((word) => {
        const lower = word.toLowerCase();
        if (lower === "phv") return "PHV";
        if (lower === "tfl") return "TfL";
        return word.charAt(0).toUpperCase() + word.slice(1);
      })
      .join(" ");
  };

  const journeyTypes = [
    trans.journeyTypes?.airportTransfers ||
      (locale === "ar" ? "خدمة نقل المطار" : "Airport Transfer"),
    trans.journeyTypes?.cityToCity ||
      (locale === "ar" ? "رحلات بين المدن" : "City-to-city"),
    trans.journeyTypes?.localRides ||
      (locale === "ar" ? "رحلات داخلية" : "Local rides"),
    trans.journeyTypes?.noPreference ||
      (locale === "ar" ? "بدون تفضيل" : "No preference"),
  ];

  const workAreaOptions =
    locale === "ar"
      ? [
          "أي مكان في لندن",
          "وسط لندن",
          "شمال لندن",
          "جنوب لندن",
          "شرق لندن",
          "غرب لندن",
          "شمال شرق لندن",
          "شمال غرب لندن",
          "جنوب شرق لندن",
          "جنوب غرب لندن",
          "مطار هيثرو",
          "مطار لوتون",
          "مطار ستانستد",
          "مطار غاتويك",
        ]
      : [
          "Anywhere in London",
          "Central London",
          "North London",
          "South London",
          "East London",
          "West London",
          "North East London",
          "North West London",
          "South East London",
          "South West London",
          "Heathrow Airport",
          "Luton Airport",
          "Stansted Airport",
          "Gatwick Airport",
        ];

  useEffect(() => {
    // When locale changes, ensure previously selected journey types
    // are still valid options for the current language.
    setSelectedJourneyTypes((prev) => {
      const filtered = prev.filter((type) => journeyTypes.includes(type));
      setValue("preferred_journey_types", filtered as any, {
        shouldValidate: true,
      });
      return filtered;
    });
  }, [locale, setValue]);

  const toggleJourneyType = (type: string) => {
    setSelectedJourneyTypes((prev) => {
      const next = prev.includes(type)
        ? prev.filter((t) => t !== type)
        : [...prev, type];
      setValue("preferred_journey_types", next, { shouldValidate: true });
      return next;
    });
  };

  // Functions to manage dynamic lists
  const addCompany = () => {
    if (newCompany.trim() && !previousCompanies.includes(newCompany.trim())) {
      const updated = [...previousCompanies, newCompany.trim()];
      setPreviousCompanies(updated);
      setValue("previous_companies", updated.join(", "), {
        shouldValidate: true,
      });
      setNewCompany("");
    }
  };

  const removeCompany = (company: string) => {
    const updated = previousCompanies.filter((c) => c !== company);
    setPreviousCompanies(updated);
    setValue("previous_companies", updated.join(", "), {
      shouldValidate: true,
    });
  };

  const addLocation = () => {
    if (newLocation.trim() && !preferredLocations.includes(newLocation.trim())) {
      const updated = [...preferredLocations, newLocation.trim()];
      setPreferredLocations(updated);
      setValue("preferred_locations", updated.join(", "), {
        shouldValidate: true,
      });
      setNewLocation("");
    }
  };

  const removeLocation = (location: string) => {
    const updated = preferredLocations.filter((l) => l !== location);
    setPreferredLocations(updated);
    setValue("preferred_locations", updated.join(", "), {
      shouldValidate: true,
    });
  };

  const addArea = () => {
    if (newArea.trim() && !familiarAreas.includes(newArea.trim())) {
      const updated = [...familiarAreas, newArea.trim()];
      setFamiliarAreas(updated);
      setValue("familiar_areas", updated as any, { shouldValidate: true });
      setNewArea("");
    }
  };

  const removeArea = (area: string) => {
    const updated = familiarAreas.filter((a) => a !== area);
    setFamiliarAreas(updated);
    setValue("familiar_areas", updated as any, { shouldValidate: true });
  };

  const steps = [
    { id: 1, title: trans.step1 || "Personal details" },
    { id: 2, title: trans.step2 || "Professional profile" },
    { id: 3, title: trans.step3 || "Vehicle information" },
    { id: 4, title: trans.step4 || "Upload required documents" },
  ];

  const stepFields: Record<number, (keyof DriverOnboardingInput)[]> = {
    1: [
      "first_name",
      "last_name",
      "username",
      "email_address",
      "mobile_number",
      "home_postcode",
      "preferred_communication",
      "password",
      "confirm_password",
    ],
    2: [
      "years_experience",
      "previous_companies",
      "familiar_areas",
      "preferred_journey_types",
    ],
    3: ["vehicle_ownership", "vehicle_type", "fuel_type"],
    4: [
      "availability",
      "notification_method",
      "has_tfl_licence",
      "willing_dbs_check",
      "agrees_policies",
    ],
  };

  const goNext = async () => {
    // Clear phone error first
    if (currentStep === 1) {
      setPhoneError("");
    }

    // Validate current step fields
    const valid = await trigger(stepFields[currentStep] as any, {
      shouldFocus: true,
    });

    if (!valid) {
      const currentStepErrors = stepFields[currentStep].filter(
        (field) => errors[field]
      );
      if (currentStepErrors.length > 0) {
        console.log(
          "Please complete all required fields before proceeding",
          currentStepErrors
        );
      }
      return;
    }

    if (currentStep === 1 && !isValidPhoneNumber(phone)) {
      setPhoneError(
        trans.phoneInvalid || "Please enter a valid phone number"
      );
      return;
    }

    if (currentStep === 2 && selectedJourneyTypes.length === 0) {
      return;
    }

    setCurrentStep((s) => Math.min(4, s + 1));
  };

  const goBack = () => setCurrentStep((s) => Math.max(1, s - 1));

  const mutation = useMutation({
    mutationFn: async (data: DriverOnboardingInput) => {
      const previousCompaniesArray = previousCompanies;
      const preferredLocationsArray = preferredLocations;
      const familiarAreasArray = familiarAreas;

      const body = {
        full_name: `${data.first_name} ${data.last_name}`.trim(),
        mobile_number: phone,
        email_address: data.email_address,
        home_postcode: data.home_postcode,
        preferred_communication: data.preferred_communication,
        username: data.username,
        password: data.password,
        confirm_password: data.confirm_password,

        years_experience: data.years_experience,
        previous_companies: previousCompaniesArray,
        familiar_areas: familiarAreasArray,
        preferred_journey_types: selectedJourneyTypes,

        vehicle_ownership: data.vehicle_ownership,
        vehicle_type: data.vehicle_type,
        fuel_type: data.fuel_type,

        preferred_locations: ["London"], // Temporarily sending empty array until backend makes this field optional
        availability: data.availability,
        notification_method: data.notification_method,

        has_tfl_licence: data.has_tfl_licence,
        willing_dbs_check: data.willing_dbs_check,
        agrees_policies: data.agrees_policies,
      };

      return await postData<any>({
        endpoint: "/api/drivers/onboarding/step1/",
        body,
        queryParams: { locale },
      });
    },
    onSuccess: (response) => {
      setSuccessModal(true);
      if (onSuccess && response?.onboarding_request_id) {
        onSuccess(response.onboarding_request_id);
      }
    },
    onError: (err) => {
      console.error(err);
    },
  });

  const onSubmit = async (data: DriverOnboardingInput) => {
    if (!isValidPhoneNumber(phone)) {
      setPhoneError(trans.phoneInvalid || "Phone Number is Invalid");
      return;
    }
    setPhoneError("");
    setLoading(true);
    mutation.mutate(data, {
      onSettled: () => setLoading(false),
    });
  };

  return (
    <>
      <GlobalModal
        isOpen={successModal}
        onClose={() => {
          setSuccessModal(false);
          setTapAction(1);
        }}
      >
        <div className="flex items-center justify-center flex-col gap-4 p-4">
          <FaCheckCircle className="text-6xl text-green-500" />
          <h1 className="text-2xl font-extrabold text-center text-white">
            {"Thank you - Application Submitted"}
          </h1>
          <h2 className="text-xl font-bold text-center text-green-400">
            {"Successfully!"}
          </h2>
          <div className="text-center mt-2 text-gray-200">
            <p className="font-semibold">{"Please note!!!"}</p>
            <p className="mt-1">{"Your onboarding request has been"}</p>
            <p>{"received. Your application will be"}</p>
            <p>{"reviewed, and you will be"}</p>
            <p>{"contacted in due course."}</p>
          </div>
          <Button
            onClick={() => {
              setSuccessModal(false);
              setTapAction(1);
            }}
            className="px-10"
          >
            {"OK"}
          </Button>
        </div>
      </GlobalModal>

      <div className="w-full max-h-[85vh] overflow-y-auto on-scrollbar px-2">
        <div className="text-center mb-6 px-2">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl mb-3 font-extrabold text-white">
            {trans.title || "Driver Registration"}
          </h1>
          <p className="text-gray-300 text-sm sm:text-base">
            {trans.desc ||
              "Please provide your details to start the onboarding process"}
          </p>
          <div className="mt-4 text-xs sm:text-sm text-gray-400">
            {trans.stepOf
              ? trans.stepOf
                  .replace("{step}", currentStep.toString())
                  .replace(
                    "{title}",
                    steps.find((s) => s.id === currentStep)?.title || ""
                  )
              : `Step ${currentStep} of 4 - ${
                  steps.find((s) => s.id === currentStep)?.title
                }`}
          </div>
        </div>

        {/* Stepper */}
        <div className="w-full max-w-full sm:max-w-[800px] mx-auto mb-8 px-2 sm:px-4">
          <div className="flex flex-wrap items-center justify-center gap-y-4 relative">
            {steps.map((s, idx) => (
              <div
                key={s.id}
                className="flex items-center justify-center flex-1 min-w-[70px]"
              >
                <div className="flex flex-col items-center min-w-0 flex-shrink-0">
                  <div
                    className={`relative w-9 h-9 sm:w-11 sm:h-11 rounded-full flex items-center justify-center font-bold text-xs sm:text-sm transition-all duration-300 ${
                      currentStep >= s.id
                        ? "bg-gradient-to-r from-primary to-primary/80 text-white shadow-lg shadow-primary/30 scale-110"
                        : "bg-muted text-muted-foreground border-2 border-border"
                    }`}
                  >
                    {currentStep > s.id ? (
                      <svg
                        className="w-4 h-4 sm:w-5 sm:h-5"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    ) : (
                      s.id
                    )}
                    {currentStep === s.id && (
                      <div className="absolute inset-0 rounded-full bg-primary/20 animate-pulse"></div>
                    )}
                  </div>
                  <span
                    className={`text-[10px] sm:text-xs font-medium mt-1 sm:mt-2 transition-colors duration-300 text-center leading-tight px-1 max-w-[80px] ${
                      currentStep >= s.id
                        ? "text-yellow-400"
                        : "text-gray-400"
                    }`}
                  >
                    {s.title}
                  </span>
                </div>
                {idx < steps.length - 1 && (
                  <div
                    className={`h-0.5 flex-1 mx-1 sm:mx-4 rounded-full transition-all duration-300 max-w-[40px] sm:max-w-none ${
                      currentStep > s.id
                        ? "bg-gradient-to-r from-primary to-primary/60"
                        : "bg-border"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-6 w-full text-sm px-1 sm:px-2"
        >
          {/* Step 1: Personal Information */}
          {currentStep === 1 && (
            <div className="space-y-6">
              <div className="border border-gray-600 p-4 sm:p-6 rounded-xl bg-gradient-to-br from-gray-800/50 to-gray-700/30">
                <h2 className="text-lg sm:text-xl font-bold text-yellow-400 mb-4 sm:mb-6 flex items-center gap-2">
                  <div className="w-8 h-8 bg-yellow-400/20 rounded-full flex items-center justify-center">
                    <span className="text-yellow-400 font-bold">1</span>
                  </div>
                  {trans.step1 || "Personal"}
                </h2>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 w-full">
                  <div className="space-y-4">
                    <div className="flex flex-col sm:flex-row items-center w-full gap-3 sm:gap-4">
                      <div className="w-full">
                        <InputField
                          label={trans.firstName || "First Name"}
                          placeholder={
                            trans.placeholders?.firstName || "John"
                          }
                          register={register}
                          name="first_name"
                          requiredMsg={
                            trans.firstNameRequired ||
                            "First name is required"
                          }
                          error={errors.first_name}
                        />
                      </div>
                      <div className="w-full">
                        <InputField
                          label={trans.lastName || "Last Name"}
                          placeholder={
                            trans.placeholders?.lastName || "Doe"
                          }
                          register={register}
                          name="last_name"
                          requiredMsg={
                            trans.lastNameRequired ||
                            "Last name is required"
                          }
                          error={errors.last_name}
                        />
                      </div>
                    </div>

                    <InputField
                      label={trans.username || "Username"}
                      placeholder={
                        trans.placeholders?.username || "johndoe"
                      }
                      register={register}
                      name="username"
                      requiredMsg={
                        trans.usernameRequired || "Username is required"
                      }
                      error={errors.username}
                    />

                    <InputField
                      label={trans.emailAddress || "Email Address"}
                      placeholder={
                        trans.placeholders?.email || "john@example.com"
                      }
                      register={register}
                      name="email_address"
                      requiredMsg={
                        trans.emailAddressRequired || "Email is required"
                      }
                      error={errors.email_address}
                      type="email"
                      icon={<IoMail className="mx-2 text-lg" />}
                    />
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="text-[14px] sm:text-[16px]">
                        {trans.mobileNumber || "Mobile Number"}{" "}
                        <span className="text-primary">*</span>
                      </label>
                      <div
                        className="flex items-center w-full min-w-0 p-3 border-2 bg-foreground border-muted rounded-lg mt-1"
                        dir="ltr"
                      >
                        <PhoneInputWithCountrySelect
                          defaultCountry="GB"
                          value={phone}
                          onChange={(val) => setPhone(val || "")}
                          international
                          countryCallingCodeEditable={false}
                          className="w-full bg-foreground focus:outline-none"
                        />
                        <BsFillTelephoneFill className="mx-2 shrink-0" />
                      </div>
                      {phoneError && (
                        <p className="text-xs text-error mt-1.5">
                          {phoneError}
                        </p>
                      )}
                    </div>

                    <div className="space-y-4">
                      <div>
                        <label className="text-sm font-medium mb-1 flex items-center gap-2">
                          <IoLocation className="text-lg" />
                          {trans.location || "Home Postcode"}{" "}
                          <span className="text-primary">*</span>
                        </label>
                        <LocationSelector
                          locale={locale}
                          value={watch("home_postcode") || ""}
                          locationType={"dropoff"}
                          setValue={(data: PlaceSuggestion) => {
                            setValue(
                              "home_postcode",
                              (data && (data as any).description) || "",
                              { shouldValidate: true }
                            );
                          }}
                        />
                        {errors.home_postcode && (
                          <p className="text-xs text-error mt-1.5">
                            {errors.home_postcode?.message ||
                              trans.homePostcodeRequired ||
                              "Home postcode is required"}
                          </p>
                        )}
                      </div>

                      <div>
                        <label className="text-sm font-medium mb-1">
                          {trans.preferredCommunication || "Preferred Communication"}{" "}
                          <span className="text-primary">*</span>
                        </label>
                        <select
                          {...register("preferred_communication", {
                            required:
                              trans.preferredCommunicationRequired ||
                              "Please select preferred communication method",
                          })}
                          className="w-full p-3 border-2 bg-foreground border-muted rounded-lg mt-1 focus:outline-none focus:border-primary"
                        >
                          <option value="">
                            {trans.select || "Select..."}
                          </option>
                          {preferredCommunicationEnum.options.map((opt) => (
                            <option key={opt} value={opt}>
                              {opt === "phone"
                                ? trans.preferredCommunicationOptions?.phone || "Phone Call"
                                : opt === "sms"
                                ? trans.preferredCommunicationOptions?.sms || "SMS"
                                : opt === "email"
                                ? trans.preferredCommunicationOptions?.email || "Email"
                                : opt === "whatsapp"
                                ? trans.preferredCommunicationOptions?.whatsapp || "WhatsApp"
                                : opt}
                            </option>
                          ))}
                        </select>
                        {errors.preferred_communication && (
                          <p className="text-xs text-error mt-1.5">
                            {errors.preferred_communication.message}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
                  <PasswordField
                    label={trans.password || "Password"}
                    name="password"
                    register={register}
                    show={showPassword}
                    setShow={setShowPassword}
                    validate={{
                      required:
                        trans.passwordRequired || "Password is required",
                      minLength: {
                        value: 8,
                        message:
                          trans.passwordRequired ||
                          "Password must be at least 8 characters",
                      },
                    }}
                    error={errors.password}
                  />

                  <PasswordField
                    label={trans.confirmPassword || "Confirm Password"}
                    name="confirm_password"
                    register={register}
                    show={showConfirmPassword}
                    setShow={setShowConfirmPassword}
                    validate={{
                      validate: (value: string) =>
                        value === password ||
                        trans.passwordMismatch ||
                        "Passwords do not match",
                    }}
                    error={errors.confirm_password}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Driving Experience */}
          {currentStep === 2 && (
            <div className="space-y-6">
              <div className="border border-gray-600 p-4 sm:p-6 rounded-xl bg-gradient-to-br from-gray-800/50 to-gray-700/30">
                <h2 className="text-lg sm:text-xl font-bold text-yellow-400 mb-4 sm:mb-6 flex items-center gap-2">
                  <div className="w-8 h-8 bg-yellow-400/20 rounded-full flex items-center justify-center">
                    <span className="text-yellow-400 font-bold">2</span>
                  </div>
                  {trans.step2 || "Experience"}
                </h2>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <label className="text-sm font-medium mb-1">
                        {trans.yearsExperience || "Years of Experience"}{" "}
                        <span className="text-primary">*</span>
                      </label>
                      <select
                        {...register("years_experience", {
                          required:
                            trans.yearsExperienceRequired ||
                            "Please select years of experience",
                        })}
                        className="w-full p-3 border-2 bg-foreground border-muted rounded-lg mt-1 focus:outline-none focus:border-primary"
                      >
                        <option value="">
                          {trans.select || "Select..."}
                        </option>
                        {yearsExperienceEnum.options.map((opt) => (
                          <option key={opt} value={opt}>
                            {opt === "less_than_1"
                              ? "Less than 1 year"
                              : opt === "1_to_3"
                              ? "1–3 years"
                              : opt === "3_to_5"
                              ? "3–5 years"
                              : "5+ years"}
                          </option>
                        ))}
                      </select>
                      {errors.years_experience && (
                        <p className="text-xs text-error mt-1.5">
                          {errors.years_experience.message}
                        </p>
                      )}
                    </div>

                    <div>
                      <label className="text-sm font-medium mb-1">
                        {trans.previousCompanies || "Previous Companies"}
                      </label>
                      <div className="space-y-2">
                        <div className="flex flex-col sm:flex-row gap-2">
                          <input
                            type="text"
                            value={newCompany}
                            onChange={(e) => setNewCompany(e.target.value)}
                            placeholder={
                              trans.placeholders?.previousCompanies ||
                              "Enter company name"
                            }
                            className="flex-1 p-3 border-2 bg-foreground border-muted rounded-lg focus:outline-none focus:border-primary"
                            onKeyPress={(e) =>
                              e.key === "Enter" &&
                              (e.preventDefault(), addCompany())
                            }
                          />
                          <Button
                            type="button"
                            onClick={addCompany}
                            className="px-4 py-3 bg-primary text-black hover:bg-primary/90"
                          >
                            Add
                          </Button>
                        </div>
                        {previousCompanies.length > 0 && (
                          <div className="flex flex-wrap gap-2">
                            {previousCompanies.map((company, index) => (
                              <div
                                key={index}
                                className="flex items-center gap-2 bg-primary/20 text-primary px-3 py-1 rounded-full"
                              >
                                <span className="text-sm">{company}</span>
                                <button
                                  type="button"
                                  onClick={() => removeCompany(company)}
                                  className="text-primary hover:text-red-400"
                                >
                                  ×
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <MultiSelect
                        label={"Journey Preferences"}
                        options={journeyTypes}
                        selected={selectedJourneyTypes}
                        onChange={(values) => {
                          setSelectedJourneyTypes(values);
                          setValue(
                            "preferred_journey_types",
                            values as any,
                            { shouldValidate: true }
                          );
                        }}
                        placeholder={trans.select || "Select..."}
                        minMenuHeight={160}
                      />
                      <input
                        type="hidden"
                        {...register("preferred_journey_types", {
                          validate: () =>
                            selectedJourneyTypes.length > 0
                              ? true
                              : trans.preferredJourneyTypesRequired ||
                                "Please select at least one",
                        })}
                        value={selectedJourneyTypes.join(",")}
                      />
                      {selectedJourneyTypes.length === 0 &&
                        errors.preferred_journey_types && (
                          <p className="text-xs text-error mt-1.5">
                            {
                              (errors.preferred_journey_types
                                .message as any) || ""
                            }
                          </p>
                        )}
                    </div>

                    <div>
                      <MultiSelect
                        label={"Work areas of interest"}
                        options={workAreaOptions}
                        selected={familiarAreas}
                        onChange={(values) => {
                          setFamiliarAreas(values);
                          setValue("familiar_areas", values as any, {
                            shouldValidate: true,
                          });
                        }}
                        placeholder={trans.select || "Select..."}
                        minMenuHeight={180}
                      />
                      <input
                        type="hidden"
                        {...register("familiar_areas", {
                          validate: () =>
                            familiarAreas.length > 0
                              ? true
                              : trans.familiarAreasRequired ||
                                "Please select at least one area",
                        })}
                        value={familiarAreas.join(",")}
                      />
                      {errors.familiar_areas && (
                        <p className="text-xs text-error mt-1.5">
                          {(errors as any).familiar_areas?.message}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Vehicle Information */}
          {currentStep === 3 && (
            <div className="space-y-6">
              <div className="border border-gray-600 p-4 sm:p-6 rounded-xl bg-gradient-to-br from-gray-800/50 to-gray-700/30">
                <h2 className="text-lg sm:text-xl font-bold text-yellow-400 mb-4 sm:mb-6 flex items-center gap-2">
                  <div className="w-8 h-8 bg-yellow-400/20 rounded-full flex items-center justify-center">
                    <span className="text-yellow-400 font-bold">3</span>
                  </div>
                {trans.vehicleInformation || "Vehicle Information"}
                </h2>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <label className="text-sm font-medium mb-1">
                      {trans.vehicleOwnership || "Vehicle Ownership"}{" "}
                      <span className="text-primary">*</span>
                    </label>
                    <select
                      {...register("vehicle_ownership", {
                        required:
                          trans.vehicleOwnershipRequired ||
                          "Please select ownership type",
                      })}
                      className="w-full p-3 border-2 bg-foreground border-muted rounded-lg mt-1 focus:outline-none focus:border-primary"
                    >
                      <option value="">
                        {trans.select || "Select..."}
                      </option>
                      {vehicleOwnershipEnum.options.map((opt) => (
                        <option key={opt} value={opt}>
                          {formatEnumOption(opt)}
                        </option>
                      ))}
                    </select>
                    {errors.vehicle_ownership && (
                      <p className="text-xs text-error mt-1.5">
                        {errors.vehicle_ownership.message}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-1">
                      {trans.vehicleType || "Vehicle Type"}{" "}
                      <span className="text-primary">*</span>
                    </label>
                    <select
                      {...register("vehicle_type", {
                        required:
                          trans.vehicleTypeRequired ||
                          "Please select vehicle type",
                      })}
                      className="w-full p-3 border-2 bg-foreground border-muted rounded-lg mt-1 focus:outline-none focus:border-primary"
                    >
                      <option value="">
                        {trans.select || "Select..."}
                      </option>
                      {vehicleTypeEnum.options.map((opt) => (
                        <option key={opt} value={opt}>
                          {formatEnumOption(opt)}
                        </option>
                      ))}
                    </select>
                    {errors.vehicle_type && (
                      <p className="text-xs text-error mt-1.5">
                        {errors.vehicle_type.message}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-1">
                      {trans.fuelType || "Fuel Type"}{" "}
                      <span className="text-primary">*</span>
                    </label>
                    <select
                      {...register("fuel_type", {
                        required:
                          trans.fuelTypeRequired ||
                          "Please select fuel type",
                      })}
                      className="w-full p-3 border-2 bg-foreground border-muted rounded-lg mt-1 focus:outline-none focus:border-primary"
                    >
                      <option value="">
                        {trans.select || "Select..."}
                      </option>
                      {fuelTypeEnum.options.map((opt) => (
                        <option key={opt} value={opt}>
                          {formatEnumOption(opt)}
                        </option>
                      ))}
                    </select>
                    {errors.fuel_type && (
                      <p className="text-xs text-error mt-1.5">
                        {errors.fuel_type.message}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Preferences & Availability */}
          {currentStep === 4 && (
            <div className="space-y-6">
              <div className="border border-gray-600 p-4 sm:p-6 rounded-xl bg-gradient-to-br from-gray-800/50 to-gray-700/30">
                <h2 className="text-lg sm:text-xl font-bold text-yellow-400 mb-4 sm:mb-6 flex items-center gap-2">
                  <div className="w-8 h-8 bg-yellow-400/20 rounded-full flex items-center justify-center">
                    <span className="text-yellow-400 font-bold">4</span>
                  </div>
                  {trans.preferencesAvailability ||
                    "Preferences & Availability"}
                </h2>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="space-y-4">
                  <h3 className="text-base sm:text-lg font-semibold text-yellow-400 mb-2 sm:mb-3">
                      {trans.appAvailability || "App Availability"}
                    </h3>
                 

                    <div>
                        <label className="text-sm font-medium mb-1">
                          {trans.availability || "Availability"}{" "}
                          <span className="text-primary">*</span>
                        </label>
                      <select
                        {...register("availability", {
                          required:
                            trans.availabilityRequired ||
                            "Please select availability",
                        })}
                        className="w-full p-3 border-2 bg-foreground border-muted rounded-lg mt-1 focus:outline-none focus:border-primary"
                      >
                        <option value="">
                          {trans.select || "Select..."}
                        </option>
                        {availabilityEnum.options.map((opt) => (
                          <option key={opt} value={opt}>
                            {formatEnumOption(opt)}
                          </option>
                        ))}
                      </select>
                      {errors.availability && (
                        <p className="text-xs text-error mt-1.5">
                          {errors.availability.message}
                        </p>
                      )}
                    </div>

                    <div>
                      <label className="text-sm font-medium mb-1">
                        {trans.notificationMethod || "Notification Method"}{" "}
                        <span className="text-primary">*</span>
                      </label>
                      <select
                        {...register("notification_method", {
                          required:
                            trans.notificationMethodRequired ||
                            "Please select notification method",
                        })}
                        className="w-full p-3 border-2 bg-foreground border-muted rounded-lg mt-1 focus:outline-none focus:border-primary"
                      >
                        <option value="">
                          {trans.select || "Select..."}
                        </option>
                        {notificationMethodEnum.options.map((opt) => (
                          <option key={opt} value={opt}>
                            {formatEnumOption(opt)}
                          </option>
                        ))}
                      </select>
                      {errors.notification_method && (
                        <p className="text-xs text-error mt-1.5">
                          {errors.notification_method.message}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h3 className="text-base sm:text-lg font-semibold text-yellow-400 mb-2 sm:mb-3">
                      {trans.complianceSafety || "Compliance & Safety"}
                    </h3>

                    <label className="flex items-start gap-3 cursor-pointer p-3 border border-gray-600 rounded-lg hover:bg-gray-700/30 transition-colors">
                      <input
                        type="checkbox"
                        {...register("has_tfl_licence", {
                          required:
                            trans.hasTflLicenceRequired ||
                            "You must have a TfL licence",
                        })}
                        className="mt-1 w-5 h-5 accent-yellow-400"
                      />
                      <span className="text-sm text-gray-200">
                        {trans.hasTflLicenceText ||
                          "I have a valid TfL (Transport for London) licence"}{" "}
                        <span className="text-yellow-400">*</span>
                      </span>
                    </label>
                    {errors.has_tfl_licence && (
                      <p className="text-xs text-error">
                        {errors.has_tfl_licence.message}
                      </p>
                    )}

                    <label className="flex items-start gap-3 cursor-pointer p-3 border border-gray-600 rounded-lg hover:bg-gray-700/30 transition-colors">
                      <input
                        type="checkbox"
                        {...register("willing_dbs_check", {
                          required:
                            trans.willingDbsCheckRequired ||
                            "DBS check is required",
                        })}
                        className="mt-1 w-5 h-5 accent-yellow-400"
                      />
                      <span className="text-sm text-gray-200">
                        {trans.willingDbsCheckText ||
                          "I am willing to undergo a DBS (Disclosure and Barring Service) check"}{" "}
                        <span className="text-yellow-400">*</span>
                      </span>
                    </label>
                    {errors.willing_dbs_check && (
                      <p className="text-xs text-error">
                        {errors.willing_dbs_check.message}
                      </p>
                    )}

                    <label className="flex items-start gap-3 cursor-pointer p-3 border border-gray-600 rounded-lg hover:bg-gray-700/30 transition-colors">
                      <input
                        type="checkbox"
                        {...register("agrees_policies", {
                          required:
                            trans.agreesPoliciesRequired ||
                            "You must agree to the terms and policies",
                        })}
                        className="mt-1 w-5 h-5 accent-yellow-400"
                      />
                      <span className="text-sm text-gray-200">
                        {trans.agreesPoliciesText ||
                          "I agree to the terms, conditions, and company policies"}{" "}
                        <span className="text-yellow-400">*</span>
                      </span>
                    </label>
                    {errors.agrees_policies && (
                      <p className="text-xs text-error">
                        {errors.agrees_policies.message}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex flex-col sm:flex-row items-center gap-3 sm:gap-4 mt-6 sm:mt-8">
            {currentStep > 1 && (
              <Button
                type="button"
                onClick={goBack}
                variant="secondary"
                className="w-full sm:flex-1 py-3 text-base sm:text-lg font-medium"
              >
                {trans.back || "← Back"}
              </Button>
            )}
            {currentStep < 4 && (
              <Button
                type="button"
                onClick={goNext}
                className="w-full sm:flex-1 py-3 text-base sm:text-lg font-medium bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 transition-all duration-200"
              >
                {trans.next || "Next →"}
              </Button>
            )}
            {currentStep === 4 && (
              <Button
                type="submit"
                className="w-full sm:flex-1 py-3 text-base sm:text-lg font-medium bg-gradient-to-r from-green-600 to-green-500 hover:from-green-700 hover:to-green-600 disabled:opacity-50"
                disabled={loading || mutation.isPending}
              >
                {loading || mutation.isPending ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    {trans.submitting || "Submitting..."}
                  </div>
                ) : (
                  trans.submitApplication || "✓ Submit Application"
                )}
              </Button>
            )}
          </div>

          <p className="text-center text-sm mt-4 text-gray-400 pb-4">
            {trans.alreadyHaveAccount || "Already have an account?"}{" "}
            <span
              onClick={() => setTapAction(1)}
              className="text-yellow-400 px-1 underline cursor-pointer hover:text-yellow-300"
            >
              {trans.login || "Login"}
            </span>
          </p>
        </form>
      </div>
    </>
  );
}
