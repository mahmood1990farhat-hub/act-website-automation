"use client";

import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import { useParams } from "next/navigation";
import { runtimeText } from "@/lib/customer-runtime";
import { useState } from "react";

type AppType = "driver" | "passenger";

export default function DownloadButton({ 
  downloadText, 
  downloadingText,
  appType = "driver" 
}: { 
  downloadText: string;
  downloadingText?: string;
  appType?: AppType;
}) {
  const locale = String(useParams()?.locale || "en");
  const [error, setError] = useState("");
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    const apkPath = appType === "driver" 
      ? "/apps/driver-app.apk" 
      : "/apps/passenger-app.apk";
    const filename = appType === "driver" 
      ? "driver-app.apk" 
      : "passenger-app.apk";
    
    setError("");
    setIsDownloading(true);
    
    try {
      // Use fetch + blob approach for reliable download of large files
      const response = await fetch(apkPath, {
        method: "GET",
        headers: {
          "Content-Type": "application/vnd.android.package-archive",
        },
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch APK: ${response.status} ${response.statusText}`);
      }
      
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = filename;
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Clean up the blob URL after a delay
      setTimeout(() => {
        window.URL.revokeObjectURL(blobUrl);
        setIsDownloading(false);
      }, 100);
    } catch (error) {
      console.error("Error downloading APK:", error);
      setError(runtimeText(locale, "downloadError"));
      setIsDownloading(false);
    }
  };

  return (
    <>
    <Button
      onClick={handleDownload}
      size="lg"
      disabled={isDownloading}
      className="px-8 py-6 text-lg font-semibold cursor-pointer disabled:opacity-60"
    >
      <Download className="w-5 h-5 mr-2" />
      {isDownloading ? downloadingText || downloadText : downloadText}
    </Button>
    {error && <p role="alert" className="mt-3 text-red-400">{error}</p>}
    </>
  );
}

