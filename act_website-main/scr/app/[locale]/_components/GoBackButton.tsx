"use client";

import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { Locale } from "../../../../i18n.config";

export default function GoBackButton({
  locale,
  isRTL,
  label,
}: {
  locale: Locale;
  isRTL: boolean;
  label: string;
}) {
  const router = useRouter();

  const handleGoBack = () => {
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push(`/${locale}`);
    }
  };

  return (
    <Button
      size="lg"
      variant="outline"
      onClick={handleGoBack}
      className="w-full sm:w-auto px-8 py-6 text-lg font-semibold border-2 border-gray-300 dark:border-gray-600 hover:border-primary hover:bg-primary/5 transition-all duration-300 cursor-pointer"
    >
      <ArrowLeft className={`w-5 h-5 ${isRTL ? "ml-2 rotate-180" : "mr-2"}`} />
      {label}
    </Button>
  );
}
