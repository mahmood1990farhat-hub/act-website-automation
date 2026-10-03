"use client";
import { Button } from "@/components/ui/button";
import React, { useState, useEffect, useRef } from "react";
import PasswordField from "./PasswordField";
import { useForm } from "react-hook-form";
import { Locale } from "../../../../i18n.config";
import { postData } from "@/lib/api/postData";
import { accountText } from "@/lib/customer-account-text";
import InputField from "./InputField";
import { IoMail } from "react-icons/io5";

type FormData = {
  email: string;
  otp_code: string;
  new_password: string;
  confirm_new_password: string;
};

export default function ResetPasswordForm({
  locale,
  trans,
  setTap,
}: {
  locale: Locale;
  setTap: (tep: number) => void;
  trans: any;
}) {
  const t = (key: Parameters<typeof accountText>[1]) => accountText(locale, key);
  const [requestError, setRequestError] = useState("");
  const [success, setSuccess] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [otp, setOtp] = useState<string[]>(["", "", "", "", "", ""]);
  const otpRefs = useRef<(HTMLInputElement | null)[]>([]);
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormData>();

  const password = watch("new_password");
  const email = watch("email");

  useEffect(() => {
    // Get email from sessionStorage (set by forgot password form)
    if (typeof window !== "undefined") {
      const storedEmail = sessionStorage.getItem("resetPasswordEmail");
      if (storedEmail) {
        setValue("email", storedEmail);
      }
    }
  }, [setValue]);

  const handleOtpChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    idx: number
  ) => {
    const value = e.target.value;
    if (!/^\d*$/.test(value)) return;
    const newOtp = [...otp];
    newOtp[idx] = value;
    setOtp(newOtp);
    setValue("otp_code", newOtp.join(""));

    if (value && idx < otp.length - 1) {
      otpRefs.current[idx + 1]?.focus();
    }
  };

  const handleBackspace = (
    e: React.KeyboardEvent<HTMLInputElement>,
    idx: number
  ) => {
    if (e.key === "Backspace" && !otp[idx] && idx > 0) {
      otpRefs.current[idx - 1]?.focus();
    }
  };

  const onSubmit = async (data: FormData) => {
    setRequestError("");
    setSuccess(false);
    setIsLoading(true);
    try {
      await postData({
        endpoint: "/api/auth/reset-password/",
        noToast: true,
        body: {
          email: data.email,
          otp_code: data.otp_code,
          new_password: data.new_password,
          confirm_new_password: data.confirm_new_password,
        },
        queryParams: { locale },
      });
      setSuccess(true);
      // Navigate back to login
      setTimeout(() => {
        setTap(1); // Login step
      }, 1500);
    } catch (error) {
      setRequestError(t("resetFailed"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full space-y-5">
      <div className="">
        <h1 className="text-lg font-bold text-center py-1">{trans.title}</h1>
        <p className="text-sm text-center text-muted px-10">{trans.desc}</p>
      </div>
      {requestError && <p role="alert" className="text-error text-sm">{requestError}</p>}
      {success && <p role="status" className="text-green-400 text-sm">{t("resetSuccess")}</p>}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        <InputField
          label={t("email")}
          placeholder="your-email@example.com"
          register={register}
          name="email"
          requiredMsg={t("emailRequired")}
          error={errors.email}
          type="email"
          icon={<IoMail className="mx-2 text-lg" />}
        />

        <div>
          <label className="block mb-1 text-[16px]">
            {t("otp")} <span className="text-primary">*</span>
          </label>
          <div className="flex justify-between gap-2 mb-4" dir="ltr">
            {Array.from({ length: 6 }).map((_, idx) => (
              <input
                key={idx}
                type="text"
                aria-label={t("otpDigit").replace("{number}", String(idx + 1))}
                inputMode="numeric"
                maxLength={1}
                className="w-12 h-12 text-center text-xl border-2 border-muted rounded-lg bg-foreground focus:ring-2 focus:ring-primary focus:border-primary"
                value={otp[idx] || ""}
                onChange={(e) => handleOtpChange(e, idx)}
                onKeyDown={(e) => handleBackspace(e, idx)}
                ref={(el) => {
                  if (el) otpRefs.current[idx] = el;
                }}
              />
            ))}
          </div>
          {errors.otp_code && (
            <p className="text-error text-sm">{errors.otp_code.message}</p>
          )}
          <input
            type="hidden"
            {...register("otp_code", {
              required: t("otpRequired"),
              validate: (value) =>
                value.length === 6 || t("otpLength"),
            })}
          />
        </div>

        <PasswordField
          label={t("newPassword")}
          name="new_password"
          register={register}
          show={showPassword}
          setShow={setShowPassword}
          validate={{
            required: t("passwordRequired"),
            minLength: {
              value: 6,
              message: t("passwordMinLength"),
            },
          }}
          error={errors.new_password}
        />

        <PasswordField
          label={t("confirmPassword")}
          name="confirm_new_password"
          register={register}
          show={showConfirmPassword}
          setShow={setShowConfirmPassword}
          validate={{
            required: t("passwordRequired"),
            validate: (value: string) =>
              value === password || t("passwordMismatch"),
          }}
          error={errors.confirm_new_password}
        />
        <Button
          type="submit"
          disabled={isLoading}
          className="text-2xl w-full p-6"
        >
          {isLoading ? t("resetting") : t("resetPassword")}
        </Button>
      </form>
    </div>
  );
}
