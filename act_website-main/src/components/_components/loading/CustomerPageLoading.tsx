"use client";

import { useParams } from "next/navigation";
import { accountText } from "@/lib/customer-account-text";
import PageLoading from "./PageLoading";

export default function CustomerPageLoading() {
  const params = useParams<{ locale: string }>();
  return <PageLoading message={accountText(params?.locale, "loading")} />;
}
