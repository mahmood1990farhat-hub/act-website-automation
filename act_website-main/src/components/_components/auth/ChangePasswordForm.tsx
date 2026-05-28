"use client";
import { Button } from "@/components/ui/button";
import React, { useState } from "react";
import PasswordField from "./PasswordField";
import { useForm } from "react-hook-form";
import { Locale } from "../../../../i18n.config";
import { postData } from "@/lib/api/postData";
import { getCookie } from "cookies-next";
import { toast } from "react-toastify";

type FormData = {
  old_password: string;
  new_password: string;
  confirm_new_password: string;
};

export default function ChangePasswordForm({
  locale,
  trans,
  onSuccess,
}: {
  locale: Locale;
  trans: any;
  onSuccess?: () => void;
}) {
  const [showOldPassword, setShowOldPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors },
  } = useForm<FormData>();

  const newPassword = watch("new_password");
  const token = getCookie("userToken") as string | undefined;

  const onSubmit = async (data: FormData) => {
    if (!token) {
      toast.error("Please login to change your password");
      return;
    }

    setIsLoading(true);
    try {
      await postData({
        endpoint: "/api/auth/change-password/",
        body: {
          old_password: data.old_password,
          new_password: data.new_password,
          confirm_new_password: data.confirm_new_password,
        },
        token,
        queryParams: { locale },
      });
      reset();
      if (onSuccess) {
        onSuccess();
      }
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full space-y-5">
      <div className="">
        <h1 className="text-lg font-bold text-center py-1">
          {trans.title || "Change Password"}
        </h1>
        <p className="text-sm text-center text-muted px-10">
          {trans.desc || "Enter your current password and new password"}
        </p>
      </div>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        <PasswordField
          label={trans.oldPassword || "Current Password"}
          name="old_password"
          register={register}
          show={showOldPassword}
          setShow={setShowOldPassword}
          validate={{
            required: trans.passwordRequired || "Required",
          }}
          error={errors.old_password}
        />

        <PasswordField
          label={trans.password || "New Password"}
          name="new_password"
          register={register}
          show={showNewPassword}
          setShow={setShowNewPassword}
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
              value === newPassword || trans.passwordMismatch || "Passwords do not match",
          }}
          error={errors.confirm_new_password}
        />
        <Button
          type="submit"
          disabled={isLoading}
          className="text-2xl w-full p-6"
        >
          {isLoading
            ? "Changing..."
            : trans.confirmBtn || trans.changePasswordButton || "Change Password"}
        </Button>
      </form>
    </div>
  );
}

