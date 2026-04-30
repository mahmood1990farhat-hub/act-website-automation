"use client";

import React, { useState, useEffect } from "react";
import { useForm, SubmitHandler } from "react-hook-form";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Locale } from "../../../../i18n.config";
import { fetchData } from "@/lib/api/fetchData";
import { patchData } from "@/lib/api/patchApi";
import { toast } from "react-toastify";
import { Button } from "@/components/ui/button";
import InputField from "../auth/InputField";
import IsLoading from "../ISloading";
import { extract_error } from "@/lib/api/errorApi";

type PricingSettingsData = {
  vat_rate: string;
  minimum_fare: string;
  maximum_distance_miles: string;
  currency: string;
  default_peak_multiplier: string;
  use_dynamic_pricing: boolean;
};

type PricingSettingsProps = {
  trans: any;
  token?: string;
  locale: Locale;
};

type PricingSettingsResponse = {
  success: boolean;
  message: string;
  data: {
    id: number;
    vat_rate: string;
    minimum_fare: string;
    maximum_distance_miles: string;
    currency: string;
    default_peak_multiplier: string;
    use_dynamic_pricing: boolean;
  };
  pagination: null;
};

export default function PricingSettings({
  trans,
  token,
  locale,
}: PricingSettingsProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const queryClient = useQueryClient();

  const {
    data: pricingData,
    isLoading,
    error,
  } = useQuery<PricingSettingsResponse>({
    queryKey: ["pricing-settings", token, locale],
    queryFn: async () => {
      try {
        return await fetchData({
          endpoint: "/api/pricing/settings/",
          token,
          queryParams: {
            locale,
          },
        });
      } catch (err: any) {
        console.error("Failed to fetch pricing settings:", err);
        toast.error(
          extract_error(err) || err?.message || "Failed to load pricing settings"
        );
        throw err;
      }
    },
    enabled: !!token,
    retry: 1,
    refetchOnWindowFocus: false,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PricingSettingsData>({
    defaultValues: {
      vat_rate: "",
      minimum_fare: "",
      maximum_distance_miles: "",
      currency: "EUR",
      default_peak_multiplier: "",
      use_dynamic_pricing: false,
    },
  });

  // Update form when data is loaded
  useEffect(() => {
    if (pricingData?.data) {
      reset({
        vat_rate: pricingData.data.vat_rate || "",
        minimum_fare: pricingData.data.minimum_fare || "",
        maximum_distance_miles: pricingData.data.maximum_distance_miles || "",
        currency: "EUR", // Always EUR, read-only
        default_peak_multiplier: pricingData.data.default_peak_multiplier || "",
        use_dynamic_pricing: pricingData.data.use_dynamic_pricing || false,
      });
    }
  }, [pricingData, reset]);

  const onSubmit: SubmitHandler<PricingSettingsData> = async (data) => {
    setIsSubmitting(true);
    try {
      await patchData<PricingSettingsResponse>({
        endpoint: "/api/pricing/settings/",
        token,
        body: {
          vat_rate: data.vat_rate,
          minimum_fare: data.minimum_fare,
          maximum_distance_miles: data.maximum_distance_miles,
          currency: data.currency,
          default_peak_multiplier: data.default_peak_multiplier,
          use_dynamic_pricing: data.use_dynamic_pricing,
        },
      });

      queryClient.invalidateQueries({ queryKey: ["pricing-settings"] });
      toast.success(
        trans.pricing?.updateSuccess || "Pricing settings updated successfully"
      );
    } catch (error: any) {
      const errorMessage =
        extract_error(error) || error?.message || "Failed to update settings";
      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <IsLoading />
      </div>
    );
  }

  if (error) {
    console.error("Pricing settings error:", error);
    return (
      <div className="bg-card rounded-xl shadow-xl border-2 border-border p-6">
        <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4">
          <p className="text-red-700 font-medium">
            {trans.pricing?.loadError ||
              "Failed to load pricing settings. Please try again."}
          </p>
          {error instanceof Error && (
            <p className="text-red-600 text-sm mt-2">{error.message}</p>
          )}
        </div>
      </div>
    );
  }

  if (!pricingData) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <IsLoading />
      </div>
    );
  }

  return (
    <div>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 md:space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
            {/* VAT Rate */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {trans.pricing?.vatRate || "VAT Rate"}
                <span className="text-red-500 ml-1">*</span>
              </label>
              <input
                type="text"
                {...register("vat_rate", {
                  required: trans.pricing?.vatRateRequired || "VAT rate is required",
                  pattern: {
                    value: /^\d+(\.\d{1,4})?$/,
                    message: trans.pricing?.vatRateInvalid || "Invalid VAT rate format",
                  },
                })}
                placeholder="0.2000"
                className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
              />
              {errors.vat_rate && (
                <p className="text-error text-sm mt-1">{errors.vat_rate.message}</p>
              )}
            </div>

            {/* Minimum Fare */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {trans.pricing?.minimumFare || "Minimum Fare"}
                <span className="text-red-500 ml-1">*</span>
              </label>
              <input
                type="text"
                {...register("minimum_fare", {
                  required: trans.pricing?.minimumFareRequired || "Minimum fare is required",
                  pattern: {
                    value: /^\d+(\.\d{1,2})?$/,
                    message: trans.pricing?.minimumFareInvalid || "Invalid amount format",
                  },
                })}
                placeholder="40.00"
                className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
              />
              {errors.minimum_fare && (
                <p className="text-error text-sm mt-1">{errors.minimum_fare.message}</p>
              )}
            </div>

            {/* Maximum Distance Miles */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {trans.pricing?.maximumDistance || "Maximum Distance (Miles)"}
                <span className="text-red-500 ml-1">*</span>
              </label>
              <input
                type="text"
                {...register("maximum_distance_miles", {
                  required: trans.pricing?.maximumDistanceRequired || "Maximum distance is required",
                  pattern: {
                    value: /^\d+(\.\d{1,2})?$/,
                    message: trans.pricing?.maximumDistanceInvalid || "Invalid distance format",
                  },
                })}
                placeholder="90.00"
                className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
              />
              {errors.maximum_distance_miles && (
                <p className="text-error text-sm mt-1">
                  {errors.maximum_distance_miles.message}
                </p>
              )}
            </div>

            {/* Currency */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {trans.pricing?.currency || "Currency"}
              </label>
              <input
                type="text"
                value="EUR"
                readOnly
                disabled
                className="w-full p-3 border-2 border-border rounded-lg bg-muted text-muted-foreground cursor-not-allowed opacity-60"
              />
              <input
                type="hidden"
                {...register("currency")}
                value="EUR"
              />
            </div>

            {/* Default Peak Multiplier */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {trans.pricing?.peakMultiplier || "Default Peak Multiplier"}
                <span className="text-red-500 ml-1">*</span>
              </label>
              <input
                type="text"
                {...register("default_peak_multiplier", {
                  required:
                    trans.pricing?.peakMultiplierRequired ||
                    "Peak multiplier is required",
                  pattern: {
                    value: /^\d+(\.\d{1,3})?$/,
                    message:
                      trans.pricing?.peakMultiplierInvalid ||
                      "Invalid multiplier format",
                  },
                })}
                placeholder="1.000"
                className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
              />
              {errors.default_peak_multiplier && (
                <p className="text-error text-sm mt-1">
                  {errors.default_peak_multiplier.message}
                </p>
              )}
            </div>

            {/* Use Dynamic Pricing */}
            <div className="flex items-center">
              <label className="flex items-center cursor-pointer group">
                <input
                  type="checkbox"
                  {...register("use_dynamic_pricing")}
                  className="w-5 h-5 text-primary bg-background border-2 border-border rounded focus:ring-2 focus:ring-primary focus:ring-offset-2 cursor-pointer transition-colors"
                />
                <span className="ml-3 text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                  {trans.pricing?.useDynamicPricing || "Use Dynamic Pricing"}
                </span>
              </label>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex justify-end pt-4 border-t-2 border-border">
            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full md:w-auto min-w-[140px] bg-primary hover:bg-primary/90 text-foreground font-semibold shadow-lg shadow-primary/30 transition-all duration-200 disabled:opacity-50"
            >
              {isSubmitting
                ? trans.pricing?.updating || "Updating..."
                : trans.pricing?.updateButton || "Update Settings"}
            </Button>
          </div>
        </form>
    </div>
  );
}
