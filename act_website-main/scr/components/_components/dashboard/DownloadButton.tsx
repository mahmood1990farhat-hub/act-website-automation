"use client";

import { FaDownload } from "react-icons/fa";

export default function DownloadButton() {
  const downloadFile = async () => {
const proxyUrl = "https://cors-anywhere.herokuapp.com/";
const url = "https://airportandcitytransfer.com/media/driver_docs/pco/Screenshot_from_2025-07-21_09-47-02_mDYgCRo.png";
    try {
const response = await fetch(proxyUrl + url);
      if (!response.ok) throw new Error("Failed to fetch file");

      const blob = await response.blob();
      const link = document.createElement("a");
      link.href = window.URL.createObjectURL(blob);
      link.download = "Screenshot.png";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(link.href); // تنظيف ال URL بعد التحميل
    } catch (error) {
      console.error("Download failed", error);
    }
  };

  return (
    <button
      onClick={downloadFile}
      className="inline-flex items-center gap-2 text-primary font-medium hover:underline"
    >
      <FaDownload />
      تحميل الصورة
    </button>
  );
}
