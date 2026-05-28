import React from "react";
import { Locale } from "../../../../../i18n.config";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Smartphone, AlertCircle } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import getTrans from "@/lib/translation";
import DownloadAppTabs from "@/components/_components/download-app/DownloadAppTabs";

type PageProps = {
  params: Promise<{ locale: Locale }>;
};

export default async function DownloadAppPage({ params }: PageProps) {
  const locale = (await params).locale;
  const isRTL = locale === "ar";
  const { download_app } = await getTrans(locale, "home");

  return (
    <div className={`min-h-screen bg-gradient-to-br from-gray-50 to-white py-2 md:py-20 ${isRTL ? "rtl" : "ltr"}`}>
      <div className="container mx-auto px-6 max-w-4xl">
        {/* Header Section */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-primary/10 rounded-full mb-6">
            <Smartphone className="w-10 h-10 text-primary" />
          </div>
          
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            {download_app.subtitle}
          </p>
        </div>

        {/* Main Card with Tabs */}
        <Card className="shadow-xl border-0 mb-8">
          <DownloadAppTabs locale={locale} downloadApp={download_app} />
        </Card>
      </div>
    </div>
  );
}

