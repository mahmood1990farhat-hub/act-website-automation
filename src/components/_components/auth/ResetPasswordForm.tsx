"use client";
import { Button } from "@/components/ui/button";
import React, { useState, useEffect, useRef } from "react";
import PasswordField from "./PasswordField";
import { useForm } from "react-hook-form";
import { Locale } from "../../../../i18n.config";
import { postData } from "@/lib/api/postData";
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
    setIsLoading(true);
    try {
      await postData({
        endpoint: "/api/auth/reset-password/",
        body: {
          email: data.email,
          otp_code: data.otp_code,
          new_password: data.new_password,
          confirm_new_password: data.confirm_new_password,
        },
        queryParams: { locale },
      });
      // Navigate back to login
      setTimeout(() => {
        setTap(1); // Login step
      }, 1500);
    } catch (error) {
      console.error("Error:", error);
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
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        <InputField
          label="Email"
          placeholder="your-email@example.com"
          register={register}
          name="email"
          requiredMsg="Email is required"
          error={errors.email}
          type="email"
          icon={<IoMail className="mx-2 text-lg" />}
        />

        <div>
          <label className="block mb-1 text-[16px]">
            OTP Code <span className="text-primary">*</span>
          </label>
          <div className="flex justify-between gap-2 mb-4" dir="ltr">
            {Array.from({ length: 6 }).map((_, idx) => (
              <input
                key={idx}
                type="text"
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
              required: "OTP code is required",
              validate: (value) =>
                value.length === 6 || "Please enter 6-digit OTP code",
            })}
          />
        </div>

        <PasswordField
          label={trans.password || "New Password"}
          name="new_password"
          register={register}
          show={showPassword}
          setShow={setShowPassword}
          validate={{
            required: trans.passwordRequired || "Required",
            minLength: {
              value: 6,
              message: trans.passwordMinLength || "At least 6 characters",
            },
          }}
          error={errors.new_password}
        />

        <PasswordField
          label={trans.confirmPassword || "Confirm New Password"}
          name="confirm_new_password"
          register={register}
          show={showConfirmPassword}
          setShow={setShowConfirmPassword}
          validate={{
            required: trans.passwordRequired || "Required",
            validate: (value: string) =>
              value === password || trans.passwordMismatch || "Passwords do not match",
          }}
          error={errors.confirm_new_password}
        />
        <Button
          type="submit"
          disabled={isLoading}
          className="text-2xl w-full p-6"
        >
          {isLoading ? "Resetting..." : trans.confirmBtn || "Reset Password"}
        </Button>
      </form>
    </div>
  );
}
