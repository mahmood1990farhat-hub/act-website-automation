"use client";

import { Suspense } from "react";
import { Locale } from "../../../../i18n.config";
import Earnings from "./Earnings";
import IsLoading from "../ISloading";

type EarningsWrapperProps = {
  trans: any;
  token?: string;
  locale: Locale;
};

export default function EarningsWrapper({
  trans,
  token,
  locale,
}: EarningsWrapperProps) {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center items-center min-h-[400px]">
          <IsLoading />
        </div>
      }
    >
      <Earnings locale={locale} token={token} trans={trans} />
    </Suspense>
  );
}
