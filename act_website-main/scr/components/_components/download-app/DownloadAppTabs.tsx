"use client";

import React, { useState, useEffect } from "react";
import { Locale } from "../../../../i18n.config";
import { CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle, FileText } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import DownloadButton from "./DownloadButton";
import { FaDownload } from "react-icons/fa";
import { getInstructionFile } from "@/lib/api/fetchInstructionFile";
import IsLoading from "../ISloading";

type DownloadAppTabsProps = {
  locale: Locale;
  downloadApp: {
    title: string;
    subtitle: string;
    downloading?: string;
    driver: {
      title: string;
      subtitle: string;
      description: string;
      downloadButton: string;
      logoAlt?: string;
      instructions: {
        title: string;
        downloadButton?: string;
        downloadFileName?: string;
        step1: string;
        step2: string;
        step3: string;
        step4: string;
      };
      note: string;
    };
    passenger: {
      title: string;
      subtitle: string;
      description: string;
      downloadButton: string;
      logoAlt?: string;
      instructions: {
        title: string;
        downloadButton?: string;
        downloadFileName?: string;
        step1: string;
        step2: string;
        step3: string;
        step4: string;
      };
      note: string;
    };
  };
};

export default function DownloadAppTabs({ locale, downloadApp }: DownloadAppTabsProps) {
  const isRTL = locale === "ar";
  const [driverFile, setDriverFile] = useState<any>(null);
  const [passengerFile, setPassengerFile] = useState<any>(null);
  const [isLoadingDriver, setIsLoadingDriver] = useState(false);
  const [isLoadingPassenger, setIsLoadingPassenger] = useState(false);

  useEffect(() => {
    // Fetch driver guidelines
    setIsLoadingDriver(true);
    getInstructionFile("DRIVER_GUIDELINES", locale as any)
      .then((file) => {
        if (file) {
          setDriverFile(file);
        }
      })
      .catch(() => {
        // Silently fail, will use fallback
      })
      .finally(() => {
        setIsLoadingDriver(false);
      });

    // Fetch passenger guidelines
    setIsLoadingPassenger(true);
    getInstructionFile("PASSENGER_GUIDELINES", locale as any)
      .then((file) => {
        if (file) {
          setPassengerFile(file);
        }
      })
      .catch(() => {
        // Silently fail, will use fallback
      })
      .finally(() => {
        setIsLoadingPassenger(false);
      });
  }, [locale]);

  return (
    <Tabs defaultValue="driver" className="w-full">
      <CardHeader className="text-center pb-4">
        <TabsList className="grid w-full max-w-md mx-auto grid-cols-2 mb-4">
          <TabsTrigger value="driver" className="text-base font-semibold">
            {downloadApp.driver.title}
          </TabsTrigger>
          <TabsTrigger value="passenger" className="text-base font-semibold">
            {downloadApp.passenger.title}
          </TabsTrigger>
        </TabsList>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Driver App Tab */}
        <TabsContent value="driver" className="space-y-6 mt-0">
          <div className="text-center">
            <CardDescription className="text-base mb-4">
              {downloadApp.driver.description}
            </CardDescription>
          </div>

          {/* App Logo/Image */}
          <div className="flex justify-center">
            <div className="relative w-32 h-32 bg-primary/10 rounded-2xl flex items-center justify-center">
              <Image
                src="/images/logo.png"
                alt={downloadApp.driver.logoAlt || "Driver App"}
                width={128}
                height={128}
                className="object-contain p-4"
              />
            </div>
          </div>

          {/* Download Button */}
          <div className="flex justify-center">
            <DownloadButton 
              downloadText={downloadApp.driver.downloadButton} 
              downloadingText={downloadApp.downloading}
              appType="driver"
            />
          </div>

          {/* Instructions */}
          <div className="mt-8 pt-8 border-t border-gray-200">
            <div className="flex flex-col sm:flex-row items-center sm:items-center sm:justify-between gap-4 mb-6">
              <h2 className="text-2xl font-bold text-black text-center sm:text-left">
                {downloadApp.driver.instructions.title}
              </h2>
              {isLoadingDriver ? (
                <div className="flex items-center gap-2 px-4 py-2">
                  <IsLoading />
                </div>
              ) : (
                <button
                  onClick={() => {
                    const fileUrl = driverFile?.file_url || process.env.NEXT_PUBLIC_INSTRUCTIONS_FILE_URL || "/files/driver-instructions.pdf";
                    const fileName = driverFile?.title 
                      ? `${driverFile.title}.pdf` 
                      : downloadApp.driver.instructions.downloadFileName || "driver-instructions.pdf";
                    const link = document.createElement("a");
                    link.href = fileUrl;
                    link.download = fileName;
                    link.target = "_blank";
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                  }}
                  className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-black font-semibold rounded-lg transition-colors"
                >
                  <FaDownload className="w-4 h-4" />
                  {downloadApp.driver.instructions.downloadButton || "Download Instructions"}
                </button>
              )}
            </div>
            <div className="space-y-4">
              <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex-shrink-0 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center font-bold">
                  1
                </div>
                <p className="text-gray-700 flex-1 pt-1">{downloadApp.driver.instructions.step1}</p>
              </div>
              <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex-shrink-0 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center font-bold">
                  2
                </div>
                <p className="text-gray-700 flex-1 pt-1">{downloadApp.driver.instructions.step2}</p>
              </div>
              <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex-shrink-0 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center font-bold">
                  3
                </div>
                <p className="text-gray-700 flex-1 pt-1">{downloadApp.driver.instructions.step3}</p>
              </div>
              <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex-shrink-0 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center font-bold">
                  4
                </div>
                <p className="text-gray-700 flex-1 pt-1">{downloadApp.driver.instructions.step4}</p>
              </div>
            </div>
          </div>

          {/* Note */}
          <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-yellow-800">{downloadApp.driver.note}</p>
          </div>
        </TabsContent>

        {/* Passenger App Tab */}
        <TabsContent value="passenger" className="space-y-6 mt-0">
          <div className="text-center">
            <CardDescription className="text-base mb-4">
              {downloadApp.passenger.description}
            </CardDescription>
          </div>

          {/* App Logo/Image */}
          <div className="flex justify-center">
            <div className="relative w-32 h-32 bg-primary/10 rounded-2xl flex items-center justify-center">
              <Image
                src="/images/logo.png"
                alt={downloadApp.passenger.logoAlt || "Passenger App"}
                width={128}
                height={128}
                className="object-contain p-4"
              />
            </div>
          </div>

          {/* Download Button */}
          <div className="flex justify-center">
            <DownloadButton 
              downloadText={downloadApp.passenger.downloadButton} 
              downloadingText={downloadApp.downloading}
              appType="passenger"
            />
          </div>

          {/* Instructions */}
          <div className="mt-8 pt-8 border-t border-gray-200">
            <div className="flex flex-col sm:flex-row items-center sm:items-center sm:justify-between gap-4 mb-6">
              <h2 className="text-2xl font-bold text-black text-center sm:text-left">
                {downloadApp.passenger.instructions.title}
              </h2>
              {isLoadingPassenger ? (
                <div className="flex items-center gap-2 px-4 py-2">
                  <IsLoading />
                </div>
              ) : (
                <button
                  onClick={() => {
                    const fileUrl = passengerFile?.file_url || process.env.NEXT_PUBLIC_INSTRUCTIONS_FILE_URL || "/files/passenger-instructions.pdf";
                    const fileName = passengerFile?.title 
                      ? `${passengerFile.title}.pdf` 
                      : downloadApp.passenger.instructions.downloadFileName || "passenger-instructions.pdf";
                    const link = document.createElement("a");
                    link.href = fileUrl;
                    link.download = fileName;
                    link.target = "_blank";
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                  }}
                  className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-black font-semibold rounded-lg transition-colors"
                >
                  <FaDownload className="w-4 h-4" />
                  {downloadApp.passenger.instructions.downloadButton || "Download Instructions"}
                </button>
              )}
            </div>
            <div className="space-y-4">
              <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex-shrink-0 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center font-bold">
                  1
                </div>
                <p className="text-gray-700 flex-1 pt-1">{downloadApp.passenger.instructions.step1}</p>
              </div>
              <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex-shrink-0 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center font-bold">
                  2
                </div>
                <p className="text-gray-700 flex-1 pt-1">{downloadApp.passenger.instructions.step2}</p>
              </div>
              <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex-shrink-0 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center font-bold">
                  3
                </div>
                <p className="text-gray-700 flex-1 pt-1">{downloadApp.passenger.instructions.step3}</p>
              </div>
              <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex-shrink-0 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center font-bold">
                  4
                </div>
                <p className="text-gray-700 flex-1 pt-1">{downloadApp.passenger.instructions.step4}</p>
              </div>
            </div>
          </div>

          {/* Note */}
          <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-yellow-800">{downloadApp.passenger.note}</p>
          </div>
        </TabsContent>

        {/* Back to Home */}
        <div className="flex justify-center mt-8 pt-8 border-t border-gray-200">
          <Link href={`/${locale}`}>
            <Button variant="outline" className="cursor-pointer">
              {isRTL ? "العودة إلى الصفحة الرئيسية" : "Back to Home"}
            </Button>
          </Link>
        </div>
      </CardContent>
    </Tabs>
  );
}

