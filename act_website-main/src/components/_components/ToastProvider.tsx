"use client";

import { useEffect } from "react";
import { ToastContainer } from "react-toastify";

export default function ToastProvider() {
  useEffect(() => {
    // Ensure toast container is properly mounted and visible
    if (typeof window !== "undefined") {
      // Wait a bit for the container to be rendered
      const checkContainer = () => {
        const container = document.querySelector(".Toastify__toast-container") as HTMLElement;
        if (container) {
          container.style.zIndex = "10000";
          container.style.position = "fixed";
          // Ensure it's visible
          if (container.style.display === "none") {
            container.style.display = "block";
          }
        } else {
          // Retry after a short delay if container not found
          setTimeout(checkContainer, 100);
        }
      };
      checkContainer();
    }
  }, []);

  return (
    <ToastContainer
      position="top-right"
      autoClose={5000}
      hideProgressBar={false}
      newestOnTop
      closeOnClick
      rtl={false}
      pauseOnFocusLoss
      draggable
      pauseOnHover
      theme="light"
      toastStyle={{
        fontSize: "14px",
        color: "white",
        backgroundColor: "#18181A",
        fontWeight: "bold",
      }}
      toastClassName="custom-toast"
      style={{ zIndex: 10000 }}
      containerId="toast-container"
      limit={5}
    />
  );
}
